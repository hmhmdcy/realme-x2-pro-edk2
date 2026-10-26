from pathlib import Path
import importlib.util,json
root=Path('/mnt/e/RealmeX2Pro edk2');p=Path('/mnt/e/edk2-samurai-out/kernel231')
spec=importlib.util.spec_from_file_location('h',root/'reference/kernel230/host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);h.PRIVATE=p;h.transport.PRIVATE=p
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess,traceback
os.umask(0o077)
root=Path('/var/lib/samurai');out=root/'k231-stock-rfs-layout';assert not out.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k230-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
expected={}
for row in (root/'k115-vendor-camera-source/vendor-before.sha256').read_text().splitlines():
 digest,name=row.split(None,1);expected[name.strip()]=digest
for row in (root/'k230-baseline/partition-check.sha256').read_text().splitlines():
 digest,name=row.split(None,1)
 if subprocess.check_output(['lsblk','-ndo','PARTLABEL',name.strip()],text=True).strip()=='persist':expected[name.strip()]=digest
selected={}
for name,digest in expected.items():
 label=subprocess.check_output(['lsblk','-ndo','PARTLABEL',name],text=True).strip()
 if label in ['vendor','persist']:
  assert label not in selected;selected[label]=dict(device=name,sha256=digest)
assert set(selected)=={'vendor','persist'}
out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot)
def checkdev(label):
 rec=selected[label];r=subprocess.run(['sha256sum',rec['device']],capture_output=True,timeout=50);assert r.returncode==0
 assert r.stdout.decode().split()[0]==rec['sha256']
for label in selected:checkdev(label)
(out/'partitions-private.json').write_text(json.dumps(selected,indent=2)+'\n')
def metadata(path):
 s=path.lstat();result=dict(path=str(path),mode=stat.S_IMODE(s.st_mode),type=stat.S_IFMT(s.st_mode),bytes=s.st_size,inode=s.st_ino)
 if stat.S_ISLNK(s.st_mode):result['target']=os.readlink(path)
 return result
mounts={};mounted=[]
try:
 for label in ['vendor','persist']:
  mp=Path('/run/k231-rfs-'+label+'-ro');assert not mp.exists();mp.mkdir(mode=0o700)
  subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',selected[label]['device'],str(mp)],capture_output=True,check=True,timeout=20);mounted.append(mp)
  records=[line for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1]==str(mp)];assert len(records)==1
  options=records[0].split()[3].split(',');assert 'ro' in options and 'norecovery' in options
  mounts[label]=records[0]
  if label=='vendor':
   paths=[mp/'rfs/msm/mpss',mp/'rfs/msm/mpss/shared',mp/'rfs/msm/mpss/readwrite',mp/'rfs/msm/mpss/readonly/firmware',mp/'rfs/msm/mpss/readonly/vendor/firmware']
   rows=[metadata(x) if x.exists() or x.is_symlink() else dict(path=str(x),missing=True) for x in paths]
   (out/'vendor-rfs-layout-private.json').write_text(json.dumps(rows,indent=2)+'\n')
   snippets=[]
   for path in sorted((mp/'etc/init').glob('*.rc')):
    text=path.read_text(errors='replace');lines=text.splitlines()
    for i,line in enumerate(lines):
     if any(v in line.lower() for v in ['rfs/','rfs ', 'shared/configs','mdtime']):snippets.append(dict(file=str(path.relative_to(mp)),line=i+1,text='\n'.join(lines[max(0,i-1):min(len(lines),i+2)])))
   (out/'vendor-init-rfs-private.json').write_text(json.dumps(snippets,indent=2)+'\n')
  else:
   paths=[mp/'rfs',mp/'rfs/shared',mp/'rfs/shared/configs',mp/'rfs/shared/configs/mcfg_sw',mp/'rfs/shared/configs/mcfg_sw/mdtime.txt',mp/'rfs/msm/mpss']
   rows=[metadata(x) if x.exists() or x.is_symlink() else dict(path=str(x),missing=True) for x in paths]
   shared=mp/'rfs/shared'
   if shared.is_dir() and not shared.is_symlink():
    children=list(shared.rglob('*'));assert len(children)<4096
    rows.extend(metadata(x) for x in sorted(children))
   (out/'persist-rfs-stat-only-private.json').write_text(json.dumps(rows,indent=2)+'\n')
   # No proprietary/shared/calibration payload is read in this layout pass.
 (out/'mounts-private.json').write_text(json.dumps(mounts,indent=2)+'\n')
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc());raise
finally:
 for mp in reversed(mounted):subprocess.run(['umount',str(mp)],capture_output=True,check=True,timeout=20)
for label in selected:checkdev(label)
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
report=dict(stage=231,guard_current230=True,vendor_and_persist_ro_noload=True,both_partition_hashes_preserved=True,temporary_mounts_closed=True,shared_payloads_not_read=True,no_service_power_gnss_session_change=True)
(out/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
files={x.name:x.read_text() for x in out.iterdir() if x.is_file() and x.name not in ['partitions-private.json','boot-id-private.txt']}
print(json.dumps(dict(summary=report,files=files)))
'''
r=h.ssh('python3 -',input=code.encode(),timeout=130);(p/'stock-layout-host-private.json').write_bytes(r.stdout)
data=json.loads(r.stdout)
target=p/'stock-layout';assert not target.exists();target.mkdir()
for name,value in data['files'].items():assert Path(name).name==name;(target/name).write_text(value)
print(json.dumps(data['summary']))
