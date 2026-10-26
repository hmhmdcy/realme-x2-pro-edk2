"""Record current device health and absence of AF controls on the unmodified r23 stack."""
from pathlib import Path
import ast,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;proof=json.loads((R/'af-probe-build-validation.json').read_text());binary=P/'af-native278'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof['binary_sha256']
remote='/run/samurai-camera278-probes/af-native278'
upload="from pathlib import Path;import sys,hashlib;p=Path(%r);assert not p.exists();p.parent.mkdir(mode=0o755,exist_ok=True);b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;p.write_bytes(b);p.chmod(0o755)"%(remote,proof['binary_sha256'])
host.ssh('python3 -c '+shlex.quote(upload),input=binary.read_bytes(),timeout=15)
t=ast.parse((R.parent/'kernel276/test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call))
code=ast.literal_eval(n.value.func.value);code=code[:code.index('save();report={}')].replace('k276-manager-lifetime-r1','k278-negative-support')
code+=r'''
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
assert health()['passed'];user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
q=subprocess.run(['/run/samurai-camera278-probes/af-native278','--support'],capture_output=True,preexec_fn=demote,env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,USER=user.pw_name),timeout=25)
(root/'support-stdout-private.json').write_bytes(q.stdout);(root/'support-stderr-private.log').write_bytes(q.stderr);assert q.returncode==0
supported=json.loads(q.stdout);assert supported==dict(af_mode=False,af_trigger=False,af_state=False)
versions=subprocess.check_output(['apk','info','-v','libcamera','libcamera-ipa','samurai-camera-config'],text=True);assert 'libcamera-99990.7.2-r23' in versions and 'samurai-camera-config-0.1.0-r18' in versions
time.sleep(3);after=health();assert after['passed']
report=dict(stage=278,old_r23_af_controls_absent=True,old_system_packages_unchanged=True,current_boot276_guard_verified=True,health=after)
state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=40);(P/'negative-support-response-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
(R/'negative-support-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k!='health'}))
