#!/bin/bash
D=/home/cy122/x2pro-linux/upstream
mkdir -p "$D"; cd "$D"
[ -d .git ] || git init -q
git remote get-url origin >/dev/null 2>&1 || git remote add origin https://github.com/hmhmdcy/linux.git
git remote get-url up     >/dev/null 2>&1 || git remote add up     https://github.com/torvalds/linux.git
echo "remotes:"; git remote -v
pkill -f 'git fetch --depth=1' 2>/dev/null
nohup git fetch --depth=1 up refs/tags/v7.3-rc6:refs/tags/v7.3-rc6 > /tmp/fetch.log 2>&1 &
echo "started pid $!"
sleep 30
echo "--- 30s ---"; tail -4 /tmp/fetch.log; du -sh .git | cut -f1; pgrep -c -f 'git fetch'