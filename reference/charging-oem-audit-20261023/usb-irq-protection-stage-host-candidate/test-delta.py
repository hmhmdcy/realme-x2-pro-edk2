"""Only new host binding/once/fetch boundaries. No network or existing suite."""
from pathlib import Path
import base64
import copy
import hashlib
import importlib.util
import json
import os
import stat
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    host = load('stage_host_test', 'host.py')
    remote = load('stage_remote_test', 'remote.py')
    supervisor = load('stage_supervisor_test', 'supervisor.py')
    cases = []

    def done(name):
        cases.append(dict(name=name, passed=True))

    def rejected(name, function):
        try:
            function()
        except (ValueError, FileNotFoundError):
            done(name)
        else:
            raise AssertionError(name)

    # These are explicitly synthetic local values for the new thin comparison
    # function, not a generated runtime request or a claimed actual new boot.
    boot = '12345678-1234-4123-8123-123456789abc'
    d = dict(transaction_id=host.ADOPTION_TX, guard=host.GUARD,
             candidate_boot_sha256=host.BOOT, candidate_logdump_sha256=host.LOGDUMP,
             manifest=host.R8, version=host.VERSION, boot=boot,
             old_boot='22345678-1234-4123-8123-123456789abc', postboot_raw_sha256='1' * 64,
             serial_sha256='2' * 64, compatible_sha256='3' * 64, rootfs='4' * 64)
    pointer = dict(guard_path=host.GUARD, original_key_verified=True, baseline481_verified=True,
                   charging_manifest_sha256=host.R8, candidate_boot_sha256=host.BOOT,
                   candidate_logdump_sha256=host.LOGDUMP, Image502_verified=True,
                   postboot_raw_sha256=d['postboot_raw_sha256'])
    result = dict(passed=True, guard_created=True, old_pointer_backup_preserved=True,
                  old_guards_preserved=True, pointer=pointer)
    endpoint = dict(kind='usb-ipv6', peer=host.PEER, interface_index=29, host_key_alias=host.ALIAS,
                    original_key_verified=True, observed_new_boot=boot, guard_path=host.GUARD,
                    postboot_Image502_passed=True)
    reply = dict(guard_created=True, old_guards_preserved=True, transaction_id=host.ADOPTION_TX,
                 boot_id=boot, guard=host.GUARD, boot_and_logdump_verified=True,
                 postboot_raw_sha256=d['postboot_raw_sha256'], fresh_validation_passed=True,
                 charging_controls_written=False)
    terminal = dict(terminal=True, returncode=0, pid=23)
    arguments = [d, pointer, result, endpoint, reply, terminal, d]
    host.validate_adoption(*arguments)
    done('actual thin comparison accepts internally coherent synthetic 502 proof only')
    mutations = [('old501 version', 0, 'version', '#501 old'),
                 ('different boot partition', 0, 'candidate_boot_sha256', '0' * 64),
                 ('different logdump partition', 0, 'candidate_logdump_sha256', '0' * 64),
                 ('old current pointer', 1, 'Image502_verified', False),
                 ('wrong strict endpoint', 3, 'peer', '169.254.42.1'),
                 ('unknown adoption child', 5, 'terminal', False),
                 ('unverified guard creation', 4, 'guard_created', False)]
    for label, index, key, value in mutations:
        args = copy.deepcopy(arguments)
        args[index][key] = value
        rejected(label, lambda args=args: host.validate_adoption(*args))

    with tempfile.TemporaryDirectory(prefix='samurai-stage-host-test-') as directory:
        temporary = Path(directory)
        private = temporary / 'private'
        private.mkdir()
        fake_source = temporary / 'source'
        fake_source.mkdir()
        (fake_source / 'source-pins.json').write_text('{}')
        tx = 'usb-irq-protection-stage-test-0001'
        out = private / tx
        failure = SimpleNamespace(review=lambda *args: (_ for _ in ()).throw(ValueError('no real postboot')))
        with patch.object(host, 'PRIVATE', private), patch.object(host, 'source_check', return_value=({'adoption': {'path': 'unused'}}, {})), patch.object(host, 'load_module', return_value=failure):
            rejected('missing real postboot refuses before runtime directory or request', lambda: host.bind(tx, 'missing', 'missing', 'missing'))
        assert not out.exists()

        out.mkdir()
        worker = b'# synthetic worker bytes; never executed\n'
        request = dict(transaction_id=tx, worker_sha256=sha(worker), identity=dict(boot_id=boot))
        raw = (json.dumps(request) + '\n').encode()
        (out / 'request-private.json').write_bytes(raw)
        (out / 'stage-worker.py').write_bytes(worker)
        evidence = temporary / 'pointer.json'
        evidence.write_bytes(b'original')
        binding = dict(transaction_id=tx, request_sha256=sha(raw),
                       source_pins_sha256=sha((fake_source / 'source-pins.json').read_bytes()),
                       generated_from_actual_Image502=True, endpoint=endpoint,
                       evidence={'pointer': {'path': str(evidence), 'sha256': sha(b'original')}})
        (out / 'binding-private.json').write_text(json.dumps(binding))
        pins = {'worker': {'sha256': sha(worker)}, 'key_transport': {'path': 'fake'}, 'supervisor': {'sha256': sha(b'fake supervisor')}}
        with patch.object(host, 'PRIVATE', private), patch.object(host, 'HERE', fake_source), patch.object(host, 'source_check', return_value=(pins, {})):
            host.bound(tx, launching=True)
            done('bound request and actual-evidence digests gate launch')
            evidence.write_bytes(b'changed')
            rejected('pointer drift blocks launch', lambda: host.bound(tx, launching=True))
            host.bound(tx, launching=False)
            done('same retained request remains fetchable after pointer drift')
            evidence.write_bytes(b'original')
            (fake_source / 'remote.py').write_bytes(b'# fake transport; never sent\n')
            (fake_source / 'supervisor.py').write_bytes(b'fake supervisor')
            calls = []

            class Child:
                pid = 42

                def __init__(self, argv, **kwargs):
                    self.argv = argv
                    self.stdout = kwargs['stdout']
                    self.returncode = None
                    self.waited = 0
                    calls.append(self)

                def communicate(self, input):
                    assert b'STAGE_TRANSPORT=' in input
                    self.stdout.write(json.dumps(dict(transaction_id=tx, request_sha256=sha(raw),
                        process={'state': 'unknown'}, worker_result=None, files={})).encode())
                    self.returncode = 255 if len(calls) == 1 else 0

                def wait(self):
                    self.waited += 1
                    return self.returncode

            key = SimpleNamespace(SSH='original-ssh', OPTIONS=['-o', 'StrictHostKeyChecking=yes'])
            with patch.object(host, 'load_module', return_value=key), patch.object(host.subprocess, 'Popen', Child):
                rejected('unknown launch retains original child and permanent once intent', lambda: host.transfer('launch', tx, True))
                assert len(calls) == 1 and calls[0].waited == 1
                assert 'HostKeyAlias=169.254.42.1' in calls[0].argv and 'root@' + host.PEER in calls[0].argv
                rejected('same transaction cannot launch twice after unknown', lambda: host.transfer('launch', tx, True))
                assert len(calls) == 1
                response = host.transfer('fetch', tx)
                assert len(calls) == 2 and calls[1].waited == 1 and response['runtime_validation_accepted'] is False
                done('fetch observes same bound request without relaunch after unknown')

        # Exercise the actual detached supervisor, with only Popen, /proc ticks
        # and Linux directory fsync substituted. Worker stdin is an ordinary fd.
        for fail_receipt in (False, True):
            owner = temporary / ('owner-failed' if fail_receipt else 'owner') / tx
            owner.mkdir(parents=True)
            req = dict(transaction_id=tx, worker_sha256=sha(worker), identity={'boot_id': boot})
            req_raw = json.dumps(req).encode()
            sup_raw = b'# synthetic on-disk supervisor for source identity only\n'
            (owner / 'request-private.json').write_bytes(req_raw)
            (owner / 'stage-worker.py').write_bytes(worker)
            (owner / 'stage-supervisor.py').write_bytes(sup_raw)
            (owner / 'launch-claim-private.json').write_text(json.dumps(dict(transaction_id=tx,
                request_sha256=sha(req_raw), supervisor_sha256=sha(sup_raw))))
            owned = []

            class OwnedChild:
                pid = 712

                def __init__(self, argv, **kwargs):
                    assert stat.S_ISREG(os.fstat(kwargs['stdin'].fileno()).st_mode)
                    assert kwargs['stdin'].read() == req_raw
                    assert kwargs['stdout'].name == str(owner / 'worker-private.log')
                    self.waited = 0
                    owned.append(self)

                def wait(self):
                    self.waited += 1
                    return 0

            def fake_save(path, value):
                if fail_receipt and path.name == 'worker-launch-receipt-private.json':
                    raise OSError('injected receipt fsync failure')
                with path.open('x') as stream:
                    json.dump(value, stream)

            with patch.object(supervisor, 'save', side_effect=fake_save), patch.object(supervisor, 'ticks', return_value=77), patch.object(supervisor.os, 'umask', return_value=0), patch.object(supervisor.subprocess, 'Popen', OwnedChild):
                if fail_receipt:
                    try:
                        supervisor.supervise(owner)
                    except OSError:
                        pass
                    else:
                        raise AssertionError('receipt error must remain visible')
                else:
                    supervisor.supervise(owner)
            assert len(owned) == 1 and owned[0].waited == 1
            actual_terminal = json.loads((owner / 'worker-terminal-private.json').read_bytes())
            assert actual_terminal['pid'] == 712 and actual_terminal['terminal'] and actual_terminal['returncode'] == 0
            done('same Popen finally waits after receipt failure' if fail_receipt else 'regular stdin fd and real Popen wait terminal persisted')

        # Actual remote fetch with only a filesystem boundary redirected. It
        # does not invoke a subprocess, worker, manager, module, lease or API.
        root = temporary / 'remote-root'
        root.mkdir()

        class Mapped:
            def __init__(self, *parts):
                self.logical = Path(*parts)

            @property
            def physical(self):
                return root / str(self.logical).replace('\\', '/').lstrip('/')

            @property
            def name(self):
                return self.logical.name

            def __str__(self):
                return str(self.logical).replace('\\', '/')

            def __truediv__(self, value):
                return Mapped(self.logical / value)

            def __lt__(self, other):
                return str(self) < str(other)

            def read_bytes(self):
                return self.physical.read_bytes()

            def read_text(self):
                return self.physical.read_text()

            def exists(self):
                return self.physical.exists()

            def is_dir(self):
                return self.physical.is_dir()

            def is_symlink(self):
                return self.physical.is_symlink()

            def lstat(self):
                return self.physical.lstat()

            def iterdir(self):
                return (self / entry.name for entry in self.physical.iterdir())

        def write(path, data):
            p = Mapped(path).physical
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

        guard_raw = (boot + '\n').encode()
        request = dict(schema='samurai-usb-irq-protection-stage-request-v1', transaction_id=tx,
                       worker_sha256=sha(worker), identity={'boot_id': boot},
                       adoption={'transaction_id': host.ADOPTION_TX, 'guard_path': host.GUARD, 'guard_sha256': sha(guard_raw)})
        request_raw = json.dumps(request).encode()
        remote_root = '/root/charging-management-20261023/' + tx
        argv = ['python3', '-B', remote_root + '/stage-worker.py', '--execute-stage']
        supervisor_argv = ['python3', '-B', remote_root + '/stage-supervisor.py', '--execute-supervisor']
        sup_raw = b'fake supervisor'
        write('/proc/sys/kernel/random/boot_id', guard_raw)
        write(host.GUARD, guard_raw)
        write(remote_root + '/request-private.json', request_raw)
        write(remote_root + '/stage-worker.py', worker)
        write(remote_root + '/stage-supervisor.py', sup_raw)
        write(remote_root + '/launch-claim-private.json', json.dumps(dict(transaction_id=tx,
            request_sha256=sha(request_raw), argv=argv, supervisor_argv=supervisor_argv, supervisor_sha256=sha(sup_raw))).encode())
        bad = b'{"terminal":true,\n'
        write(remote_root + '/device-stage/result.json', bad)
        envelope = dict(action='fetch', request=request, request_sha256=sha(request_raw),
                        request_base64=base64.b64encode(request_raw).decode(), supervisor_sha256=sha(sup_raw))
        with patch.object(remote, 'Path', Mapped), patch.object(remote.os, 'geteuid', return_value=0, create=True), patch.object(remote.os, 'umask', return_value=0):
            response = remote.execute(envelope)
            assert response['process']['state'] == 'unknown' and response['worker_result']['read_error'] == 'JSONDecodeError'
            assert base64.b64decode(response['files']['result.json']['base64']) == bad
            assert not response['runtime_validation_accepted']
            done('malformed partial worker result is retained raw and never accepted')
            write('/proc/sys/kernel/random/boot_id', (d['old_boot'] + '\n').encode())
            Mapped(host.GUARD).physical.unlink()
            with patch.object(remote, 'process', side_effect=AssertionError('must not inspect a current PID from another boot')):
                after_boot = remote.execute(envelope)
            assert after_boot['process']['state'] == after_boot['supervisor_process']['state'] == 'source_boot_ended'
            assert base64.b64decode(after_boot['files']['result.json']['base64']) == bad
            done('new boot and missing old guard still fetch original raw without current PID attribution')

    # Default performs only local source/payload checks after final worker pins
    # exist. No bind, runtime identity, subprocess or transport is called here.
    pins, raw = host.source_check()
    done('default source-only checks use final real worker and cohort bytes')
    result = dict(passed=True, cases=cases, count=len(cases),
                  source_files={n: sha((HERE / n).read_bytes()) for n in ('host.py', 'remote.py', 'supervisor.py', 'source-pins.json', 'test-delta.py')},
                  actual_new_functions_used=True, OS_transport_and_saved_identity_boundaries_fake=True,
                  actual_runtime_request_or_identity_generated=False, network_or_device_accessed=False,
                  old_suites_rerun=False)
    (HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, count=len(cases))))


if __name__ == '__main__':
    main()
