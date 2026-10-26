"""Exercise the real pair dispatcher and durable state with fake fastboot only."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pair_operator', HERE / 'fastboot-operator.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cases = []


def refuses(fn):
    try:
        fn()
    except (ValueError, FileExistsError):
        return
    raise AssertionError('required refusal missing')


class Calls:
    def __init__(self, fail=None, wrong_size=None):
        self.seen = []
        self.fail = fail
        self.wrong_size = wrong_size

    def __call__(self, label, argv):
        self.seen.append((label, argv))
        if label == self.fail:
            raise ValueError('known fake terminal failure')
        if label == 'devices':
            return 'FIXTURE fastboot\n', ''
        if label == 'product':
            return '', 'product: msmnile\n'
        if label.endswith('-size'):
            part = label.removesuffix('-size')
            size = m.IMAGES['candidate'][part][2] + int(part == self.wrong_size)
            return '', f'partition-size:{part}: {size}\n'
        if label.startswith('flash-'):
            return '', f"Writing '{label.removeprefix('flash-')}' OKAY\n"
        if label == 'reboot':
            return '', 'Rebooting OKAY\n'
        raise AssertionError(label)


def request(action, seq):
    return dict(action=action, transaction_id='fixture', token='fixture', old_boot_id='fixture',
                context_sha256='fixture', claimed_ns=seq)


def execute(base, action, seq, fail=None):
    directory = m.claim_action(base, action, request(action, seq))
    calls = Calls(fail)
    report = {}
    passed = False
    try:
        report = m.run_action(action, 'FIXTURE', calls)
        passed = True
    except ValueError:
        assert fail is not None
    m.publish_result(directory / 'result-private.json', dict(report, action=action, terminal=True,
        commands_terminal=True, passed=passed, claimed_ns=seq, transaction_id='fixture', token='fixture',
        old_boot_id='fixture', context_sha256='fixture'))
    return directory, calls, report


with tempfile.TemporaryDirectory(prefix='image501-pair-offline-', dir=m.PRIVATE) as temporary:
    temporary = Path(temporary)
    real_images = m.IMAGES
    m.IMAGES = {}
    for which in real_images:
        m.IMAGES[which] = {}
        for part in real_images[which]:
            path = temporary / (which + '-' + part + '.img')
            raw = (which + ':' + part).encode()
            path.write_bytes(raw)
            m.IMAGES[which][part] = path, hashlib.sha256(raw).hexdigest(), len(raw)

    # Full candidate, explicit reboot, full independent rollback, explicit original reboot.
    base = temporary / 'success'; base.mkdir()
    refuses(lambda: m.claim_action(base, 'reboot-candidate', request('reboot-candidate', 0)))
    directory, calls, report = execute(base, 'flash-candidate', 1)
    assert [x[0] for x in calls.seen] == ['devices', 'product', 'boot-size', 'logdump-size',
                                         'flash-logdump', 'flash-boot']
    assert report['flashed_pair_sha256'] == m.pair_hashes('candidate')
    refuses(lambda: m.claim_action(base, 'reboot-original', request('reboot-original', 2)))
    execute(base, 'reboot-candidate', 2)
    execute(base, 'rollback-original', 3)
    refuses(lambda: m.claim_action(base, 'reboot-candidate', request('reboot-candidate', 4)))
    directory, calls, report = execute(base, 'reboot-original', 4)
    assert [x[0] for x in calls.seen][-1] == 'reboot' and not report['boot_success_proven']
    assert m.read_json(directory / 'request-private.json')['image_binding']['pair_sha256'] == m.pair_hashes('original')
    refuses(lambda: m.claim_action(base, 'rollback-original', request('rollback-original', 5)))
    cases.append('both_pairs_then_separate_matching_reboots_and_no_replay')

    # First member succeeded, second failed: neither candidate nor original reboot allowed.
    base = temporary / 'partial'; base.mkdir()
    directory, calls, report = execute(base, 'flash-candidate', 1, fail='flash-boot')
    assert calls.seen[-2][0] == 'flash-logdump' and calls.seen[-1][0] == 'flash-boot'
    for action in m.REBOOT_IMAGES:
        refuses(lambda action=action: m.claim_action(base, action, request(action, 2)))
    execute(base, 'rollback-original', 2)
    execute(base, 'reboot-original', 3)
    cases.append('known_partial_pair_refuses_reboot_then_explicit_full_rollback')

    # Missing original terminal never becomes success from an absent process.
    base = temporary / 'unknown'; base.mkdir()
    m.claim_action(base, 'flash-candidate', request('flash-candidate', 1))
    for action in ('rollback-original', 'reboot-candidate', 'reboot-original'):
        refuses(lambda action=action: m.claim_action(base, action, request(action, 2)))
    cases.append('unknown_original_pair_blocks_all_following_mutations')

    calls = Calls(wrong_size='logdump')
    refuses(lambda: m.run_action('flash-candidate', 'FIXTURE', calls))
    assert not any(label.startswith('flash-') for label, argv in calls.seen)
    cases.append('both_partition_sizes_checked_before_any_write')

    path = m.IMAGES['candidate']['boot'][0]
    raw = path.read_bytes(); path.write_bytes(b'corrupt')
    calls = Calls()
    refuses(lambda: m.run_action('flash-candidate', 'FIXTURE', calls))
    assert not any(label.startswith('flash-') for label, argv in calls.seen)
    path.write_bytes(raw)
    cases.append('second_member_corruption_prevents_first_member_write')

    # Failed latest rollback must hide an older successful candidate pair from reboot binding.
    base = temporary / 'rollback-failed'; base.mkdir()
    execute(base, 'flash-candidate', 1)
    execute(base, 'rollback-original', 2, fail='flash-logdump')
    for action in m.REBOOT_IMAGES:
        refuses(lambda action=action: m.claim_action(base, action, request(action, 3)))
    cases.append('failed_latest_pair_never_reuses_older_success_for_reboot')

old = HERE.parent / 'eud-fastboot-operator-r2'
def functions(path):
    source = path.read_text()
    return {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef)}
old_functions = functions(old / 'fastboot-operator.py')
new_functions = functions(HERE / 'fastboot-operator.py')
unchanged = ['command', 'process_info', 'fetch', 'prior_terminal', 'claim_action']
assert all(old_functions[name] == new_functions[name] for name in unchanged)
assert m.sha(old / 'fastboot-operator.py') == '9894563222eb44e81b1fa1e7f1b755884ca161916b2a58650eac2edc20800912'
result = {'passed': True, 'case_count': len(cases), 'cases': cases,
          'operator_sha256': m.sha(HERE / 'fastboot-operator.py'), 'test_sha256': m.sha(__file__),
          'unchanged_original_functions': unchanged, 'old_test_receipt_sha256': m.sha(old / 'test-result.json'),
          'boundary': 'real pair, files, durable claim and reboot binding; fake fastboot commands only',
          'device_usb_ssh_sdk_git_accessed': False}
(HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
