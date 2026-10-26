#!/bin/bash
cd /home/cy122/edk2-samurai/repo
export PATH=/home/cy122/.local/bin:/usr/local/bin:/usr/bin:/bin
export CPATH=/home/cy122/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
./build.sh -d samurai --toolchain GCC5 > /home/cy122/edk2-samurai/build-uas.log 2>&1
echo "BUILD_SCRIPT_EXITED" >> /home/cy122/edk2-samurai/build-uas.log
