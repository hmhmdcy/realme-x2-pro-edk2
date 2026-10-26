#!/bin/bash
# Rebuild the samurai firmware volume after the PlatformBm.c LoadOptions change.
# Kept next to the other linux-port scripts so the step is reproducible.
set -u
RK=/home/cy122/edk2-samurai/repo
LOG=$HOME/build-cmdline.log

cd "$RK" || exit 1
echo "HEAD: $(git log --oneline -1)"

export PATH="$HOME/.local/bin:$PATH"
export CPATH="$HOME/edk2-samurai/local/uuid/usr/include"
export LIBRARY_PATH="$HOME/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu"

rm -f "$LOG"
nohup ./build.sh -d samurai --toolchain GCC5 > "$LOG" 2>&1 < /dev/null &
echo "started pid $!"