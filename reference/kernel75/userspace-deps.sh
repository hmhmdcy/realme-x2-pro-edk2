#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel75/userspace
opts=(-o APT::Architecture=arm64 -o APT::Architectures=arm64 -o Dir::Etc::sourcelist="$out/sources.list" -o Dir::Etc::sourceparts=- -o Dir::State::lists="$out/lists" -o Dir::Cache="$out/cache")
cd "$out/debs"
apt-get "${opts[@]}" download libc6 libgcc-s1 libstdc++6 zlib1g libzstd1 libdrm2 libxcb-dri3-0 libwayland-client0 libxcb1 libx11-xcb1 libxcb-present0 libxcb-xfixes0 libxcb-sync1 libxcb-randr0 libxcb-shm0 libxshmfence1 libdisplay-info3 libexpat1 libffi8 libxau6 libxdmcp6 libbsd0 libmd0 > "$out/apt-deps.log" 2>&1
for pkg in ./*.deb; do dpkg-deb -x "$pkg" "$out/root"; done
mkdir -p "$out/host"
dpkg-deb -x "$out"/glslang-tools_*_amd64.deb "$out/host"
"$out/host/usr/bin/glslangValidator" --version
