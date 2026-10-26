"""Read/hash/AST-only review; never imports or executes activation code."""
from pathlib import Path
import ast
import copy
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NEW = ROOT / 'reference/charging-session-20261023/gauge-image501-activation-candidate'
OLD = ROOT / 'reference/charging-session-20261023/eud-boot-activation-host-candidate'
OLD_WORKERS = ROOT / 'reference/charging-session-20261023/eud-boot-activation-candidate'
ADDENDUM = ROOT / 'reference/charging-session-20261023/gauge-image501-activation-scope-addendum/result.json'
sha = lambda b: hashlib.sha256(b).hexdigest()
read_json = lambda p: json.loads(p.read_bytes())


def tree(path):
    return ast.parse(path.read_text(encoding='utf-8'))


def functions(path):
    return {n.name: n for n in tree(path).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def dump(node):
    return ast.dump(node, include_attributes=False)


def main():
    delivery = read_json(NEW / 'delivery.json')
    assert sha((NEW / 'delivery.json').read_bytes()) == 'c7983040c0bc5a58976acc4973ea5a2bfd793a62c2a3410cfeb7fb3c0a240a46'
    frozen = {}
    for name, wanted in delivery['files'].items():
        raw = (NEW / name).read_bytes()
        actual = {'sha256': sha(raw), 'bytes': len(raw)}
        assert actual == wanted, name
        frozen[name] = actual
    for path, expected in read_json(NEW / 'source-provenance.json')['base_files'].items():
        assert sha((ROOT / Path(path)).read_bytes()) == expected, path

    result = read_json(NEW / 'test-result.json')
    assert result['passed'] and len(result['groups']) == 4
    assert result['native_worker_or_syscall_or_transport_executed'] is False
    assert result['old_suites_rerun'] is False
    assert len(result['groups'][0]['cases']) == 10
    assert len(result['groups'][2]['cases']) == 7
    for name, expected in result['files'].items():
        assert sha((NEW / name).read_bytes()) == expected, name

    prior = functions(OLD / 'controller.py')
    current = functions(NEW / 'controller.py')
    same = ['create', 'save', 'process_identity', 'process_status', 'ssh_worker',
            'start_job', 'terminal_job', 'require_known', 'reconcile',
            'fetch_reconcile', 'retain_fetch', 'copy_exact', 'host_jobs']
    for name in same:
        assert dump(prior[name]) == dump(current[name]), name

    normalized_context = copy.deepcopy(current['export_context'])
    changed = 0
    for node in ast.walk(normalized_context):
        if isinstance(node, ast.Constant) and node.value == 'samurai-image501-fastboot-context-v1':
            node.value = 'samurai-eud-fastboot-context-v1'
            changed += 1
    assert changed == 1
    assert dump(prior['export_context']) == dump(normalized_context)

    old_remote = (OLD / 'remote.py').read_text(encoding='utf-8')
    new_remote = (NEW / 'remote.py').read_text(encoding='utf-8')
    new_remote = new_remote.replace('/run/samurai-image501-activation-owner-private.json',
                                    '/run/samurai-eud-boot-activation-owner-private.json')
    new_remote = new_remote.replace("r'image501-[a-z0-9-]{8,64}'", "r'eud-boot-[a-z0-9-]{8,64}'")
    assert dump(ast.parse(old_remote)) == dump(ast.parse(new_remote))

    marker = "assert sys.argv[3]=='--commit-quiesce'"
    old_q = (OLD_WORKERS / 'eud-quiesce.py').read_text(encoding='utf-8')
    new_q = (NEW / 'eud-quiesce.py').read_text(encoding='utf-8')
    assert old_q.count(marker) == new_q.count(marker) == 1
    assert old_q[old_q.index(marker):] == new_q[new_q.index(marker):].replace('image501-activation', 'eud-boot-activation')

    fragment = (NEW / 'guard-fragment.py').read_text(encoding='utf-8')
    assert fragment in new_q
    assert fragment in (NEW / 'eud-restart.py').read_text(encoding='utf-8')
    restart = (NEW / 'eud-restart.py').read_text(encoding='utf-8')
    assert '/dev/mem' not in restart and 'mmap' not in restart and 'pack_into' not in restart
    assert restart.count('libc.syscall(142,') == 1
    assert "with phase.open('x')" in restart
    assert 'except OSError:pass # informational transport/log failure' in restart
    assert restart.index('os.fsync(claim.fileno())') < restart.index('fcntl.ioctl(rootfd,0xc0045877,0)') < restart.index('libc.syscall(142,')
    assert 'if frozen:fcntl.ioctl(rootfd,0xc0045878,0)' in restart

    raw = (NEW / 'controller.py').read_bytes()
    normalized = (NEW / 'controller.py').read_text(encoding='utf-8').encode('utf-8')
    scope = read_json(NEW / 'context-scope.json')
    addendum = read_json(ADDENDUM)
    assert sha(raw) == addendum['raw_controller_sha256']
    assert sha(normalized) == scope['new_source_sha256'] == addendum['LF_normalized_text_sha256']
    assert sha(ADDENDUM.read_bytes()) == '0fafcffe54f32d66b8eea91c20a60ad2e3b1ec03fa115b3f08d01555e101860d'

    report = {
        'status': 'accepted-within-static-review-scope',
        'blockers': [],
        'reviewed_delivery_sha256': sha((NEW / 'delivery.json').read_bytes()),
        'frozen_files': frozen,
        'independently_confirmed': {
            'all_delivery_and_test_source_pins_match_final_raw_bytes': True,
            'base_provenance_raw_hashes_match': True,
            'supervisor_same_child_unknown_functions_ast_unchanged': same,
            'export_context_actual_final_ast_only_schema_literal_changed': True,
            'remote_only_owner_and_transaction_regex_changed': True,
            'quiesce_hardware_suffix_unchanged_except_work_label': True,
            'guard_fragment_exact_text_in_both_workers': True,
            'no_restart_MMIO_single_syscall_durable_claim_order': True,
            'context_scope_raw_and_LF_hashes_distinguished': {
                'raw_controller_sha256': sha(raw),
                'LF_normalized_controller_sha256': sha(normalized),
                'addendum_sha256': sha(ADDENDUM.read_bytes()),
            },
        },
        'reused_author_tests': {
            'receipt_sha256': sha((NEW / 'test-result.json').read_bytes()),
            'groups': 4, 'actual_guard_cases': 10, 'actual_restart_tail_cases': 7,
            'independent_reexecution': False,
        },
        'scope': [
            'New profile/guard bindings and removal of EUD controls; transport-independent single restart tail.',
            'Original SSH child identity/terminal reconciliation; persistent mutation intent and fetch-only unknown outcome.',
            'Seven-raw context export distinguishes dispatch/armed intent from syscall, bootloader and new-boot success.',
        ],
        'limits': [
            'Static review plus hash/AST comparisons; no worker, controller entry, transport, syscall, old test suite, device, SDK, build or Git operation executed.',
            'Root/UI independently own candidate/rollback carrier pair, fastboot tool, live handoff and postboot verification.',
            'SSH loss, filesystem_frozen_restart2_armed and terminal SSH return do not prove reboot; fresh fastboot identity and a separately validated new boot remain required.',
            'No requirement to fetch vanished /run logs after reboot; available phase logs are evidence of intent only.',
        ],
    }
    report['review_program_sha256'] = sha(Path(__file__).read_bytes())
    (HERE / 'review.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'review_sha256': sha((HERE / 'review.json').read_bytes())}))


if __name__ == '__main__':
    main()
