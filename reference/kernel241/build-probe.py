from pathlib import Path
import importlib.util,base64,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel241')
spec=importlib.util.spec_from_file_location('host241',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
payload=base64.b64encode((R/'loc-differential.c').read_bytes()).decode()
code=r'''
from pathlib import Path
import base64,hashlib,json,os,shlex,subprocess
os.umask(0o077);root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
out=root/'k241-loc-tools';assert not out.exists();out.mkdir(mode=0o700)
source=out/'loc-differential.c';source.write_bytes(base64.b64decode(PAYLOAD))
db=Path('/lib/apk/db/installed').read_bytes();env=json.loads((root/'k190-mm-build/build-environment-private.json').read_text())
flags=subprocess.run(['pkg-config','--cflags','--libs','qmi-glib','qrtr-glib','gio-2.0'],env=env,capture_output=True,text=True,check=True)
args=shlex.split(env['CC'])+['-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(out/'loc-differential')]+shlex.split(flags.stdout)+shlex.split(env.get('LDFLAGS',''))
p=subprocess.run(args,env=env,capture_output=True,timeout=180);(out/'compile-private.log').write_bytes(p.stdout+p.stderr)
assert p.returncode==0,'compile failed; inspect private log'
clean=dict(os.environ);clean.pop('LD_LIBRARY_PATH',None);clean.pop('LD_PRELOAD',None)
p=subprocess.run(['ldd',str(out/'loc-differential')],env=clean,capture_output=True);(out/'ldd-private.txt').write_bytes(p.stdout+p.stderr)
assert p.returncode==0 and b'not found' not in p.stdout+p.stderr
assert Path('/lib/apk/db/installed').read_bytes()==db
r=dict(stage=241,compiled_native=True,system_runtime_libraries_resolved=True,package_database_unchanged=True,
 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((out/'loc-differential').read_bytes()).hexdigest(),
 message_allowlist=[33,34,35,50,51,63,75,136,186,208],observation_seconds=360,
 no_lock_or_nv_configuration=True,no_engine_started_by_build=True)
(out/'build-summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''.replace('PAYLOAD',repr(payload))
run=host.ssh('python3 -',input=code.encode(),timeout=210)
(P/'build-host-private.log').write_bytes(run.stdout+run.stderr)
report=json.loads(run.stdout);(R/'probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
