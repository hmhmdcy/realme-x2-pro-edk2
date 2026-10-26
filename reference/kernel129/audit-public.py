from pathlib import Path
import json,re,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');private=Path('/mnt/e/edk2-samurai-out')
code=(r/'reference/kernel113/audit-public.py').read_text();scope={};exec(code[:code.index('paths = ')],scope);secrets=scope['secrets']
for stage in [114,115,117,118,119,120,121,122,123,124,125,126,127,128,129]:
 for p in (private/f'kernel{stage}').glob('*boot-id-private.txt'):secrets.append(p.read_text().strip())
 for p in (private/f'kernel{stage}').glob('*.tar*'):
  if p.name=='delay-fix-runtime.tar':continue
  with tarfile.open(p) as tf:
   for m in tf:
    if m.isfile() and m.name.endswith('boot-id-private.txt'):secrets.append(tf.extractfile(m).read().decode().strip())
import configparser
for name in ['live-wifi-profile-before-private.nmconnection','wifi-dual-band-candidate-private.nmconnection']:
 cfg=configparser.ConfigParser(interpolation=None);cfg.read(private/'kernel128'/name)
 for section,key in [('connection','uuid'),('wifi','ssid'),('wifi-security','psk')]:
  if cfg.has_option(section,key):secrets.append(cfg.get(section,key))
paths=[r/p for p in ['README.md','NEXT-SESSION.md','FLYWHEEL.md','DOCS-INDEX.md','linux-port/docs/HARDWARE-STATUS.md']]
paths.extend(p for p in (r/'sessions').glob('*.md') if p.name.startswith(tuple(str(n)+'-' for n in range(109,130))))
for stage in range(109,130):paths.extend((r/f'reference/kernel{stage}').glob('*'))
checked=0
for p in paths:
 if not p.is_file():continue
 text=p.read_text();assert all(s not in text for s in secrets if len(s)>=8),p.name
 assert ''.join(['-----BEGIN ','OPENSSH PRIVATE KEY-----']) not in text,p.name
 checked+=1
hardware=(r/'linux-port/docs/HARDWARE-STATUS.md').read_text()
assert len(re.findall(r'^\| (?:触摸|原生显示面板|GPU|普通USB与OTG|Wi-Fi|蓝牙|NFC|音频|电池与充电|蜂窝网络/数据|摄像头|其它传感器|指纹|振动|GNSS定位) \|',hardware,re.M))==15
assert '#129' in hardware and '阶段129' in hardware and '物理camera' in hardware and 'GPU' in hardware and 'sim-missing' in hardware
report=dict(public_files_checked=checked,no_private_values_found=True,hardware_groups_preserved=15,current_kernel=129,rootfs_generation=129,internal_csid0_vfe0_tpg_pass=True,physical_camera_and_gpu_display_full_acceptance=False,persistent_display_fix=False,goal_complete=False)
(r/'reference/kernel129/public-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
