"""Local receipts only. Never imports a device/transport/adoption entry point."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
adopt=HERE.parent/'image502-adoption-candidate'
for leaf in [HERE,adopt]:
 test=json.loads((leaf/'test-result.json').read_bytes());assert test['passed']
 for name,digest in test['tested_files'].items():assert sha(leaf/name)==digest,name
 for row in json.loads((leaf/'source-pins.json').read_bytes()).values():assert sha(Path(row['path']))==row['sha256']
 checks=json.loads((HERE/'local-check-result.json').read_bytes());assert checks['passed'] and all(x['exit_code']==0 for x in checks['commands'])
 assert checks['additional_default_check']['exit_code']==0
 files={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(leaf.iterdir()) if p.is_file() and p.name!='delivery.json'}
 report={'status':'offline-affected-tests-and-default-check-passed-unexecuted',
  'files':files,'transaction_id':'image502-notify-live-001',
  'unchanged_boot_sha256':'97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
  'candidate_logdump_sha256':'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1',
  'Image502_sha256':'085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955',
  'adopted_guard':'/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt',
  'actual_test_case_count':test['affected_case_count'],'old_suites_rerun':False,
  'read_only_default_checks_receipt':{'path':str(HERE/'local-check-result.json'),'sha256':sha(HERE/'local-check-result.json')},
  'device_SSH_USB_prepare_adoption_global_pointer_or_Git_accessed':False,
  'actual_new_boot_or_guard_or_endpoint_created':False}
 (leaf/'delivery.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'leaf':leaf.name,'delivery_sha256':sha(leaf/'delivery.json'),
  'source_sha256':sha(leaf/('device.py' if leaf==HERE else 'adopt.py')),
  'test_sha256':sha(leaf/'test-result.json')}))
