"""Build a precise additive deployment payload; does not access the phone."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile

ref=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/service')
out.mkdir(mode=0o700,exist_ok=True)
build=json.loads((ref/'integrated-build-result.json').read_text())
release='7.3.0-rc6-rmx1931-samurai-k363+'
files={'usr/sbin/samurai-charging':ref/'samurai-charging.py',
       'etc/init.d/samurai-charging':ref/'samurai-charging.openrc',
       'usr/lib/samurai-charging/control-trial.py':ref/'control-trial.py',
       'usr/lib/samurai-charging/live-session.py':ref/'live-session.py'}
modules={}
for name,info in build['modules'].items():
    p=Path(info['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256']
    target='lib/modules/'+release+'/extra/samurai-charging/'+name+'.ko'
    files[target]=p;modules[name]={'target':'/'+target,'sha256':info['sha256']}
meta={'release':release,'modules':modules,'default_input_cap_ua':900000,
    'default_charge_cap_ua':250000,'source_budget_enforced':True,
    'installed_files':{'/'+n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}}
manifest=out/'manifest.json';manifest.write_text(json.dumps(meta,indent=2)+'\n')
files['usr/share/samurai-charging/manifest.json']=manifest
for p in [ref/'samurai-charging.py',ref/'control-trial.py',ref/'live-session.py']:
    compile(p.read_text(),str(p),'exec')
subprocess.run(['sh','-n',str(ref/'samurai-charging.openrc')],check=True)
archive=out/'samurai-charging-payload.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for name,p in files.items():
        info=tar.gettarinfo(p,arcname=name);info.uid=info.gid=0;info.uname=info.gname='root'
        info.mode=0o755 if name.startswith(('usr/sbin/','etc/init.d/')) else 0o600
        with p.open('rb') as f:tar.addfile(info,f)
with tarfile.open(archive) as tar:
    assert {x.name for x in tar.getmembers()}==files.keys()
    for name,p in files.items():assert tar.extractfile(name).read()==p.read_bytes()
report={'payload_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,
    'files':meta['installed_files'],'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
    'default_input_cap_ua':900000,'default_charge_cap_ua':250000,'phase':'offline-payload-build','installed_by_this_build':False,
    'native_provider_unload_policy':'retain until next boot when DWC3 boot property exists',
    'runtime_validation_is_separate':True}
(ref/'service-payload-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
