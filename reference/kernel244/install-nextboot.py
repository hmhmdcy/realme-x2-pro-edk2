"""Install a unique temporary startup item; never start it in the current boot."""
from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel244');payloads={n:base64.b64encode((R/n).read_bytes()).decode() for n in ['boot-diag.py','diag_transport_boot.py','samurai-diag244.initd']}
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==(r/'k236-runtime/boot-id-private.txt').read_text().strip()
base=r/'k244-nextboot';assert not base.exists();base.mkdir(mode=0o700);service=Path('/etc/init.d/samurai-diag244');assert not service.exists()
hashes={}
for name,encoded in PAYLOADS.items():
 b=base64.b64decode(encoded)
 if name.endswith('.py'):compile(b,name,'exec')
 p=service if name.endswith('.initd') else base/name;p.write_bytes(b);p.chmod(0o755 if p==service else 0o600);hashes[name]=hashlib.sha256(b).hexdigest()
build=json.loads((r/'k226-loc-tools-r3/build-summary.json').read_text());assert build['fixed_observation_seconds']==90 and build['message_allowlist']==[33,34,35,50,51,63,75]
cfg=dict(previous_boot=boot,model_hex=Path('/proc/device-tree/model').read_bytes().hex(),kernel_release=os.uname().release,loc_binary_sha256=build['binary_sha256'])
(base/'config-private.json').write_text(json.dumps(cfg,indent=2)+'\n')
subprocess.run(['sh','-n',str(service)],check=True);subprocess.run(['rc-update','add','samurai-diag244','default'],capture_output=True,check=True)
assert Path('/etc/runlevels/default/samurai-diag244').resolve()==service and not Path('/run/samurai-diag244.pid').exists()
(base/'installed-source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n');os.sync()
print(json.dumps(dict(stage=244,temporary_startup_installed=True,before_samurai_radio=True,not_started_in_current_boot=True,source_sha256=hashes,no_existing_service_overwritten=True)))
'''.replace('PAYLOADS',repr(payloads))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'nextboot-install-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout);(R/'nextboot-install-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
