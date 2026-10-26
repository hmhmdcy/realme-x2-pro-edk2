"""Local archival/hash validation only. Never creates runtime material."""
from pathlib import Path
import ast
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
file_sha = lambda p: sha(Path(p).read_bytes())
contract_sha = '13bc81d89bfe34e573b4a23287c7841c67cd82c563cfc3266004b9ab3eba0914'
assert file_sha(HERE / 'prepare-contract.json') == contract_sha
test = json.loads((HERE / 'test-result.json').read_bytes())
assert test['passed'] is True and test['methods'] == 12 and len(test['default_checks']) == 4
assert test['device_accessed'] is False and test['runtime_request_generated'] is False and test['old_suites_rerun'] is False
for name, digest in test['tested_files'].items():
    assert file_sha(HERE / name) == digest, name


def functions(raw):
    source = raw.decode()
    return {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}


reuse = json.loads((HERE / 'source-reuse.json').read_bytes())
current = functions((HERE / 'common.py').read_bytes())
for item in reuse['reused_functions']:
    raw = (REF / item['source']).read_bytes()
    original = functions(raw)[item['name']]
    assert sha(raw) == item['source_sha256']
    assert original == current[item['name']] and sha(original.encode()) == item['function_sha256']
for name, digest in reuse['source_pins'].items():
    assert file_sha(REF / name) == digest
for item in reuse['worker_suffixes']:
    assert file_sha(HERE / item['name']) == item['candidate_sha256']
    compile((HERE / item['name']).read_bytes(), item['name'], 'exec')

proof_root = REF / 'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate'
proof_pins = dict(source_sha256='85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093',
                  frozen_receipt_sha256='6f5a5b7e6ad2dcbb8a51115864571b44f1561eaddd4848a03f0687328fc4a3d3')
assert file_sha(proof_root / 'stage-proof.py') == proof_pins['source_sha256']
assert file_sha(proof_root / 'stage-proof-frozen.json') == proof_pins['frozen_receipt_sha256']
proof_tree = ast.parse((proof_root / 'stage-proof.py').read_bytes())
evidence = next(ast.literal_eval(n.value) for n in proof_tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'EVIDENCE' for t in n.targets))
contract = json.loads((HERE / 'prepare-contract.json').read_bytes())
assert set(evidence) == set(contract['stage_evidence_keys'])
assert set(functions((proof_root / 'stage-proof.py').read_bytes())) >= {'review_stage', 'guard_stage_fields'}
binding = dict(stage_proof_path=str((proof_root / 'stage-proof.py').relative_to(REF)), **proof_pins,
               apis=['review_stage(stage_directory, fetch_directory, *, expected_transaction=None)', 'guard_stage_fields(review)'],
               exact_stage_fields=contract['stage_fields'], exact_device_evidence=evidence,
               host_authentication_required=True, actual_stage_or_adoption_reviewed=False)
(HERE / 'stage-proof-binding.json').write_text(json.dumps(binding, indent=2) + '\n', newline='\n')
names = sorted(p for p in HERE.rglob('*') if p.is_file() and p.name != 'delivery.json' and '__pycache__' not in p.parts)
delivery = dict(passed=True, frozen=True, source_only=True, revision=1, device_accessed=False,
                runtime_request_generated=False, deployment_or_reboot_proven=False,
                fixed_contract_sha256=contract_sha, stage_proof_sha256=proof_pins['source_sha256'],
                new_test_methods=12, old_suites_rerun=False,
                files={str(p.relative_to(HERE)).replace('\\', '/'): dict(sha256=file_sha(p), bytes=p.stat().st_size) for p in names})
(HERE / 'delivery.json').write_text(json.dumps(delivery, indent=2) + '\n', newline='\n')
print(json.dumps(dict(frozen=True, source_only=True, delivery_sha256=file_sha(HERE / 'delivery.json'),
                     contract_sha256=contract_sha,
                     workers={name: file_sha(HERE / name) for name in ['eud-quiesce.py', 'eud-restart.py']},
                     test_result_sha256=file_sha(HERE / 'test-result.json'), files=len(names))))
