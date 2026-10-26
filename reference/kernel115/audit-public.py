from pathlib import Path
import json,re,tarfile
root=Path('/mnt/e/RealmeX2Pro edk2')
private=Path('/mnt/e/edk2-samurai-out')
base=(root/'reference/kernel113/audit-public.py').read_text()
scope={}
exec(base[:base.index('paths = ')],scope)
secrets=scope['secrets']
for stage in [114,115]:
    for p in (private/f'kernel{stage}').glob('*boot-id-private.txt'):
        secrets.append(p.read_text().strip())
    for p in (private/f'kernel{stage}').glob('*.tar*'):
        if p.name=='delay-fix-runtime.tar': continue  # preserved incomplete transfer
        with tarfile.open(p) as tf:
            for m in tf:
                if m.isfile() and m.name.endswith('boot-id-private.txt'):
                    secrets.append(tf.extractfile(m).read().decode().strip())
paths=[root/p for p in ['README.md','NEXT-SESSION.md','FLYWHEEL.md','DOCS-INDEX.md','linux-port/docs/HARDWARE-STATUS.md',
 'sessions/114-complete-rootfs-and-qmi-ipa-foundation.md','sessions/115-own-ipa-modem-and-zram-rootfs.md',
 'sessions/116-camss-foundation-and-own-sensor-binaries.md']]
for stage in range(109,117): paths.extend((root/f'reference/kernel{stage}').glob('*'))
checked=0
for path in paths:
    if not path.is_file(): continue
    text=path.read_text()
    assert all(s not in text for s in secrets if len(s)>=8),path.name
    assert ''.join(['-----BEGIN ','OPENSSH PRIVATE KEY-----']) not in text,path.name
    checked+=1
hardware=(root/'linux-port/docs/HARDWARE-STATUS.md').read_text()
assert len(re.findall(r'^\| (?:触摸|原生显示面板|GPU|普通USB与OTG|Wi-Fi|蓝牙|NFC|音频|电池与充电|蜂窝网络/数据|摄像头|其它传感器|指纹|振动|GNSS定位) \|',hardware,re.M))==15
assert '#115' in hardware and '无DRM/Phosh/Phoc' in hardware and 'sim-missing' in hardware
report=dict(public_files_checked=checked,no_private_values_found=True,hardware_groups_preserved=15,current_kernel=115,current_display_failure_documented=True,offline_candidate=116,goal_complete=False)
(root/'reference/kernel115/public-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
