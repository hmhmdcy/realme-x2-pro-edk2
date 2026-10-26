"""New host dispatch boundaries only. Synthetic temp material, fake OS/SSH."""
from pathlib import Path
import base64, copy, hashlib, importlib.util, json, os, subprocess, sys, tempfile, types, unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module); return module


c = load(HERE / 'controller.py', 'actual_new_host')
r = load(HERE / 'remote.py', 'actual_new_remote')
s = load(HERE / 'supervisor.py', 'actual_new_supervisor')
sha = c.sha


def review_fixture():
    # Reuse fixture data definitions, NOT the old suite or any entrypoint.
    dm = load(c.WORKERS / 'test-delta.py', 'frozen_device_fixture_only')
    ns = dm.load_functions(); meta, records, processes, claim, raws, proof = dm.fixture(ns)
    adoption = dict(meta['adoption']); adoption['actual_fresh_validation_sha256'] = adoption.pop('fresh_validation_sha256')
    return dict(schema='samurai-authenticated-stage-review-v1', transaction_id=meta['stage']['transaction_id'],
        source_boot_id=meta['boot_id'], source_version=meta['kernel_version'], identity=records['request']['identity'],
        adoption=adoption, source_stage_authenticated=True, host_binding_sha256='6' * 64,
        stage_result=records['result']), meta['stage']


def job(directory, action, request, rc=0, value=None):
    target = directory / (action + '-job-fixture'); target.mkdir()
    program = ('CONFIG=' + repr(dict(request=request, action=action)) + '\n').encode() + (HERE / 'remote.py').read_bytes()
    c.create(target / 'program-private.py', program)
    argv = ['ssh-fixture', 'python3 -']
    c.save(target / 'job-private.json', dict(program=str(target / 'program-private.py'), program_sha256=sha(program),
        controller_sha256=sha((HERE / 'controller.py').read_bytes()), action=action, ssh_argv=argv,
        request_sha256=sha((directory / 'request-private.json').read_bytes())))
    c.save(directory / (action + '-job-private.json'), dict(job=str(target), action=action, program_sha256=sha(program)))
    original = dict(pid=201, startticks=4567, argv=argv)
    c.save(target / 'ssh-process-private.json', dict(original, requested_argv=argv, stdin_sha256=sha(program)))
    raw = json.dumps(value).encode() if value is not None else b''
    c.create(target / 'stdout-private.bin', raw); c.create(target / 'stderr-private.bin', b'')
    c.save(target / 'ssh-terminal-private.json', dict(original, terminal=True, returncode=rc, receipt_error=None,
        io_error=None, stdin_sha256=sha(program), stdout_sha256=sha(raw), stderr_sha256=sha(b'')))
    return target


def quiesce_facts(directory, request):
    target = directory / 'fetch-fixture'; target.mkdir()
    tx, token, boot = request['transaction_id'], request['token'], request['expected_boot']
    root = '/root/charging-management-20261023/' + tx
    common = dict(transaction_id=tx, token=token, boot_id=boot,
                  request_sha256=sha((directory / 'request-private.json').read_bytes()))
    argv = ['python3', '-B', root + '/eud-quiesce.py', '--guard', root + '/guard-private.json', '--commit-quiesce']
    sup = dict(common, pid=301, startticks=9875, argv=['python3', '-B', root + '/activation-supervisor.py', '--supervise-quiesce'])
    own = dict(common, pid=302, startticks=9876, argv=argv, worker_sha256=c.WORKER_HASHES['eud-quiesce.py'])
    intent = dict(common, request_count=1, argv=sup['argv'], supervisor_sha256=request['supervisor_sha256'])
    facts = {'remote-quiesce-process-private.json': own, 'remote-quiesce-supervisor-process-private.json': sup,
        'remote-quiesce-intent-private.json': intent,
        'remote-quiesce-supervisor-launch-private.json': dict(intent, pid=sup['pid'], startticks=sup['startticks']),
        'remote-quiesce-worker-launch-private.json': dict(own, supervisor_pid=sup['pid'], capture_error=None),
        'remote-quiesce-worker-terminal-private.json': dict(common, pid=own['pid'], argv=argv, supervisor_pid=sup['pid'], terminal=True, returncode=0),
        'remote-quiesce-supervisor-terminal-private.json': dict(sup, terminal=True, returncode=0, worker_pid=own['pid'], worker_returncode=0),
        'quiesce-state-private.json': dict(common, terminal=True, exit_code=0, pid=own['pid']),
        'quiesce-summary.json': dict(common, taint=0)}
    for name, data in facts.items(): c.save(target / name, data)
    c.create(target / 'quiesce-boot-id-private.txt', (boot + '\n').encode())
    value = dict(transaction_id=tx, token=token, boot_id=boot, same_old_boot=True, files={},
                 processes=dict(quiesce=dict(own, status='absent'), supervisor=dict(sup, status='zombie')))
    c.save(target / 'fetch-private.json', value)
    return target, value, facts


class Host(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.base = Path(self.temp.name)
        self.review, self.projection = review_fixture()
        self.tx = 'usb-irq-protection-activate-hostfixture-0001'
        self.endpoint = dict(kind='usb-ipv6', peer='fe80::62:bcff:fe28:a101%29', interface_index=29,
            host_key_alias='169.254.42.1', original_key_verified=True, observed_new_boot=self.review['source_boot_id'],
            guard_path=self.review['adoption']['guard_path'], postboot_Image502_passed=True)

    def tearDown(self): self.temp.cleanup()

    def bind(self):
        with patch.object(c, 'reviewed', return_value=(self.review, self.projection)), patch.object(c, 'endpoint_from_stage', return_value=self.endpoint):
            c.bind(self.tx, self.base / 'stage-missing-fixture', self.base / 'fetch-missing-fixture', private=self.base / 'activation')
        directory = self.base / 'activation' / self.tx
        return directory, c.load_json(directory / 'request-private.json')

    def test_missing_real_source_refused_before_mkdir(self):
        out = self.base / 'not-created'
        with patch.object(c, 'reviewed', side_effect=FileNotFoundError('no actual adopted/stage originals')):
            with self.assertRaises(FileNotFoundError): c.bind(self.tx, '/missing', '/missing', private=out)
        self.assertFalse(out.exists())
        bad = copy.deepcopy(self.review); bad['source_version'] = '#501'
        with patch.object(c, 'reviewed', return_value=(bad, self.projection)), patch.object(c, 'endpoint_from_stage', return_value=self.endpoint):
            with self.assertRaises(ValueError): c.bind(self.tx, '/missing', '/missing', private=out)
        self.assertFalse(out.exists())

    def test_bind_has_exact_new_guard_no_old_transaction_reuse(self):
        directory, request = self.bind(); guard = c.load_json(directory / 'guard-private.json')
        self.assertEqual(guard['stage'], self.projection)
        self.assertEqual(guard['partitions'], ['boot']); self.assertTrue(guard['kernel_version'].startswith('#502 '))
        self.assertEqual(set(request['files']), {'eud-quiesce.py', 'eud-restart.py', 'common.py', 'camera481-expected-private.json', 'activation-supervisor.py'})
        with patch.object(c, 'reviewed', return_value=(self.review, self.projection)), patch.object(c, 'endpoint_from_stage', return_value=self.endpoint):
            with self.assertRaises(ValueError): c.bind(self.tx, '/same', '/same', private=directory.parent)
        self.assertFalse((directory / 'prepare-intent-private.json').exists())

    def test_mutator_pending_has_once_intent_no_second_dispatch(self):
        directory, request = self.bind(); calls = []
        def start(d, action, req, pins, endpoint):
            calls.append(action); return dict(pending=True, job='original-only', no_replay=True)
        with patch.object(c, 'reviewed', return_value=(self.review, self.projection)), patch.object(c, 'endpoint_from_stage', return_value=self.endpoint):
            answer = c.run('prepare', self.tx, True, True, private=directory.parent, start=start)
            self.assertTrue(answer['pending'])
            with self.assertRaises(ValueError): c.run('prepare', self.tx, True, True, private=directory.parent, start=start)
        self.assertEqual(calls, ['prepare'])
        intent = c.load_json(directory / 'prepare-intent-private.json')
        self.assertEqual(intent['request_sha256'], sha((directory / 'request-private.json').read_bytes()))
        self.assertEqual(intent['guard_sha256'], request['guard_sha256'])

    def test_job_selection_precedes_popen_and_timeout_keeps_original(self):
        directory, request = self.bind(); seen = []
        class Child:
            pid = 44
            def wait(self, timeout=None): raise subprocess.TimeoutExpired('fixture', timeout)
        def popen(argv, **options):
            selected = c.load_json(directory / 'prepare-job-private.json')
            self.assertEqual(c.load_json(Path(selected['job']) / 'job-private.json')['program_sha256'], selected['program_sha256'])
            seen.append((argv, options)); return Child()
        with patch.object(c, 'ssh_argv', return_value=['ssh-fixture']), patch.object(c.subprocess, 'Popen', side_effect=popen), patch.object(c, 'process_identity', return_value=dict(pid=44, startticks=99, argv=['owned-supervisor'])):
            result = c.start_job(directory, 'prepare', request, {}, self.endpoint, wait_seconds=0)
        self.assertTrue(result['pending']); self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0][1]['start_new_session']); self.assertEqual(seen[0][1]['stdin'], subprocess.DEVNULL)

    def test_ssh_wait_and_exact_stdin_even_pipe_error(self):
        directory, request = self.bind(); target = directory / 'ssh-job'; target.mkdir()
        program = b'fixture input'; c.create(target / 'program.py', program)
        c.save(target / 'job-private.json', dict(program=str(target / 'program.py'), program_sha256=sha(program),
            controller_sha256=sha((HERE / 'controller.py').read_bytes()), ssh_argv=['ssh-fixture'], action='prepare'))
        events = []
        class Child:
            pid = 55; returncode = 255
            def communicate(self, input): events.append(('input', input)); raise BrokenPipeError('injected')
            def wait(self): events.append(('wait', self.pid)); return self.returncode
        # Windows OpenSSH's observed /proc argv may differ from its requested
        # WSL argv. Preserve both; owned handle/ticks/stdin/wait are authoritative.
        with patch.object(c, 'PRIVATE', directory.parent), patch.object(c.subprocess, 'Popen', return_value=Child()), patch.object(c, 'process_identity', return_value=dict(pid=55, startticks=88, argv=['Windows-PE-normalized-ssh-argv'])):
            c.ssh_worker(target / 'job-private.json')
        term, raw = c.terminal_job(target)
        self.assertEqual(events, [('input', program), ('wait', 55)])
        self.assertEqual(term['stdin_sha256'], sha(program)); self.assertEqual(term['returncode'], 255)
        self.assertNotEqual(term['argv'], ['ssh-fixture'])
        bad = c.load_json(target / 'ssh-process-private.json'); bad['stdin_sha256'] = '0' * 64
        (target / 'ssh-process-private.json').write_text(json.dumps(bad))
        with self.assertRaises(ValueError): c.terminal_job(target)

    def test_reconcile_promotes_only_original_rc0_input(self):
        directory, request = self.bind()
        value = dict(prepared=True, transaction_id=self.tx, token=request['token'], boot_id=request['expected_boot'],
                     request_sha256=sha((directory / 'request-private.json').read_bytes()), guard_sha256=request['guard_sha256'])
        target = job(directory, 'prepare', request, value=value)
        self.assertEqual(c.reconcile(directory)['prepare'], 'original_terminal_rc0_and_bound_reply')
        self.assertTrue(c.require_known(directory, 'prepare')['prepared'])
        original = c.load_json(target / 'ssh-terminal-private.json'); original['startticks'] += 1
        (target / 'ssh-terminal-private.json').write_text(json.dumps(original))
        with self.assertRaises(ValueError): c.require_known(directory, 'prepare')

    def test_unknown_ssh_only_qualifies_from_complete_same_remote_terminal(self):
        directory, request = self.bind(); job(directory, 'quiesce', request, rc=255)
        self.assertEqual(c.reconcile(directory)['quiesce'], 'original_failed_no_promotion')
        target, value, facts = quiesce_facts(directory, request)
        bad = copy.deepcopy(value); bad['processes']['quiesce']['status'] = 'unknown'
        with self.assertRaises(ValueError): c.qualify_quiesce(directory, bad, target)
        self.assertFalse((directory / 'quiesce-known-private.json').exists())
        c.qualify_quiesce(directory, value, target)
        self.assertTrue(c.load_json(directory / 'quiesce-known-private.json')['qualified_from_remote_terminal'])
        c.require_known(directory, 'quiesce')
        altered = copy.deepcopy(facts['remote-quiesce-worker-terminal-private.json']); altered['returncode'] = 1
        (target / 'remote-quiesce-worker-terminal-private.json').write_text(json.dumps(altered))
        with self.assertRaises(ValueError): c.qualify_quiesce(directory, value, target)

    def test_partial_prepare_never_promotes_unknown_owner(self):
        directory, request = self.bind(); job(directory, 'prepare', request, rc=255)
        target = directory / 'fetch-partial'; target.mkdir()
        c.create(target / 'remote-activation-request-private.json', (directory / 'request-private.json').read_bytes())
        c.create(target / 'remote-guard-private.json', (directory / 'guard-private.json').read_bytes())
        value = dict(same_old_boot=True)
        with self.assertRaises(FileNotFoundError): c.qualify_prepare(directory, value, target)
        self.assertFalse((directory / 'prepare-known-private.json').exists())
        for name, row in request['files'].items(): c.create(target / ('remote-' + name), base64.b64decode(row['base64']))
        c.save(target / 'remote-prepare-result-private.json', dict(prepared=True, hardware_writes=0,
            request_sha256=sha((directory / 'request-private.json').read_bytes()), guard_sha256=request['guard_sha256'],
            boot_id=request['expected_boot'], transaction_id=self.tx, token=request['token']))
        self.assertTrue(c.qualify_prepare(directory, value, target))
        self.assertTrue(c.require_known(directory, 'prepare')['prepared'])

    def test_preflight_releases_only_its_own_service_fd_on_both_paths(self):
        directory, request = self.bind(); root = self.base / 'remote-root'; root.mkdir()
        common_raw = b'# fake device-bound guard for release boundary only\n'
        (root / 'common.py').write_bytes(common_raw); req = dict(request, common_sha256=sha(common_raw))
        closed = []
        def good_guard(*args, **kwargs): return dict(transaction_id=self.tx, token=req['token'], boot_id=req['expected_boot']), None, None
        def fake_exec(code, namespace): namespace.update(_SERVICE_FD=77, os=types.SimpleNamespace(close=closed.append), validate_activation_guard=good_guard)
        with patch.object(r, 'exec', fake_exec, create=True): r.preflight(req, root)
        self.assertEqual(closed, [77])
        def bad_exec(code, namespace):
            def reject(*args, **kwargs): raise ValueError('actual guard rejects')
            namespace.update(_SERVICE_FD=78, os=types.SimpleNamespace(close=closed.append), validate_activation_guard=reject)
        with patch.object(r, 'exec', bad_exec, create=True):
            with self.assertRaises(ValueError): r.preflight(req, root)
        self.assertEqual(closed, [77, 78])

    def test_device_supervisor_metadata_failure_still_waits_original_child(self):
        directory, request = self.bind(); root = self.base / self.tx; root.mkdir()
        for name in ('eud-quiesce.py', 'activation-supervisor.py'):
            (root / name).write_bytes(base64.b64decode(request['files'][name]['base64']))
        (root / 'activation-request-private.json').write_bytes((directory / 'request-private.json').read_bytes())
        (root / 'guard-private.json').write_bytes((directory / 'guard-private.json').read_bytes())
        c.save(root / 'quiesce-intent-private.json', dict(transaction_id=self.tx, request_sha256=sha((directory / 'request-private.json').read_bytes())))
        argv = ['python3', '-B', str(root / 'eud-quiesce.py'), '--guard', str(root / 'guard-private.json'), '--commit-quiesce']
        events = []
        class Child:
            pid = 802
            def wait(self): events.append('wait-original'); return 1
        def identify(pid): return dict(pid=pid, startticks=900 + pid,
            argv=['python3', '-B', str(root / 'activation-supervisor.py'), '--supervise-quiesce'] if pid == 801 else argv)
        real_save = s.save
        def fail_launch(path, value):
            if path.name == 'quiesce-worker-launch-private.json': raise OSError('injected publication failure')
            real_save(path, value)
        fake_os = types.SimpleNamespace(umask=lambda mode: None, getpid=lambda: 801, open=os.open,
            fsync=os.fsync, close=os.close, O_RDONLY=os.O_RDONLY, O_DIRECTORY=getattr(os, 'O_DIRECTORY', 0))
        # save's directory fsync is Unix-specific; use the already tested host
        # fsynced save boundary for this Windows temp fixture.
        def portable_fail(path, value):
            if path.name == 'quiesce-worker-launch-private.json': raise OSError('injected publication failure')
            c.save(path, value)
        with patch.object(s, 'identity', side_effect=identify), patch.object(s, 'os', fake_os), patch.object(s, 'save', side_effect=portable_fail), patch.object(s.subprocess, 'Popen', return_value=Child()):
            with self.assertRaises(OSError): s.supervise(root)
        self.assertEqual(events, ['wait-original'])
        self.assertEqual(c.load_json(root / 'quiesce-worker-terminal-private.json')['returncode'], 1)
        self.assertFalse((root / 'quiesce-supervisor-terminal-private.json').exists())

    def test_restart_intent_never_execs_twice_after_error(self):
        directory, request = self.bind(); root = self.base / 'exec-root'; root.mkdir(); calls = []
        fake_os = types.SimpleNamespace(execvp=lambda command, argv: (calls.append(argv), (_ for _ in ()).throw(OSError('exec failed')))[1])
        with patch.object(r, 'preflight', return_value=(None, None, None)), patch.object(r, 'save', side_effect=c.save), patch.object(r, 'os', fake_os):
            with self.assertRaises(OSError): r.restart(request, root)
            with self.assertRaises(FileExistsError): r.restart(request, root)
        self.assertEqual(len(calls), 1)
        self.assertEqual(c.load_json(root / 'restart-intent-private.json')['request_count'], 1)

    def test_actual_export_accepted_by_frozen_root_operator_context_gate(self):
        directory, request = self.bind(); job(directory, 'quiesce', request, rc=255)
        target, value, facts = quiesce_facts(directory, request); c.qualify_quiesce(directory, value, target)
        guard = c.load_json(directory / 'guard-private.json'); remote = '/root/charging-management-20261023/' + self.tx
        c.save(directory / 'restart-claim-private.json', dict(schema='samurai-eud-restart-host-claim-v1', transaction_id=self.tx,
            token=request['token'], boot_id=request['expected_boot'], guard_sha256=request['guard_sha256'], request_count=1,
            worker_sha256=c.WORKER_HASHES['eud-restart.py'], argv=['python3', '-B', remote + '/eud-restart.py', '--guard', remote + '/guard-private.json', '--commit-restart2-bootloader']))
        job(directory, 'restart', request, rc=255)
        # A previously pending restart ends with SSH255 after USB disappears.
        # Readonly reconciliation must export before its next network query.
        starts = []
        def readonly_unreachable(*args):
            starts.append(args[1]); self.assertTrue((directory / 'host-context-private.json').exists())
            return dict(pending=True, no_replay=True)
        c.run('status', self.tx, True, True, private=directory.parent, start=readonly_unreachable)
        self.assertEqual(starts, ['status'])
        context = c.load_json(directory / 'host-context-private.json')
        operator = load(REF / 'charging-oem-audit-20261023/usb-irq-protection-fastboot-candidate/fastboot-operator.py', 'frozen_root_operator_context_only')
        fake_proof = types.SimpleNamespace(review_stage=lambda *a, **kw: self.review, guard_stage_fields=lambda _: self.projection)
        with patch.object(operator, 'stage_module', return_value=fake_proof):
            accepted = operator.validate_context(directory / 'host-context-private.json')
        self.assertEqual(accepted, context)
        self.assertFalse(c.load_json(directory / 'restart-dispatch-private.json')['syscall_success_proven'])
        self.assertEqual(set(context['files']), {'guard', 'quiesce_state', 'quiesce_summary', 'quiesce_boot_id', 'quiesce_process', 'restart_dispatch', 'restart_claim'})


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Host))
    defaults = []
    for name in ('controller.py', 'remote.py', 'supervisor.py'):
        child = subprocess.Popen([sys.executable, '-B', str(HERE / name)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = child.communicate(); rc = child.wait()
        assert rc == 0 and not stderr and json.loads(stdout)['source_only'] is True
        defaults.append(dict(source=name, pid=child.pid, terminal=True, returncode=rc, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)))
    receipt = dict(passed=result.wasSuccessful(), methods=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        default_checks=defaults, old_device_13_31_suites_rerun=False, fake_boundaries=True,
        synthetic_temp_fixture_only=True, actual_runtime_material_generated=False, device_or_transport_accessed=False,
        tested_files={name: sha((HERE / name).read_bytes()) for name in ['controller.py', 'remote.py', 'supervisor.py', 'source-pins.json', 'pin-sources.py', 'test-host.py']})
    (HERE / 'test-result.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
    if not result.wasSuccessful(): raise SystemExit(1)
    print(json.dumps(dict(passed=True, methods=result.testsRun, defaults=len(defaults))))
