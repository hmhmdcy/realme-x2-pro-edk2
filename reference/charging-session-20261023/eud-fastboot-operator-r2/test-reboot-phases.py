"""Two offline actual state sequences; command boundary is fake, no executable."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OLD = HERE.with_name('eud-fastboot-operator')
spec = importlib.util.spec_from_file_location('fastboot_r2', HERE / 'fastboot-operator.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
require = m.require


def rejects(fn):
    try:
        fn()
    except (ValueError, FileExistsError):
        return
    raise AssertionError('expected refusal')


class FakeCommands:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def __call__(self, label, argv):
        self.calls.append((label, argv))
        if label == self.fail:
            raise ValueError('fake command terminal failure')
        return {'devices': ('FIXTURE fastboot\n', ''), 'product': ('', 'product: msmnile\n'),
                'boot-size': ('', 'partition-size:boot: 0x6000000\n'),
                'flash': ('', "Writing 'boot' OKAY\n"), 'reboot': ('', 'Rebooting OKAY\n')}[label]


def request(action, sequence):
    return dict(action=action, transaction_id='fixture', token='fixture', old_boot_id='fixture',
                context_sha256='fixture', claimed_ns=sequence)


def finish(directory, calls, passed=True):
    req = m.read_json(directory / 'request-private.json')
    report = {}
    try:
        if req['action'] in m.REBOOT_IMAGES:
            require(req['image_binding'] == m.reboot_binding(directory.parent, req['action']),
                    'actual worker binding check')
        report = m.run_action(req['action'], 'FIXTURE', calls)
        require(passed, 'fixture must request actual command failure')
    except ValueError:
        require(not passed, 'unexpected actual dispatch refusal')
    m.publish_result(directory / 'result-private.json', dict(report, action=req['action'],
        terminal=True, commands_terminal=True, passed=passed, claimed_ns=req['claimed_ns'],
        transaction_id=req['transaction_id'], token=req['token'], old_boot_id=req['old_boot_id'],
        context_sha256=req['context_sha256']))
    return report


def perform(base, action, sequence, fail=None):
    directory = m.claim_action(base, action, request(action, sequence))
    calls = FakeCommands(fail)
    report = finish(directory, calls, passed=fail is None)
    require(len(calls.calls) == 4, 'three fresh queries plus exactly one explicit command')
    if action in m.REBOOT_IMAGES:
        require(calls.calls[-1][1] == [m.FASTBOOT, '-s', 'FIXTURE', 'reboot'], 'only reboot command')
    else:
        require(calls.calls[-1][1][3:5] == ['flash', 'boot'], 'only boot partition')
        require(all(label != 'reboot' for label, argv in calls.calls), 'no automatic reboot')
    return directory, report


def success_then_explicit_recovery(base):
    rejects(lambda: m.claim_action(base, 'reboot-candidate', request('reboot-candidate', 0)))
    perform(base, 'flash-candidate', 1)
    rejects(lambda: m.claim_action(base, 'reboot-original', request('reboot-original', 2)))
    candidate, report = perform(base, 'reboot-candidate', 2)
    require(report['boot_success_proven'] is False, 'command success is not boot acceptance')
    binding = m.read_json(candidate / 'request-private.json')['image_binding']
    require(binding['image_action'] == 'flash-candidate' and binding['image_sha256'] == m.CANDIDATE_SHA,
            'candidate claim bound to exact successful image')
    rejects(lambda: m.claim_action(base, 'reboot-candidate', request('reboot-candidate', 3)))
    perform(base, 'rollback-original', 3)
    rejects(lambda: m.claim_action(base, 'reboot-candidate', request('reboot-candidate', 4)))
    original, report = perform(base, 'reboot-original', 4)
    binding = m.read_json(original / 'request-private.json')['image_binding']
    require(binding['image_action'] == 'rollback-original' and binding['image_sha256'] == m.ROLLBACK_SHA,
            'original claim bound to exact successful rollback')
    require(binding['image_claim_sha256'] == m.sha(base / 'rollback-original/request-private.json') and
            binding['image_result_sha256'] == m.sha(base / 'rollback-original/result-private.json'),
            'exact original image claim/result hashes')
    rejects(lambda: m.claim_action(base, 'reboot-original', request('reboot-original', 5)))


def failed_reboot_pending_then_failed_rollback(base):
    perform(base, 'flash-candidate', 1)
    perform(base, 'reboot-candidate', 2, fail='reboot')
    rejects(lambda: m.claim_action(base, 'reboot-candidate', request('reboot-candidate', 3)))
    rejects(lambda: m.claim_action(base, 'reboot-original', request('reboot-original', 3)))
    original = m.claim_action(base, 'rollback-original', request('rollback-original', 3))
    rejects(lambda: m.claim_action(base, 'reboot-original', request('reboot-original', 4)))
    rejects(lambda: m.claim_action(base, 'reboot-candidate', request('reboot-candidate', 4)))
    rejects(lambda: m.claim_action(base, 'flash-candidate', request('flash-candidate', 4)))
    calls = FakeCommands(fail='flash')
    finish(original, calls, passed=False)
    require(len(calls.calls) == 4 and calls.calls[-1][0] == 'flash', 'original failed write known terminal')
    rejects(lambda: m.claim_action(base, 'reboot-original', request('reboot-original', 4)))
    rejects(lambda: m.claim_action(base, 'reboot-candidate', request('reboot-candidate', 4)))
    require(not (base / 'reboot-original').exists(), 'failed/latest-unknown image never consumes new reboot')


old_source = (OLD / 'fastboot-operator.py').read_text()
new_source = (HERE / 'fastboot-operator.py').read_text()
require(m.sha(OLD / 'fastboot-operator.py') == 'b8f043ea4d9c904bf36bd71ec2e861f0a74e0138fadd42f2f0b34ef534430d57',
        'old original preserved')
def functions(text):
    return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
old_functions, new_functions = functions(old_source), functions(new_source)
unchanged = ['command', 'process_info', 'fetch', 'validate_context', 'local_inputs', 'main']
require(all(old_functions[name] == new_functions[name] for name in unchanged),
        'single-command Popen/unknown/context/default boundaries changed')
old_receipt = m.read_json(OLD / 'test-result.json')
require(old_receipt['passed'] and old_receipt['case_count'] == 17 and
        m.sha(OLD / 'test-result.json') == 'cbf0162967b276fab08f435e136d055e99160ef3481ab262e1716fc764c69d54',
        'old 17 receipt binding')
cases = []
for fn in (success_then_explicit_recovery, failed_reboot_pending_then_failed_rollback):
    with tempfile.TemporaryDirectory(prefix='eud-fastboot-phase-offline-') as temp:
        fn(Path(temp))
    cases.append(fn.__name__)
receipt = {'passed': True, 'operator_sha256': m.sha(HERE / 'fastboot-operator.py'),
           'test_sha256': m.sha(__file__), 'cases': cases, 'case_count': 2,
           'unchanged_actual_function_sources': unchanged,
           'old_17_receipt_sha256': m.sha(OLD / 'test-result.json'), 'old_17_rerun': False,
           'boundary': 'actual state/claim/binding/dispatch; fake fastboot commands only',
           'fastboot_usb_device_ssh_sdk_git_invoked': False}
(HERE / 'test-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
