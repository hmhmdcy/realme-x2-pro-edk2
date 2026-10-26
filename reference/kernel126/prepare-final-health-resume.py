from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel126');s=(ref/'collect-final-health.sh').read_text()
resume='''#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k126-final-health
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(wc -l < "$dest/samples.txt")" = 6
test ! -e "$dest/SHA256SUMS"
'''+s[s.index('test -d /sys/class/bluetooth/hci0'):]
(ref/'resume-final-health.sh').write_text(resume);print('K126_SAME_BOOT_SIX_SAMPLE_FINAL_HEALTH_RESUME_READY')
