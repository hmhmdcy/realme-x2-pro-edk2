"""Offline actual guard/claim/dispatch tests; subprocess boundary is always fake."""
import importlib.util
import json
from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('operator_under_review', HERE / 'fastboot-operator.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
passed = []


def rejects(fn):
    try:
        fn()
    except (ValueError, FileExistsError):
        return
    raise AssertionError('required refusal did not occur')


def fixture(base):
    txn, token, boot = 'eud-boot-fixture-operator', '7' * 64, str(uuid.uuid4())
    base = base / txn
    base.mkdir()
    contract = m.read_json(m.ACTIVATION / 'prepare-contract.json')
    guard = dict(contract['fixed_guard_fields'], transaction_id=txn, token=token,
                 boot_id=boot, kernel_version='#363 fixture', rootfs_release_sha256='1' * 64,
                 soc_serial_sha256='2' * 64, compatible_sha256='3' * 64)
    files = {}

    def put(name, value, raw=False):
        p = base / (name + '-private.json')
        p.write_text(value if raw else json.dumps(value))
        files[name] = {'path': p.name, 'sha256': m.sha(p)}
        return p

    put('guard', guard)
    remote = '/root/charging-management-20261023/' + txn
    common = dict(transaction_id=txn, token=token, boot_id=boot)
    put('quiesce_state', dict(common, terminal=True, exit_code=0, pid=111))
    put('quiesce_summary', dict(common, taint=0))
    put('quiesce_boot_id', boot + '\n', True)
    put('quiesce_process', dict(common, pid=111, startticks=12, status='absent',
        argv=['python3', '-B', remote + '/eud-quiesce.py', '--guard',
              remote + '/guard-private.json', '--commit-quiesce']))
    restart = dict(common, request_count=1, worker_sha256=m.RESTART_SHA,
        guard_sha256=files['guard']['sha256'], argv=['python3', '-B', remote + '/eud-restart.py',
        '--guard', remote + '/guard-private.json', '--commit-restart2-bootloader'])
    put('restart_claim', dict(restart, schema='samurai-eud-restart-host-claim-v1'))
    put('restart_dispatch', dict(restart, schema='samurai-eud-restart-dispatch-v1',
        state='dispatched_once', host_claim_sha256=files['restart_claim']['sha256'],
        restart_claim_intent='claimed_by_pinned_worker', restart_claim_observed=False,
        host_process=dict(pid=112, startticks=13, argv=['ssh', 'fixture'], terminal=True, returncode=255)))
    context = dict(schema='samurai-eud-fastboot-context-v1', transaction_id=txn, token=token,
                   old_boot_id=boot, guard_sha256=files['guard']['sha256'], files=files)
    path = base / 'host-context-private.json'
    path.write_text(json.dumps(context))

    def change(name, key, value):
        record = base / files[name]['path']
        obj = m.read_json(record)
        obj[key] = value
        record.write_text(json.dumps(obj))
        files[name]['sha256'] = m.sha(record)
        path.write_text(json.dumps(context))

    return path, context, change


def case(name, fn):
    with tempfile.TemporaryDirectory(prefix='eud-fastboot-offline-') as tmp:
        fn(Path(tmp))
    passed.append(name)


def guard_cases(tmp):
    path, ctx, change = fixture(tmp)
    got = m.validate_context(path)
    assert got == ctx  # SSH255 is NOT bootloader proof; run_action still must query.
    change('quiesce_state', 'terminal', False)
    rejects(lambda: m.validate_context(path))
    change('quiesce_state', 'terminal', True)
    change('quiesce_process', 'status', 'running')
    rejects(lambda: m.validate_context(path))
    change('quiesce_process', 'status', 'zombie')
    assert m.validate_context(path)


def wrong_guard(tmp):
    path, ctx, change = fixture(tmp)
    change('guard', 'schema', 'old-r7-stage')
    # Digest is now explicitly rebound, so refusal tests schema, not stale hash.
    ctx['guard_sha256'] = ctx['files']['guard']['sha256']
    path.write_text(json.dumps(ctx))
    rejects(lambda: m.validate_context(path))


def wrong_restart(tmp):
    path, ctx, change = fixture(tmp)
    change('restart_dispatch', 'request_count', 2)
    rejects(lambda: m.validate_context(path))
    change('restart_dispatch', 'request_count', 1)
    change('restart_dispatch', 'worker_sha256', '0' * 64)
    rejects(lambda: m.validate_context(path))


def changed_evidence(tmp):
    path, ctx, change = fixture(tmp)
    (path.parent / ctx['files']['quiesce_summary']['path']).write_text('{}')
    rejects(lambda: m.validate_context(path))


def request(action='inspect', **updates):
    return dict(dict(action=action, transaction_id='fixture', token='test', old_boot_id='test',
                     context_sha256='test', claimed_ns=1), **updates)


def terminal(directory, req, **updates):
    result = dict(req, terminal=True, commands_terminal=True, passed=True)
    result.update(updates)
    m.publish_result(directory / 'result-private.json', result)


def claim_pending(tmp):
    m.claim_action(tmp, 'inspect', request())
    rejects(lambda: m.claim_action(tmp, 'flash-candidate', request('flash-candidate')))


def claim_once(tmp):
    req = request()
    d = m.claim_action(tmp, 'inspect', req)
    terminal(d, req)
    rejects(lambda: m.claim_action(tmp, 'inspect', req))
    # A known failure can permit a separately requested rollback; unknown cannot.
    data = m.read_json(d / 'result-private.json'); data['passed'] = False
    (d / 'result-private.json').write_text(json.dumps(data))
    assert m.claim_action(tmp, 'rollback-original', request('rollback-original'))


def unknown_and_partial(tmp):
    req = request()
    d = m.claim_action(tmp, 'inspect', req)
    terminal(d, req, commands_terminal=False)
    rejects(lambda: m.claim_action(tmp, 'rollback-original', request('rollback-original')))
    (d / 'result-private.json').unlink()
    (d / 'request-private.json').unlink()
    rejects(lambda: m.claim_action(tmp, 'rollback-original', request('rollback-original')))


def reboot_order(tmp):
    rejects(lambda: m.claim_action(tmp, 'reboot', request('reboot')))
    req = request('flash-candidate')
    d = m.claim_action(tmp, 'flash-candidate', req)
    terminal(d, req, passed=False)
    rejects(lambda: m.claim_action(tmp, 'reboot', request('reboot')))
    data = m.read_json(d / 'result-private.json'); data['passed'] = True
    (d / 'result-private.json').write_text(json.dumps(data))
    assert m.claim_action(tmp, 'reboot', request('reboot'))


class Calls:
    def __init__(self, devices='FIXTURE fastboot\n', product='product: msmnile\n',
                 size='partition-size:boot: 0x6000000\n', fail=None):
        self.responses = {'devices': (devices, ''), 'product': ('', product), 'boot-size': ('', size),
                          'flash': ('', "Sending 'boot' OKAY\nWriting 'boot' OKAY\n"),
                          'reboot': ('', 'Rebooting OKAY\n')}
        self.calls, self.fail = [], fail

    def __call__(self, label, argv):
        self.calls.append((label, argv))
        if label == self.fail:
            raise ValueError('fake command nonzero; no mutation retry')
        return self.responses[label]


def identity_dispatch(tmp):
    for calls in (Calls(devices='FIXTURE fastboot\nOTHER fastboot\n'),
                  Calls(devices='OTHER fastboot\n'), Calls(product='product: wrong\n'),
                  Calls(size='partition-size:boot: 0x4000000\n')):
        rejects(lambda: m.run_action('flash-candidate', 'FIXTURE', calls))
        assert not any(c[0] == 'flash' for c in calls.calls)


def read_only_inspect(tmp):
    c = Calls()
    r = m.run_action('inspect', 'FIXTURE', c)
    assert r['fresh_exact_bootloader_identity'] and r['partitions_written'] == []
    assert [v[0] for v in c.calls] == ['devices', 'product', 'boot-size']


def boot_only_dispatch(tmp):
    # Actual fixed image hashes, fake command boundary. No fastboot process.
    for action, image in (('flash-candidate', m.CANDIDATE), ('rollback-original', m.ROLLBACK)):
        c = Calls()
        result = m.run_action(action, 'FIXTURE', c)
        assert result['partitions_written'] == ['boot']
        assert len(c.calls) == 4 and c.calls[-1][1] == [m.FASTBOOT, '-s', 'FIXTURE',
                                                       'flash', 'boot', m.windows_path(image)]


def failed_flash_no_reboot(tmp):
    c = Calls(fail='flash')
    rejects(lambda: m.run_action('flash-candidate', 'FIXTURE', c))
    assert len(c.calls) == 4 and all(v[0] != 'reboot' for v in c.calls)


def explicit_reboot(tmp):
    c = Calls()
    r = m.run_action('reboot', 'FIXTURE', c)
    assert c.calls[-1][1] == [m.FASTBOOT, '-s', 'FIXTURE', 'reboot']
    assert r['boot_success_proven'] is False and r['partitions_written'] == []


def command_wait_receipt(tmp):
    class Child:
        pid = 1234
        waited = 0
        def wait(self):
            self.waited += 1
            return 0
    child = Child()
    with patch.object(m.subprocess, 'Popen', return_value=child) as popen, \
         patch.object(m, 'process_info', side_effect=OSError('fake /proc receipt failure')):
        rejects(lambda: m.command(tmp, 'devices', [m.FASTBOOT, 'devices']))
    assert child.waited == 1 and popen.call_count == 1
    assert m.read_json(tmp / 'devices-terminal-private.json')['terminal'] is True
    assert not hasattr(child, 'kill')  # Implementation cannot rely on kill.


def command_nonzero_and_spawn(tmp):
    class Child:
        pid = 1234
        def wait(self):
            return 1
    with patch.object(m.subprocess, 'Popen', return_value=Child()), \
         patch.object(m, 'process_info', return_value={'pid': 1234, 'startticks': 4, 'argv': ['fixture']}):
        rejects(lambda: m.command(tmp, 'product', [m.FASTBOOT, 'getvar', 'product']))
    assert m.read_json(tmp / 'product-terminal-private.json')['returncode'] == 1
    with patch.object(m.subprocess, 'Popen', side_effect=OSError('fake spawn failure')):
        try:
            m.command(tmp, 'devices', [m.FASTBOOT, 'devices'])
        except OSError:
            pass
        else:
            raise AssertionError('spawn error required')
    assert m.read_json(tmp / 'devices-terminal-private.json')['spawn_failed'] is True


def client_timeout_blocks_replay(tmp):
    path, ctx, change = fixture(tmp)
    class Child:
        pid = 222
    with patch.object(m, 'local_inputs', return_value={'offline_fixture': True}), \
         patch.object(m.subprocess, 'Popen', return_value=Child()) as popen, \
         patch.object(m, 'process_info', return_value={'pid': 222, 'startticks': 22, 'argv': ['fixture']}):
        rejects(lambda: m.main(['inspect', '--context', str(path)]))
        assert popen.call_count == 0
        assert m.main(['inspect', '--context', str(path), '--execute', '--window-confirmed',
                       '--wait-seconds', '0']) == 2
        rejects(lambda: m.main(['flash-candidate', '--context', str(path), '--execute',
                               '--window-confirmed', '--wait-seconds', '0']))
        assert popen.call_count == 1  # detached owner only; no retry/kill/new write
    assert not (path.parent / 'fastboot-operator/inspect/result-private.json').exists()


def actual_worker_terminal(tmp):
    path, ctx, change = fixture(tmp)
    base = path.parent / 'fastboot-operator'
    base.mkdir()
    inputs = {'offline_fixture': True}
    req = dict(schema='samurai-eud-fastboot-action-v1', execute_authorized=True,
        window_confirmed=True, action='inspect', transaction_id=ctx['transaction_id'],
        token=ctx['token'], old_boot_id=ctx['old_boot_id'], context_path=str(path),
        context_sha256=m.sha(path), operator_sha256=m.sha(HERE / 'fastboot-operator.py'),
        inputs=inputs, claimed_ns=1)
    directory = m.claim_action(base, 'inspect', req)
    responses = Calls().responses
    class Child:
        pid = 222
        def wait(self):
            return 0
    def fake_popen(argv, **kwargs):
        label = 'devices' if argv[-1] == 'devices' else 'product' if argv[-1] == 'product' else 'boot-size'
        out, err = responses[label]
        kwargs['stdout'].write(out.encode()); kwargs['stderr'].write(err.encode())
        return Child()
    with patch.object(m, 'local_inputs', return_value=inputs), \
         patch.object(m, 'read_json', wraps=m.read_json) as reader, \
         patch.object(m.subprocess, 'Popen', side_effect=fake_popen) as popen, \
         patch.object(m, 'process_info', return_value={'pid': 222, 'startticks': 22, 'argv': ['fixture']}):
        original = reader._mock_wraps
        reader.side_effect = lambda p: {'serial': 'FIXTURE'} if Path(p) == m.IDENTITY else original(p)
        m.worker(directory / 'request-private.json')
        assert popen.call_count == 3
    result = m.read_json(directory / 'result-private.json')
    assert result['passed'] and result['commands_terminal'] and result['partitions_written'] == []
    assert len(list(directory.glob('*-terminal-private.json'))) == 3
    m.prior_terminal(base, 'flash-candidate')  # actual worker result unblocks, no manual rewriting


for name, fn in [
    ('exact_new_context_and_quiesce_terminal_process', guard_cases),
    ('old_schema_rejected_after_digest_rebinding', wrong_guard),
    ('repeat_restart_claim_and_wrong_worker_rejected', wrong_restart),
    ('raw_evidence_changed_rejected', changed_evidence),
    ('pending_action_blocks_new_claim', claim_pending),
    ('claim_once_and_known_failed_action_allows_explicit_rollback', claim_once),
    ('unknown_child_and_partial_claim_block_new_action', unknown_and_partial),
    ('reboot_requires_last_image_success', reboot_order),
    ('sole_serial_product_and_boot_size_guards_before_write', identity_dispatch),
    ('inspect_queries_only', read_only_inspect),
    ('candidate_and_original_only_boot_dispatch', boot_only_dispatch),
    ('failed_flash_never_reboots_or_retries', failed_flash_no_reboot),
    ('reboot_separate_command_not_boot_acceptance', explicit_reboot),
    ('post_popen_receipt_failure_still_joins_same_child', command_wait_receipt),
    ('nonzero_and_spawn_failure_preserve_terminal_receipts', command_nonzero_and_spawn),
    ('client_timeout_keeps_claim_and_blocks_new_action_without_replay', client_timeout_blocks_replay),
    ('actual_detached_owner_function_persists_all_command_terminals', actual_worker_terminal),
]:
    case(name, fn)

receipt = {'passed': True, 'operator_sha256': m.sha(HERE / 'fastboot-operator.py'),
           'test_sha256': m.sha(__file__), 'cases': passed, 'case_count': len(passed),
           'subprocess_boundary': 'fake Popen/command only; no executable invoked',
           'scope': 'actual local guard/claim/dispatch functions, no fastboot/device/SSH/SDK/Git'}
(HERE / 'test-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
