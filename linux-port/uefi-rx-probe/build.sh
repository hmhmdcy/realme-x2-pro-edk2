#!/bin/bash
# Run in the existing edk2-msm repository; does not rebuild boot firmware.
set -euo pipefail
repo_dir=/home/cy122/edk2-samurai/repo
cd "$repo_dir"
export WORKSPACE="$repo_dir/workspace"
export PACKAGES_PATH="$repo_dir/Common/edk2:$repo_dir/Common/edk2-platforms:$repo_dir"
export GCC5_AARCH64_PREFIX=aarch64-linux-gnu-
export PATH="$HOME/.local/bin:$PATH"
export CPATH="$HOME/edk2-samurai/local/uuid/usr/include"
export LIBRARY_PATH="$HOME/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu"
# edksetup.sh assumes optional environment variables may be unset.
set +u
source Common/edk2/edksetup.sh
set -u
build -s -n 4 -a AARCH64 -t GCC5 -b RELEASE \
  -p Platform/Realme/sm8150/linux-port/uefi-rx-probe/RxProbe.dsc
