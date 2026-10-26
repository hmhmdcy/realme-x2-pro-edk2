"""Stage a distinct kernel release; keep the running362 camera tree intact."""
from pathlib import Path
import hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent
package=json.loads((HERE/'boot-package-validation.json').read_text());assert package['kernel_build']==363
data=(host.PRIVATE/'modules-k363-private.tar.gz').read_bytes();assert hashlib.sha256(data).hexdigest()==package['module_archive']['sha256']
adopted=json.loads((host.PRIVATE.parent/'kernel360/recovered-boot-adoption-private.json').read_text())
manifest=dict(release=package['release'],sha256=package['module_archive']['sha256'],bytes=len(data),guard=adopted['guard_path'])
code=r'''
from pathlib import Path
import hashlib,io,json,os,subprocess,sys,tarfile
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(meta['guard']).read_bytes()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k298+'
root=Path('/var/lib/samurai/k363-deployment');assert not root.exists();root.mkdir(mode=0o700)
(root/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
blob=sys.stdin.buffer.read();assert len(blob)==meta['bytes'] and hashlib.sha256(blob).hexdigest()==meta['sha256']
(root/'modules-private.tar.gz').write_bytes(blob)
stage=root/'stage';stage.mkdir();prefix='usr/lib/modules/'+meta['release'];target=Path('/usr/lib/modules')/meta['release'];assert not target.exists()
with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
 members=tar.getmembers();assert all(m.name==prefix or m.name.startswith(prefix+'/') for m in members)
 assert all('..' not in Path(m.name).parts and (m.isfile() or m.isdir()) for m in members)
 assert sum(m.name.endswith('.ko') for m in members)==778
 tar.extractall(stage,filter='data')
source=stage/prefix;assert source.stat().st_dev==target.parent.stat().st_dev
inventory={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*.ko')};assert len(inventory)==778
(root/'module-inventory-private.json').write_text(json.dumps(inventory))
source.rename(target)
q=subprocess.run(['depmod','-a',meta['release']],capture_output=True);assert not q.returncode and not q.stderr
for name in ['qcom_camss','s5kgw1','s5k3m5','imx319','imx471']:
 assert subprocess.check_output(['modinfo','-k',meta['release'],'-F','vermagic',name],text=True).split()[0]==meta['release']
report=dict(stage=363,new_release=meta['release'],new_modules=778,distinct_release_staged=True,running_release=os.uname().release,loaded_new_modules=False,kernel_not_switched=True,all778_installed_hashes_verified=True)
(root/'module-install-validation-private.json').write_text(json.dumps(report));os.sync();print(json.dumps(report))
'''
q=host.ssh('python3 -c '+shlex.quote('meta='+repr(manifest)+'\n'+code),input=data,timeout=60)
report=json.loads(q.stdout);(HERE/'module-staging-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
