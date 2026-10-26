from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2')
s=(r/'reference/kernel119/collect-runtime.sh').read_text().replace('k119','k126').replace("'^#118 '","'^#126 '").replace('7.3.0-rc6-rmx1931-samurai+','7.3.0-rc6-rmx1931-samurai-k126+').replace('KERNEL118_FIRST_NATIVE_RUNTIME_CAPTURED','KERNEL126_FIRST_NATIVE_RUNTIME_CAPTURED')
s=s.replace('cat /sys/class/drm/card0-DSI-1/status', 'cat /sys/class/drm/card*-DSI-1/status')
s=s.replace('cat /sys/kernel/debug/dri/0/state', '''card=$(basename "$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)")
test -n "$card"
minor=$(cat "/sys/class/drm/$card/dev"); minor=${minor#*:}
printf '%s %s\\n' "$card" "$minor" > "$dest/drm-resolved.txt"
cat "/sys/kernel/debug/dri/$minor/state"''')
s=s.replace('dmesg > "$dest/dmesg.txt"', '''ls -l /dev/media* /dev/video* /dev/v4l-subdev* > "$dest/camera-nodes.txt" 2>&1 || true
cat /sys/module/qcom_camss/parameters/dma_trace > "$dest/dma-trace.txt" 2>&1 || true
cat /proc/interrupts > "$dest/interrupts.txt"
for item in /sys/class/remoteproc/remoteproc*; do printf '%s %s %s\\n' "${item##*/}" "$(cat "$item/name")" "$(cat "$item/state")"; done > "$dest/remoteproc-names.txt"
dmesg > "$dest/dmesg.txt"''')
(r/'reference/kernel126/collect-runtime.sh').write_text(s)
resume='''#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k126-first-runtime
uname -v | grep -q '^#126 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test ! -e "$dest/SHA256SUMS"
'''+s[s.index('card=$(basename'):]
(r/'reference/kernel126/resume-collect-runtime.sh').write_text(resume)
print('K126_RUNTIME_COLLECTOR_READY')
