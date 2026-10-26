from pathlib import Path
import ast

ref=Path(__file__).resolve().parent
s=(ref/'quiesce-current183.sh').read_text();s=s[s.index('for pid in $(pidof ModemManager'):]
s='''#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k200-baseline
dest=/var/lib/samurai/k200-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 512
test ! -e /sys/module/qcom_camss
if rc-service modemmanager status >/dev/null 2>&1; then timeout -s TERM -k 2 25 rc-service modemmanager stop; fi
'''+s
s=s.replace('"$before/old132-module-tree.sha256"','/var/lib/samurai/k200-deploy/paired-module-tree.sha256')
(ref/'finish-quiesce-after-network-stop.sh').write_text(s)
print('K200_DETACHED_TAIL_PREPARED_NETWORKMANAGER_STOPS_BEFORE_MODEMMANAGER')
