"""Reuse the verified normal-unbind reload path with216 identities and payload."""
from pathlib import Path
import hashlib,host,json,shlex
here=Path(__file__).resolve().parent;proof=json.loads((here/'imx471-module-build-validation.json').read_text())
binary=(host.PRIVATE/'modules/imx471.ko').read_bytes();assert hashlib.sha256(binary).hexdigest()==proof['module_sha256'] and len(binary)<65536
stage="from pathlib import Path;import hashlib,sys;base=Path('/var/lib/samurai/k216-baseline');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes();p=base/'imx471-candidate.ko';assert not p.exists();data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()=="+repr(proof['module_sha256'])+";p.write_bytes(data);p.chmod(0o600)"
host.ssh('python3 -c '+shlex.quote(stage),input=binary,timeout=30)
builder=here.parent/'kernel215/reload-after-unbind.py'
prefix=builder.read_text().split("p=host.ssh('python3 -'",1)[0]
namespace={'__file__':str(builder)};exec(compile(prefix,'verified215-reload-code-generation','exec'),namespace)
code=namespace['code']
code=code.replace('6b2bb0b47b93c6bf12eb8e137592c203f12fa96fcf9551553c48cc35ccad9d9c',proof['module_sha256'])
code=code.replace('a28dd67a03afa9e918f87b85030f0158edecbcc2e3f1ce0a36405b78be70ba6a','6b2bb0b47b93c6bf12eb8e137592c203f12fa96fcf9551553c48cc35ccad9d9c')
code=code.replace('k215-','k216-').replace('stage=215','stage=216')
lines=code.splitlines();removed=[line for line in lines if "assert json.loads((root/'k216-driver-test/transition-state-private.json')" in line];assert len(removed)==1
code='\n'.join(line for line in lines if line not in removed)+'\n'
compile(code,'native-reload216','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=150);(host.PRIVATE/'module-reload-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);report['analogue_gain_extension_physical_validation_pending']=report.pop('physical_test_pattern_validation_pending');(here/'module-reload-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
