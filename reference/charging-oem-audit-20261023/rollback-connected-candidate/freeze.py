"""Freeze only this source leaf and existing offline receipts, no runtime bind."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
files=['prepare.py','host-body.py.inc','host.py','remote.py','supervisor.py','pin-sources.py','source-pins.json','source-reuse.json',
       'test-wire.py','test-result.json','test-transfer.py','test-transfer-result.json','check-defaults.py','local-checks.json','README.md','contract.json','owner-delta.patch','freeze.py']
for receipt in ('test-result.json','test-transfer-result.json'):
    report=json.loads((HERE/receipt).read_bytes());assert report['passed']
    for name,digest in report['tested_files'].items():assert sha((HERE/name).read_bytes())==digest
defaults=json.loads((HERE/'local-checks.json').read_bytes());assert defaults['passed']
assert all(row['terminal'] is True and row['returncode']==0 and row['source_sha256']==sha(Path(row['argv'][-1]).read_bytes()) for row in defaults['commands'])
pins=json.loads((HERE/'source-pins.json').read_bytes())
assert all(sha(Path(item['path']).read_bytes())==item['sha256'] for item in pins.values())
delta=''
for name in ('remote.py','supervisor.py'):
    before=(HERE.parent/'usb-irq-protection-stage-host-candidate-r2'/name).read_text().splitlines(True)
    after=(HERE/name).read_text().splitlines(True)
    delta+=''.join(difflib.unified_diff(before,after,fromfile='stage-host-r2/'+name,tofile='rollback-connected/'+name))
(HERE/'owner-delta.patch').write_text(delta,encoding='utf-8',newline='\n')
contract=dict(schema='samurai-rollback-connected-contract-v1',source_only_default=True,
    actual_runtime_material_generated=False,actual_device_or_transport_accessed=False,
    binder_sha256=pins['binder']['sha256'],worker_sha256=pins['worker']['sha256'],
    request_schema='samurai-usb-irq-protection-rollback-request-v1',transaction_regex='usb-irq-protection-rollback-[a-z0-9-]{8,48}',
    API=dict(bind='bind(transaction,profile,stage_directory,stage_fetch_directory,probe_directory,context=None)',
        transfer='transfer(action,transaction,window_confirmed=False)'),
    profiles=['staged_same_boot_old_resident','booted_irq_new_resident','booted_original_new_resident'],
    actions=['launch','status','fetch'],lease_boottime_seconds=120,parent_wait_seconds=35,parent_timeout='pending; original owner continues; no lease extension',
    owner_chains=['detached local owner -> exact SSH Popen communicate/owned EOF/actual finally wait/closed logs/exact terminal',
                  'detached device supervisor -> fsynced regular request FD -> exact restore-worker Popen/actual finally wait'],
    source_boot_changed='fetch original bytes; source_boot_ended; never attribute current same PID',
    once_outcome_unknown='fetch/status original transaction only; no kill/retry/replay',
    original_launch_required='exact intent/input/action + terminal0 + original response transaction/request + original supervisor receipt',
    success_only='staged_original/runtime_pending',runtime_validation_accepted=False,
    no_module_or_carrier_or_restart_or_AUTO_operation=True,old_unchanged_suites_rerun=False)
(HERE/'contract.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8',newline='\n')
delivery=dict(schema='samurai-rollback-connected-delivery-v1',passed=True,source_only=True,
    files={name:dict(sha256=sha((HERE/name).read_bytes()),bytes=(HERE/name).stat().st_size) for name in files},
    source_inputs=pins,tests=dict(new_wire_cases=29,new_transfer_cases=3,local_default_children_actual_wait0=3,old_suites_rerun=False),
    scope='connected once adapter implemented offline; no actual bind, request, lease, transport, device or runtime validation',
    archive=dict(explicit_whitelist=files,recursive_scan=False,binaries_or_cache_included=False,text_log_aliases=[]))
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha((HERE/'delivery.json').read_bytes()),host_sha256=pins['host']['sha256'],remote_sha256=pins['remote']['sha256'],supervisor_sha256=pins['supervisor']['sha256'])))
