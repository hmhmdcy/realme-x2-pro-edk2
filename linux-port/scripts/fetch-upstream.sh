#!/bin/bash
D=/home/cy122/x2pro-linux/upstream
mkdir -p "$D"; cd "$D"
[ -d .git ] || { git init -q; git remote add origin https://github.com/hmhmdcy/linux.git; }
echo "proxy: $(git config --get http.proxy)  $(git config --global --get http.proxy)"
for i in 1 2 3 4 5; do
  echo "--- attempt $i ---"
  timeout 55 git fetch --depth=1 origin refs/tags/v7.3-rc6:refs/tags/v7.3-rc6 > /tmp/fetch.log 2>&1
  rc=$?
  tail -2 /tmp/fetch.log
  if git rev-parse --verify -q refs/tags/v7.3-rc6 >/dev/null; then echo "GOT TAG"; break; fi
  if [ $rc -ne 124 ]; then sleep 3; fi
done
echo "--- ?? ---"; du -sh .git; git rev-parse --verify -q refs/tags/v7.3-rc6 2>/dev/null || echo "(??????????????)"