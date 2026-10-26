"""Bind the actual terminal build and the unchanged 501 ABI evidence."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = json.loads((HERE / 'build-result.json').read_bytes())
assert result['passed'] and result['child_returncode'] == 0
assert result['parent_namespace_unchanged'] and result['parent_mounts_unchanged']
assert result['shared_before'] == result['shared_after']
assert result['original363_before'] == result['original363_after']
assert all(result['baseline_trees_preserved'].values())
assert result['B_source_sha256'] == '0014077792948460fc2a2e9581225dc684cba4d5bff95c3e88767d661ce5439b'
assert sha(HERE / 'run-502.py') == 'cf11d0135c56d5a63ce862833579292805c368b714ede7734378ef21ccbfe3e8'
assert sha(HERE / 'metadata-proof.py') == '31f22e48c033fc52ca380c8f1eb5d5737ba017fab5d0e8d8e7f4598abbcb4bcb'
build = result['build']
assert build['passed'] and result['child_state']['terminal'] and result['child_state']['returncode'] == 0
assert build['unchanged_other_leaf_count'] == 3245 and build['unchanged_libstub_count'] == 32
assert [row['path'] for row in build['leaf_delta']] == ['drivers/power/supply/bq27xxx_battery.o', 'init/version.o']
assert build['initramfs_exact_original_hashes'] == {
    'usr/initramfs_data.cpio': 'fc1d27728b2ab7dc8c08b3a372b9f1a025a9db60faaad6b33001398e214c9669',
    'usr/initramfs_inc_data': '319b665d4bdbf9647efb1ae1055438e5a7990c69e7016190c9625de414b81678',
    'usr/initramfs_data.o': '2524437833f58ecd8410d6c1d740d0f412faaae85d3ae73c63d3f1f3607484de',
}
for obj in build['metadata_proof']['objects'].values():
    assert obj['whole_object_identity_substitution_only'] and obj['all_executable_sections_identical']
assert build['metadata_proof']['old_identity'].startswith('#501 ')
assert build['metadata_proof']['new_identity'].startswith('#502 ')
assert build['identity']['UTS_RELEASE'] == '7.3.0-rc6-rmx1931-samurai-k363+'
assert build['identity']['KBUILD_BUILD_VERSION'] == '502'
compat = build['compatibility']
assert compat['passed'] and compat['builtin_export_count'] == 15097
assert compat['actual_ELF_export_names_exact_501'] and compat['builtin_export_rows_exact_501']
assert compat['Module_symvers_exact_501'] and compat['public_headers_unchanged']
assert compat['archive_order_exact'] and not compat['diagnostics']
assert build['config_exact_original'] and build['release_unchanged']
assert compat['default_opt_in_zero_BSS'] and build['B_default_false_unchanged']
old_abi = REF / 'charging-session-20261023/gauge-image501-repro-candidate/abi-result.json'
cci = REF / 'charging-session-20261023/gauge-image501-abi-provider-supplement/result.json'
assert sha(old_abi) == '3ed8fc61424cf82a0465a1876c8c2ec88d31b714accffa81d4f0f31c5f7ac25c'
assert sha(cci) == 'db8dffd5443b1e60944ee33879283d530183ca832e29d6bb1e2f22b60fd483d2'
abi = {'passed': True, 'scope': 'unchanged 501 ABI evidence reused after actual 502 output comparisons',
       'new_build_receipt_sha256': sha(HERE / 'build-result.json'),
       'actual_502_comparisons': compat,
       'reused_501_ABI_receipt_sha256': sha(old_abi), 'reused_CCI_provider_receipt_sha256': sha(cci),
       'modules_rescanned': False, 'type_ABI_proven': False, 'runtime_or_module_load_tested': False}
(HERE / 'abi-reuse-result.json').write_text(json.dumps(abi, indent=2) + '\n')
execution = {'passed': True, 'native_exec_session': 22677, 'parent_pid': 805,
             'namespace_worker_pid': result['child_state']['worker_pid'],
             'returncode': 0, 'same_original_exec_handle_waited': True,
             'runner_sha256': sha(HERE / 'run-502.py'),
             'actual_execution_UTC': result['identity']['actual_build_utc'],
             'original_Ubuntu_root_storage284_guard': True,
             'no_live_build_process_remaining': True,
             'new_boot_carrier_or_deployment': False}
(HERE / 'execution-receipt.json').write_text(json.dumps(execution, indent=2) + '\n')
delivery = {'passed': True, 'private_output': result['private_output'],
            'source_sha256': result['B_source_sha256'], 'identity': result['identity'],
            'outputs': build['outputs'],
            'files': {str(p.relative_to(HERE)).replace('\\', '/'): sha(p)
                      for p in sorted(HERE.rglob('*')) if p.is_file() and p.name != 'delivery.json'},
            'linked_Image': True, 'new_boot_carrier': False, 'installed': False,
            'physical_edge_or_latency_validated': False, 'Phosh_UPower_modified': False}
(HERE / 'delivery.json').write_text(json.dumps(delivery, indent=2) + '\n')
print(json.dumps({'passed': True, 'delivery_sha256': sha(HERE / 'delivery.json'),
                  'build_sha256': sha(HERE / 'build-result.json'),
                  'abi_reuse_sha256': sha(HERE / 'abi-reuse-result.json'), 'outputs': build['outputs']}))
