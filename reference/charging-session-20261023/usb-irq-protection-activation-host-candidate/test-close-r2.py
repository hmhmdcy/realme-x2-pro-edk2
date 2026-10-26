"""Three new actual ssh_worker cleanup boundaries; no R1 suite or transport."""
from pathlib import Path
import hashlib, importlib.util, json, subprocess, sys, tempfile, unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_host_r2_close', HERE / 'controller.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
sha = lambda raw: hashlib.sha256(raw).hexdigest()


class Close(unittest.TestCase):
    def run_case(self, *, receipt_failure=False, close_failure=False, returncode=255):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / 'original-job'; target.mkdir()
            program = b'# synthetic inert stdin fixture, not an activation request\n'
            c.create(target / 'program.py', program)
            c.save(target / 'job-private.json', dict(program=str(target / 'program.py'), program_sha256=sha(program),
                controller_sha256=sha((HERE / 'controller.py').read_bytes()), ssh_argv=['requested-ssh-fixture', 'python3 -']))
            events = []
            class Pipe:
                closed = False
                def close(self):
                    events.append('close-owned-stdin')
                    if close_failure: raise OSError('injected stdin close failure')
                    self.closed = True
            class Child:
                pid = 9001; stdin = Pipe()
                def __init__(self): self.returncode = returncode
                def communicate(self, input):
                    self_input = input
                    if self_input != program: raise AssertionError('wrong original bytes')
                    events.append('send-before-first-byte-error' if receipt_failure else 'send-partial-error')
                    raise OSError('before send' if receipt_failure else 'injected partial send')
                def wait(self):
                    events.append('wait-same-child')
                    if 'close-owned-stdin' not in events: raise AssertionError('wait before EOF attempt')
                    return self.returncode
            child = Child()
            identity = dict(pid=child.pid, startticks=123, argv=['observed-Windows-PE-argv'])
            observed = patch.object(c, 'process_identity', side_effect=OSError('receipt before send')) if receipt_failure else patch.object(c, 'process_identity', return_value=identity)
            with patch.object(c, 'PRIVATE', root), patch.object(c.subprocess, 'Popen', return_value=child) as popen, observed:
                if close_failure:
                    with self.assertRaises(RuntimeError): c.ssh_worker(target / 'job-private.json')
                else: c.ssh_worker(target / 'job-private.json')
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(events[-2:], ['close-owned-stdin', 'wait-same-child'])
            terminal = c.load_json(target / 'ssh-terminal-private.json')
            final = c.load_json(target / 'ssh-finalization-private.json')
            self.assertTrue(terminal['terminal']); self.assertTrue(final['wait_returned'])
            self.assertEqual(terminal['stdin_sha256'], sha(program)); self.assertIsNotNone(terminal['io_error'])
            if receipt_failure:
                self.assertIsNotNone(terminal['receipt_error'])
                with self.assertRaises(FileNotFoundError): c.terminal_job(target)
            elif close_failure:
                self.assertEqual(terminal['returncode'], 0)  # Real child rc0 cannot mask cleanup failure.
                self.assertIn('stdin_close', terminal['cleanup_errors'])
                self.assertFalse(final['cleanup_passed'])
                with self.assertRaises(ValueError): c.terminal_job(target)
            else:
                qualified, raw = c.terminal_job(target)
                self.assertEqual(qualified['returncode'], 255)
                self.assertIsNotNone(qualified['io_error'])
                self.assertEqual(final['cleanup_errors'], {})
                self.assertTrue(child.stdin.closed)
            return dict(events=events, receipt_error=terminal['receipt_error'], io_error=terminal['io_error'],
                        cleanup_errors=final['cleanup_errors'], cleanup_passed=final['cleanup_passed'], returncode=terminal['returncode'])

    def test_receipt_before_send_failure_closes_and_waits(self): self.run_case(receipt_failure=True)
    def test_partial_communicate_closes_before_same_wait(self): self.run_case()
    def test_close_failure_still_waits_and_cannot_qualify_rc0(self): self.run_case(close_failure=True, returncode=0)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Close)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    child = subprocess.Popen([sys.executable, '-B', str(HERE / 'controller.py')], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(); rc = child.wait()
    assert rc == 0 and not stderr and json.loads(stdout)['source_only'] is True
    receipt = dict(passed=result.wasSuccessful(), methods=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        only_new_cleanup_boundaries=True, old_R1_12_device_13_31_suites_rerun=False,
        default_controller=dict(pid=child.pid, terminal=True, returncode=rc, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)),
        actual_runtime_material_generated=False, actual_transport_or_device_accessed=False,
        tested_files={name: sha((HERE / name).read_bytes()) for name in ('controller.py', 'remote.py', 'supervisor.py', 'test-close-r2.py', 'source-pins.json')})
    (HERE / 'close-r2-result.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
    if not result.wasSuccessful(): raise SystemExit(1)
    print(json.dumps(dict(passed=True, methods=result.testsRun, controller_default_returncode=rc)))
