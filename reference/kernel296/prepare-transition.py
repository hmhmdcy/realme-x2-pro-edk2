"""Lock the verified current boot, rollback image and native restart tools after module staging."""
from pathlib import Path
import base64,hashlib,json
import host

ROOT=Path(__file__).resolve().parent
assert json.loads((ROOT/'module-staging-validation.json').read_text())['all778_installed_hashes_verified']
package=json.loads((ROOT/'boot-package-validation.json').read_text())
sources={n:(ROOT/n).read_bytes() for n in ['native-quiesce.py','restart-bootloader.py']}
args={n:base64.b64encode(data).decode() for n,data in sources.items()}
code=r'''
from pathlib import Path
import base64,json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k295-work/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#295 ') and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k295+'
assert json.loads((r/'k296-deployment/module-install-validation-private.json').read_text())['all778_installed_hashes_verified']
assert not (r/'k296-quiesce').exists()
p=r/'k296-tools';assert p.is_dir()
for name,data in args.items():
 f=p/name;assert not f.exists();f.write_bytes(base64.b64decode(data));compile(f.read_bytes(),name,'exec')
for addr in ['1-0039','1-003a']:assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices',addr,'status').read_text()
print(json.dumps(dict(stage=296,transition_tools_prepared=True,current_boot295_verified=True,audio_idle_addresses_verified=True,no_services_stopped=True)))
'''
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=20)
(host.PRIVATE/'transition-tools-private.json').write_bytes(q.stdout)
files={}
for label,path,sha in [('candidate',host.PRIVATE/'logdump-k296-candidate-private.img',package['logdump_sha256']),
 ('rollback',host.PRIVATE.parent/'kernel290/logdump-k290-candidate-private.img',package['rollback_logdump_sha256']),
 ('firmware_boot',host.PRIVATE.parent/'kernel276/boot-partition-k276-cci-io.img',package['firmware_boot_preserved_sha256'])]:
 assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
 files[label]=dict(path=str(path),sha256=sha,bytes=path.stat().st_size)
(host.PRIVATE/'deployment-lock-private.json').write_text(json.dumps(dict(stage=296,files=files,package=package),indent=2)+'\n');print(q.stdout.decode())
