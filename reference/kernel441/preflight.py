"""Read the installed 440 baseline; no device changes on connection failure."""
from pathlib import Path
import hashlib, json, shlex
import host

HERE = Path(__file__).resolve().parent
P = host.PRIVATE
guard = json.loads((P.parent / 'kernel429/postboot-adoption-private.json').read_text())['guard_path']
code = r'''from pathlib import Path
import hashlib,json,struct,subprocess
d=Path('/sys/bus/platform/devices/ac10000.icp')
names=['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']
packages={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if f.get('P') in ['libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack']:packages[f['P']]=f['V']
modules={}
for n in names:
 p=Path(subprocess.check_output(['modinfo','-n',n],text=True).strip())
 raw=p.read_bytes();off=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)];ns=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 note=next(s for s in sections if ns[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
 loaded=Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes();assert loaded==raw[note[4]:note[4]+note[5]]
 modules[n]=dict(sha256=hashlib.sha256(raw).hexdigest(),note=hashlib.sha256(loaded).hexdigest())
print(json.dumps(dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),status=json.loads((d/'m2m_status').read_text()),core=json.loads((d/'state').read_text()),notes={n:r['note'] for n,r in modules.items()},modules=modules,packages=packages)))
'''
try:
    # Keep the original verified SSH key; an old boot guard may be stale.
    q = host.raw_ssh('python3 -c ' + shlex.quote(code), timeout=25)
    q.check_returncode()
    baseline = json.loads(q.stdout)
except Exception as error:
    (P / 'connection-failure-private.txt').write_text(str(error) + '\n')
    report = dict(stage=441, phone_connected=False, phone_changed=False,
                  hardware_validation_pending=True, passed=False)
    (HERE / 'preflight-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    raise SystemExit(1)
expected = json.loads((HERE.parent / 'kernel440/current-state-validation.json').read_text())
assert baseline['packages'] == expected['packages']
assert baseline['taint'] == 0
assert all(baseline['modules'][n]['sha256'] == r['sha256'] for n, r in expected['modules'].items())
assert not any(baseline['status'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert baseline['status']['jobs'] == baseline['status']['completed'] == baseline['status']['direct_completed']
(P / 'preflight-private.json').write_bytes(q.stdout)
new_guard='/var/lib/samurai/k441-adopted/boot-id-private.txt'
adopt='''from pathlib import Path
import os
boot=Path('/proc/sys/kernel/random/boot_id').read_text();assert boot==EXPECTED
p=Path(GUARD);p.parent.mkdir(mode=0o700,exist_ok=True)
if p.exists():assert p.read_text()==boot
else:
 with p.open('x') as f:f.write(boot);f.flush();os.fsync(f.fileno())
'''.replace('EXPECTED',repr(baseline['boot_id'])).replace('GUARD',repr(new_guard))
host.raw_ssh('python3 -c '+shlex.quote(adopt),timeout=20).check_returncode()
(P/'boot-adoption-private.json').write_text(json.dumps(dict(guard_path=new_guard,original_key_verified=True,baseline440_verified=True))+'\n')
report = dict(stage=441, phone_connected=True, boot_guard_matches=True,
              formal_440_r32_r27_and_434_module_files=True, taint=0,
              idle_m2m=True, current_boot_adopted_after_baseline_verification=True,
              installed_payload_changed=False, passed=True)
(HERE / 'preflight-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
