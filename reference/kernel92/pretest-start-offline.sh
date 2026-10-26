#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = 7ed1ff99-4a7d-459c-b3e0-3f4e20a982ac ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
echo '8a9e9bb15daa5fe2763f4c616cd936d791d208f403cc734dd7c8efc2479cf89b  /tmp/k92-runtime-tools.tar' | sha256sum -c -
tar -xf /tmp/k92-runtime-tools.tar -C /
umask 077
nohup /usr/sbin/samurai-wifi start > /run/samurai-wifi-pretest.log 2>&1 < /dev/null &
echo $! > /tmp/k92-pretest.pid
sleep 3
cat /run/samurai-wifi-pretest.log
