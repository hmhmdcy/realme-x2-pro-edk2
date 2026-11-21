#!/bin/sh
# Reproduce the delivered image's sshd inside a local tree.
#
# Run on x86_64 WSL against an aarch64 root (qemu-aarch64 binfmt required).
# Usage: repro-sshd-in-chroot.sh <rootfs-dir> [port]
set -eu
ROOT=${1:?rootfs dir}
PORT=${2:-2222}
LOG=/tmp/sshd-repro.log

if [ ! -e /proc/sys/fs/binfmt_misc/qemu-aarch64 ]; then
  echo ':qemu-aarch64:M::\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\xb7\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-aarch64-static:F' \
    > /proc/sys/fs/binfmt_misc/register
fi

[ -x "$ROOT/usr/sbin/sshd.pam" ] || { echo "FATAL: no sshd.pam in $ROOT"; exit 1; }
[ -d "$ROOT/var/empty" ] || { echo "FATAL: $ROOT/var/empty missing (sshd needs it)"; exit 1; }

# Host keys are generated on first boot by sshdgenkeys.service; an image that
# ships pre-generated ones leaks a fixed host identity.
if ls "$ROOT"/etc/ssh/ssh_host_*_key >/dev/null 2>&1; then
  echo "FATAL: image already contains host keys:"
  ls -l "$ROOT"/etc/ssh/ssh_host_*_key
  exit 1
fi

mkdir -p "$ROOT/run/sshd" "$ROOT/dev" "$ROOT/proc"
chmod 755 "$ROOT/run/sshd"
mount --bind /dev "$ROOT/dev" 2>/dev/null || true
mount -t proc proc "$ROOT/proc" 2>/dev/null || true

echo "== config test =="
chroot "$ROOT" /usr/bin/ssh-keygen -A >/dev/null
chroot "$ROOT" /usr/sbin/sshd.pam -t && echo "sshd -t: OK"

echo "== live connection =="
chroot "$ROOT" /usr/sbin/sshd.pam -D -p "$PORT" -e -o LogLevel=DEBUG1 >"$LOG" 2>&1 &
PID=$!
sleep 3
OUT=$(timeout 10 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes -p "$PORT" user@127.0.0.1 true 2>&1 || true)
echo "$OUT" | head -8
kill "$PID" 2>/dev/null || true
sleep 1

echo "== log tail =="
tail -15 "$LOG"

rm -f "$ROOT"/etc/ssh/ssh_host_*_key "$ROOT"/etc/ssh/ssh_host_*_key.pub
umount "$ROOT/dev" 2>/dev/null || true
umount "$ROOT/proc" 2>/dev/null || true
echo "host keys removed after test"

case "$OUT" in
  *"Permission denied"*|*"Postponed keyboard-interactive"*|*"Authenticated"*)
     echo "RESULT: image sshd reached authentication (server healthy)"; exit 0;;
  *"Connection closed"*|*"Connection refused"*)
     echo "RESULT: image sshd failed before/at banner"; exit 1;;
  *) echo "RESULT: inconclusive"; exit 2;;
esac