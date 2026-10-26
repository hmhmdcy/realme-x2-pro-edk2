"""Only R2 close/wait and truncated-parent-receipt boundaries; no old suite."""
from pathlib import Path
import ast
import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
R1 = HERE.parent / 'usb-irq-protection-stage-host-candidate'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    host = load('stage_host_r2', HERE / 'host.py')
    remote = load('stage_remote_r2', HERE / 'remote.py')
    cases = []
    with tempfile.TemporaryDirectory(prefix='samurai-stage-r2-') as directory:
        tmp = Path(directory)
        sources = tmp / 'source'; sources.mkdir()
        (sources / 'remote.py').write_bytes(b'# fake transport boundary\n')
        (sources / 'supervisor.py').write_bytes(b'# fake supervisor boundary\n')
        for mode in ('receipt_fail', 'communicate_fail'):
            tx = 'usb-irq-protection-stage-' + mode.replace('_', '-') + '-001'
            out = tmp / tx; out.mkdir()
            (out / 'stage-worker.py').write_bytes(b'# fake worker boundary\n')
            request = dict(transaction_id=tx, identity={'boot_id': '12345678-1234-4123-8123-123456789abc'})
            raw = json.dumps(request).encode()
            endpoint = dict(peer=host.PEER, host_key_alias=host.ALIAS, observed_new_boot=request['identity']['boot_id'])
            binding = dict(endpoint=endpoint)
            pins = dict(key_transport={'path': 'fake'}, supervisor={'sha256': sha((sources / 'supervisor.py').read_bytes())})
            children = []

            class Pipe:
                closed = False
                def close(self):
                    self.closed = True

            class Child:
                pid = 909
                returncode = None
                def __init__(self, argv, **kwargs):
                    self.stdin = Pipe()
                    self.communicated = False
                    self.waited = 0
                    children.append(self)
                def communicate(self, input):
                    self.communicated = True
                    assert mode == 'communicate_fail' and input.startswith(b'STAGE_TRANSPORT=')
                    raise BrokenPipeError('injected partial communicate')
                def wait(self):
                    assert self.stdin.closed, 'owned PIPE must reach EOF before wait'
                    self.waited += 1
                    self.returncode = 0
                    return 0

            original_save = host.save
            def save(path, value):
                if mode == 'receipt_fail' and path.name == 'transport-child-private.json':
                    raise OSError('injected receipt fsync')
                return original_save(path, value)

            with patch.object(host, 'HERE', sources), patch.object(host, 'bound', return_value=(out, binding, request, raw, pins)), patch.object(host, 'load_module', return_value=SimpleNamespace(SSH='fake-ssh', OPTIONS=[])), patch.object(host, 'save', side_effect=save), patch.object(host.subprocess, 'Popen', Child):
                try:
                    host.transfer('launch', tx, True)
                except OSError as error:
                    assert 'injected' in str(error)
                else:
                    raise AssertionError('original error must remain visible')
                assert len(children) == 1 and children[0].waited == 1
                assert children[0].communicated == (mode == 'communicate_fail')
                terminal = json.loads((out / 'launch-transport-private/transport-terminal-private.json').read_bytes())
                assert terminal['terminal'] is True and terminal['returncode'] == 0 and terminal['primary_error']
                assert not terminal['cleanup_errors']
                try:
                    host.transfer('launch', tx, True)
                except ValueError:
                    pass
                else:
                    raise AssertionError('unknown outcome cannot authorize redispatch')
                assert len(children) == 1
            cases.append(dict(name=mode, passed=True, same_child_waits=1,
                              payload_sent=mode == 'communicate_fail', owned_stdin_closed=True, no_relaunch=True))

        # Redirect the filesystem boundary; execute the real remote fetch.
        disk = tmp / 'remote'; disk.mkdir()
        class Mapped:
            def __init__(self, *parts): self.logical = Path(*parts)
            @property
            def physical(self): return disk / str(self.logical).replace('\\', '/').lstrip('/')
            @property
            def name(self): return self.logical.name
            def __str__(self): return str(self.logical).replace('\\', '/')
            def __truediv__(self, name): return Mapped(self.logical / name)
            def __lt__(self, other): return str(self) < str(other)
            def read_bytes(self): return self.physical.read_bytes()
            def read_text(self): return self.physical.read_text()
            def exists(self): return self.physical.exists()
            def is_dir(self): return self.physical.is_dir()
            def is_symlink(self): return self.physical.is_symlink()
            def lstat(self): return self.physical.lstat()
            def iterdir(self): return (self / p.name for p in self.physical.iterdir())
        def write(path, raw):
            target = Mapped(path).physical
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        tx = 'usb-irq-protection-stage-truncated-001'
        boot = '12345678-1234-4123-8123-123456789abc'
        guard_raw = (boot + '\n').encode()
        request = dict(schema='samurai-usb-irq-protection-stage-request-v1', transaction_id=tx,
                       identity={'boot_id': boot}, worker_sha256=sha(b'worker'),
                       adoption=dict(transaction_id=host.ADOPTION_TX, guard_path=host.GUARD, guard_sha256=sha(guard_raw)))
        raw = json.dumps(request).encode()
        root = '/root/charging-management-20261023/' + tx
        argv = ['python3', '-B', root + '/stage-worker.py', '--execute-stage']
        sup_argv = ['python3', '-B', root + '/stage-supervisor.py', '--execute-supervisor']
        write('/proc/sys/kernel/random/boot_id', guard_raw)
        write(host.GUARD, guard_raw)
        write(root + '/request-private.json', raw)
        write(root + '/stage-worker.py', b'worker')
        write(root + '/stage-supervisor.py', b'supervisor')
        write(root + '/launch-claim-private.json', json.dumps(dict(transaction_id=tx, request_sha256=sha(raw),
             argv=argv, supervisor_argv=sup_argv, supervisor_sha256=sha(b'supervisor'))).encode())
        truncated = b'{"pid":12,'
        write(root + '/launch-receipt-private.json', truncated)
        write(root + '/device-stage/result.json', b'{"terminal":true,"phase":"failed"}\n')
        envelope = dict(action='fetch', request=request, request_sha256=sha(raw),
                        request_base64=base64.b64encode(raw).decode(), supervisor_sha256=sha(b'supervisor'))
        with patch.object(remote, 'Path', Mapped), patch.object(remote.os, 'geteuid', return_value=0, create=True), patch.object(remote.os, 'umask', return_value=0):
            result = remote.execute(envelope)
        assert result['supervisor_receipt_observation']['read_error'] == 'JSONDecodeError'
        assert result['process']['state'] == result['supervisor_process']['state'] == 'unknown'
        assert not result['worker_terminal_verified'] and not result['runtime_validation_accepted']
        assert base64.b64decode(result['files']['launch-receipt-private.json']['base64']) == truncated
        cases.append(dict(name='truncated parent receipt remains unknown and raw remains fetchable', passed=True))

    # Independently confirm the reused functions / supervisor are unchanged.
    reused = {}
    for file, names in {'host.py': ['source_check', 'validate_adoption', 'make_request', 'bind', 'bound'],
                        'remote.py': ['process', 'observed_json']}.items():
        old, new = (R1 / file).read_text(), (HERE / file).read_text()
        def functions(text):
            return {node.name: ast.get_source_segment(text, node) for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}
        a, b = functions(old), functions(new)
        for name in names:
            assert a[name] == b[name]
            reused[file + ':' + name] = sha(a[name].encode())
    assert (R1 / 'supervisor.py').read_bytes() == (HERE / 'supervisor.py').read_bytes()
    child = subprocess.Popen([sys.executable, '-B', str(HERE / 'host.py')], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(); rc = child.wait()
    assert rc == 0 and not stderr and json.loads(stdout)['runtime_request_generated'] is False
    result = dict(passed=True, new_cases=cases, new_case_count=3,
                  reused_R1_delivery_sha256=sha((R1 / 'delivery.json').read_bytes()),
                  reused_R1_tests_sha256=sha((R1 / 'test-result.json').read_bytes()),
                  reused_R1_interface_sha256=sha((R1 / 'interface-check-result.json').read_bytes()),
                  unchanged_functions=reused, supervisor_byte_equal_R1=True,
                  default_source_only=dict(pid=child.pid, terminal=True, returncode=rc, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)),
                  files={name: sha((HERE / name).read_bytes()) for name in ('host.py', 'remote.py', 'supervisor.py', 'source-pins.json', 'test-r2.py')},
                  old_20_and_interface_cases_rerun=False, device_or_transport_accessed=False,
                  actual_runtime_request_generated=False, OS_Popen_and_saved_identity_boundaries_fake=True)
    (HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, new_case_count=3, default_source_only_cli_returncode=rc)))


if __name__ == '__main__': main()
