"""Adapt the previously verified Image183 quiesce/restart sequence to this exact transaction."""
from pathlib import Path
import base64,hashlib,json
import host

ROOT=Path(__file__).resolve().parent
assert json.loads((ROOT/'module-staging-validation.json').read_text())['all778_installed_hashes_verified']
assert not json.loads((ROOT/'preserved-source-validation.json').read_text())['differences']
package=json.loads((ROOT/'boot-package-validation.json').read_text())
sources={}
for name in ['native-quiesce.py','restart-bootloader.py']:
    s=(ROOT.parent/'kernel276'/name).read_text().replace('k276','k288').replace('stage=276','stage=288').replace('k275-work','k276-work')
    if name=='native-quiesce.py':
        before="assert json.loads((r/'k288-cci-transaction-r2/summary.json').read_text())['new_module_staged']"
    else:
        before="assert json.loads((r/'k288-cci-transaction-r2/state-private.json').read_text())['exit_code']==0"
    assert before in s
    s=s.replace(before,"assert json.loads((r/'k288-deployment/module-install-validation-private.json').read_text())['all778_installed_hashes_verified']")
    compile(s,name,'exec')
    p=ROOT/name;assert not p.exists();p.write_text(s);sources[name]=s
args={n:base64.b64encode(s.encode()).decode() for n,s in sources.items()}
code=r'''
from pathlib import Path
import base64,hashlib,json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k276-work/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert json.loads((r/'k288-deployment/module-install-validation-private.json').read_text())['all778_installed_hashes_verified']
assert not (r/'k288-quiesce').exists()
p=r/'k288-tools';assert not p.exists();p.mkdir(mode=0o700)
for name,data in args.items():
 f=p/name;f.write_bytes(base64.b64decode(data));compile(f.read_bytes(),name,'exec')
print(json.dumps(dict(stage=288,transition_tools_prepared=True,current_boot276_verified=True,no_services_stopped=True)))
'''
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=20)
(host.PRIVATE/'transition-tools-private.json').write_bytes(q.stdout)
files={}
for label,path,sha in [
    ('candidate',host.PRIVATE/'logdump-pix288-candidate-private.img',package['logdump_sha256']),
    ('rollback',host.PRIVATE.parent/'kernel183/logdump-k183-offline-stream.img',package['rollback_logdump_sha256']),
    ('firmware_boot',host.PRIVATE.parent/'kernel276/boot-partition-k276-cci-io.img',package['firmware_boot_preserved_sha256'])]:
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
    files[label]=dict(path=str(path),sha256=sha,bytes=path.stat().st_size)
(host.PRIVATE/'deployment-lock-private.json').write_text(json.dumps(dict(stage=288,files=files,package=package),indent=2)+'\n')
print(q.stdout.decode())
