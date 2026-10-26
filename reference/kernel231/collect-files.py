from pathlib import Path
import hashlib,importlib.util,io,json,tarfile
root=Path('/mnt/e/RealmeX2Pro edk2');private=Path('/mnt/e/edk2-samurai-out/kernel231')
spec=importlib.util.spec_from_file_location('host230',root/'reference/kernel230/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
host.PRIVATE=private;host.transport.PRIVATE=private
endpoint=private/'usb-ipv6-candidates-private.json';assert not endpoint.exists();endpoint.write_bytes((private.parent/'kernel230/usb-ipv6-candidates-private.json').read_bytes())
code=r'''
from pathlib import Path
import dbus,hashlib,json,os,stat,tarfile,time
os.umask(0o077)
root=Path('/var/lib/samurai');base=Path('/run/samurai-wifi');out=root/'k231-file-service-audit'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k230-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not out.exists()
b=dbus.SystemBus(private=True);objs=dbus.Interface(b.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();paths=[p for p,v in objs.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(paths)==1
loc=dbus.Interface(b.get_object('org.freedesktop.ModemManager1',paths[0]),'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(loc['Enabled'])==0;b.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert not watch['active'] and watch['worker_starts']==watch['worker_completions']==0
out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot)
def st(s):return dict(dev=s.st_dev,inode=s.st_ino,bytes=s.st_size,mtime_ns=s.st_mtime_ns,mode=stat.S_IMODE(s.st_mode))
def identity(name):
 p=base/(name+'.pid');pid=int(p.read_text());proc=Path('/proc')/str(pid)
 raw=(proc/'stat').read_text();start=raw.rsplit(')',1)[1].split()[19]
 exe=(proc/'exe').resolve(strict=True)
 env={}
 for row in (proc/'environ').read_bytes().split(b'\0'):
  if b'=' in row:
   k,v=row.split(b'=',1)
   if k in [b'SAMURAI_TFTP_RW_ROOT',b'SAMURAI_TFTP_FIRMWARE_ROOT']:env[k.decode()]=v.decode()
 logs={}
 for fd in ['1','2']:logs[fd]=os.readlink(proc/'fd'/fd)
 result=dict(pid=pid,start_ticks=start,exe=str(exe),exe_sha256=hashlib.sha256((proc/'exe').read_bytes()).hexdigest(),cmdline=(proc/'cmdline').read_bytes().decode().split('\0'),environment=env,stdout_stderr=logs,pid_file=st(p.stat()))
 assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==start
 return result
before={name:identity(name) for name in ['tftp','rmtfs']}
(out/'processes-before-private.json').write_text(json.dumps(before,indent=2)+'\n')
logs={}
for name in ['tftp','rmtfs']:
 path=base/(name+'.log')
 with path.open('rb') as f:
  first=os.fstat(f.fileno());assert stat.S_ISREG(first.st_mode) and first.st_size<32*1024*1024
  size=first.st_size;data=f.read(size);last=os.fstat(f.fileno())
 (out/(name+'-snapshot-private.log')).write_bytes(data)
 logs[name]=dict(before=st(first),after=st(last),path_after=st(path.stat()),copied_bytes=len(data),complete_open_size=len(data)==size,append_allowed=True,monotonic_before=time.monotonic())
(out/'log-snapshot-metadata-private.json').write_text(json.dumps(logs,indent=2)+'\n')
sources=['/etc/samurai-wifi/modem-sha256.txt','/run/samurai-wifi/firmware-check.txt','/run/samurai-wifi/mcfg-prepare.log','/run/samurai-wifi/mcfg-state/source-manifest-private.json','/run/samurai-wifi/nv-snapshot-sha256.txt','/run/samurai-wifi/nv-source-hashes.txt']
files={}
for i,name in enumerate(sources):
 path=Path(name);entry=dict(exists=path.exists());files[name]=entry
 if path.is_file():
  meta=path.stat();assert stat.S_ISREG(meta.st_mode) and meta.st_size<8*1024*1024
  data=path.read_bytes();target='source-'+str(i)+'-private.txt';(out/target).write_bytes(data);entry.update(snapshot=target,stat=st(meta),bytes=len(data))
(out/'source-files-private.json').write_text(json.dumps(files,indent=2)+'\n')
rows=[]
rw=base/'tftp-rw';assert rw.is_dir()
for path in sorted(rw.rglob('*')):
 meta=path.lstat();rows.append(dict(relative=str(path.relative_to(rw)),stat=st(meta),file_type=stat.S_IFMT(meta.st_mode),symlink=os.readlink(path) if path.is_symlink() else None))
(out/'tftp-rw-stat-only-private.json').write_text(json.dumps(rows,indent=2)+'\n')
mounts=[line for line in Path('/proc/self/mountinfo').read_text().splitlines() if 'samurai-wifi' in line]
(out/'runtime-mounts-private.txt').write_text('\n'.join(mounts)+'\n')
after={name:identity(name) for name in ['tftp','rmtfs']}
(out/'processes-after-private.json').write_text(json.dumps(after,indent=2)+'\n')
stable=all(before[n]==after[n] for n in before)
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
report=dict(stage=231,guard_current230=True,gps_inactive=True,no_new_session=True,process_identities_unchanged=stable,log_lines={n:len((out/(n+'-snapshot-private.log')).read_bytes().splitlines()) for n in logs},log_complete_open_size={n:v['complete_open_size'] for n,v in logs.items()},no_service_restart_or_power_or_nv_write=True,rw_payloads_not_read=True,log_time_scope='current boot230; not a GNSS session timeline')
(out/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
members=[p for p in sorted(out.iterdir()) if p.is_file()]
manifest={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in members}
with tarfile.open(out/'snapshot-private.tar.gz','w:gz') as archive:
 for path in members:archive.add(path,arcname=path.name,recursive=False)
data=(out/'snapshot-private.tar.gz').read_bytes();meta=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),files=manifest,summary=report)
(out/'transfer-manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=60)
(private/'native-manifest-private.json').write_bytes(result.stdout);meta=json.loads(result.stdout)
data=bytearray()
for start in range(0,meta['bytes'],48*1024):
 count=min(48*1024,meta['bytes']-start)
 script="from pathlib import Path;import sys;f=Path('/var/lib/samurai/k231-file-service-audit/snapshot-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()"%(start,count)
 part=host.ssh('python3 -',input=script.encode(),timeout=25).stdout;assert len(part)==count;data.extend(part)
assert hashlib.sha256(data).hexdigest()==meta['sha256'];(private/'snapshot-private.tar.gz').write_bytes(data)
target=private/'native-snapshot';assert not target.exists();target.mkdir()
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 members=archive.getmembers();assert {m.name for m in members}==set(meta['files'])
 for member in members:
  assert member.isfile() and Path(member.name).name==member.name
  content=archive.extractfile(member).read();expected=meta['files'][member.name]
  assert len(content)==expected['bytes'] and hashlib.sha256(content).hexdigest()==expected['sha256'];(target/member.name).write_bytes(content)
report=meta['summary'];report.update(archive_members=len(members),all_members_verified=True,private_fingerprints_not_published=True)
(private/'collection-validation-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
