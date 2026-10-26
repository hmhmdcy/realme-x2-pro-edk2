"""Static independent worker review only. Never import or execute a worker."""
from pathlib import Path
import ast, hashlib, json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
ACT = REF / 'charging-session-20261023/eud-boot-activation-candidate'
OLD = REF / 'charging-oem-audit-20261023/normal-restart-candidate'
PRIVATE = Path('/mnt/e/edk2-samurai-out')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
pins = {
    'guard-fragment.py': '80c25f129fc6319aff189368a527e0a912868ba7d0d1823054d75188502a18a6',
    'eud-quiesce.py': '311e416bc2c91a053c334b025327e79df24d7a68e82ce4ee393311284b34bc0c',
    'eud-restart.py': '0fb0948b49f7b15ca04015991d771056f1f5357539d7e9a834d4536928956ddf',
    'prepare-contract.json': 'f12d65b62f8787732795f45d15edf0560672f3782bc16aed915c42dbd6f92dec',
}
assert all(sha(ACT / name) == digest for name, digest in pins.items())
guard = (ACT / 'guard-fragment.py').read_text()
quiesce = (ACT / 'eud-quiesce.py').read_text()
restart = (ACT / 'eud-restart.py').read_text()
for name in ('guard-fragment.py', 'eud-quiesce.py', 'eud-restart.py'):
    ast.parse((ACT / name).read_text(), filename=name)
assert guard in quiesce and guard in restart
constants = {}
for node in ast.parse(guard).body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        try:
            constants[node.targets[0].id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            pass
generation = read(ACT / 'generation-result.json')
assert sha(OLD / 'r7-quiesce-review.py') == generation['files']['eud-quiesce.py']['source_sha256']
old_restart = OLD / 'transport-tail-audit/r7-restart-transport-tail-review.py'
assert sha(old_restart) == generation['files']['eud-restart.py']['source_sha256']
marker = "assert sys.argv[3]=='--commit-quiesce'"
old = (OLD / 'r7-quiesce-review.py').read_text()
normalized = quiesce[quiesce.index(marker):].replace("work='eud-boot-activation'", "work='charging-r7-restart'").replace(",token=meta['token']", '')
assert normalized == old[old.index(marker):]

# Independently constrain the restart suffix diff to metadata, strict full-word
# CSR checks, token binding and pre-freeze claim durability. No tail execution.
marker = "assert sys.argv[3] in ['--inspect','--commit-restart2-bootloader']"
old = old_restart.read_text()
expected = old[old.index(marker):]
expected = expected.replace("work='charging-r7-restart'", "work='eud-boot-activation'")
expected = expected.replace("transaction_id=meta['transaction_id'],boot_id=meta['boot_id']", "transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],token=meta['token']")
expected = expected.replace("assert (before&255) in [0,1]", "assert before in (0,1,0x01010101)")
expected = expected.replace("assert struct.unpack_from('<I',csr,0x14)[0]&255==0", "assert struct.unpack_from('<I',csr,0x14)[0]==0")
expected = expected.replace("assert s['transaction_id']==proof['transaction_id']==meta['transaction_id']", "assert s['transaction_id']==proof['transaction_id']==meta['transaction_id']\nassert s['token']==proof['token']==meta['token']")
expected = expected.replace("with phase.open('x') as claim:json.dump(dict(transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],token=meta['token'],state='claimed_once',request_count=1),claim)", "with phase.open('x') as claim:\n   json.dump(dict(transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],token=meta['token'],state='claimed_once',request_count=1),claim);claim.flush();os.fsync(claim.fileno())\n  phase_parent=os.open(phase.parent,os.O_RDONLY|os.O_DIRECTORY)\n  try:os.fsync(phase_parent)\n  finally:os.close(phase_parent)")
assert expected == restart[restart.index(marker):]
assert restart.index("if sys.argv[3]=='--inspect'") < restart.index("os.open('/dev/mem'")
assert restart.index("with phase.open('x')") < restart.index('0xc0045877')
assert restart.index('os.fsync(phase_parent)') < restart.index('0xc0045877')
tail = restart[restart.index("struct.pack_into('<I',csr,0x14,0)"):restart.index('  raise RuntimeError(')]
assert "print(" not in tail and 'phase.write' not in tail and 'sleep(' not in tail
assert 'close(' not in tail and tail.count('libc.syscall(') == 1
assert "struct.unpack_from('<I',csr,0x14)[0]==0" in tail

test = read(ACT / 'test-result.json')
assert test['passed'] and len(test['actual_guard_cases']) == 18 and len(test['actual_restart_tail_cases']) == 7
assert not test['old_suites_rerun'] and not test['device_access'] and not test['native_syscall_executed']
for name, digest in test['files'].items():
    assert sha(ACT / name) == digest
old_test = read(OLD / 'transport-tail-audit/test-result.json')
assert old_test['passed'] and old_test['candidate_sha256'] == sha(old_restart)
assert len(old_test['actual_worker_ast_boundary_cases']) == 8
assert old_test['actual_cpython_pipe']['type'] == 'BrokenPipeError'

package_path = REF / 'charging-session-20261023/eud-boot-two-ffs-candidate/result.json'
package = read(package_path)
assert package['passed'] and package['boot_sha256'] == constants['CANDIDATE_BOOT']
assert package['boot_bytes'] == 100663296 and package['rollback_a30_sha256'] == constants['ROLLBACK_BOOT']
assert package['external_Image_untouched'] and package['no_deployment_or_device_access']
fat_path = REF / 'kernel365/boot-package-validation.json'
fat = read(fat_path)
assert fat['image_sha256'] == constants['IMAGE363'] and fat['logdump_sha256'] == constants['LOGDUMP365']
assert fat['fat_image_and_dtb_readback_exact'] and fat['fat_readonly_check_pass']
assert "['mcopy','-i',str(target),'::/Image','-']" in (REF / 'kernel365/prepare-deployment.py').read_text()
wrapper_path = PRIVATE / 'kernel481/formal-expected-private.json'
return_path = PRIVATE / 'kernel481/return-to-charging-private.json'
assert sha(wrapper_path) == constants['CAMERA481']
assert sha(return_path) == constants['CAMERA_RETURN']
returned = read(return_path)
assert returned['released'] and returned['actual_transaction_terminal'] and returned['worker_absent'] and returned['active_child_absent']
assert returned['expected_wrapper_sha256'] == constants['CAMERA481']
assert returned['charging']['manifest_sha256'] == constants['R8_MANIFEST']
assert returned['charging']['notes'] == constants['R8_NOTES']
csr_path = REF / 'charging-management-20261023/eud-csr-r8-result.json'
csr = read(csr_path)
assert csr['passed'] and csr['hardware_writes'] == 0 and csr['csr_width_bits'] == 32
assert csr['csr_address'] == '0x088e1014' and [x['value'] for x in csr['csr']] == [0x01010101] * 2

references = [ACT / 'README.md', ACT / 'generation-result.json', ACT / 'test-result.json',
              OLD / 'test-result.json', OLD / 'transport-tail-audit/test-result.json',
              OLD / 'transport-tail-audit/r7-restart-transport-tail-review.py',
              REF / 'charging-management-20261023/r7-restart-state.json',
              package_path, fat_path, REF / 'kernel365/prepare-deployment.py', csr_path]
result = dict(schema=1, conclusion='no_new_blocker_in_frozen_worker_scope', findings=[],
              reviewed_files=pins, references={str(p.relative_to(REF)): sha(p) for p in references},
              private_evidence_hashes={'formal481': sha(wrapper_path), 'camera481_return': sha(return_path)},
              static_checks=dict(shared_guard_embedded=True, old_quiesce_hardware_suffix_identical=True,
                                 restart_suffix_only_reviewed_narrow_changes=True, inspect_before_mem_open=True,
                                 durable_exclusive_claim_before_freeze=True, CSR_full_word_readback_zero=True,
                                 no_transport_operation_between_CSR_and_syscall=True,
                                 entire_logdump_identity_bound_to_FAT_Image363_receipt=True),
              author_actual_guard_cases_reused=18, author_actual_tail_cases_reused=7,
              prior_transport_tail_cases_reused=8, prior_guard_cases_reused=17,
              tests_rerun=False, workers_executed=False, device_access=False, SDK_invoked=False, Git_invoked=False,
              host_controller_or_fastboot_tool_reviewed=False, restart_success_proven=False,
              caveats=['root exclusive ownership and original pinned transport are external prerequisites',
                       'armed phase or SSH loss is intent/unknown, not bootloader or new-boot success',
                       'unknown restart must not be replayed; fresh fastboot identity is separate',
                       'successful reboot may destroy tmpfs /run logs; their later fetch is not a completion requirement',
                       'syscall-return failure thaws only; stopped services/EUD are not automatically restored'])
assert all(sha(ACT / name) == digest for name, digest in pins.items())
(HERE / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(conclusion=result['conclusion'], result_sha256=sha(HERE / 'result.json')), indent=2))
