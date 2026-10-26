#!/bin/bash
set -euo pipefail
umask 077
out=/mnt/e/edk2-samurai-out/kernel114
stage=/home/cy122/pmos-samurai-rootfs114
test ! -e "$stage"
mkdir -p "$out"
mkdir -m700 "$stage"
install -m600 /mnt/e/edk2-samurai-out/kernel72/id_ed25519 "$stage/ssh-key-private"
opts=(-F none -i "$stage/ssh-key-private" -o UserKnownHostsFile=/mnt/e/edk2-samurai-out/kernel109/known_hosts-pmos -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=5 -o ServerAliveInterval=10 -o ServerAliveCountMax=3)
ssh "${opts[@]}" root@169.254.42.1 'cat /var/lib/samurai/k114-rootfs-export/rootfs-payload-private.tar.gz' > "$out/rootfs-payload-private.tar.gz"
ssh "${opts[@]}" root@169.254.42.1 'tar -C /var/lib/samurai/k114-rootfs-export --exclude=rootfs-payload-private.tar.gz -czf - .' > "$out/export-evidence-private.tar.gz"
mkdir -m700 "$stage/evidence"
tar -xzf "$out/export-evidence-private.tar.gz" -C "$stage/evidence"
(cd "$out" && sha256sum -c "$stage/evidence/archive.sha256")
gzip -t "$out/rootfs-payload-private.tar.gz"
cp -a --reflink=auto /home/cy122/pmos-samurai-kernel109/rootfs "$stage/rootfs"
python3 - "$stage/rootfs" <<'PY'
from pathlib import Path
import shutil, sys
root=Path(sys.argv[1]).resolve()
assert root == Path('/home/cy122/pmos-samurai-rootfs114/rootfs')
for name in ('usr','etc','home','root'):
    p=root/name
    assert p.is_dir() and not p.is_symlink()
    shutil.rmtree(p)
PY
tar --same-owner -xzf "$out/rootfs-payload-private.tar.gz" -C "$stage/rootfs"
(cd "$stage/rootfs" && sha256sum -c "$stage/evidence/static-before.sha256") > "$out/import-static-check.log"
test ! -s "$stage/evidence/capabilities.txt"
echo ROOTFS114_OFFLINE_IMPORT_AND_STATIC_HASHES_PASS
