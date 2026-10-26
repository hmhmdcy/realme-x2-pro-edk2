#!/bin/bash
# Push the kernel bring-up branch to the fork, reliably.
#
# Why this is a script and not a one-liner (HANDOVER-NEXT.md section 24):
#   * a nohup'ed background `git push` does NOT survive a WSL distro recycle;
#     the distro only stays alive while a wsl.exe client is attached, so run
#     this from a foreground wsl.exe, e.g. from Windows:
#         Start-Process wsl.exe -ArgumentList '--','bash',<this script> `
#           -RedirectStandardOutput <log> -RedirectStandardError <err> -WindowStyle Hidden
#   * the Windows proxy (http.proxy=127.0.0.1:7890) breaks the TLS handshake
#     a few seconds in, so the proxy is disabled per-repo first (section 23.0);
#   * a --depth=1 clone is accepted by GitHub, but the transfer is the whole
#     snapshot pack (~285 MiB, ~4.5 min), so give it time.
set -u
D=${1:-/home/cy122/x2pro-linux/upstream}
BRANCH=${2:-samurai-bringup}
cd "$D" || exit 1
git config --local http.proxy ""
git config --local https.proxy ""
rm -f .git/objects/pack/tmp_pack_* 2>/dev/null
echo "=== push $BRANCH start $(date +%T) ==="
timeout 1800 git push -u origin "$BRANCH" 2>&1
echo "PUSH_RC=$? end $(date +%T)"
echo "=== verify (ls-remote) ==="
timeout 60 git ls-remote origin "$BRANCH" 2>&1
echo "=== local HEAD ==="
git rev-parse HEAD