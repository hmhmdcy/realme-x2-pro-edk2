#!/bin/bash
LOG=/mnt/e/wsl-recover/work/g3.log
exec > "$LOG" 2>&1
check() {
  local img="$1" label="$2"
  echo "================ $label ================"
  simg2img "$img" /root/g3.raw
  M=/root/g3-mnt
  mkdir -p "$M"
  mount -o ro,loop /root/g3.raw "$M"
  python3 - "$M" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
rows = []
for d in sorted((root / 'lib/modules').glob('*')):
    if not d.is_dir():
        continue
    q = d / 'kernel/drivers/leds/flash/leds-qcom-flash.ko'
    v = d / 'kernel/drivers/media/v4l2-core/v4l2-flash-led-class.ko'
    refs = b'v4l2_flash_init' in q.read_bytes() if q.is_file() else False
    rows.append(dict(release=d.name, qcom=q.is_file(), v4l2=v.is_file(), refs=refs))
running = [r for r in rows if r['release'].endswith('-usbwake-otg')]
ok = bool(running) and all(r['qcom'] and r['v4l2'] and r['refs'] for r in running)
for r in rows:
    print(f"  {r['release']:44s} qcom={r['qcom']} v4l2={r['v4l2']} refs={r['refs']}")
print("running-tree present:", bool(running))
print("GATE:", "PASS" if ok else "FAIL")
PY
  umount "$M"
  rm -f /root/g3.raw
}
check "/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-clean/samurai-stable-f2fs-partuuid.simg" "OLD"
check "/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261121-camflash/samurai-stable-f2fs-partuuid.simg" "NEW"