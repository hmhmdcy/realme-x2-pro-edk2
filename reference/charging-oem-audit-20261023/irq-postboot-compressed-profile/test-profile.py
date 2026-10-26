"""Only the new fixed compression/composition/receipt-alias boundaries."""
from pathlib import Path
import contextlib
import argparse
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('irq_compression_profile_under_test', HERE / 'profile.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
sha = lambda raw: hashlib.sha256(raw).hexdigest()


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = p.check_sources()

    def test_only_C_differs_for_both_original_commands(self):
        old = p.load(p.HOST / 'host.py', 'test_original_host')
        new = p.host_module()
        for collection in (False, True):
            before = old.transport_argv(old.PEER, collection=collection)
            after = new.transport_argv(new.PEER, collection=collection)
            self.assertEqual(after, [before[0], '-C', *before[1:]])
            self.assertEqual(after.count('-C'), 1)
        with self.assertRaises(ValueError):
            new.transport_argv('::1')

    def send_fixture(self, out, *, collection=False, rc=0):
        host, adopt = p.host_module(), p.adoption_module()
        actual_popen = subprocess.Popen
        children, requested = [], []

        def local_child(argv, **kwargs):
            requested.append(argv)
            # Fake the SSH boundary only. The unchanged transfer really owns
            # this harmless Linux child, captures /proc and waits that child.
            child = actual_popen([sys.executable, '-B', '-c',
                'import sys;sys.stdin.buffer.read();print("{\\"synthetic_fixture\\":true}");'
                'sys.stderr.write("fixture stderr\\n");sys.exit(' + str(rc) + ')'], **kwargs)
            children.append(child)
            return child

        code = b'print("synthetic fixture input, never device evidence")\n'
        with patch.object(p, 'host_module', return_value=host), \
             patch.object(p, 'adoption_module', return_value=adopt), \
             patch.object(adopt.subprocess, 'Popen', side_effect=local_child):
            if rc:
                with self.assertRaises(ValueError):
                    p.send_readonly(out, code, collection=collection)
            else:
                self.assertEqual(p.send_readonly(out, code, collection=collection),
                                 {'synthetic_fixture': True})
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].poll(), rc)
        self.assertEqual(requested, [host.transport_argv(host.PEER, collection=collection)])
        return host, code

    def test_actual_owned_sender_both_commands_and_exact_aliases(self):
        for collection in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                out = Path(directory)
                host, code = self.send_fixture(out, collection=collection)
                stdout, stderr, terminal = host.saved_transport(out, code, host.PEER,
                                                               collection=collection)
                self.assertTrue(json.loads(stdout)['synthetic_fixture'])
                self.assertEqual(stderr, b'fixture stderr\n')
                self.assertEqual(terminal['returncode'], 0)
                for source, alias in [('adopt-stdout-private.json', 'stdout-private.json'),
                        ('adopt-stderr-private.txt', 'stderr-private.txt'),
                        ('adopt-child-private.json', 'child-private.json'),
                        ('adopt-terminal-private.json', 'terminal-private.json')]:
                    self.assertEqual((out / source).read_bytes(), (out / alias).read_bytes())
                # The old profile cannot quietly authenticate compressed argv.
                original = p.load(p.HOST / 'host.py', 'test_old_profile_rejects_C')
                with self.assertRaises(ValueError):
                    original.saved_transport(out, code, host.PEER, collection=collection)

    def test_failed_original_child_still_retains_raw_and_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            host, code = self.send_fixture(out, collection=True, rc=9)
            stdout, stderr, terminal = host.saved_transport(out, code, host.PEER, collection=True)
            self.assertTrue(stdout and stderr)
            self.assertTrue(terminal['terminal'])
            self.assertEqual(terminal['returncode'], 9)
            self.assertEqual(terminal['stdout_sha256'], sha(stdout))

    def test_missing_C_or_input_binding_is_refused_by_original_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            host, code = self.send_fixture(out)
            child_path, terminal_path = out / 'child-private.json', out / 'terminal-private.json'
            child = json.loads(child_path.read_bytes())
            terminal = json.loads(terminal_path.read_bytes())
            for row in (child, terminal):
                row['argv'].remove('-C')
            child_path.write_text(json.dumps(child)); terminal_path.write_text(json.dumps(terminal))
            with self.assertRaises(ValueError):
                host.saved_transport(out, code, host.PEER)
            for row in (child, terminal):
                row['argv'].insert(1, '-C')
            child['stdin_sha256'] = '0' * 64
            child_path.write_text(json.dumps(child)); terminal_path.write_text(json.dumps(terminal))
            with self.assertRaises(ValueError):
                host.saved_transport(out, code, host.PEER)

    def test_adoption_bodies_and_device_payload_remain_original(self):
        old = p.load(p.ADOPT / 'adopt.py', 'test_frozen_adoption')
        new = p.adoption_module()
        for name in ['review', 'payload', 'transfer', 'process_identity', 'publish', 'adopt']:
            self.assertEqual(getattr(old, name).__code__.co_code,
                             getattr(new, name).__code__.co_code)
            self.assertEqual(getattr(old, name).__code__.co_consts,
                             getattr(new, name).__code__.co_consts)
        raw = old.sources()[1]
        self.assertEqual(old.payload({'synthetic_fixture': True}, raw),
                         new.payload({'synthetic_fixture': True}, raw))
        self.assertIn('-C', new.host_module().transport_argv('fe80::62:bcff:fe28:a101%29'))

    def test_missing_real_material_precedes_output_and_default_is_local(self):
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory) / 'host-context-private.json'
            output = Path(directory) / 'unused-output'
            with self.assertRaises(ValueError):
                p.probe(context, output)
            self.assertFalse(output.exists())
            with self.assertRaises(ValueError):
                p.output_path(context, Path(directory).parent / 'outside-fixture-output')
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            p.main([])
        reply = json.loads(stream.getvalue())
        self.assertFalse(reply['device_accessed'])
        self.assertFalse(reply['runtime_request_generated'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only')
    parser.add_argument('--output', default='test-result.json')
    args = parser.parse_args()
    if args.only and args.only not in unittest.defaultTestLoader.getTestCaseNames(ProfileTests):
        raise ValueError('unknown new profile test method')
    log = io.StringIO()
    suite = (unittest.TestSuite([ProfileTests(args.only)]) if args.only else
             unittest.defaultTestLoader.loadTestsFromTestCase(ProfileTests))
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(
        suite)
    receipt = {'schema': 'samurai-irq-fixed-compression-tests-v1',
               'passed': result.wasSuccessful(), 'test_methods': result.testsRun,
               'profile_sha256': sha((HERE / 'profile.py').read_bytes()),
               'test_sha256': sha(Path(__file__).read_bytes()),
               'original_source_pins': p.check_sources(),
               'actual_local_Popen_used_at_fake_SSH_boundary': True,
               'device_accessed': False, 'SDK_or_build_mount_used': False,
               'old_matrix_rerun': False, 'log': log.getvalue()}
    receipt['selected_method'] = args.only
    if Path(args.output).name != args.output:
        raise ValueError('test receipt filename must stay inside this leaf')
    with (HERE / args.output).open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(log.getvalue(), end='')
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
