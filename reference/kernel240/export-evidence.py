"""Export all scoped240 diagnostics privately, excluding APK caches and media."""
from pathlib import Path
import hashlib,io,json,tarfile
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077);r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
h=json.loads((r/'k240-final-health/summary.json').read_text())
assert h['taint']==0 and h['snapshot_per_user_desktop_and_real_dbus_cpu_flags_verified']
assert not any(h['fault_delta_since_faulting_snapshot_stopped'].values()) and h['fault_counts']['gpu']>0
out=r/'k240-evidence';assert not out.exists()
contexts=[p for p in sorted(r.glob('k240-*')) if p.is_dir() and p.name not in ['k240-tools','k240-snapshot-host-packages','k240-evidence']]
files=[]
for context in contexts:
 for p in sorted(context.rglob('*')):
  if not p.is_file():continue
  assert not p.is_symlink()
  if any(part in ['cache','apks','keys'] for part in p.relative_to(context).parts):continue
  if p.suffix in ['.apk','.adb']:continue
  assert p.suffix.lower() not in ['.raw','.dng','.png','.jpg','.jpeg','.rgb','.mp4','.webm']
  files.append(p)
for p in sorted((r/'k240-snapshot-host-packages').iterdir()):
 if p.is_file() and (p.name in ['manifest.json','summary.json'] or p.name.endswith('-verify-private.log')):files.append(p)
files.append(r/'k240-tools/idle-policy-identity-private.json')
assert len(set(files))==len(files);out.mkdir(mode=0o700)
manifest={str(p.relative_to(r)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files}
with tarfile.open(out/'evidence-private.tar.gz','w:gz') as a:
 for p in files:a.add(p,arcname=str(p.relative_to(r)),recursive=False)
data=(out/'evidence-private.tar.gz').read_bytes();meta=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),contexts=len(contexts),files=manifest)
(out/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=50)
target=host.PRIVATE/'native-evidence-manifest-private.json';assert not target.exists();target.write_bytes(p.stdout)
meta=json.loads(p.stdout);data=bytearray()
for start in range(0,meta['bytes'],48*1024):
 count=min(48*1024,meta['bytes']-start)
 code="from pathlib import Path;import sys;f=Path('/var/lib/samurai/k240-evidence/evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()"%(start,count)
 block=host.ssh('python3 -',input=code.encode(),timeout=25).stdout;assert len(block)==count;data.extend(block)
 if start%(8*48*1024)==0:print(json.dumps(dict(private_evidence_bytes_received=len(data),total=meta['bytes'])),flush=True)
assert hashlib.sha256(data).hexdigest()==meta['sha256']
target=host.PRIVATE/'native-evidence-private.tar.gz';assert not target.exists();target.write_bytes(data)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as a:
 members=a.getmembers();assert len(members)==len(meta['files']) and {m.name for m in members}==set(meta['files'])
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  b=a.extractfile(m).read();expected=meta['files'][m.name]
  assert len(b)==expected['bytes'] and hashlib.sha256(b).hexdigest()==expected['sha256']
report=dict(stage=240,native_members=len(members),native_contexts=meta['contexts'],all_members_verified=True,
 failures_default_vulkan_faults_and_cpu_mmap_results_retained=True,package_and_launcher_transactions_retained=True,
 no_scene_pixels_saved_or_transferred=True,no_apks_or_repository_caches_in_archive=True,usb_chunk_bytes=48*1024)
(R/'evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
