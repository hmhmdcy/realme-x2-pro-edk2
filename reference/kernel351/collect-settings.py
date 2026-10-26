"""Read only the stock vendor camera override configuration if not cached."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;cache=P/'vendor-settings-private.json'
code=r'''
from pathlib import Path
import json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()
block=Path('/dev/disk/by-partlabel/vendor').resolve()
assert block.name=='sda9' and 'PARTNAME=vendor' in Path('/sys/class/block/sda9/uevent').read_text().splitlines()
device=Path('/sys/class/block/sda9/dev').read_text().strip()
assert not any(l.split()[2]==device for l in Path('/proc/self/mountinfo').read_text().splitlines())
mount=Path('/run/k351-vendor-settings-ro');assert not mount.exists();mount.mkdir(mode=0o700);owned=False
result=dict(files={},candidate_names=[],readonly_noload_noexec=True)
try:
 subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],capture_output=True,check=True);owned=True
 line=next(l for l in Path('/proc/mounts').read_text().splitlines() if l.split()[1]==str(mount));opts=set(line.split()[3].split(','))
 assert {'ro','nosuid','nodev','noexec'}<=opts and 'rw' not in opts
 for directory in ['etc/camera','etc']:
  path=mount/directory
  if path.is_dir():result['candidate_names'] += [directory+'/'+p.name for p in path.iterdir() if 'camx' in p.name.lower()]
 for name in ['etc/camera/camxoverridesettings.txt','etc/camera/camxsettings.xml']:
  path=mount/name
  if not path.exists():continue
  assert path.is_file() and not path.is_symlink() and path.stat().st_size<262144
  result['files'][name]=path.read_text()
finally:
 if owned:subprocess.run(['umount',str(mount)],capture_output=True,check=True)
 mount.rmdir()
assert not any(l.split()[2]==device for l in Path('/proc/self/mountinfo').read_text().splitlines())
result['unmounted']=True;print(json.dumps(result))
'''
if not cache.exists():
 q=host.raw_ssh('python3 -',input=code.encode(),timeout=30);result=json.loads(q.stdout)
 cache.write_text(json.dumps(result,indent=2)+'\n')
else:result=json.loads(cache.read_text())
assert result['unmounted']
report=dict(stage=351,files=[dict(path=k,bytes=len(v.encode())) for k,v in result['files'].items()],
 candidate_names=result['candidate_names'],readonly_noload_noexec=True,unmounted=True,
 no_nv_otp_eeprom_or_persist_access=True,no_installed_camera_files_changed=True,
 target_android_runtime_values_not_observed=True,passed=True)
(HERE/'vendor-settings-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
