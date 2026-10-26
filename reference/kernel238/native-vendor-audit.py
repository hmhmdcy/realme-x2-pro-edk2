"""Read the identified vendor filesystem with noload; never run vendor code."""
from pathlib import Path
import hashlib,json,os,re,stat,subprocess,time,traceback
os.umask(0o077)
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k236-runtime/boot-id-private.txt').read_bytes()
out=root/'k238-vendor-audit';assert not out.exists();out.mkdir(mode=0o700)
state=dict(stage=238,state='running',phase='preflight',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
def save(phase=None):
 if phase:state['phase']=phase
 p=out/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');os.replace(p,out/'state-private.json')
def checked(args,label):
 p=subprocess.run(args,capture_output=True);(out/(label+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,label
 return p.stdout
def digest(path):
 h=hashlib.sha256()
 with path.open('rb',buffering=0) as f:
  while chunk:=f.read(4*1024*1024):h.update(chunk)
 return h.hexdigest()
save();mounted=False;mount=Path('/run/k238-vendor-readonly');error=None;report=None;cleanup_errors=[]
try:
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert 'PARTNAME=vendor' in Path('/sys/class/block/sda9/uevent').read_text().splitlines()
 assert Path('/sys/class/block/sda9/size').read_text().strip()=='3342336'
 assert not mount.exists()
 mounts=Path('/proc/self/mountinfo').read_text();(out/'mountinfo-before-private.txt').write_text(mounts)
 assert not any(line.split()[2]==Path('/sys/class/block/sda9/dev').read_text().strip() for line in mounts.splitlines()),'vendor already mounted; inspect existing mount first'
 block=Path('/dev/sda9');save('hashing-vendor-before-readonly');before=digest(block)
 (out/'vendor-before-private.sha256').write_text(before+'  /dev/sda9\n')
 mount.mkdir(mode=0o700);checked(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],'mount');mounted=True;save('reading-version-gnss-files')
 lines=[line for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1]==str(mount)]
 assert len(lines)==1;options=set(lines[0].split()[3].split(','));assert {'ro','nosuid','nodev','noexec'}<=options and 'rw' not in options
 (out/'mount-options-private.txt').write_text(lines[0]+'\n')
 selected=set();links={};payload=out/'payload';payload.mkdir(mode=0o700);total=0;records={}
 def select(p):
  if not p.exists() and not p.is_symlink():return
  relative=str(p.relative_to(mount));assert not relative.startswith('/') and '..' not in Path(relative).parts
  if p.is_symlink():links[relative]=os.readlink(p);return
  assert p.resolve().is_relative_to(mount.resolve()) and stat.S_ISREG(p.stat().st_mode)
  selected.add(p)
 select(mount/'build.prop')
 for directory in ['etc/vintf','etc/vintf/manifest']:
  if (mount/directory).is_dir():
   for p in (mount/directory).glob('*.xml'):
    if p.is_file() and (p.name=='manifest.xml' or b'gnss' in p.read_bytes().lower()):select(p)
 wanted=re.compile(r'gnss|gps|loc_launcher|xtra|izat|location_api|loc_api|loc_core|gps\.utils',re.I)
 for directory in ['etc/init','etc','bin','bin/hw','lib64','lib64/hw','lib','lib/hw']:
  if not (mount/directory).is_dir():continue
  for p in (mount/directory).iterdir():
   if wanted.search(p.name) and (p.is_file() or p.is_symlink()):select(p)
 # RC files can name a service executable whose filename was not in the filter.
 for p in list(selected):
  if p.suffix=='.rc':
   for executable in re.findall(r'^\s*service\s+\S+\s+(/vendor/\S+)',p.read_text(errors='replace'),re.M):select(mount/executable.removeprefix('/vendor/'))
 for p in sorted(selected):
  data=p.read_bytes();total+=len(data);assert total<=64*1024*1024
  relative=str(p.relative_to(mount));dest=payload/relative;dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700);dest.write_bytes(data);dest.chmod(0o600)
  records[relative]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),source_mode=stat.S_IMODE(p.stat().st_mode),elf=data.startswith(b'\x7fELF'))
 assert 'build.prop' in records
 props={}
 for line in (payload/'build.prop').read_text(errors='replace').splitlines():
  if '=' in line and not line.lstrip().startswith('#'):k,v=line.split('=',1);props[k.strip()]=v.strip()
 (out/'source-properties-private.json').write_text(json.dumps(props,indent=2)+'\n')
 (out/'files-manifest-private.json').write_text(json.dumps(records,indent=2)+'\n');(out/'symlinks-private.json').write_text(json.dumps(links,indent=2)+'\n')
 checked(['umount',str(mount)],'unmount');mounted=False
 save('hashing-vendor-after-readonly');after=digest(block);(out/'vendor-after-private.sha256').write_text(after+'  /dev/sda9\n');assert after==before
 assert not any(line.split()[4]==str(mount) for line in Path('/proc/self/mountinfo').read_text().splitlines())
 assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 report=dict(stage=238,current236_boot=True,identified_vendor_partition_geometry=True,readonly_noload_noexec_mount=True,unmounted=True,vendor_before_after_equal=True,
  selected_files=len(records),selected_bytes=total,elf_files=sum(r['elf'] for r in records.values()),symlink_metadata_only=len(links),
  vendor_android_release=props.get('ro.vendor.build.version.release'),vendor_sdk=props.get('ro.vendor.build.version.sdk'),vendor_security_patch=props.get('ro.vendor.build.security_patch'),
  no_vendor_code_executed=True,no_nv_or_persist_read=True,no_gnss_set_or_search=True,private_fingerprints_and_partition_digest_not_published=True,taint=0)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state.update(exit_code=0)
except BaseException:
 error=traceback.format_exc();(out/'failure-private.txt').write_text(error);state.update(exit_code=1)
finally:
 if mounted:
  try:checked(['umount',str(mount)],'cleanup-unmount');mounted=False
  except BaseException as e:cleanup_errors.append(type(e).__name__)
 state.update(state='terminal',mount_still_owned=mounted,cleanup_errors=cleanup_errors);save('terminal')
if report:print(json.dumps(report),flush=True)
if error:raise SystemExit(1)
