from pathlib import Path
import json,re
root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel109')
private=(out/'wpa-2g-private.conf').read_text()
secrets=[]
for key,value in re.findall(r'^\s*(ssid|psk)\s*=\s*(.+?)\s*$',private,re.M):
    raw=value.strip('"');secrets.append(raw)
    if key=='ssid' and re.fullmatch('[0-9a-fA-F]+',raw):
        secrets.append(bytes.fromhex(raw).decode())
pin=(out/'login-pin-private.txt').read_text().strip()
# The private PIN file includes only the generated numeric PIN.
if re.fullmatch(r'\d{8}',pin):secrets.append(pin)
paths=[root/name for name in ['README.md','NEXT-SESSION.md','FLYWHEEL.md',
    'linux-port/docs/HARDWARE-STATUS.md','sessions/109-pmos-userdata-phosh-and-desktop-audio.md']]
paths+=list((root/'reference/kernel109').glob('*'))+list((root/'reference/kernel110').glob('*'))
checked=0
for path in paths:
    if not path.is_file():continue
    text=path.read_text()
    for secret in secrets:
        assert secret not in text, f'Private value appears in {path.name}'
    assert ''.join(['-----BEGIN ', 'OPENSSH PRIVATE KEY-----']) not in text
    checked+=1
assert len(re.findall(r'^\| (?:触摸|原生显示面板|GPU|普通USB与OTG|Wi-Fi|蓝牙|NFC|音频|电池与充电|蜂窝网络/数据|摄像头|其它传感器|指纹|振动|GNSS定位) \|',
    (root/'linux-port/docs/HARDWARE-STATUS.md').read_text(),re.M))==15
print(json.dumps(dict(public_files_checked=checked,no_private_values_found=True,
                     hardware_groups_preserved=15,goal_complete=False)))
