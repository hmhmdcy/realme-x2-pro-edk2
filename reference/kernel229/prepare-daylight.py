"""Retain the validated RAM-only probe, with explicit current-boot/OOT guards."""
from pathlib import Path
import hashlib
import json
import host

ref = Path(__file__).resolve().parent
endpoint = host.PRIVATE / 'usb-ipv6-candidates-private.json'
assert not endpoint.exists()
endpoint.write_bytes((host.PRIVATE.parent / 'kernel228/usb-ipv6-candidates-private.json').read_bytes())
probe = host.PRIVATE.parent / 'kernel219/native-mode-probe219'
build = json.loads((ref.parent / 'kernel219/native-probe-build-validation.json').read_text())
assert hashlib.sha256(probe.read_bytes()).hexdigest() == build['probe_sha256']
preflight = b"from pathlib import Path;import os;assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k228-runtime/boot-id-private.txt').read_bytes();assert Path('/proc/sys/kernel/tainted').read_text().strip()=='4096';p=Path('/run/samurai-camera229-probes');assert not p.exists();p.mkdir(mode=0o755);print('Current boot verified; RAM-only probe directory created')"
result = host.ssh('python3 -', input=preflight, timeout=15)
(host.PRIVATE / 'probe-directory-private.log').write_bytes(result.stdout + result.stderr)
host.upload(probe, '/run/samurai-camera229-probes/native-mode-probe')
check = "from pathlib import Path;import hashlib,os,json;p=Path('/run/samurai-camera229-probes/native-mode-probe');assert hashlib.sha256(p.read_bytes()).hexdigest()==%r;os.chmod(p,0o755);print(json.dumps({'original_RAM_stats_probe_verified':True,'bytes':p.stat().st_size}))" % build['probe_sha256']
result = host.ssh('python3 -', input=check.encode(), timeout=15)
(host.PRIVATE / 'probe-upload-verified-private.log').write_bytes(result.stdout + result.stderr)
source = (ref.parent / 'kernel219/native-mode-runner.py').read_text()
source = source.replace("guard=root/'k219-runtime/boot-id-private.txt'", "guard=root/'k228-runtime/boot-id-private.txt'")
source = source.replace("assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'",
                        "assert Path('/proc/sys/kernel/tainted').read_text().strip()=='4096'\nassert {p.parent.name:p.read_text().strip() for p in Path('/sys/module').glob('*/taint') if p.read_text().strip()}=={'fastrpc':'O'}")
source = source.replace("'k219-capture-'", "'k229-capture-daylight-baseline-'")
source = source.replace('/run/samurai-camera219-probes/native-mode-probe', '/run/samurai-camera229-probes/native-mode-probe')
source = source.replace('report=dict(stage=219,', 'report=dict(stage=229,')
source = source.replace('room_lights_off=True,', "lighting_condition='user reports daylight',")
compile(source, 'native-daylight-baseline229', 'exec')
(ref / 'native-daylight-baseline.py').write_text(source)
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(dict(
    stage=229, state='daylight RAM-only baseline prepared; no capture started',
    guard='/var/lib/samurai/k228-runtime/boot-id-private.txt', full_peripheral_goal_active=True,
    loaded_fastrpc='7ca5d442: external OOT4096 only', default_fastrpc='2abde0ea: genuine intree staged',
    clean_intree_boot_pending=True, transition_pending=False, user_no_sim=True,
    latest_user_steering='daylight, test camera colours'), indent=2) + '\n')
print(json.dumps(dict(stage=229, RAM_only_probe_verified=True, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                      capture_started=False, new_boot228_guard=True, scene_storage=False)))
