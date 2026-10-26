#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
dir=/tmp/k97-preflash-retry1
test ! -e "$dir"
mkdir -m 700 "$dir"
cp -a /tmp/k97-preflash/. "$dir/"
mv "$dir/SHA256SUMS" "$dir/SHA256SUMS-before-coverage-fix"
(cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
sha256sum /dev/sde11 /dev/sde32
tar -C /tmp -cf /tmp/k97-preflash-retry1.tar k97-preflash-retry1
sha256sum /tmp/k97-preflash-retry1.tar
