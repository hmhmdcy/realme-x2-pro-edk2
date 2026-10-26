"""Only new IRQ profile/receipt and bind boundaries; all fixtures are temporary."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast, copy, hashlib, importlib.util, json, tempfile
HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / 'charging-oem-audit-20261023/icon-capture-image502-candidate'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def functions(path):
    text = path.read_text()
    return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}


def main():
    a = load('icon_irq_actual_review', HERE / 'adoption-review.py')
    m = load('icon_irq_actual_launcher', HERE / 'launcher.py')
    b = load('icon_irq_actual_bind', HERE / 'bind-identity.py')
    cases = []
    def passed(name): cases.append(name)
    def rejects(name, call):
        try: call()
        except (ValueError, OSError, KeyError, AssertionError): passed(name)
        else: raise AssertionError(name)
    for name in ('worker.py', 'audit.py', 'baseline-test-result.json'):
        assert (HERE / name).read_bytes() == (OLD / name).read_bytes()
    old, new = functions(OLD / 'launcher.py'), functions(HERE / 'launcher.py')
    same = {name: a.sha(text.encode()) for name, text in old.items() if new.get(name) == text}
    assert all(name in same for name in ('ready_check', 'retain_fetch', 'cleanup_check', 'save_new', 'transport'))
    baseline = load('icon_irq_old_readonly', OLD / 'launcher.py')
    assert m.REMOTE.replace('/charging-session-20261023/icon-capture-irq-cohort',
                            '/charging-ui-audit-20261023/icon-capture-image502') == baseline.REMOTE
    # The sampling and Cycle bodies are exact; only request guard validation changed.
    entry_old, entry_new = ast.parse((OLD / 'capture-entry.py').read_text()), ast.parse((HERE / 'capture-entry.py').read_text())
    classes = lambda tree: {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    assert ast.dump(classes(entry_old)['CaptureCycle']) == ast.dump(classes(entry_new)['CaptureCycle'])
    sample = lambda tree: next(n for n in classes(tree)['CaptureIO'].body if isinstance(n, ast.FunctionDef) and n.name == 'sample')
    assert ast.dump(sample(entry_old)) == ast.dump(sample(entry_new))
    passed('worker/audit/32 receipt and ready/fetch/cleanup/REMOTE/sample/Cycle exact reuse')

    with tempfile.TemporaryDirectory(prefix='icon-irq-synthetic-') as tmp:
        root = Path(tmp); tx = 'usb-irq-protection-activate-fixture0001'; folder = root / tx; folder.mkdir()
        context, camera, probe, capture = folder / 'host-context-private.json', root / 'camera.json', folder / 'probe', folder / 'capture'
        context.write_text('{}'); camera.write_text('{}'); probe.mkdir(); capture.mkdir()
        boot = '22222222-2222-4222-8222-222222222222'; guard = '/var/lib/samurai/' + tx + '-adopted/boot-id-private.txt'
        raw = {'charging_modules': {'samurai-usb-input': {'loaded_note_sha256': '1' * 64},
                'samurai-gauge-protection': {'loaded_note_sha256': '2' * 64}, 'samurai-mp2650': {'loaded_note_sha256': '3' * 64}},
               'camera_modules': {'qcom_camss': {'loaded_note_sha256': '4' * 64}}, 'sensor_note': '5' * 64}
        (capture / 'stdout-private.json').write_text(json.dumps({'raw': raw}))
        descriptor = {'transaction_id': tx, 'stage_transaction_id': 'usb-irq-protection-stage-fixture0001',
            'boot': boot, 'old_boot': '11111111-1111-4111-8111-111111111111', 'guard': guard,
            'manifest': a.MANIFEST, 'candidate_boot_sha256': a.BOOT, 'candidate_logdump_sha256': a.LOGDUMP,
            'postboot_raw_sha256': a.sha((capture / 'stdout-private.json').read_bytes()),
            'release': 'same-k363-release', 'version': '#502 synthetic fixture', 'rootfs': '6' * 64,
            'endpoint': 'fe80::62:bcff:fe28:a101%29'}
        adopt = folder / 'irq-adoption-01-private'; adopt.mkdir()
        base = root / 'private'; base.mkdir(); code = b'synthetic already-reviewed adoption input\n'
        argv = ['synthetic-strict-key', '-C', 'python3 -']
        fake = SimpleNamespace(review=lambda *args: (copy.deepcopy(descriptor), {}),
            payload=lambda *args: code, check_previous=lambda *args: None,
            host_module=lambda: SimpleNamespace(transport_argv=lambda endpoint: argv))
        docs = {}
        def save(name, value):
            path = adopt / name; path.write_text(json.dumps(value)); docs[name] = copy.deepcopy(value)
        save('adopt-request-private.json', descriptor); (adopt / 'executed-adoption-source.py').write_bytes(code)
        save('dispatch-intent-private.json', {'request_count': 1, 'argv': argv, 'stdin_sha256': a.sha(code), 'no_replay': True})
        child = {'pid': 700, 'start_ticks': 123, 'argv': argv, 'observed_argv': ['Windows-interop-different'], 'stdin_sha256': a.sha(code)}
        save('adopt-child-private.json', child)
        reply = {'guard_created': True, 'old_guards_preserved': True, 'transaction_id': tx, 'boot_id': boot,
            'guard': guard, 'postboot_raw_sha256': descriptor['postboot_raw_sha256'], 'fresh_validation_passed': True,
            'cohort_verified': True, 'charging_controls_written': False, 'hardware_writes': 0,
            'guard_sha256': a.sha((boot + '\n').encode()), 'fresh_validation_sha256': '7' * 64}
        save('adopt-stdout-private.json', reply); (adopt / 'adopt-stderr-private.txt').write_bytes(b'')
        terminal = {**child, 'terminal': True, 'returncode': 0, 'primary_error': None, 'cleanup_errors': [],
            'stdout_sha256': a.sha((adopt / 'adopt-stdout-private.json').read_bytes()), 'stderr_sha256': a.sha(b'')}
        save('adopt-terminal-private.json', terminal)
        pointer = {'guard_path': guard, 'original_key_verified': True, 'baseline481_verified': True,
            'Image502_verified': True, 'USB_IRQ_protection_verified': True, 'charging_manifest_sha256': a.MANIFEST,
            'candidate_boot_sha256': a.BOOT, 'candidate_logdump_sha256': a.LOGDUMP,
            'postboot_raw_sha256': descriptor['postboot_raw_sha256'], 'fresh_validation_sha256': '7' * 64,
            'stage_transaction_id': descriptor['stage_transaction_id']}
        endpoint = {'kind': 'usb-ipv6', 'peer': descriptor['endpoint'], 'interface_index': 29, 'host_key_alias': '169.254.42.1',
            'original_key_verified': True, 'observed_new_boot': boot, 'guard_path': guard,
            'postboot_Image502_passed': True, 'postboot_USB_IRQ_protection_passed': True}
        save('adoption-pointer-private.json', pointer); save('new-endpoint-private.json', endpoint)
        save('boot-adoption-before-irq-private.json', {'synthetic-predecessor': True})
        save('adoption-result-private.json', {'passed': True, 'pointer': pointer, 'old_pointer_and_guards_preserved': True,
             'no_charge_or_USB_or_carrier_control_write': True})
        (base / 'boot-adoption-private.json').write_text(json.dumps(pointer))
        review = lambda: a.review_adoption(context, camera, probe, capture)
        with patch.object(a, 'BASE', base), patch.object(a, 'adoption_module', return_value=fake):
            checked = review(); assert checked['boot_id'] == boot and checked['guard_path'] == guard
            assert checked['runtime_expected']['notes']['samurai_usb_input'] == '1' * 64
            assert checked['runtime_expected']['notes']['s5k3m5'] == '5' * 64
            passed('actual new review forwarding and complete receipt chain derives new notes/guard')
            for filename, edit in [
                ('adopt-terminal-private.json', lambda d: d.update(terminal=False)),
                ('adopt-terminal-private.json', lambda d: d.update(returncode=255)),
                ('adopt-terminal-private.json', lambda d: d.update(start_ticks=124)),
                ('adopt-child-private.json', lambda d: d.update(stdin_sha256='0' * 64)),
                ('adopt-child-private.json', lambda d: d.update(argv=['synthetic-strict-key', 'python3 -'])),
                ('dispatch-intent-private.json', lambda d: d.update(request_count=2)),
                ('adoption-result-private.json', lambda d: d.update(passed=False))]:
                bad = copy.deepcopy(docs[filename]); edit(bad); (adopt / filename).write_text(json.dumps(bad))
                rejects(filename + ' mismatch refused', review); (adopt / filename).write_text(json.dumps(docs[filename]))
            (adopt / 'executed-adoption-source.py').write_bytes(code + b'changed')
            rejects('changed executed adoption input refused', review); (adopt / 'executed-adoption-source.py').write_bytes(code)
            (base / 'boot-adoption-private.json').write_text('{}')
            rejects('old502 or superseded current pointer refused', review)
            (base / 'boot-adoption-private.json').write_text(json.dumps(pointer))
            old_guard = descriptor['guard']; descriptor['guard'] = '/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt'
            rejects('old502 guard refused before publication', review); descriptor['guard'] = old_guard
            (adopt / 'adopt-terminal-private.json').unlink()
            rejects('missing real terminal refused', review); (adopt / 'adopt-terminal-private.json').write_text(json.dumps(terminal))
            with patch.object(fake, 'review', side_effect=ValueError('unpassed actual postboot')):
                rejects('upstream reviewed postboot failure never replaced by local labels', review)
            checked = review()
        fake_identity = SimpleNamespace(review_adoption=lambda *args: copy.deepcopy(checked))
        migration = root / 'migration.json'
        receipt = {'schema': 'charging-icon-irq-template-tests-v1', 'passed': True, 'runtime_identity_unbound': True,
            'launcher_sha256': a.sha((HERE / 'launcher.py').read_bytes()), 'sha256': m.FROZEN,
            'manifest_sha256': m.MANIFEST, 'files': {name: a.sha((HERE / name).read_bytes()) for name in
             ('launcher.py', 'bind-identity.py', 'transport.py', 'capture-entry.py', 'adoption-review.py', 'source-pins.json', 'test-profile.py')}}
        migration.write_text(json.dumps(receipt)); target = root / 'binding' / 'identity-pins-private.json'
        with patch.object(b.m, 'identity_review', return_value=fake_identity), patch.object(b, 'sync_directory'):
            answer = b.bind(context, camera, probe, capture, pins=target, migration=migration)
            assert answer['bound_actual_identity'] and target.exists()
            assert b.m.runtime_expected(target)['notes'] == checked['runtime_expected']['notes']
            passed('actual bind and launcher review publish only checked pins; full new notes retained')
            rejects('second bind never replaces original pins', lambda: b.bind(context, camera, probe, capture, pins=target, migration=migration))
            with patch.object(fake_identity, 'review_adoption', side_effect=ValueError('missing real adoption')):
                missing = root / 'must-not-exist' / 'pins.json'
                rejects('missing future adoption refuses before mkdir', lambda: b.bind(context, camera, probe, capture, pins=missing, migration=migration))
                assert not missing.parent.exists()
        request = {'transaction': 'charging-icon-irq-fixture', 'token': 'synthetic', 'expected_boot': boot,
            'manifest_sha256': m.MANIFEST, 'files': m.FROZEN, 'argv': ['synthetic-worker'], 'max_seconds': 300}
        launch = {**request, 'pid': 99, 'start_ticks': 10}
        status = {'active': True, 'terminal': False, 'phase': 'ready', 'ready_for_user_action': True, 'pid': 99, 'start_ticks': 10}
        obs = [{'status': {**status, 'tick': 3+i, 't': 20+i*2, 'realtime': 100+i*2, 'remaining_boottime_seconds': 280-i*2},
                'process': {'state': 'alive', 'pid': 99, 'start_ticks': 10, 'argv': request['argv']},
                'remote_realtime': 100+i*2, 'remote_boottime': 20+i*2} for i in range(2)]
        data = {'observations': obs, 'identity_unchanged': True, 'launch_receipt': launch,
            'clock_start': {'boot': 0}, 'host_roundtrip_seconds': 1}
        assert m.ready_check(data, request)['may_prompt_user']; passed('new manifest request accepts two real advancing heartbeat facts')
        data['observations'] = obs[:1]; assert not m.ready_check(data, request)['may_prompt_user']
        passed('no single heartbeat prompt after profile migration')
        guard_function = next(n for n in ast.parse((HERE / 'capture-entry.py').read_text()).body
                              if isinstance(n, ast.FunctionDef) and n.name == 'adopted_guard')
        namespace = {}; exec(compile(ast.Module(body=[guard_function], type_ignores=[]), 'actual-entry-guard', 'exec'), namespace)
        assert namespace['adopted_guard']({'guard_path': guard}) == guard
        rejects('capture entry refuses old502 namespace', lambda: namespace['adopted_guard'](
            {'guard_path': '/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt'}))
        t = load('icon_irq_transport_actual', HERE / 'transport.py')
        transport_pins = root / 'transport-pins.json'
        transport_pins.write_text(json.dumps({'reviewed': {'endpoint': endpoint},
                                            'transport_inputs': {'key_transport': {'path': 'synthetic-key.py'}}}))
        launcher_stub = SimpleNamespace(reviewed_identity=lambda: None, PINS=transport_pins)
        key_stub = SimpleNamespace(SSH='synthetic-original-ssh', OPTIONS=['-o', 'StrictHostKeyChecking=yes'])
        modules = iter((launcher_stub, key_stub))
        fake_spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _: None))
        response = SimpleNamespace(stdout=b'{}', stderr=b'', returncode=0, check_returncode=lambda: None)
        with patch.object(t.importlib.util, 'spec_from_file_location', return_value=fake_spec), \
             patch.object(t.importlib.util, 'module_from_spec', side_effect=lambda _: next(modules)), \
             patch.object(t.subprocess, 'run', return_value=response) as sent:
            assert t.raw_ssh('synthetic-readonly-command', input=b'exact-input', timeout=45) is response
            argv = sent.call_args.args[0]
            assert argv[:4] == ['synthetic-original-ssh', '-C', '-6', '-T'] and argv[-2:] == ['root@'+endpoint['peer'], 'synthetic-readonly-command']
            assert sent.call_args.kwargs['input'] == b'exact-input' and sent.call_count == 1
        passed('actual icon transport uses fixed compression and exact peer/key once')
    result = {**receipt, 'affected_cases': len(cases), 'cases': cases, 'unchanged_launcher_functions': same,
        'reused_old_delivery_sha256': a.sha((OLD / 'delivery.json').read_bytes()),
        'synthetic_receipt_boundary': 'upstream adopted postboot audit is mocked; no actual future boot asserted',
        'old32_12_14_not_rerun': True, 'network_device_pointer_accessed': False}
    (HERE / 'template-test-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'affected_cases': len(cases), 'runtime_pins_created': False}))


if __name__ == '__main__': main()
