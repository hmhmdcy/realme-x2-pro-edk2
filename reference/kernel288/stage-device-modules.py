"""Stage the complete matching module tree without altering the running kernel's tree."""
from pathlib import Path
import hashlib,json,shlex,time
import host

ROOT=Path(__file__).resolve().parent
package=json.loads((ROOT/'boot-package-validation.json').read_text())
archive=host.PRIVATE/'modules-pix288-private.tar.gz'
data=archive.read_bytes()
assert len(data)==package['module_archive']['bytes'] and hashlib.sha256(data).hexdigest()==package['module_archive']['sha256']
target='/var/lib/samurai/k288-deployment'
prepare=r'''
from pathlib import Path
import json,os
p=Path('/var/lib/samurai/k288-deployment');assert not p.exists();p.mkdir(mode=0o700)
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k132+'
assert not Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k279candidate+').exists()
(p/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
(p/'modules-private.tar.gz.part').write_bytes(b'')
print(json.dumps(dict(prepared=True)))
'''
q=host.ssh('python3 -',input=prepare.encode(),timeout=15)
assert json.loads(q.stdout)['prepared']
start=time.monotonic()
for offset in range(0,len(data),65536):
    block=data[offset:offset+65536]
    code=f'''from pathlib import Path
import hashlib,json,os,sys
p=Path({target!r})
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(p/'boot-id-private.txt').read_bytes()
f=p/'modules-private.tar.gz.part';assert f.stat().st_size=={offset}
b=sys.stdin.buffer.read();assert len(b)=={len(block)} and hashlib.sha256(b).hexdigest()=={hashlib.sha256(block).hexdigest()!r}
with f.open('ab') as w:w.write(b);w.flush();os.fsync(w.fileno())
print(json.dumps(dict(written=f.stat().st_size)))
'''
    q=host.ssh('python3 -c '+shlex.quote(code),input=block,timeout=15)
    assert json.loads(q.stdout)['written']==offset+len(block)
    if offset//65536%16==0:print(json.dumps(dict(bytes=offset+len(block),total=len(data))),flush=True)
final=r'''
from pathlib import Path
import hashlib,json,os,subprocess,tarfile
p=Path('/var/lib/samurai/k288-deployment')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(p/'boot-id-private.txt').read_bytes()
part=p/'modules-private.tar.gz.part';archive=p/'modules-private.tar.gz'
assert not archive.exists() and part.stat().st_size==BYTES and hashlib.sha256(part.read_bytes()).hexdigest()==SHA
part.rename(archive)
release=RELEASE;stage=p/'stage';assert not stage.exists();stage.mkdir(mode=0o700)
prefix='usr/lib/modules/'+release
with tarfile.open(archive) as tar:
 members=tar.getmembers()
 assert all(m.name==prefix or m.name.startswith(prefix+'/') for m in members)
 assert all('..' not in Path(m.name).parts and not m.issym() and not m.islnk() for m in members)
 assert sum(m.name.endswith('.ko') for m in members)==778
 tar.extractall(stage,filter='data')
source=stage/prefix;target=Path('/usr/lib/modules')/release;assert not target.exists()
assert source.stat().st_dev==target.parent.stat().st_dev
current=Path('/usr/lib/modules')/os.uname().release
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(f.relative_to(current)):sha(f) for f in current.rglob('*.ko')};assert len(before)==776
inventory={str(f.relative_to(source)):sha(f) for f in source.rglob('*.ko')};assert len(inventory)==778
(p/'module-inventory-private.json').write_text(json.dumps(inventory,indent=2)+'\n')
source.rename(target)
q=subprocess.run(['depmod','-a',release],capture_output=True);assert q.returncode==0 and not q.stderr
for name in ['qcom_camss','i2c_qcom_cci','s5k3m5','s5kgw1','imx319','imx471','lc898219xi']:
 assert subprocess.check_output(['modinfo','-k',release,'-F','vermagic',name],text=True).split()[0]==release
assert before=={str(f.relative_to(current)):sha(f) for f in current.rglob('*.ko')}
assert inventory=={str(f.relative_to(target)):sha(f) for f in target.rglob('*.ko')}
os.sync()
report=dict(stage=288,new_release=release,new_modules=778,running_release=os.uname().release,
            all776_running_release_modules_preserved=True,all778_installed_hashes_verified=True,
            explicit_release_depmod_pass=True,loaded_new_modules=False,kernel_not_switched=True)
(p/'module-install-validation-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
final=final.replace('BYTES',str(len(data))).replace('SHA',repr(package['module_archive']['sha256'])).replace('RELEASE',repr(package['release']))
q=host.ssh('python3 -',input=final.encode(),timeout=45)
report=json.loads(q.stdout);report['upload_seconds']=round(time.monotonic()-start,2)
(ROOT/'module-staging-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(host.PRIVATE/'module-staging-validation-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
