"""CLI entry point for moveapps-cwl-package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .packager import (
    DEFAULT_WRAPPER_IMAGE,
    InvalidRepoUrlError,
    PackagingError,
    package_repo,
    parse_github_url,
    repo_name_to_image,
)


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
        help="Directory for generated artifacts (default: ./generated/<repo-name>/)",
    )
    parser.add_argument(
        "--wrapper-image",
        metavar="IMAGE",
        default=DEFAULT_WRAPPER_IMAGE,
        help=f"Pre-built SDK base image to extend (default: {DEFAULT_WRAPPER_IMAGE}). "
             "Build it once with build-sdk.sh.",
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
        owner, repo_name = parse_github_url(args.repo_url)
    except InvalidRepoUrlError as exc:
        parser.error(str(exc))

    app_name = repo_name_to_image(repo_name)
    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path("generated") / repo_name
    )

    print(f"Fetching repository: {owner}/{repo_name}")

    try:
        result = package_repo(args.repo_url, args.wrapper_image, args.github_token)
    except PackagingError as exc:
        print(f"ERROR: Could not package repository — {exc}", file=sys.stderr)
        return 1

    cwl_text = result.cwl
    inputs_yaml = result.inputs_yaml
    appspec_settings = result.settings

    # ── Dry-run ───────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[DRY RUN — no files written]\n")
        _print_section(f"{repo_name}.cwl  →  {out_dir}/{repo_name}.cwl", cwl_text)
        _print_section(f"inputs.yaml  →  {out_dir}/inputs.yaml", inputs_yaml)
        _print_summary(repo_name, app_name, appspec_settings, args.wrapper_image, out_dir, dry=True)
        return 0

    # ── Write files ──────────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)

    _write(out_dir / f"{repo_name}.cwl", cwl_text)
    _write(out_dir / "inputs.yaml", inputs_yaml)
    _write(
        out_dir / "metadata.json",
        json.dumps({
            "commitSha": result.commit_sha,
            "description": result.description,
            "author": result.author,
        }),
    )

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
    for f in [f"{repo_name}.cwl", "inputs.yaml"]:
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
        print(f"\n  To run:  cwltool {out_dir}/{repo_name}.cwl {out_dir}/inputs.yaml")
    print()