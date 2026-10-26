"""Hash local source/receipts only. Does not bind a runtime identity."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
test=json.loads((HERE/'template-test-result.json').read_bytes());assert test['passed'] and test['runtime_identity_unbound']
for n,d in test['files'].items():assert sha(HERE/n)==d,n
for row in json.loads((HERE/'source-pins.json').read_bytes()).values():assert sha(Path(row['path']))==row['sha256']
checks=json.loads((HERE/'local-check-result.json').read_bytes());assert checks['passed'] and not checks['runtime_identity_created']
files={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'}
result={'status':'offline-template-ready-not-launched','files':files,
 'runtime_identity_pins_generated':False,'affected_groups':3,'affected_cases':14,
 'old32_and12_rerun':False,'network_device_USB_ADB_build_Git_accessed':False,
 'required_adopted_guard':'/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt',
 'boot_sha256':'97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
 'logdump_sha256':'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1',
 'deadline_seconds':300,'reconnect_stable_observation_seconds':90,'host_ready_min_remaining_seconds':130}
(HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'delivery_sha256':sha(HERE/'delivery.json'),'launcher_sha256':sha(HERE/'launcher.py'),
 'template_test_sha256':sha(HERE/'template-test-result.json')}))
