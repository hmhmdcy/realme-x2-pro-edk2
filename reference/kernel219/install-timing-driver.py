from pathlib import Path
import hashlib,host,json,shlex

here=Path(__file__).resolve().parent;proof=json.loads((here/'timing-candidate-build-validation.json').read_text())
binary=(host.PRIVATE/'timing-build/imx471-factory-modes.ko').read_bytes()
assert len(binary)<65536 and hashlib.sha256(binary).hexdigest()==proof['module_sha256']
prepare=r'''
from pathlib import Path
import hashlib,os,shutil
root=Path('/var/lib/samurai');base=root/'k219-timing-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
assert not base.exists();base.mkdir(mode=0o700)
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()=='d82c941d4b7b1a66e616a8ecc09558afd19385ca7a0b4860be0b6f05bd2c354c'
for path,name in [(Path('/proc/sys/kernel/random/boot_id'),'boot-id-private.txt'),(module,'imx471-original.ko'),(Path('/lib/apk/db/installed'),'installed-before-private.txt')]:shutil.copyfile(path,base/name)
'''
host.ssh('python3 -',input=prepare.encode(),timeout=30)
stage="from pathlib import Path;import hashlib,sys;d=sys.stdin.buffer.read();assert hashlib.sha256(d).hexdigest()=="+repr(proof['module_sha256'])+";p=Path('/var/lib/samurai/k219-timing-baseline/imx471-candidate.ko');assert not p.exists();p.write_bytes(d);p.chmod(0o600)"
host.ssh('python3 -c '+shlex.quote(stage),input=binary,timeout=30)
builder=here.parent/'kernel215/reload-after-unbind.py'
prefix=builder.read_text().split("p=host.ssh('python3 -'",1)[0]
prefix=prefix.replace("proof=json.loads((here/'imx471-module-build-validation.json').read_text())","proof="+repr(proof))
prefix=prefix.replace("assert json.loads((here/'reload-ref-validation.json').read_text())['module_file_matches_original']",'')
namespace={'__file__':str(builder)};exec(compile(prefix,'timing-unbind-code-generation','exec'),namespace)
code=namespace['code'].replace('6b2bb0b47b93c6bf12eb8e137592c203f12fa96fcf9551553c48cc35ccad9d9c',proof['module_sha256'])
code=code.replace('a28dd67a03afa9e918f87b85030f0158edecbcc2e3f1ce0a36405b78be70ba6a','d82c941d4b7b1a66e616a8ecc09558afd19385ca7a0b4860be0b6f05bd2c354c')
code=code.replace('k215-','k219-timing-').replace('stage=215','stage=219')
lines=code.splitlines();removed=[line for line in lines if "assert json.loads((root/'k219-timing-driver-test/transition-state-private.json')" in line];assert len(removed)==1
code='\n'.join(l for l in lines if l not in removed)+'\n'
p=host.ssh('python3 -',input=code.encode(),timeout=150)
(host.PRIVATE/'timing-module-reload-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);assert report['new_sensor_module_installed'] and report['taint']==0 and not any(report['fault_delta'].values())
(here/'timing-module-reload-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
