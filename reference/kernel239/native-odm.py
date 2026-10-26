"""Read only exact ODM gps.conf and source properties, with no symlink traversal."""
from pathlib import Path
import fcntl,hashlib,json,os,stat,struct,subprocess,time,traceback
os.umask(0o077)
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k236-runtime/boot-id-private.txt').read_bytes()
out=root/'k239-odm-source';assert not out.exists();out.mkdir(mode=0o700)
state=dict(stage=239,state='running',phase='preflight',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
def save(phase=None):
 if phase:state['phase']=phase
 p=out/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');os.replace(p,out/'state-private.json')
def digest(path):
 h=hashlib.sha256()
 with path.open('rb',buffering=0) as f:
  while block:=f.read(4*1024*1024):h.update(block)
 return h.hexdigest()
def command(args,label):
 p=subprocess.run(args,capture_output=True,timeout=30);(out/(label+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,label
 return p.stdout
save();mounted=False;mount=Path('/run/k239-odm-readonly');error=None;report=None;cleanup_errors=[]
try:
 assert json.loads((root/'k239-paired-r14/state-private.json').read_text())['state']=='terminal'
 assert json.loads((root/'k239-paired-r14/summary.json').read_text())['diagnostic_capture_completed']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 found=[]
 for node in Path('/sys/class/block').iterdir():
  values=dict(line.split('=',1) for line in (node/'uevent').read_text().splitlines() if '=' in line)
  if values.get('PARTNAME') in ['odm','odm_a','odm_b']:found.append((node,values))
 (out/'partition-candidates-private.json').write_text(json.dumps([dict(name=n.name,partname=v['PARTNAME']) for n,v in found],indent=2)+'\n')
 exact=[(n,v) for n,v in found if v['PARTNAME']=='odm']
 assert len(exact)==1 and len(found)==1,'Need explicit current-slot source before a slotted ODM read'
 node,values=exact[0];block=Path('/dev')/node.name;info=block.stat();assert stat.S_ISBLK(info.st_mode)
 major_minor=(node/'dev').read_text().strip();assert major_minor==str(os.major(info.st_rdev))+':'+str(os.minor(info.st_rdev))
 fd=os.open(block,os.O_RDONLY|os.O_CLOEXEC)
 try:size=struct.unpack('<Q',fcntl.ioctl(fd,0x80081272,b'\0'*8))[0];magic=os.pread(fd,2,1080)
 finally:os.close(fd)
 assert size==int((node/'size').read_text())*512 and size>0
 (out/'geometry-private.json').write_text(json.dumps(dict(device=str(block),partname='odm',major_minor=major_minor,bytes=size,ext_superblock_magic=magic.hex()),indent=2)+'\n')
 assert magic==b'\x53\xef','ODM is not the expected ext filesystem; do not guess another mount'
 mounts=Path('/proc/self/mountinfo').read_text();(out/'mountinfo-before-private.txt').write_text(mounts)
 assert not any(line.split()[2]==major_minor for line in mounts.splitlines()),'ODM already mounted; inspect owner first'
 assert not mount.exists();save('hashing-exact-odm-before');before=digest(block);(out/'odm-before-private.sha256').write_text(before+'\n')
 mount.mkdir(mode=0o700);command(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],'mount');mounted=True;save('reading-only-gps-and-build-properties')
 lines=[line for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1]==str(mount)];assert len(lines)==1
 options=set(lines[0].split()[3].split(','));assert {'ro','nosuid','nodev','noexec'}<=options and 'rw' not in options
 (out/'mount-options-private.txt').write_text(lines[0]+'\n')
 payload=out/'payload';payload.mkdir(mode=0o700);records={};paths={}
 def selected(relative):
  current=mount
  for part in Path(relative).parts:
   current=current/part
   try:details=current.lstat()
   except FileNotFoundError:paths[relative]=dict(exists=False);return
   if stat.S_ISLNK(details.st_mode):
    paths[relative]=dict(exists=True,symlink=True,at=str(current.relative_to(mount)),target=os.readlink(current),followed=False);return
   if current!=mount/relative:assert stat.S_ISDIR(details.st_mode)
  assert current.resolve().is_relative_to(mount.resolve()) and stat.S_ISREG(details.st_mode) and details.st_size<=65536
  fd=os.open(current,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
  try:data=os.read(fd,65537)
  finally:os.close(fd)
  assert len(data)==details.st_size and len(data)<=65536
  target=payload/relative;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);target.write_bytes(data);target.chmod(0o600)
  records[relative]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),source_mode=stat.S_IMODE(details.st_mode))
  paths[relative]=dict(exists=True,symlink=False,regular=True,bytes=len(data))
 for relative in ['etc/gps.conf','build.prop','etc/build.prop']:selected(relative)
 (out/'exact-paths-private.json').write_text(json.dumps(paths,indent=2)+'\n');(out/'files-manifest-private.json').write_text(json.dumps(records,indent=2)+'\n')
 props={}
 for relative in ['build.prop','etc/build.prop']:
  if relative not in records:continue
  for line in (payload/relative).read_text(errors='replace').splitlines():
   if '=' in line and not line.lstrip().startswith('#'):key,value=line.split('=',1);props[key.strip()]=value.strip()
 (out/'source-properties-private.json').write_text(json.dumps(props,indent=2)+'\n')
 command(['umount',str(mount)],'unmount');mounted=False;save('hashing-exact-odm-after');after=digest(block);(out/'odm-after-private.sha256').write_text(after+'\n');assert after==before
 assert not any(line.split()[4]==str(mount) for line in Path('/proc/self/mountinfo').read_text().splitlines())
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 gps=paths['etc/gps.conf']
 report=dict(stage=239,current236_boot_verified=True,exact_odm_partition_identified=True,geometry_and_ext_superblock_verified=True,readonly_noload_noexec_mount=True,unmounted=True,odm_before_after_equal=True,
             gps_path_exists=gps['exists'],gps_regular_file_copied='etc/gps.conf' in records,gps_symlink_recorded_only=bool(gps.get('symlink')),selected_files=len(records),
             odm_android_release=props.get('ro.odm.build.version.release'),odm_sdk=props.get('ro.odm.build.version.sdk'),
             no_vendor_or_nv_or_persist_read=True,no_vendor_code_executed=True,no_symlink_followed=True,no_gnss_set_or_search=True,private_digest_and_payload_not_published=True,taint=0)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state['exit_code']=0
except BaseException:
 error=traceback.format_exc();(out/'failure-private.txt').write_text(error);state['exit_code']=1
finally:
 if mounted:
  try:command(['umount',str(mount)],'cleanup-unmount');mounted=False
  except BaseException as e:cleanup_errors.append(type(e).__name__)
 state.update(state='terminal',mount_still_owned=mounted,cleanup_errors=cleanup_errors);save('terminal')
if report:print(json.dumps(report),flush=True)
if error:raise SystemExit(1)
