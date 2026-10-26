from pathlib import Path
import json, re, tarfile
root = Path('/mnt/e/RealmeX2Pro edk2')
private = Path('/mnt/e/edk2-samurai-out')
secrets = []
text = (private / 'kernel109/wpa-2g-private.conf').read_text()
for key, value in re.findall(r'^\s*(ssid|psk)\s*=\s*(.+?)\s*$', text, re.M):
    raw = value.strip('"'); secrets.append(raw)
    if key == 'ssid' and re.fullmatch('[0-9a-fA-F]+', raw): secrets.append(bytes.fromhex(raw).decode())
pin_text = (private / 'kernel109/login-pin-private.txt').read_text()
pins = re.findall(r'(?<!\d)\d{8}(?!\d)', pin_text)
assert len(pins) == 1; secrets.extend(pins)
secrets.append(json.loads((private / 'kernel109/fastboot-identity.json').read_text())['serial'])
init = Path('/home/cy122/pmos-samurai-kernel112/initramfs/usr/sbin/samurai-rootfs').read_text()
secrets.extend(re.findall(r'expected_(?:fs_uuid|partuuid)=([^\s]+)', init))
for path in (private / 'kernel112').glob('*.tar'):
    with tarfile.open(path) as tar:
        for m in tar:
            if m.isfile() and m.name.endswith('boot-id-private.txt'):
                secrets.append(tar.extractfile(m).read().decode().strip())
paths = [root / p for p in ['README.md', 'NEXT-SESSION.md', 'FLYWHEEL.md', 'linux-port/docs/HARDWARE-STATUS.md',
                          'sessions/109-pmos-userdata-phosh-and-desktop-audio.md',
                          'sessions/111-slpi-fastrpc-and-display-regression.md',
                          'sessions/112-startup-sensor-registry-and-reboot.md']]
for stage in (109, 110, 111, 112, 113): paths.extend((root / f'reference/kernel{stage}').glob('*'))
checked = 0
for path in paths:
    if not path.is_file(): continue
    text = path.read_text()
    assert all(secret not in text for secret in secrets if len(secret) >= 8), path.name
    assert ''.join(['-----BEGIN ', 'OPENSSH PRIVATE KEY-----']) not in text, path.name
    checked += 1
hardware = (root / 'linux-port/docs/HARDWARE-STATUS.md').read_text()
assert len(re.findall(r'^\| (?:触摸|原生显示面板|GPU|普通USB与OTG|Wi-Fi|蓝牙|NFC|音频|电池与充电|蜂窝网络/数据|摄像头|其它传感器|指纹|振动|GNSS定位) \|', hardware, re.M)) == 15
assert '当前部署Linux #112' in hardware
report = dict(public_files_checked=checked, no_private_values_found=True, hardware_groups_preserved=15, goal_complete=False)
(root / 'reference/kernel112/public-audit.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
