from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';full=(ref/'quiesce-current118.sh').read_text();a=full.index('test -e /sys/bus/platform/devices/18800000.wifi')
prefix='''#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k126-preflash
dest=/var/lib/samurai/k126-quiesce
uname -v | grep -q '^#118 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat "$dest/boot-id-private.txt")" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
test "$(wc -l < /sys/kernel/debug/dri/1/clients)" = 1
test "$(grep -c 'active=1' /sys/kernel/debug/dri/1/state || true)" = 0
test ! -d /sys/class/bluetooth/hci0
test ! -e "$dest/remoteproc-final-state.txt"
'''
(ref/'resume-quiesce-current118.sh').write_text(prefix+full[a:]);print('K126_SAME_BOOT_BOUNDED_QUIESCE_RESUME_READY')
