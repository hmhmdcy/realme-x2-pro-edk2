#!/bin/bash
D=/home/cy122/x2pro-linux/upstream
cd "$D" || exit 1
# ???????????Windows ????? WSL ??????
git config --local http.proxy ""
git config --local https.proxy ""
echo "local proxy ??: [$(git config --local --get http.proxy)]"
echo "=== fetch ?? $(date +%T) ==="
timeout 235 git fetch --depth=1 up refs/tags/v7.3-rc6:refs/tags/v7.3-rc6 2>&1 | tail -3
echo "=== ?? $(date +%T) ==="
if git rev-parse --verify -q refs/tags/v7.3-rc6 >/dev/null; then
  echo "TAG OK: $(git rev-parse refs/tags/v7.3-rc6)"
  du -sh .git
else
  echo "NO TAG"; du -sh .git
fi