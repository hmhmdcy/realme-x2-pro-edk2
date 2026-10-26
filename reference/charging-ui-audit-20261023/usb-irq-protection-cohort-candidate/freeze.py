"""Publish only safe manifest/identity/results after the actual private build."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('frozen_cohort', HERE / 'cohort.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def freeze(name, raw):
    target = HERE / name
    if target.exists():
        m.need(target.read_bytes() == raw, 'changed frozen receipt requires a new revision: ' + name)
    else:
        with target.open('xb') as stream:
            stream.write(raw)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    pins, cohort, forward, backward = m.local_inputs()
    audited = m.audit(m.OUT, cohort, forward, backward)
    result = json.loads((m.OUT / 'result.json').read_bytes())
    tests = json.loads((HERE / 'test-result.json').read_bytes())
    m.need(tests['passed'] and tests['tested_files']['cohort.py'] == m.file_sha(HERE / 'cohort.py'), 'test binding')
    old = json.loads(backward[m.MANIFEST])
    new = json.loads(forward[m.MANIFEST])
    delta = {
        'old_manifest_sha256': m.sha(backward[m.MANIFEST]),
        'new_manifest_sha256': m.sha(forward[m.MANIFEST]),
        'old_revision': old['adapter_revision'], 'new_revision': new['adapter_revision'],
        'changed_modules': list(m.CHANGED),
        'changed_installed_files': [old['modules'][name]['target'] for name in m.CHANGED],
        'all_other_manifest_values_exact': True,
        'original_manager_sha256': pins['retained']['/usr/sbin/samurai-charging']['sha256'],
        'manager_has_no_adapter_revision_read_or_comparison': True,
        'manager_review_scope': 'actual verify/load_module source; no runtime invocation',
        'rootfs_payload_has_only_three_files': True,
    }
    execution = {
        'scope': 'actual local exec-tool completions; no device or external build tools',
        'commands': [
            {'argv': ['python', '-B', 'cohort.py'], 'terminal': True, 'returncode': 0,
             'output_directory_existed': False, 'exec_chunk': '1f4db5'},
            {'argv': ['python', '-B', 'cohort.py', 'build', '--execute'], 'terminal': True,
             'returncode': 0, 'exec_chunk': 'c7747c'},
            {'argv': ['python', '-B', 'cohort.py', 'audit'], 'terminal': True,
             'returncode': 0, 'exec_chunk': '7dc359'},
        ],
        'private_materialization_invocations': 1,
        'source_sha256': m.file_sha(HERE / 'cohort.py'),
        'private_result_sha256': m.file_sha(m.OUT / 'result.json'),
        'new_device_or_stage_guard_created': False,
        'prepared_Image502_transaction_modified': False,
    }
    if not args.execute:
        print(json.dumps({'passed': audited['passed'], 'published': False, 'device_accessed': False}))
        return
    freeze('manifest.json', forward[m.MANIFEST])
    freeze('cohort-manifest.json', m.encode(cohort))
    freeze('payload-result.json', m.encode(result))
    freeze('audit-result.json', m.encode(audited))
    freeze('manifest-delta.json', m.encode(delta))
    freeze('execution-receipt.json', m.encode(execution))
    file_names = ['cohort.py', 'prepare-inputs.py', 'input-pins.json', 'test-cohort.py',
                  'test-result.json', 'freeze.py', 'README.md', 'manifest.json',
                  'cohort-manifest.json', 'payload-result.json', 'audit-result.json',
                  'manifest-delta.json', 'execution-receipt.json']
    delivery = {
        'schema': 'samurai-usb-irq-protection-cohort-delivery-v1',
        'passed': True, 'frozen': True, 'cohort_id': cohort['cohort_id'],
        'phase': 'offline-three-file-payload-and-exact-R8-rollback-materialized',
        'files': {name: {'sha256': m.file_sha(HERE / name), 'bytes': (HERE / name).stat().st_size}
                  for name in file_names},
        'private_output': str(m.OUT),
        'forward_payload': result['files']['usb-irq-protection-payload.tar.gz'],
        'rollback_payload': result['files']['rollback-r8-payload.tar.gz'],
        'new_manifest_sha256': cohort['new_manifest_sha256'],
        'old_manifest_sha256': cohort['old_manifest_sha256'],
        'new_USB_sha256': cohort['modules']['samurai-usb-input']['new']['sha256'],
        'new_protection_sha256': cohort['modules']['samurai-gauge-protection']['new']['sha256'],
        'required_boot_sha256': pins['carriers']['boot']['sha256'],
        'required_native_DTB_sha256': pins['carriers']['native_DTB']['sha256'],
        'required_logdump_sha256': pins['carriers']['logdump']['sha256'],
        'required_Image502_sha256': pins['carriers']['Image502_sha256'],
        'actual_package_boundary_cases': tests['actual_package_boundary_cases'],
        'driver_tests_or_compilation_repeated': False,
        'installed_or_device_accessed': False,
        'staged_runtime_pending_transition_requires_new_transaction_guard': True,
        'runtime_IRQ_evidence_and_protection_query_pending': True,
        'module_binary_or_raw_private_device_identity_published': False,
    }
    freeze('delivery.json', m.encode(delivery))
    print(json.dumps({'passed': True, 'delivery_sha256': m.file_sha(HERE / 'delivery.json'),
                      'new_manifest_sha256': cohort['new_manifest_sha256'],
                      'forward_payload_sha256': delivery['forward_payload']['sha256']}))

if __name__ == '__main__':
    main()
