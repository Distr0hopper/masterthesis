#!/usr/bin/env python3
"""Evaluate the MoveApps CWL packager against every repository of the movestore organisation.

For each repository of https://github.com/movestore the script determines how far it gets:

  1. discover   list all repositories of the organisation (GitHub REST API)
  2. classify   decide from the files in the repository what it is; only R function apps
                (appspec.json-based apps with an RFunction.R) are in scope of the packager,
                templates, Shiny apps, Python apps and repositories without an app are excluded
  3. package    generate the CWL CommandLineTool with the packager (package_repo)
  4. build      build the per-app Docker image from the dockerFile embedded in the CWL
  5. run        execute the CWL with cwltool on a test dataset (move2 object), every setting
                at its appspec.json default; the run succeeds when cwltool exits with 0,
                which requires the app to have written output.rds

Apps with a file setting (USER_FILE/LOCAL_FILE) run like every other app, but without the
file: the packager cannot pass one in yet, so they are marked and reported separately.

Every app ends in exactly one status, so the counts form a funnel. Results are appended to
results.jsonl as they come in (an interrupted run continues with --resume) and summarised in
results.csv and summary.md.

Requirements: the packager installed (pip install -e .), Docker, cwltool, and a GitHub token
in GITHUB_TOKEN (packaging makes ~5 API calls per app, unauthenticated GitHub allows 60/h).

Usage:
    python evaluation/evaluate_movestore.py --input input-files/input1.rds
    python evaluation/evaluate_movestore.py --only RemoveOutliers --only Geofence
    python evaluation/evaluate_movestore.py --resume --jobs 2
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from moveapps_cwl_packager.packager import (
    DEFAULT_WRAPPER_IMAGE,
    GitHubUnavailableError,
    PackagingError,
    package_repo,
)

ORG = "movestore"
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

# classification of a repository, decided by the files at the root of its default branch
TEMPLATE = "template"
R_FUNCTION_APP = "r_function_app"
R_SHINY_APP = "r_shiny_app"
PYTHON_APP = "python_app"
NO_APP = "no_app"

# settings whose value is a file the user uploads on MoveApps; the packager maps them to a
# string, so the file cannot be passed in yet - apps with one are reported separately
FILE_SETTING_TYPES = {"USER_FILE", "LOCAL_FILE"}

# final status of an app; the order is the funnel
STATUSES = [
    "excluded",
    "package_failed",
    "build_failed",
    "build_timeout",
    "run_failed",
    "run_timeout",
    "success",
]


@dataclass
class Result:
    repo: str
    url: str
    category: str
    archived: bool
    fork: bool
    status: str = "excluded"
    commit_sha: str = ""
    settings: int = 0
    settings_without_default: int = 0
    file_settings: str = ""  # "id (TYPE)" of every FILE_SETTING_TYPES setting, comma-separated
    package_seconds: float = 0.0
    build_seconds: float = 0.0
    run_seconds: float = 0.0
    error: str = ""
    finished_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# 1 + 2: discover and classify
# ---------------------------------------------------------------------------


def github_session(token: str | None) -> requests.Session:
    session = requests.Session()
    # a dropped connection or a 5xx from GitHub is retried instead of ending up in the results
    retry = Retry(total=5, backoff_factor=2, status_forcelist=(500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["Accept"] = "application/vnd.github+json"
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def list_repositories(session: requests.Session) -> list[dict]:
    repos, page = [], 1
    while True:
        resp = session.get(
            f"{API}/orgs/{ORG}/repos",
            params={"type": "all", "per_page": 100, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            return sorted(repos, key=lambda r: r["name"].lower())
        repos += batch
        page += 1


def file_exists(session: requests.Session, repo: dict, path: str) -> bool:
    # raw.githubusercontent.com does not count against the API rate limit
    url = f"{RAW}/{ORG}/{repo['name']}/{repo['default_branch']}/{path}"
    return session.head(url, timeout=30, allow_redirects=True).status_code == 200


def classify(session: requests.Session, repo: dict) -> str:
    if repo["is_template"]:
        return TEMPLATE
    if file_exists(session, repo, "RFunction.R"):
        return R_FUNCTION_APP
    if file_exists(session, repo, "ShinyModule.R"):
        return R_SHINY_APP
    if file_exists(session, repo, "app/app.py"):
        return PYTHON_APP
    return NO_APP


# ---------------------------------------------------------------------------
# 3 - 5: package, build, run
# ---------------------------------------------------------------------------


def tail(text: str, lines: int = 15, chars: int = 1500) -> str:
    relevant = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(relevant[-lines:])[-chars:]


def run_logged(cmd: list[str], log: Path, timeout: int, stdin: str | None = None) -> int:
    """Runs cmd with stdout+stderr written to log; raises TimeoutExpired."""
    with log.open("w") as fh:
        proc = subprocess.run(
            cmd, input=stdin, stdout=fh, stderr=subprocess.STDOUT, text=True, timeout=timeout
        )
    return proc.returncode


def is_r_error(line: str) -> bool:
    # R prints "Error in <call> : ..." or "Error: ..."; cwltool's own "Error collecting output" is no R error
    return line.startswith(("Error in ", "Error: "))


def run_error(app_dir: Path, run_log: Path) -> str:
    """The R error: from error.log if the SDK wrote one (in the kept job dir), else the last
    R error in the cwltool log (e.g. a library() call failing before the SDK took over),
    else the end of the cwltool log."""
    for error_log in app_dir.glob("tmp/**/error.log"):
        text = error_log.read_text(errors="replace")
        if text.strip():
            return tail(text)
    log_lines = run_log.read_text(errors="replace").splitlines()
    r_errors = [i for i, line in enumerate(log_lines) if is_r_error(line)]
    if r_errors:
        return tail("\n".join(log_lines[r_errors[-1]:r_errors[-1] + 3]))
    # cwltool failed on a JavaScript expression of the generated CWL before the container started
    js_errors = [line for line in log_lines if line.startswith("SyntaxError")]
    if js_errors:
        return f"Error: CWL expression failed - {js_errors[0]}"
    return tail("\n".join(log_lines))


def build_error(build_log: Path) -> str:
    """The packager's own message naming the R packages that could not be installed, else the
    end of the docker build log."""
    text = build_log.read_text(errors="replace")
    # the R output line, not the echoed RUN command that contains the same words
    missing = re.findall(r"R packages could not be installed: ([\w.]+(?:, [\w.]+)*)\s*$", text, re.MULTILINE)
    if missing:
        return f"Error: R packages could not be installed: {missing[-1]}"
    return tail(text)


def package_with_retry(args: argparse.Namespace, url: str, attempts: int = 4):
    """package_repo, retried when GitHub is unreachable: that is no property of the app, so
    after the last attempt the error propagates and the app is left for --resume."""
    for attempt in range(1, attempts + 1):
        try:
            return package_repo(url, args.wrapper_image, args.github_token)
        except GitHubUnavailableError:
            if attempt == attempts:
                raise
            time.sleep(15 * attempt)


def evaluate_app(result: Result, args: argparse.Namespace) -> Result:
    app_dir = args.out / "apps" / result.repo
    shutil.rmtree(app_dir, ignore_errors=True)
    app_dir.mkdir(parents=True)

    # 3. package
    start = time.monotonic()
    try:
        packaged = package_with_retry(args, result.url)
    except GitHubUnavailableError:
        raise
    except PackagingError as exc:
        result.status, result.error = "package_failed", f"{type(exc).__name__}: {exc}"
        return result
    finally:
        result.package_seconds = round(time.monotonic() - start, 1)

    result.commit_sha = packaged.commit_sha
    result.settings = len(packaged.settings)
    result.settings_without_default = sum(
        1 for s in packaged.settings if s.get("defaultValue") in (None, "")
    )
    result.file_settings = ", ".join(
        f"{s['id']} ({s['type']})"
        for s in packaged.settings
        if str(s.get("type", "")).upper() in FILE_SETTING_TYPES
    )
    cwl_path = app_dir / f"{result.repo}.cwl"
    cwl_path.write_text(packaged.cwl)
    # only the input file: every setting falls back to its CWL default (the appspec.json
    # defaultValue), a setting without one stays null - exactly the generated inputs.yaml
    job_path = app_dir / "job.yaml"
    job_path.write_text(yaml.safe_dump({"input_rds": {"class": "File", "path": str(args.input)}}))

    # 4. build - cwltool would build the image itself; building it beforehand separates
    # build failures (e.g. an R package that no longer installs) from failures of the app
    docker = yaml.safe_load(packaged.cwl)["requirements"]["DockerRequirement"]
    image = docker["dockerImageId"]
    start = time.monotonic()
    try:
        code = run_logged(
            ["docker", "build", "--platform", "linux/amd64", "--tag", image, "-"],
            app_dir / "build.log",
            args.build_timeout,
            stdin=docker["dockerFile"],
        )
    except subprocess.TimeoutExpired:
        result.status = "build_timeout"
        return result
    finally:
        result.build_seconds = round(time.monotonic() - start, 1)
    if code != 0:
        result.status = "build_failed"
        result.error = build_error(app_dir / "build.log")
        return result

    # 5. run
    run_log = app_dir / "run.log"
    start = time.monotonic()
    try:
        code = run_logged(
            [
                args.cwltool,
                "--outdir", str(app_dir / "out"),
                "--tmpdir-prefix", f"{app_dir}/tmp/",
                "--tmp-outdir-prefix", f"{app_dir}/tmp/",
                "--leave-tmpdir",  # keeps error.log of a failed run
                str(cwl_path),
                str(job_path),
            ],
            run_log,
            args.run_timeout,
        )
    except subprocess.TimeoutExpired:
        result.status = "run_timeout"
        return result
    finally:
        result.run_seconds = round(time.monotonic() - start, 1)
        if not args.keep_images:
            subprocess.run(["docker", "rmi", "--force", image], capture_output=True)

    if code == 0 and (app_dir / "out" / "output.rds").exists():
        result.status = "success"
        shutil.rmtree(app_dir / "tmp", ignore_errors=True)
    else:
        result.status = "run_failed"
        result.error = run_error(app_dir, run_log)
    return result


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------


def load_results(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = (json.loads(line) for line in path.read_text().splitlines() if line.strip())
    return {row["repo"]: row for row in rows}


def write_reports(out: Path, results: list[dict], input_file: Path, wrapper_image: str) -> str:
    results = sorted(results, key=lambda r: r["repo"].lower())
    with (out / "results.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(Result.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(results)

    def count(predicate) -> int:
        return sum(1 for r in results if predicate(r))

    apps = [r for r in results if r["category"] == R_FUNCTION_APP]
    n_apps = len(apps)

    def pct(n: int) -> str:
        return f"{100 * n / n_apps:.1f} %" if n_apps else "-"

    packaged = count(lambda r: r["category"] == R_FUNCTION_APP and r["status"] != "package_failed")
    built = count(lambda r: r["status"] in ("run_failed", "run_timeout", "success"))
    ran = count(lambda r: r["status"] == "success")

    lines = [
        f"# Evaluation of the MoveApps CWL packager on github.com/{ORG}",
        "",
        f"- date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- wrapper image: `{wrapper_image}`",
        f"- test input: `{input_file.name}`",
        "",
        "## Repositories",
        "",
        "| Category | Repositories | of which archived | of which forks |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category in (R_FUNCTION_APP, R_SHINY_APP, PYTHON_APP, TEMPLATE, NO_APP):
        rows = [r for r in results if r["category"] == category]
        lines.append(
            f"| {category} | {len(rows)} | {sum(r['archived'] for r in rows)} | "
            f"{sum(r['fork'] for r in rows)} |"
        )
    lines += [
        f"| **total** | **{len(results)}** | | |",
        "",
        "## Funnel (R function apps)",
        "",
        "| Stage | Apps | Share |",
        "| --- | ---: | ---: |",
        f"| in scope | {n_apps} | {pct(n_apps)} |",
        f"| packaged (CWL generated) | {packaged} | {pct(packaged)} |",
        f"| image built | {built} | {pct(built)} |",
        f"| ran successfully | {ran} | {pct(ran)} |",
        "",
        "## Final status",
        "",
        "Apps with file settings (USER_FILE/LOCAL_FILE) cannot get their file passed in yet.",
        "",
        "| Status | Apps | of which with file settings |",
        "| --- | ---: | ---: |",
    ]
    for status in STATUSES[1:]:
        rows = [r for r in apps if r["status"] == status]
        with_files = sum(1 for r in rows if r.get("file_settings"))
        lines.append(f"| {status} | {len(rows)} | {with_files} |")
    lines += ["", "## Failures", ""]
    for r in apps:
        if r["status"] != "success":
            error_lines = r["error"].splitlines() or [""]
            r_errors = [line for line in error_lines if is_r_error(line)]
            first_line = (r_errors or error_lines)[-1][:200]
            files = f" [file settings: {r['file_settings']}]" if r.get("file_settings") else ""
            lines.append(f"- **{r['repo']}** ({r['status']}){files}: `{first_line}`")

    summary = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(summary)
    return summary


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input", type=Path, default=here.parent / "input-files" / "input1.rds",
                        help="test dataset passed as input_rds (default: input-files/input1.rds)")
    parser.add_argument("--out", type=Path, default=here / "output",
                        help="directory for logs and reports (default: evaluation/output)")
    parser.add_argument("--only", action="append", metavar="REPO",
                        help="evaluate only this repository (repeatable)")
    parser.add_argument("--resume", action="store_true",
                        help="skip repositories already in results.jsonl")
    parser.add_argument("--jobs", type=int, default=1, help="apps evaluated in parallel")
    parser.add_argument("--build-timeout", type=int, default=3600, help="seconds per image build")
    parser.add_argument("--run-timeout", type=int, default=1800, help="seconds per cwltool run")
    parser.add_argument("--wrapper-image", default=DEFAULT_WRAPPER_IMAGE)
    parser.add_argument("--cwltool", default=shutil.which("cwltool") or "cwltool")
    parser.add_argument("--keep-images", action="store_true",
                        help="keep the per-app images (default: removed after the run)")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN"))
    args = parser.parse_args(argv)
    args.input = args.input.resolve()
    args.out = args.out.resolve()
    if not args.input.is_file():
        parser.error(f"test input not found: {args.input}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    session = github_session(args.github_token)

    limit = session.get(f"{API}/rate_limit", timeout=30)
    if limit.status_code == 401:
        print("GITHUB_TOKEN is invalid (401 from GitHub)", file=sys.stderr)
        return 1
    remaining = limit.json()["resources"]["core"]["remaining"]
    print(f"GitHub API requests remaining: {remaining}")

    repos = list_repositories(session)
    print(f"{len(repos)} repositories in github.com/{ORG}")
    if args.only:
        repos = [r for r in repos if r["name"] in args.only]

    results_path = args.out / "results.jsonl"
    done = load_results(results_path) if args.resume else {}
    if not args.resume:
        results_path.unlink(missing_ok=True)
    todo = [r for r in repos if r["name"] not in done]
    write_lock = threading.Lock()

    def evaluate(repo: dict) -> None:
        try:
            result = Result(
                repo=repo["name"],
                url=repo["html_url"],
                category=classify(session, repo),
                archived=repo["archived"],
                fork=repo["fork"],
            )
            if result.category == R_FUNCTION_APP:
                result = evaluate_app(result, args)
        except Exception as exc:
            # a failure of the harness or the network says nothing about the app: it is not
            # recorded, so --resume evaluates the app again, and the other apps go on
            print(f"[ harness error] {repo['name']}: {exc!r} - rerun with --resume", flush=True)
            return
        result.finished_at = datetime.now(timezone.utc).isoformat()
        with write_lock:
            with results_path.open("a") as fh:
                fh.write(json.dumps(asdict(result)) + "\n")
            print(f"[{result.status:>14}] {result.repo} ({result.category})", flush=True)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(evaluate, todo))

    summary = write_reports(
        args.out, list(load_results(results_path).values()), args.input, args.wrapper_image
    )
    print("\n" + summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
