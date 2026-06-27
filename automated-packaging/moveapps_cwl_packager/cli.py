"""CLI entry point for moveapps-cwl-package."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from .generators import (
    generate_build_sh,
    generate_cwl,
    generate_dockerfile,
    generate_inputs_yaml,
)
from .github import GitHubClient, RepoContents

_DEFAULT_WRAPPER_IMAGE = "moveapps-r-wrapper:latest"


def _parse_github_url(url: str) -> tuple[str, str]:
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip()
    )
    if not m:
        raise argparse.ArgumentTypeError(
            f"Not a valid GitHub repository URL: {url!r}\n"
            "Expected format: https://github.com/<owner>/<repo>"
        )
    return m.group(1), m.group(2)


def _repo_name_to_image(repo_name: str) -> str:
    return repo_name.lower().replace("_", "-")


def _print_section(title: str, content: str) -> None:
    bar = "─" * 60
    print(f"\n{bar}\n  {title}\n{bar}")
    print(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="moveapps-cwl-package",
        description="Automatically package a MoveApps R app as a CWL CommandLineTool.",
    )
    parser.add_argument(
        "repo_url",
        metavar="<github-repo-url>",
        help="Full GitHub URL of the MoveApps R app, e.g. https://github.com/movestore/RemoveOutliers",
    )
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        default=None,
        help="Directory for generated artifacts (default: ./<repo-name>/)",
    )
    parser.add_argument(
        "--wrapper-image",
        metavar="IMAGE",
        default=_DEFAULT_WRAPPER_IMAGE,
        help=f"Pre-built CWL wrapper image to extend (default: {_DEFAULT_WRAPPER_IMAGE}). "
             "Build it once with build-sdk.sh.",
    )
    parser.add_argument(
        "--docker-registry",
        metavar="REGISTRY",
        default="moveapps",
        help="Docker registry prefix for the CWL dockerPull image name (default: moveapps). "
             "Pass empty string for local-only images.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated without writing any files.",
    )
    parser.add_argument(
        "--github-token",
        metavar="TOKEN",
        default=None,
        help="GitHub personal access token (also read from GITHUB_TOKEN env var).",
    )

    args = parser.parse_args(argv)

    try:
        owner, repo_name = _parse_github_url(args.repo_url)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    app_name = _repo_name_to_image(repo_name)
    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path("generated") / repo_name
    )

    print(f"Fetching repository: {owner}/{repo_name}")

    client = GitHubClient(token=args.github_token)
    try:
        contents = client.fetch_repo(owner, repo_name)
    except Exception as exc:
        print(f"ERROR: Could not fetch repository — {exc}", file=sys.stderr)
        return 1

    appspec_settings = contents.appspec.get("settings", [])
    r_packages = [d["name"] for d in contents.appspec.get("dependencies", {}).get("R", [])]

    # Generate artifacts
    dockerfile = generate_dockerfile(args.wrapper_image, r_packages or None)
    build_sh = generate_build_sh(app_name, args.docker_registry)
    cwl_text = generate_cwl(app_name, appspec_settings, args.docker_registry)
    app_config_dict = json.loads(contents.app_config.content)
    inputs_yaml = generate_inputs_yaml(appspec_settings, app_config_dict)

    # ── Dry-run ───────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[DRY RUN — no files written]\n")
        _print_section(f"Dockerfile  →  {out_dir}/Dockerfile", dockerfile)
        _print_section(f"build.sh  →  {out_dir}/build.sh", build_sh)
        _print_section(f"{repo_name}.cwl  →  {out_dir}/{repo_name}.cwl", cwl_text)
        _print_section(f"inputs.yaml  →  {out_dir}/inputs.yaml", inputs_yaml)
        _print_summary(repo_name, app_name, appspec_settings, args.wrapper_image, out_dir, dry=True)
        return 0

    # ── Write files ──────────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)

    _write(out_dir / "RFunction.R", contents.rfunction.content)
    _write(out_dir / "app-configuration.json", contents.app_config.content)
    _write(out_dir / "Dockerfile", dockerfile)
    _write(out_dir / f"{repo_name}.cwl", cwl_text)
    _write(out_dir / "inputs.yaml", inputs_yaml)
    _write(out_dir / "build.sh", build_sh)

    os.chmod(out_dir / "build.sh", 0o755)

    _print_summary(repo_name, app_name, appspec_settings, args.wrapper_image, out_dir, dry=False)
    return 0


def _write(path: Path, content: bytes | str) -> None:
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _print_summary(
    repo_name: str,
    app_name: str,
    settings: list[dict],
    wrapper_image: str,
    out_dir: Path,
    *,
    dry: bool,
) -> None:
    action = "Would write" if dry else "Written"
    print(f"\n{'─'*60}")
    print(f"  Summary — {repo_name}")
    print(f"{'─'*60}")
    print(f"  Output directory : {out_dir}/")
    print(f"  Wrapper image    : {wrapper_image}")

    print(f"\n  {action}:")
    for f in ["RFunction.R", "app-configuration.json", "Dockerfile",
              f"{repo_name}.cwl", "inputs.yaml", "build.sh"]:
        print(f"    {out_dir}/{f}")

    print(f"\n  Detected parameters ({len(settings)}):")
    if settings:
        for s in settings:
            default = s.get("defaultValue")
            opt = f"  [default: {default!r}]" if default is not None else "  [required]"
            print(f"    {s['id']:30s}  {s.get('type', '?'):12s}{opt}")
    else:
        print("    (none)")

    if not dry:
        print(f"\n  To build:  cd {out_dir} && bash build.sh")
    print()
