from pathlib import Path
import hashlib,host,json

ref=Path(__file__).resolve().parent
s=(ref/'quiesce-current183.sh').read_text()
position=s.index('for pid in $(pidof ModemManager')
prefix='''#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k200-baseline
dest=/var/lib/samurai/k200-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 512
test ! -e /sys/module/qcom_camss
test -z "$(pgrep -u 10000 || true)"
if rc-service modemmanager status >/dev/null 2>&1; then timeout -s TERM -k 2 25 rc-service modemmanager stop >> "$dest/modemmanager-service-stop.txt" 2>&1; fi
'''
dest=ref/'continue-quiesce-current183.sh';dest.write_text(prefix+s[position:])
host.upload(dest,'/var/lib/samurai/k200-reboot-tools/continue-quiesce-current183.sh')
try:
 p=host.ssh('sh -x /var/lib/samurai/k200-reboot-tools/continue-quiesce-current183.sh',timeout=120)
except Exception as error:
 if hasattr(error,'stdout'):(host.PRIVATE/'continue-quiesce-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''))
 raise SystemExit('Continuation stopped; inspect its private trace and current state')
(host.PRIVATE/'continue-quiesce-host-private.log').write_bytes(p.stdout+p.stderr)
print('K200_QUIESCE_CONTINUATION_COMPLETE')
