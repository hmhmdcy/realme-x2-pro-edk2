"""Read-only AST/hash review of frozen operator receipts, never import it."""
from pathlib import Path
import ast
import hashlib
import json
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = REF/'charging-oem-audit-20261023/usb-irq-protection-fastboot-candidate'
BASE = REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def functions(p):
    raw = p.read_text()
    lines = raw.splitlines(True)
    return {n.name: ''.join(lines[n.lineno-1:n.end_lineno])
            for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}


def check_files(folder, receipt):
    for name, entry in receipt['files'].items():
        digest = entry['sha256'] if isinstance(entry, dict) else entry
        assert sha(folder/name) == digest, name


def main():
    assert not sys.flags.optimize
    assert not (HERE/'review-result.json').exists(), 'Preserve original frozen review'
    delivery = json.loads((AUTHOR/'delivery.json').read_bytes())
    assert delivery['passed'] is True and delivery['frozen'] is True
    assert delivery['only_write_partition'] == 'boot'
    assert delivery['rootfs_rollback_proven'] is False
    assert delivery['complete_activation_flow_ready'] is False
    check_files(AUTHOR, delivery)
    old, new = functions(BASE/'fastboot-operator.py'), functions(AUTHOR/'fastboot-operator.py')
    assert sha(BASE/'fastboot-operator.py') == '7f473d8698e2e2f83ff768db98de167998a6d7b53e948421b8019fec141d2121'
    unchanged = {name:hashlib.sha256(body.encode()).hexdigest()
                 for name, body in old.items() if new.get(name) == body}
    assert len(unchanged) == 15
    for name in ['worker','main']:
        assert new[name] == old[name].replace('samurai-image502-notify-fastboot-action-v1',
                                              'samurai-usb-irq-protection-fastboot-action-v1')
    reuse = json.loads((AUTHOR/'source-reuse.json').read_bytes())
    tests = json.loads((AUTHOR/'test-result.json').read_bytes())
    assert reuse['unchanged_functions'] == tests['unchanged_15_function_bodies'] == unchanged
    assert tests['passed'] is True and tests['new_changed_boundary_cases'] == 31
    assert tests['old_suites_rerun'] is False
    for name, digest in tests['tested_sources'].items():
        assert sha(AUTHOR/name) == digest
    completion = json.loads((AUTHOR/'completion-test-result.json').read_bytes())
    assert completion['passed'] is True and completion['new_cases'] == 13
    assert completion['old31_or_old22_rerun'] is False
    assert completion['operator_auth_and_USB_boundaries_fake'] is True
    for name, digest in completion['files'].items():
        assert sha(AUTHOR/name) == digest
    ast.parse((AUTHOR/'completion-proof.py').read_text())
    local = json.loads((AUTHOR/'local-check-result.json').read_bytes())
    assert local['terminal'] is True and local['returncode'] == 0
    assert local['USB_device_runtime_binding_accessed'] is False
    pins = json.loads((AUTHOR/'source-pins.json').read_bytes())['files']
    locations = {
        'baseline/operator.py':BASE/'fastboot-operator.py',
        'boot/delivery.json':REF/'charging-ui-audit-20261023/usb-input-irq-boot-candidate/delivery.json',
        'boot/result.json':REF/'charging-ui-audit-20261023/usb-input-irq-boot-candidate/result.json',
        'cohort/delivery.json':REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/delivery.json',
        'stage-proof.py':REF/'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/stage-proof.py',
    }
    restart = REF/'charging-session-20261023/usb-irq-protection-restart-candidate'
    for name in ['delivery.json','prepare-contract.json','eud-quiesce.py','eud-restart.py']:
        locations['restart/'+name] = restart/name
    assert set(locations) == set(pins)
    assert all(sha(path) == pins[name] for name,path in locations.items())
    restart_delivery = json.loads((restart/'delivery.json').read_bytes())
    assert restart_delivery['passed'] is True and restart_delivery['frozen'] is True
    check_files(restart, restart_delivery)
    stage_folder = locations['stage-proof.py'].parent
    stage_frozen = json.loads((stage_folder/'stage-proof-frozen.json').read_bytes())
    assert stage_frozen['passed'] is True and stage_frozen['stage_proof_sha256'] == pins['stage-proof.py']
    check_files(stage_folder, stage_frozen)
    result = dict(schema=1,passed=True,new_blockers=[],review_kind='independent static source and receipt binding only',
        author_delivery_sha256=sha(AUTHOR/'delivery.json'),operator_sha256=sha(AUTHOR/'fastboot-operator.py'),
        author_test_receipt_sha256=sha(AUTHOR/'test-result.json'),unchanged_15_actual_function_bodies=unchanged,
        completion_proof_sha256=sha(AUTHOR/'completion-proof.py'),
        completion_13_test_receipt_sha256=sha(AUTHOR/'completion-test-result.json'),
        worker_main_schema_only=True,source_dependency_sha256=pins,
        accepted_boundaries=['actual stage re-review and source adoption/board/rootfs equality before action claim',
             'new stage-aware seven-original context plus sole fresh exact fastboot identity and both geometry reads',
             'only boot eddadec candidate / 97811 original; no logdump, rootfs or other partition writes',
             'old running/unknown action prevents another claim; no auto reboot, retry or timeout kill',
             'explicit reboot binds the last corresponding successful exact boot receipt',
             'completion API rechecks saved exact requested argv, original child identity, same-PID wait0 and output hashes',
             'completion saved-call replay uses actual dispatch parser with exact consumed command set and no new transport',
             'boot-only rollback never claims complete rootfs rollback'],
        limitations=['author 31 cases use explicit fake USB, process and stage-auth boundaries',
             'no actual context, new guard, bootloader write, runtime boot or IRQ delivery is validated by this review',
             'unchanged_logdump is an authenticated source identity and no-write boundary, not a new fastboot readback',
             'captured interop argv is retained nonempty; exact requested argv is bound by Popen source/claim, not byte-equal observed argv',
             'complete activation and rootfs rollback remain unimplemented here'],
        tests_or_author_entry_executed=False,device_or_USB_or_SSH_or_SDK_or_Git_used=False,
        own_files={n:sha(HERE/n) for n in ['review.py','README.md']})
    (HERE/'review-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,review_sha256=sha(HERE/'review-result.json'),
                          source_sha256=result['operator_sha256'])))


if __name__ == '__main__':
    main()
