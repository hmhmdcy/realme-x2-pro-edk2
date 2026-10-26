"""Give WLAN management to NM after verified same-handset radio startup."""
from pathlib import Path
import shutil
assert Path('/etc/samurai-rootfs-stage').read_text().strip() == 'kernel109'
backup = Path('/var/lib/samurai/k109-nm-config-before')
backup.mkdir(mode=0o700)
wifi = Path('/usr/sbin/samurai-wifi')
shutil.copy2(wifi, backup/'samurai-wifi')
text = wifi.read_text()
begin = '    cp /etc/samurai-wifi/wpa-empty.conf "$base/wpa.conf"\n'
end = '    sleep 45\n'
assert text.count(begin) == text.count(end) == 1
left, block = text.split(begin)
wpa, right = block.split(end)
text = left + '    if [ "${SAMURAI_WIFI_MANAGED:-0}" != 1 ]; then\n' + begin + wpa + '    fi\n' + end + right
old = '    kill -0 "$(cat "$base/tftp.pid")" "$(cat "$base/rmtfs.pid")" "$(cat "$base/wpa.pid")"\n'
assert text.count(old) == 1
text = text.replace(old, '''    kill -0 "$(cat "$base/tftp.pid")" "$(cat "$base/rmtfs.pid")"
    if [ "${SAMURAI_WIFI_MANAGED:-0}" != 1 ]; then
        kill -0 "$(cat "$base/wpa.pid")"
    fi
''')
wifi.write_text(text)
radio = Path('/etc/init.d/samurai-radio')
shutil.copy2(radio, backup/'samurai-radio')
radio.write_text('''#!/sbin/openrc-run
description="Same-handset radio firmware and RAM COW services"
depend() {
    need localmount
    after udev
    before networkmanager
}
start() {
    ebegin "Preparing Samurai radio for NetworkManager"
    mkdir -p /run/samurai-wifi
    : > /run/samurai-wifi/boot-started
    SAMURAI_WIFI_MANAGED=1 /usr/sbin/samurai-wifi start > /run/samurai-wifi-boot.log 2>&1
    result=$?
    echo "$result" > /run/samurai-wifi/boot-finished
    eend "$result"
}
''')
conf = Path('/etc/NetworkManager/conf.d/10-samurai-unmanaged.conf')
for file in conf.parent.glob('*.conf'):
    if 'unmanaged-devices=interface-name:usb0;interface-name:wlan0' in file.read_text():
        shutil.copy2(file, backup/file.name)
        file.write_text(file.read_text().replace(';interface-name:wlan0', ''))
(conf.parent/'20-samurai-wlan.conf').write_text('''[device-samurai-wlan]
match-device=interface-name:wlan0
wifi.scan-rand-mac-address=no

[connection-samurai-wlan]
match-device=interface-name:wlan0
wifi.cloned-mac-address=preserve
''')
Path('/etc/conf.d/networkmanager').write_text('rc_need="samurai-radio"\n')
profile = Path('/tmp/k109-samurai-wifi-private.nmconnection')
dest = Path('/etc/NetworkManager/system-connections/samurai-wifi.nmconnection')
shutil.copy2(profile, dest)
dest.chmod(0o600)
profile.unlink()
print('NETWORKMANAGER_CONFIG_READY')
