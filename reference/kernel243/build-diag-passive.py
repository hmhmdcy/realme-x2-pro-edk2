from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,shlex,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
o=root/'k243-diag-tools-r3';assert not o.exists();o.mkdir(mode=0o700);src=o/'diag-passive.c';src.write_bytes(base64.b64decode(PAYLOAD))
db=Path('/lib/apk/db/installed').read_bytes();env=json.loads((root/'k190-mm-build/build-environment-private.json').read_text())
args=shlex.split(env['CC'])+['-std=c11','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(o/'diag-passive')]+shlex.split(env.get('LDFLAGS',''))
x=subprocess.run(args,env=env,capture_output=True,timeout=90);(o/'build-private.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,'Inspect build log before retry'
assert db==Path('/lib/apk/db/installed').read_bytes()
report=dict(stage=243,native_build_passed=True,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((o/'diag-passive').read_bytes()).hexdigest(),package_database_unchanged=True,diagnostic_payloads_sent_by_probe=0,no_probe_run_by_build=True)
(o/'build-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('PAYLOAD',repr(base64.b64encode((R/'diag-passive.c').read_bytes()).decode()))
x=host.ssh('python3 -',input=code.encode(),timeout=105);(P/'diag-build-r3-host-private.log').write_bytes(x.stdout+x.stderr)
report=json.loads(x.stdout);(R/'diag-build-r3-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
