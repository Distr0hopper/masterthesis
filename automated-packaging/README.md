# MoveApps CWL Packager

Automatically packages MoveApps R apps from GitHub as CWL v1.2 `CommandLineTool` descriptors, ready to run locally with `cwltool`.

---

## How it works — big picture

Running a MoveApps R app via CWL requires three things:

1. A **Docker image** with the full R environment and the app's code
2. A **CWL descriptor** (`.cwl`) that tells cwltool how to invoke the image
3. An **inputs file** (`inputs.yaml`) that provides the concrete parameter values for one run

This framework automates producing all three. The core idea is a two-layer Docker setup:

```
moveapps-r-wrapper:latest          ← shared base, built once with build-sdk.sh
       │
       └── <app-name>:latest       ← per-app image, built with the generated build.sh
```

The shared wrapper image contains everything that is identical across all apps (R packages, SDK runtime files, the CWL entry point script). The per-app image just adds the two files that differ between apps: `RFunction.R` and `app-configuration.json`.

---

## File overview

### Repo-level files (run once)

| File | Purpose |
|---|---|
| `build-sdk.sh` | Builds the shared `moveapps-r-wrapper:latest` image |
| `Dockerfile.sdk` | Defines that image |
| `cwl-wrapper.sh` | Runtime entry point baked into the wrapper image |
| `moveapps_cwl_packager/` | Python CLI that generates per-app artifacts |

### Generated per-app files (one folder per app)

| File | Purpose |
|---|---|
| `Dockerfile` | Extends the wrapper image with this app's files |
| `build.sh` | Runs `docker build` for this app |
| `<app>.cwl` | CWL CommandLineTool descriptor |
| `inputs.yaml` | Parameter values for one run — **edit this before running** |
| `RFunction.R` | The app's R code, fetched from GitHub |
| `app-configuration.json` | App parameter config, fetched from GitHub (baked into image as fallback) |

---

## The shared wrapper image in detail

`Dockerfile.sdk` builds the image in these layers (top to bottom = slow to fast):

1. **`rocker/geospatial:4.5.1`** — Ubuntu + R + geospatial system libraries
2. **Create `moveapps` user** — non-root user that runs the app
3. **`renv::restore()`** — restores all R packages from `movestore/Template_R_Function_App`'s `renv.lock` (the slow step, ~minutes)
4. **Copy SDK runtime files** — `sdk.R`, `start-process.sh`, `.env` from the template repo
5. **Copy `cwl-wrapper.sh`** — the CWL entry point script

Because Docker caches layers, only changing `cwl-wrapper.sh` re-executes just step 5 — the expensive `renv::restore()` stays cached.

### What `cwl-wrapper.sh` does at runtime

This script runs inside the container each time cwltool invokes the tool. It:

1. Reads `app-configuration.json` from the CWL working directory (written by the CWL's JS expression from `inputs.yaml`) — falls back to the image's baked-in copy if not found
2. Symlinks `RFunction.R`, `start-process.sh`, and `src/` from their fixed locations inside the image into the writable working directory
3. Patches `sdk.R` with `sed` to strip the `remotes::install_github()` call — this call is unnecessary (the package is already installed via `renv`) and fails because cwltool runs containers with `--net=none`
4. Writes a `.env` file pointing to all input/output paths
5. Runs `bash start-process.sh`, which sources `sdk.R`, which reads the config and calls `rFunction()`

---

## How parameters flow from inputs.yaml into R

```
appspec.json (on GitHub)
    └── settings[].id          ← becomes the CWL input name AND the JSON key
            │
            ▼
        inputs.yaml            ← user provides values here
            │
            ▼
   CWL JS expression           ← writes app-configuration.json at runtime
   (InitialWorkDirRequirement)    {"maxspeed": 20.0, "MBremove": true, ...}
            │
            ▼
        sdk.R                  ← reads app-configuration.json
            │
            ▼
    do.call(rFunction, config) ← named args match rFunction parameters
```

The CWL parameter names come directly from `appspec.json`'s `settings[].id` fields, which for MoveApps apps are identical to the `rFunction` argument names. This means the JSON written at runtime has the correct keys for R without any name mapping.

---

## Setup

### 1. Install the CLI

```bash
cd automated-packaging
pip install -e .
```

### 2. Build the shared wrapper image (once)

```bash
bash build-sdk.sh
```

This fetches the template R environment from `movestore/Template_R_Function_App` on GitHub and builds `moveapps-r-wrapper:latest`. Takes several minutes due to `renv::restore()`.

Re-run only if the template `renv.lock` or `cwl-wrapper.sh` changes.

**Options:**
```bash
bash build-sdk.sh --tag my-wrapper:v1 --push
```

---

## Packaging an app

```bash
moveapps-cwl-package <github-repo-url> [options]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--output-dir PATH` | `./<repo-name>/` | Where to write generated files |
| `--wrapper-image IMAGE` | `moveapps-r-wrapper:latest` | Base image to extend |
| `--docker-registry REGISTRY` | `moveapps` | Registry prefix for `dockerPull` — pass `""` for local-only images |
| `--dry-run` | — | Print generated files without writing anything |
| `--github-token TOKEN` | `$GITHUB_TOKEN` | GitHub PAT (also read from env) |

### Example

```bash
moveapps-cwl-package https://github.com/movestore/RemoveOutliers \
    --docker-registry "" \
    --output-dir RemoveOutliers
```

---

## Building and running an app

```bash
# 1. Build the app-specific Docker image
cd RemoveOutliers
bash build.sh

# 2. Edit inputs.yaml — update the input_rds path to your actual file
#    All other parameters are pre-filled from app-configuration.json

# 3. Run
cwltool RemoveOutliers.cwl inputs.yaml
```

### Outputs

| File | Description |
|---|---|
| `output.rds` | Processed move2/MoveStack object |
| `error.log` | R error output (only present if an error occurred) |
| `artifacts/*` | Any plot or data files written by the app |

---

## GitHub token

Set `GITHUB_TOKEN` to avoid rate limits or to access private repos:

```bash
export GITHUB_TOKEN=ghp_...
```

---

## Troubleshooting

**Platform warning on Apple Silicon** — expected, the images are `linux/amd64`:
```
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8)
```

**`remotes::install_github` fails at runtime** — cwltool uses `--net=none`. This is handled automatically: `cwl-wrapper.sh` strips that line from `sdk.R` at runtime via `sed`. The package is already installed in the image.

**Parameters are all NULL** — the CWL file and `inputs.yaml` must come from the same `moveapps-cwl-package` run. If you regenerate one without the other, the input names will mismatch. Regenerate both together and rebuild the image.
