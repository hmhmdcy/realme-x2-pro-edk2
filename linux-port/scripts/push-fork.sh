#!/bin/bash
# Retry the fork push until the local master is on the remote (network here is flaky).
set -u
RK=/home/cy122/edk2-samurai/repo
cd "$RK"
HEAD=$(git rev-parse HEAD)
echo "local HEAD: $HEAD"
for i in $(seq 1 10); do
  echo "--- attempt $i ---"
  timeout 150 git push fork master > /tmp/push.log 2>&1
  rc=$?
  tail -3 /tmp/push.log
  if [ $rc -eq 0 ]; then
    echo "push returned 0"
    break
  fi
  sleep 10
done
echo "--- verify ---"
timeout 60 git ls-remote fork master
echo "local:  $HEAD"