"""Privately retain one original ICP firmware without loading it on the phone."""
from pathlib import Path
import gzip,hashlib,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;cache=P/'icp-collection-private.json';binary=P/'CAMERA_ICP.elf-private'
code=r'''
from pathlib import Path
import gzip,hashlib,json,struct,subprocess,sys
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()
result=dict(files_checked=[],source=None,unmounted=True,readonly=True,firmware_executed=False)
reserve=Path('/sys/firmware/devicetree/base/reserved-memory');result['camera_reserved_nodes']=[]
if reserve.is_dir():
 for node in reserve.iterdir():
  if node.is_dir() and ('camera' in node.name or 'icp' in node.name):
   result['camera_reserved_nodes'].append(dict(name=node.name,reg=(node/'reg').read_bytes().hex() if (node/'reg').is_file() else None))
data=None
for name in ['/lib/firmware/CAMERA_ICP.elf','/lib/firmware/qcom/sm8150/realme/rmx1931/CAMERA_ICP.elf']:
 path=Path(name);result['files_checked'].append(name)
 if path.is_file():data=path.read_bytes();result['source']=name;break
if data is None:
 block=Path('/dev/disk/by-partlabel/vendor').resolve();assert block.name=='sda9'
 assert 'PARTNAME=vendor' in Path('/sys/class/block/sda9/uevent').read_text().splitlines()
 device=Path('/sys/class/block/sda9/dev').read_text().strip()
 assert not any(l.split()[2]==device for l in Path('/proc/self/mountinfo').read_text().splitlines())
 mount=Path('/run/k352-icp-fw-ro');assert not mount.exists();mount.mkdir(mode=0o700);owned=False
 try:
  subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],capture_output=True,check=True);owned=True
  line=next(l for l in Path('/proc/mounts').read_text().splitlines() if l.split()[1]==str(mount));opts=set(line.split()[3].split(','))
  assert {'ro','nosuid','nodev','noexec'}<=opts and 'rw' not in opts
  for name in ['firmware/CAMERA_ICP.elf','firmware/camera/CAMERA_ICP.elf']:
   path=mount/name;result['files_checked'].append('vendor:'+name)
   if path.is_file() and not path.is_symlink():
    assert path.stat().st_size<8*1024*1024;data=path.read_bytes();result['source']='vendor:'+name;break
 finally:
  if owned:subprocess.run(['umount',str(mount)],capture_output=True,check=True)
  mount.rmdir()
 assert not any(l.split()[2]==device for l in Path('/proc/self/mountinfo').read_text().splitlines())
 result['readonly_noload_noexec']=True
if data is not None:
 assert data[:4]==b'\x7fELF';result.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest());packed=gzip.compress(data,mtime=0)
else:packed=b''
header=json.dumps(result).encode();sys.stdout.buffer.write(struct.pack('<I',len(header))+header+packed)
'''
if not cache.exists():
 q=host.raw_ssh('python3 -',input=code.encode(),timeout=35);size=struct.unpack_from('<I',q.stdout)[0]
 result=json.loads(q.stdout[4:4+size]);packed=q.stdout[4+size:]
 if result['source']:
  raw=gzip.decompress(packed);assert len(raw)==result['bytes'] and hashlib.sha256(raw).hexdigest()==result['sha256'];binary.write_bytes(raw)
 cache.write_text(json.dumps(result,indent=2)+'\n')
else:result=json.loads(cache.read_text())
assert result['unmounted']
report=dict(stage=352,source=result['source'],collected=result['source'] is not None,bytes=result.get('bytes'),sha256=result.get('sha256'),
 readonly_noload_noexec=result.get('readonly_noload_noexec',False),unmounted=True,firmware_executed=False,
 camera_reserved_nodes=result['camera_reserved_nodes'],no_nv_otp_eeprom_or_persist_access=True,
 no_installed_files_or_modules_changed=True,passed=result['source'] is not None)
(HERE/'icp-firmware-collection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
