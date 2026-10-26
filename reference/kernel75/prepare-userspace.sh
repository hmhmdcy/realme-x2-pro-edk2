#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel75/userspace
mkdir -p "$out/lists/partial" "$out/cache/archives/partial" "$out/debs" "$out/root"
echo 'deb [arch=arm64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://ports.ubuntu.com/ubuntu-ports resolute main universe' > "$out/sources.list"
opts=(-o APT::Architecture=arm64 -o APT::Architectures=arm64 -o Dir::Etc::sourcelist="$out/sources.list" -o Dir::Etc::sourceparts=- -o Dir::State::lists="$out/lists" -o Dir::Cache="$out/cache" -o APT::Get::List-Cleanup=0)
apt-get "${opts[@]}" update > "$out/apt-update.log" 2>&1
cd "$out/debs"
apt-get "${opts[@]}" download mesa-vulkan-drivers libvulkan1 libvulkan-dev > "$out/apt-download.log" 2>&1
for pkg in ./*.deb; do dpkg-deb -x "$pkg" "$out/root"; done
find "$out/root" -name '*freedreno*' -o -name '*vulkan*so*'
