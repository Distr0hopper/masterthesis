import asyncio
import json
import logging
import subprocess
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("app.infrastructure.packaging.packaging_cli")


async def run_packaging_cli(repo_url: str, output_dir: Path) -> None:
    settings = get_settings()
    args = [repo_url, "--output-dir", str(output_dir)]
    if settings.github_token:
        args.extend(["--github-token", settings.github_token])

    logger.info(f"Running: {settings.packaging_executable} {' '.join(args)}")
    # FileNotFoundError (executable missing/misconfigured) is intentionally left
    # uncaught here - that's a deployment/config problem, not a normal failure mode
    process = await asyncio.create_subprocess_exec(
        settings.packaging_executable,
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        # never include the raw args in the exception - they may contain the github token,
        # and CalledProcessError's default __str__ prints .cmd verbatim (e.g. in logs)
        safe_cmd = [settings.packaging_executable, repo_url, "--output-dir", str(output_dir)]
        raise subprocess.CalledProcessError(process.returncode, safe_cmd, stderr=stderr)


def read_packaging_output(output_dir: Path, repo_name: str) -> tuple[str, str | None, str | None, str | None]:
    # a missing/malformed file here means the CLI exited 0 but didn't actually
    # produce valid output - a genuine bug in the CLI or its config, not a normal
    # failure mode, so FileNotFoundError/JSONDecodeError are left uncaught
    cwl_content = (output_dir / f"{repo_name}.cwl").read_text()
    metadata = json.loads((output_dir / "metadata.json").read_text())
    return cwl_content, metadata.get("commitSha"), metadata.get("description"), metadata.get("author")