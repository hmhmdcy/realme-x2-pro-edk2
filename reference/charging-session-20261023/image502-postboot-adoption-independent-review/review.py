"""Read/hash/AST review only; never import or execute an author entry point."""
from pathlib import Path
import ast
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
POST = REF / 'charging-oem-audit-20261023/image502-postboot-readonly'
ADOPT = REF / 'charging-oem-audit-20261023/image502-adoption-candidate'
OLD_POST = REF / 'charging-management-20261023/image501-postboot-readonly'
OLD_ADOPT = REF / 'charging-session-20261023/gauge-image501-adoption-candidate'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def local(path):
    if path.startswith('/mnt/e/'):
        return Path('E:/' + path[len('/mnt/e/'):])
    return Path(path)


def functions(path):
    text = path.read_text(encoding='utf-8')
    return {node.name: ast.get_source_segment(text, node)
            for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}


def delivery(directory, expected):
    raw = (directory / 'delivery.json').read_bytes()
    assert sha(raw) == expected
    value = json.loads(raw)
    for name, row in value['files'].items():
        body = (directory / name).read_bytes()
        assert sha(body) == row['sha256'] and len(body) == row['bytes'], name
    return value


def bindings(directory):
    pins = json.loads((directory / 'source-pins.json').read_bytes())
    for row in pins.values():
        assert sha(local(row['path']).read_bytes()) == row['sha256'], row['path']
    return pins


post_delivery = delivery(POST, '876d19e4550815fc6c6e3cd35f095d9aa150e087004da74d92dde09d25cdb19b')
adopt_delivery = delivery(ADOPT, '20f4ee55e1659083301f38f43139f5a9a2581dc95366d08a6e8d87885e2471fd')
post_pins, adopt_pins = bindings(POST), bindings(ADOPT)
post_test = json.loads((POST / 'test-result.json').read_bytes())
adopt_test = json.loads((ADOPT / 'test-result.json').read_bytes())
for directory, receipt, count in [(POST, post_test, 8), (ADOPT, adopt_test, 10)]:
    assert receipt['passed'] is True and receipt['affected_case_count'] == count
    assert len(receipt['cases']) == count and receipt['old_suites_rerun'] is False
    for name, expected in receipt['tested_files'].items():
        assert sha((directory / name).read_bytes()) == expected

old, new = functions(OLD_POST / 'device.py'), functions(POST / 'device.py')
same = {name: sha(source.encode()) for name, source in old.items()
        if source == new.get(name)}
assert set(old) - set(same) == {'check_identity', 'check_partitions', 'main'}
assert len(same) == 23 and same == post_test['unchanged_device_functions']
assert functions(OLD_POST / 'payload.py')['save_response'] == functions(POST / 'payload.py')['save_response']
assert sha((OLD_POST / 'test-result.json').read_bytes()) == post_test['reused_receipts']['original_postboot']
fixture = (POST / 'fixture.py').read_text()
assert "postboot-r1-04-private/stdout-private.json" in fixture
original = Path('E:/edk2-samurai-out/charging-management-20261023/image501-activation/image501-gauge-live-001/postboot-r1-04-private/stdout-private.json')
assert sha(original.read_bytes()) == post_test['fixture_source_sha256']

device = (POST / 'device.py').read_text()
assert '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026' in new['check_identity']
assert "r['boot_id']!=g['boot_id']" in new['check_identity']
assert "r['boot_partition']['sha256']==UNCHANGED_BOOT" in new['check_partitions']
assert "r['logdump_partition']['sha256']==LOGDUMP502" in new['check_partitions']
assert all(word not in device for word in ['/dev/mem', 'mmap', 'O_RDWR', 'PROT_WRITE'])
assert "request['guard']['partitions']==['logdump']" in new['main']
contract = json.loads(local(adopt_pins['activation_contract']['path']).read_bytes())
fixed = contract['fixed_guard_fields']
assert fixed['partitions'] == ['logdump']
assert fixed['unchanged_boot_sha256'] == post_delivery['unchanged_boot_sha256']
assert fixed['candidate_logdump_sha256'] == post_delivery['candidate_logdump_sha256']
assert fixed['image502_sha256'] == post_delivery['Image502_sha256']

old_a, new_a = functions(OLD_ADOPT / 'adopt.py'), functions(ADOPT / 'adopt.py')
same_a = {name: sha(source.encode()) for name, source in old_a.items()
          if source == new_a.get(name)}
assert same_a == adopt_test['unchanged_functions']
assert set(same_a) == {'create', 'save', 'sources', 'main'}
text_a = (ADOPT / 'adopt.py').read_text()
old_text_a = (OLD_ADOPT / 'adopt.py').read_text()
def join_tail(text):
    return text.split(" with (out/'adopt-stdout-private.json').open('xb') as stdout", 1)[1].split(' reply=json.loads', 1)[0]
assert join_tail(text_a) == join_tail(old_text_a)
assert sha(join_tail(text_a).encode()) == adopt_test['unchanged_actual_same_child_join_sha256']
for name, expected in adopt_test['reused_receipts'].items():
    assert sha((OLD_ADOPT / name).read_bytes()) == expected
assert "if sys.flags.optimize:raise RuntimeError" in text_a
assert "return b'import sys\\nif sys.flags.optimize:raise RuntimeError" in new_a['payload']
assert "context=operator.validate_context(context_path)" in new_a['review']
assert "m.audit(report['raw'],request)['passed'] is True" in new_a['review']
assert "'candidate_boot_sha256':fixed['unchanged_boot_sha256']" in new_a['review']
assert new_a['payload'].index('collect(request,fresh);verified=audit(fresh,request)') < new_a['payload'].index('p.parent.mkdir(mode=0o700)')
previous = new_a['check_previous']
for expression in ["previous['Image501_verified'] is True", "previous['original_key_verified'] is True",
                   "g['unchanged_boot_sha256']", "g['rollback_logdump_sha256']",
                   '/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt',
                   '/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt']:
    assert expression in previous
publish = new_a['publish']
assert publish.index("pointer.read_bytes()==before") < publish.index('temp.replace(pointer)')
assert "os.fsync(fd)" in publish and "'boot-adoption-before-image502-private.json'" in publish
assert "boot_and_logdump_verified" in publish and 'candidate_pair_verified' not in publish
assert "create(out/'boot-adoption-before-image502-private.json',pointer_raw)" in new_a['adopt']
assert new_a['adopt'].index('check_previous(previous,d)') < new_a['adopt'].index('subprocess.Popen')

result = {
    'conclusion': 'no_new_blocker_in_reviewed_delta',
    'scope': 'Static differences, frozen source/test bindings and prior receipt reuse only',
    'author_deliveries': {str(POST.relative_to(REF)): sha((POST / 'delivery.json').read_bytes()),
                          str(ADOPT.relative_to(REF)): sha((ADOPT / 'delivery.json').read_bytes())},
    'reviewed_sources': {str(p.relative_to(REF)): sha(p.read_bytes()) for p in
                         [POST / 'device.py', POST / 'payload.py', ADOPT / 'adopt.py']},
    'author_affected_test_receipts': {'postboot': sha((POST / 'test-result.json').read_bytes()),
                                     'adoption': sha((ADOPT / 'test-result.json').read_bytes())},
    'unchanged_collector_functions': same,
    'unchanged_adoption_functions': same_a,
    'same_child_wait_tail_unchanged': True,
    'actual_boundary': 'boot97811 unchanged; logdump ace2 and new boot #502 required; previous 501 guard/7e5 required before adopting',
    'preserved': ['SDP/CDP budget classification', 'precise Full/FC and safety gates', 'R8/camera481/startup500',
                  'unknown budget rejection', 'host and remote optimize refusal', 'old pointer backup and atomic replacement'],
    'new_test_counts_reviewed_not_executed': {'postboot': 8, 'adoption': 10},
    'author_entrypoints_imported_or_executed': False,
    'tests_build_storage_device_SSH_USB_Git_used': False,
    'actual_newboot_guard_adoption_latency_proven': False,
    'reviewer_sha256': sha(Path(__file__).read_bytes())
}
output = HERE / 'review-result.json'
with output.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
print(json.dumps({'conclusion': result['conclusion'], 'review_result_sha256': sha(output.read_bytes())}))
