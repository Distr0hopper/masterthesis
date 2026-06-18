#!/bin/bash
set -e

CWL_WORKDIR=$(pwd)
EXTERNAL_INPUT=$1

# Use CWL-generated config if present, otherwise fall back to baked-in default
if [ -f "${CWL_WORKDIR}/app-configuration.json" ]; then
    CONFIG_PATH="${CWL_WORKDIR}/app-configuration.json"
else
    CONFIG_PATH="/home/moveapps/co-pilot-r/app-configuration.json"
fi

# Symlink app files into writable working directory
ln -sf /home/moveapps/co-pilot-r/RFunction.R .
ln -sf /home/moveapps/co-pilot-r/start-process.sh .

# Patch sdk.R: strip the remotes::install_github() line that pulls
# moveapps-sdk-r-package from GitHub at runtime. The package is already
# installed via renv::restore() in the Docker image, so this call is
# unnecessary and fails under cwltool's --net=none.
sed '/remotes::install_github/d' /home/moveapps/co-pilot-r/sdk.R > sdk.R

# Create artifacts subdirectory (prevents SDK clearRecentOutput() from deleting symlinks)
mkdir -p artifacts

# Generate .env file
cat <<EOF > .env
SOURCE_FILE=$EXTERNAL_INPUT
OUTPUT_FILE=${CWL_WORKDIR}/output.rds
ERROR_FILE=${CWL_WORKDIR}/error.log
APP_ARTIFACTS_DIR=${CWL_WORKDIR}/artifacts/
USER_APP_FILE_HOME_DIR=/home/moveapps/co-pilot-r/data/auxiliary/user-files
LOCAL_APP_FILES_DIR=/home/moveapps/co-pilot-r/data/auxiliary/user-files
CONFIGURATION=${CONFIG_PATH}
CONFIGURATION_FILE=${CONFIG_PATH}
PRINT_CONFIGURATION=yes
LOG_LEVEL_SDK=INFO
CLEAR_OUTPUT=yes
EOF

# Run the app
bash start-process.sh

# Copy artifacts to working directory root for CWL glob collection
cp artifacts/* . 2>/dev/null || true
