from pathlib import Path
import hashlib,host,json,shlex

here=Path(__file__).resolve().parent
proof=json.loads((here/'factory-mode-candidate-build-validation.json').read_text())
binary=(host.PRIVATE/'candidate-build/imx471-factory-modes.ko').read_bytes()
assert len(binary)<65536 and hashlib.sha256(binary).hexdigest()==proof['module_sha256']
stage="from pathlib import Path;import hashlib,sys;base=Path('/var/lib/samurai/k219-baseline');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes();p=base/'imx471-candidate.ko';assert not p.exists();data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()=="+repr(proof['module_sha256'])+";p.write_bytes(data);p.chmod(0o600)"
assert host.ssh('python3 -c '+shlex.quote(stage),input=binary,timeout=30).returncode==0
builder=here.parent/'kernel215/reload-after-unbind.py'
prefix=builder.read_text().split("p=host.ssh('python3 -'",1)[0]
prefix=prefix.replace("proof=json.loads((here/'imx471-module-build-validation.json').read_text())","proof="+repr(proof))
prefix=prefix.replace("assert json.loads((here/'reload-ref-validation.json').read_text())['module_file_matches_original']",'')
namespace={'__file__':str(builder)};exec(compile(prefix,'normal-unbind-code-generator219','exec'),namespace)
code=namespace['code']
code=code.replace('6b2bb0b47b93c6bf12eb8e137592c203f12fa96fcf9551553c48cc35ccad9d9c',proof['module_sha256'])
code=code.replace('a28dd67a03afa9e918f87b85030f0158edecbcc2e3f1ce0a36405b78be70ba6a','1388a070e9c902e6b23b3896ce1f50f8f0e44f68d5243ed73e897dcaee186a5b')
code=code.replace('k215-','k219-').replace('stage=215','stage=219')
lines=code.splitlines();removed=[line for line in lines if "assert json.loads((root/'k219-driver-test/transition-state-private.json')" in line];assert len(removed)==1
code='\n'.join(line for line in lines if line not in removed)+'\n'
compile(code,'native-mode-driver219','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=150)
(host.PRIVATE/'module-reload-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
assert report['new_sensor_module_installed'] and not report['transition_failure'] and report['taint']==0 and not any(report['fault_delta'].values())
(here/'module-reload-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
