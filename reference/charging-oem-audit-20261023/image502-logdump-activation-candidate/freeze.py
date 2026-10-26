"""Freeze local source/receipt binding only; never execute an activation action."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
test=json.loads((HERE/'test-result.json').read_bytes());assert test['passed']
for n,digest in test['tested_files'].items():assert sha(HERE/n)==digest,n
out=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-materialized-001')
mat=json.loads((out/'materialization.json').read_bytes())
assert sha(out/'materialization.json')=='09c4a086746b28cefde521092778a908f8b6175f1835ea9b64c3548b9fba2d4e'
for n,digest in mat['source_files'].items():assert sha(HERE/n)==digest,n
for n,digest in mat['files'].items():assert sha(out/n)==digest,n
files={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name!='delivery.json'}
r={'schema':'samurai-image502-logdump-activation-delivery-v1','passed':True,'frozen':True,'files':files,
 'materialization_path':str(out),'materialization_sha256':sha(out/'materialization.json'),
 'materialized_files':mat['files'],'worker_hashes':mat['worker_hashes'],
 'candidate_logdump_sha256':mat['logdumps']['candidate']['sha256'],'rollback_logdump_sha256':mat['logdumps']['original']['sha256'],
 'unchanged_boot_sha256':mat['unchanged_boot_sha256'],'only_write_partition':'logdump',
 'affected_groups':5,'actual_cases':22,'old_unchanged_functions_reused':28,
 'local_check_only_passed':True,'no_prepare_SSH_USB_fastboot_quiesce_restart_executed':True}
(HERE/'delivery.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'delivery_sha256':sha(HERE/'delivery.json'),'materialization_sha256':r['materialization_sha256'],'controller_sha256':sha(HERE/'controller.py'),'operator_sha256':sha(HERE/'fastboot-operator.py')}))
