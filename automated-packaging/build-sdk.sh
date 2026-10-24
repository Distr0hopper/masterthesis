#!/bin/bash
# Fetch the MoveApps template R environment and build the shared wrapper image.
# Run this once; re-run only when the template renv.lock or cwl-wrapper.sh changes.
#
# Usage:
#   bash build-sdk.sh [--tag TAG] [--push]
#
# Defaults:
#   --tag  moveapps-r-wrapper:latest
#
# Publishing a new version - always a new tag, never re-push one (--push refuses an existing tag;
# then bump DEFAULT_WRAPPER_IMAGE in packager.py):
#   bash build-sdk.sh --tag ghcr.io/distr0hopper/moveapps-r-wrapper:<next-tag> --push
set -e

WRAPPER_TAG="moveapps-r-wrapper:latest"
PUSH=false
TEMPLATE_REPO="movestore/Template_R_Function_App"

while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)  WRAPPER_TAG="$2"; shift 2 ;;
        --push) PUSH=true;        shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGER_PY="$SCRIPT_DIR/moveapps_cwl_packager/packager.py"

# Published CWL files reference the tag, so a pushed tag must never change. Checked before the
# long build; anything other than "not found" (network, auth) aborts rather than risk an overwrite.
if $PUSH; then
    echo "==> Checking that ${WRAPPER_TAG} is not published yet..."
    if lookup="$(docker buildx imagetools inspect "$WRAPPER_TAG" 2>&1)"; then
        echo "ERROR: ${WRAPPER_TAG} already exists in the registry. Published tags are never re-pushed;"
        echo "       use a new tag (e.g. bump the -N suffix)."
        exit 1
    elif ! grep -q "not found" <<<"$lookup"; then
        echo "ERROR: could not check whether ${WRAPPER_TAG} exists:"
        echo "$lookup"
        exit 1
    fi
fi

BUILD_CTX="$(mktemp -d)"
trap 'rm -rf "$BUILD_CTX"' EXIT

echo "==> Fetching template R environment from github.com/${TEMPLATE_REPO} ..."

fetch_file() {
    local path="$1"
    local dest="$BUILD_CTX/$path"
    mkdir -p "$(dirname "$dest")"
    curl -fsSL \
        "https://raw.githubusercontent.com/${TEMPLATE_REPO}/master/${path}" \
        -o "$dest"
}

fetch_file "renv.lock"
fetch_file "renv/activate.R"
fetch_file "renv/settings.dcf"
fetch_file "sdk.R"
fetch_file "start-process.sh"

chmod +x "$BUILD_CTX/start-process.sh"

# The template repo has no .Rprofile; create an empty one so the Dockerfile COPY succeeds
touch "$BUILD_CTX/.Rprofile"

cp "$SCRIPT_DIR/cwl-wrapper.sh" "$BUILD_CTX/cwl-wrapper.sh"
chmod +x "$BUILD_CTX/cwl-wrapper.sh"

cp "$SCRIPT_DIR/Dockerfile.sdk" "$BUILD_CTX/Dockerfile"

echo ""
echo "==> Building wrapper image (${WRAPPER_TAG})..."
docker build --platform linux/amd64 \
    -t "$WRAPPER_TAG" \
    -f "$BUILD_CTX/Dockerfile" \
    "$BUILD_CTX"

if $PUSH; then
    echo ""
    echo "==> Pushing image..."
    docker push "$WRAPPER_TAG"
fi

echo ""
echo "Done."
echo "  Wrapper image : $WRAPPER_TAG"
echo ""
if $PUSH; then
    current="$(sed -n 's/^DEFAULT_WRAPPER_IMAGE = "\(.*\)"$/\1/p' "$PACKAGER_PY")"
    echo "Next: make it the default for newly packaged tools. In"
    echo "  moveapps_cwl_packager/packager.py"
    echo "set"
    echo "  DEFAULT_WRAPPER_IMAGE = \"$WRAPPER_TAG\""
    echo "(currently: ${current:-not found}), rebuild the packaging service"
    echo "(docker compose up -d --build packaging-service) and commit."
    echo "Already published tools keep the tag they were packaged with."
else
    echo "Now package apps with:"
    echo "  moveapps-cwl-package <url> --wrapper-image $WRAPPER_TAG"
fi
