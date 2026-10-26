from pathlib import Path
import host,json,base64
here=Path(__file__).resolve().parent
payload=base64.b64encode((here/'loc-readonly.c').read_bytes()).decode()
code=r'''
from pathlib import Path
import base64,hashlib,json,os,shlex,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k221-baseline/boot-id-private.txt').read_bytes()
out=root/'k221-loc-readonly-r3';assert not out.exists();out.mkdir(mode=0o700)
source=out/'loc-readonly.c';source.write_bytes(base64.b64decode(PAYLOAD))
db=Path('/lib/apk/db/installed').read_bytes();env=json.loads((root/'k190-mm-build/build-environment-private.json').read_text())
flags=subprocess.run(['pkg-config','--cflags','--libs','qmi-glib','qrtr-glib','gio-2.0'],env=env,capture_output=True,text=True,check=True)
(out/'pkg-flags-private.txt').write_text(flags.stdout+flags.stderr)
args=shlex.split(env['CC'])+['-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(out/'loc-readonly')]+shlex.split(flags.stdout)+shlex.split(env.get('LDFLAGS',''))
p=subprocess.run(args,env=env,capture_output=True,timeout=180);(out/'compile-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
clean=dict(os.environ);clean.pop('LD_LIBRARY_PATH',None);clean.pop('LD_PRELOAD',None)
p=subprocess.run(['ldd',str(out/'loc-readonly')],env=clean,capture_output=True);(out/'ldd-private.txt').write_bytes(p.stdout+p.stderr);assert p.returncode==0 and b'not found' not in p.stdout+p.stderr
assert Path('/lib/apk/db/installed').read_bytes()==db
r=dict(stage=221,compiled_aarch64_native=True,system_runtime_libraries_resolved=True,package_database_unchanged=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((out/'loc-readonly').read_bytes()).hexdigest(),only_get_messages=[75,191,183,225],no_engine_start_or_nv_write=True)
(out/'build-summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''.replace('PAYLOAD',repr(payload))
p=host.ssh('python3 -',input=code.encode(),timeout=210);(host.PRIVATE/'loc-build-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'loc-readonly-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
