#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#129 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k129-first-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -z "$(pgrep -x bluetoothd)"
test ! -e /etc/runlevels/default/bluetooth
test "$(rc-service samurai-radio status 2>/dev/null | grep -c 'status: started')" = 1
dest=/var/lib/samurai/k130-live-bluez-service
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cp -a /etc/init.d/bluetooth "$dest/bluetooth-before"
cp -a /etc/bluetooth/main.conf "$dest/main.conf-before-private"
cp -a /etc/conf.d/bluetooth "$dest/conf.d-before"
cp -a /usr/share/dbus-1/system-services/org.bluez.service "$dest/dbus-activation-before"
cp -a /var/lib/bluetooth "$dest/storage-before-private"
dmesg > "$dest/dmesg-before.txt"
sh -n /tmp/k130-bluetooth-service
grep -qx '    need dbus localmount hostname samurai-radio' /tmp/k130-bluetooth-service
service_tmp=$(mktemp /etc/init.d/bluetooth.k130.XXXXXX)
cp /tmp/k130-bluetooth-service "$service_tmp"
chown 0:0 "$service_tmp"
chmod 755 "$service_tmp"
mv "$service_tmp" /etc/init.d/bluetooth
python3 - <<'PY'
from pathlib import Path
import os,tempfile
p=Path('/etc/bluetooth/main.conf');old=p.read_bytes();needle=b'#AutoEnable=true\n'
assert old.count(needle)==1 and b'\nAutoEnable=' not in old
fd,name=tempfile.mkstemp(prefix='main.conf.k130.',dir=p.parent)
with os.fdopen(fd,'wb') as f: f.write(old.replace(needle,b'AutoEnable=false\n'));f.flush();os.fsync(f.fileno())
os.chown(name,0,0);os.chmod(name,0o644);os.replace(name,p)
PY
rc-update add bluetooth default > "$dest/rc-update.txt" 2>&1
timeout -k 5 110 rc-service bluetooth start > "$dest/service-start-private.txt" 2>&1
cp -a /run/samurai-bluetooth-openrc.log "$dest/address-start-private.txt"
rc-service bluetooth status > "$dest/service-start-status.txt"
timeout -k 5 110 rc-service bluetooth restart > "$dest/service-restart-private.txt" 2>&1
cp -a /run/samurai-bluetooth-openrc.log "$dest/address-restart-private.txt"
rc-service bluetooth status > "$dest/service-restart-status.txt"
cp -a /etc/init.d/bluetooth "$dest/bluetooth-after"
cp -a /etc/bluetooth/main.conf "$dest/main.conf-after-private"
readlink /etc/runlevels/default/bluetooth > "$dest/runlevel-link.txt"
sha256sum /usr/bin/samurai-bluetooth /usr/bin/samurai-radio-address /usr/bin/samurai-bt-address /usr/bin/samurai-dms-mac-read > "$dest/helper-hashes.txt"
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
dmesg > "$dest/dmesg-after.txt"
sync
echo K130_STANDARD_BLUEZ_SERVICE_DEPLOYED_STARTED_RESTARTED
