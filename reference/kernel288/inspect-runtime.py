"""Read current transport, tooling and boot storage before preparing hardware tests."""
from pathlib import Path
import hashlib, json
import host

ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
tools={n:shutil.which(n) for n in ['media-ctl','v4l2-ctl','yavta','depmod','tar','gcc','cc','mcopy','fsck.fat']}
parts={}
for n in ['boot','logdump']:
 p=Path('/dev/disk/by-partlabel')/n
 if not p.exists():p=next(p for p in Path('/dev/disk/by-partlabel').iterdir() if p.name.lower()==n)
 parts[n]=dict(sha256=digest(p))
root=os.statvfs('/');refs=[]
for directory in ['/etc/init.d','/etc/conf.d','/etc/modules-load.d','/usr/local/bin','/usr/local/sbin']:
 for p in Path(directory).glob('*'):
  if p.is_file() and p.stat().st_size<256*1024:
   try:s=p.read_text()
   except (UnicodeError,OSError):continue
   if '7.3.0-rc6-rmx1931-samurai-k132+' in s:refs.append(str(p))
media=''
if tools['media-ctl']:
 q=subprocess.run([tools['media-ctl'],'-d','/dev/media0','-p'],text=True,capture_output=True,timeout=8);assert q.returncode==0;media=q.stdout
 Path('/var/lib/samurai/k288-media-graph-private.txt').write_text(media)
report=dict(stage=288,release=os.uname().release,tools=tools,root_free_bytes=root.f_bavail*root.f_frsize,
            module_directories=sorted(p.name for p in Path('/usr/lib/modules').iterdir() if p.is_dir()),
            old_release_references_in_startup_paths=refs,partitions=parts,
            existing_pix_entity='msm_vfe0_pix' in media,
            media_graph_collected=bool(media),read_only_hardware=True,no_streaming=True)
print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=40)
(host.PRIVATE/'runtime-preparation-private.json').write_bytes(r.stdout)
report=json.loads(r.stdout)
assert report['release']=='7.3.0-rc6-rmx1931-samurai-k132+'
assert report['partitions']['boot']['sha256']=='0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64'
assert report['partitions']['logdump']['sha256']=='e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'
(ROOT/'runtime-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
