"""Finite local491 contracts: owned Python children and fixture-only APK recovery."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest import mock
import ast
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel491')
NAMES = ['owner-gate.py', 'runtime-common.py', 'worker-body.py']
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(source, name):
    namespace = {'__name__': name, '__file__': str(HERE / name)}
    exec(compile(source, str(HERE / name), 'exec'), namespace)
    return namespace


def static_review(sources):
    result = {}
    for name, source in sources.items():
        tree = ast.parse(source)
        for node in tree.body:
            assert isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Expr, ast.If))
            if isinstance(node, ast.Expr):
                assert isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
            if isinstance(node, ast.If):
                assert ast.unparse(node.test) == "__name__ == '__main__'"
        result[name] = {'import_has_no_action_statements': True}
    worker = ast.parse(sources['worker-body.py'])
    functions = {node.name: node for node in worker.body if isinstance(node, ast.FunctionDef)}
    phases = [ast.literal_eval(node.args[0]) for node in ast.walk(functions['transaction'])
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'phase']
    assert phases == ['forward', 'rollback']
    literals = [node.value for node in ast.walk(worker) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    assert not any(value in {'rmmod', 'insmod', 'modprobe', 'depmod', 'forward-final', 'keep-forward'} for value in literals)
    calls = [node for node in ast.walk(worker) if isinstance(node, ast.Call)]
    assert not any(isinstance(node.func, ast.Attribute) and node.func.attr in {'unlink', 'rmdir', 'rmtree', 'remove'} for node in calls)
    atomic = [function.name for function in functions.values() for node in ast.walk(function)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'atomic']
    assert atomic == ['restore_config']
    restore = ast.unparse(functions['restore_config'])
    assert "path == '/etc/apk/world' or path in repository_files" in restore
    assert "attrs['type'] == 'file'" in restore
    assert not any(isinstance(node.func, ast.Attribute) and node.func.attr in {'kill', 'terminate'}
                   for node in ast.walk(ast.parse(sources['runtime-common.py'])) if isinstance(node, ast.Call))
    result.update(transaction_forward_then_rollback_only=True, no_module_loader_commands=True,
                  no_profile_atomic_writer=True, no_existing_repository_deletion=True,
                  atomic_restore_only_world_and_original_repository_files=True,
                  raw_database_used_as_read_only_forensic_and_logical_comparison=True,
                  owned_run_has_no_kill_or_terminate=True)
    return result


def import_contract(sources):
    def blocked(*args, **kwargs):
        raise AssertionError('Unexpected import-time action')
    # Preloaded Python imports remain available; guard operational APIs during actual exec/import.
    with mock.patch.object(Path, 'read_text', blocked), mock.patch.object(Path, 'read_bytes', blocked), \
         mock.patch.object(Path, 'write_text', blocked), mock.patch.object(Path, 'write_bytes', blocked), \
         mock.patch.object(Path, 'open', blocked), mock.patch.object(Path, 'glob', blocked), \
         mock.patch.object(os, 'uname', blocked), mock.patch.object(os, 'readlink', blocked), \
         mock.patch.object(subprocess, 'Popen', blocked), mock.patch.object(subprocess, 'check_output', blocked):
        for name, source in sources.items():
            load(source, name)
    return {'actual_imports_without_operational_io': NAMES}


def owner_contract(source):
    namespace = load(source, 'owner-gate.py')
    namespace['WINDOW'] = 'k491-package-only-r1'
    now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    stamp = now.isoformat()
    record = dict(issued_at_utc=stamp, authorized_window_ids=['k476-control-delay-r3', 'k491-package-only-r1'],
                  released=True, original_key_verified=True, charging_worker_exited=True, no_concurrent_owner=True,
                  from_owner='charging', to_owner='camera', boot_guard_path='/private/guard', boot_id='synthetic-boot',
                  charging_manifest_sha256='synthetic-manifest')
    scoped = copy.deepcopy(record); scoped['authorized_window_ids'] = ['k476-control-delay-r3']
    plan = dict(deployable=True, window_id='k491-package-only-r1', preflight_window_id='k476-control-delay-r3',
                owner=record, scoped_owner=scoped, handoff=dict(issued_at_utc=stamp, fresh_preflight_verified=True,
                window_owner='camera', window_id='k476-control-delay-r3', boot_guard_path='/private/guard',
                charging={'manifest_sha256': 'synthetic-manifest'}))
    namespace['authorization'](plan, now)
    rejected = []
    modifications = [('unbound', lambda p: p.update(deployable=False)),
                     ('wrong-window', lambda p: p.update(window_id='k491-package-only-r2')),
                     ('scope-extra', lambda p: p['scoped_owner']['authorized_window_ids'].append('other')),
                     ('scope-total-order', lambda p: p['owner']['authorized_window_ids'].reverse()),
                     ('bootguard-unlinked', lambda p: p['handoff'].update(boot_guard_path='/other/guard')),
                     ('manifest-unlinked', lambda p: p['handoff']['charging'].update(manifest_sha256='other')),
                     ('not-released', lambda p: p['owner'].update(released=False)),
                     ('not-fresh', lambda p: p['handoff'].update(fresh_preflight_verified=False))]
    for key, maximum in [('handoff', 600), ('owner', 480), ('scoped_owner', 480)]:
        modifications += [(key + '-expired', lambda p, k=key, m=maximum: p[k].update(issued_at_utc=(now-timedelta(seconds=m+1)).isoformat())),
                          (key + '-future', lambda p, k=key: p[k].update(issued_at_utc=(now+timedelta(seconds=1)).isoformat()))]
    for name, change in modifications:
        candidate = copy.deepcopy(plan); change(candidate)
        try:
            namespace['authorization'](candidate, now)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError('Accepted invalid synthetic owner: ' + name)
    return dict(valid_bound_owner_accepted=True, invalid_synthetic_owners_rejected=rejected,
                actual_device_gate_executed=False)


def run_contract(source, work):
    results = []
    real_popen = subprocess.Popen
    for name in ['success', 'nonzero', 'timeout', 'save-error-live', 'timeout-save-error-live', 'identity-error-live', 'identity-disappeared']:
        root = work / ('run-' + name); root.mkdir(); (root / 'tmp').mkdir()
        namespace = load(source, 'runtime-common.py')
        namespace.update(root=root, state={}, active_child=None, recovering=False,
                         promotion_deadline=time.monotonic()+20, overall_deadline=time.monotonic()+30, sha=sha)
        handles = []; save_errors = []; original_save = namespace['save']; original_identity = namespace['identity']
        def spawn(*args, **kwargs):
            child = real_popen(*args, **kwargs); handles.append(child); return child
        def save(phase, **values):
            fail = (name == 'save-error-live' and phase == 'owned-child' or
                    name == 'timeout-save-error-live' and phase == 'awaiting-same-owned-child')
            if fail and not save_errors:
                assert namespace['active_child'].poll() is None
                save_errors.append(phase)
                raise OSError('injected bookkeeping failure while same child is live')
            return original_save(phase, **values)
        def identity(pid):
            if name == 'identity-error-live':
                assert handles[0].poll() is None
                raise OSError('injected identity observation failure')
            if name == 'identity-disappeared':
                raise FileNotFoundError('injected short-lived /proc lookup race')
            return original_identity(pid)
        namespace.update(save=save, identity=identity)
        marker = root / 'completed-once.txt'
        program = "import pathlib,sys,time; print('ONCE',flush=True); time.sleep(.25); pathlib.Path(sys.argv[1]).open('a').write('DONE\\n'); sys.exit(int(sys.argv[2]))"
        argv = [sys.executable, '-c', program, str(marker), '7' if name == 'nonzero' else '0']
        failure = None
        with mock.patch.object(subprocess, 'Popen', spawn):
            try:
                namespace['run'](argv, 'command', timeout=.05 if name.startswith('timeout') else 2)
            except BaseException:
                failure = traceback.format_exc()
            assert len(handles) == 1 and handles[0].poll() is not None and namespace['active_child'] is None
            assert marker.read_bytes() == b'DONE\n'
            assert (root / 'command-stdout-private.txt').read_bytes() == b'ONCE\n'
            assert not (root / 'command-stderr-private.txt').read_bytes()
            assert bool(failure) == (name not in {'success', 'identity-disappeared'})
            if name == 'success':
                try:
                    namespace['run'](argv, 'command')
                except AssertionError:
                    pass
                else:
                    raise AssertionError('Duplicate log name accepted')
                assert len(handles) == 1
        if failure:
            (root / 'expected-failure-private.txt').write_text(failure)
        row = dict(case=name, spawn_count=1, pid=handles[0].pid, exit_code=handles[0].returncode,
                   same_handle_terminal=True, stdout_occurrences=1, bookkeeping_failure_phases=save_errors,
                   duplicate_label_rejected_before_spawn=name == 'success')
        results.append(row)
    return results


def fixture_contract(sources, work):
    results = []
    for scenario in ['success', 'forward-failure', 'callback-failure', 'rollback-failure', 'prove-failure',
                     'services-failure', 'services-persistent-failure', 'unknown-active-child']:
        root = work / ('fixture-' + scenario); root.mkdir()
        target = root / 'local-target'; target.mkdir()
        allowed = {'/lib/apk/db/installed', '/etc/apk/world', '/proc/sys/kernel/tainted', '/etc/apk/commit_hooks.d'}
        def path(*parts):
            value = Path(*parts)
            if value.is_absolute() and not value.is_relative_to(root):
                assert str(value) in allowed, 'Unexpected fixture path: ' + str(value)
                value = target / str(value).lstrip('/')
            return value
        for name in allowed:
            destination = path(name); destination.parent.mkdir(parents=True, exist_ok=True)
            if name.endswith('commit_hooks.d'):
                destination.mkdir()
        path('/proc/sys/kernel/tainted').write_text('0\n')
        namespace = load(sources['runtime-common.py'], 'runtime-common.py')
        exec(compile(sources['worker-body.py'], str(HERE/'worker-body.py'), 'exec'), namespace)
        names = ['libcamera', 'libcamera-gstreamer', 'libcamera-ipa', 'libcamera-tools', 'libcamera-v4l2', 'samurai-camera-config', 'samurai-camera-stack']
        old = {name: '0.1.0-r28' if name.startswith('samurai') else '99990.7.2-r33' for name in names}
        new = {name: '0.1.0-r29' if name.startswith('samurai') else '99990.7.2-r34' for name in names}
        before = {**old, 'unrelated-fixture-provider': '1-r0'}
        path('/lib/apk/db/installed').write_text(json.dumps(before, sort_keys=True, indent=2)+'\n')
        baseline_db_hash = sha(path('/lib/apk/db/installed'))
        world = b'unrelated-fixture-provider\n' + ''.join(name+'='+version+'\n' for name, version in old.items()).encode()
        path('/etc/apk/world').write_bytes(world)
        backup = root / 'backup'; (backup / 'etc/apk').mkdir(parents=True); (backup/'etc/apk/world').write_bytes(world)
        model = {'kind': 'rollback', 'injections': set(), 'commands': [], 'events': [], 'atomic_paths': []}
        def metadata(value):
            return {'sha256': sha(path(value)), 'type': 'file', 'uid': 0, 'gid': 0, 'mode': 0o600}
        def database():
            result = json.loads(path('/lib/apk/db/installed').read_text())
            if scenario == 'prove-failure' and 'prove-failure' not in model['injections']:
                model['injections'].add('prove-failure'); result['unrelated-fixture-provider'] = 'WRONG'
            return result
        def quiesce(label):
            namespace['stopped'] = True; model['events'].append(label)
        def prepare():
            model['events'].append('prepare')
        def command(argv, label, timeout=30):
            assert argv[0] == '/sbin/apk' and 'add' in argv and '--no-network' in argv
            kind = 'rollback' if label in {'rollback-exact-packages', 'recovery-packages'} else 'forward'
            expected = old if kind == 'rollback' else new
            assert argv[argv.index('add')+1:] == [name+'='+version for name, version in sorted(expected.items())]
            model['commands'].append({'label': label, 'kind': kind}); model['kind'] = kind
            path('/lib/apk/db/installed').write_text(json.dumps({**expected, 'unrelated-fixture-provider': '1-r0'})+'\n')
            path('/etc/apk/world').write_text(''.join(name+'='+version+'\n' for name, version in expected.items()))
            if scenario == 'unknown-active-child' and kind == 'forward':
                namespace['active_child'] = {'fixture_unknown_owned_child': True}
                raise RuntimeError('unknown active fixture child; never replay')
            if ((scenario == 'forward-failure' and kind == 'forward') or
                (scenario == 'rollback-failure' and label == 'rollback-exact-packages')) and scenario not in model['injections']:
                model['injections'].add(scenario)
                raise RuntimeError('injected native APK terminal failure after possible change')
        def inspect(kind):
            assert model['kind'] == kind
            assert json.loads(path('/lib/apk/db/installed').read_text()) == {**(old if kind=='rollback' else new), 'unrelated-fixture-provider':'1-r0'}
            return {'fixture_only': True, 'kind': kind}
        def probe(label):
            model['events'].append('probe-'+label)
            if scenario == 'callback-failure':
                raise RuntimeError('injected callback failure')
        def finish(label):
            model['events'].append('services-'+label)
            if scenario == 'services-persistent-failure' or scenario == 'services-failure' and label == 'final':
                raise RuntimeError('injected service restoration failure')
        def atomic(value, data, attrs):
            assert value == '/etc/apk/world'
            model['atomic_paths'].append(value); path(value).write_bytes(data)
        namespace.update(root=root, Path=path, sha=lambda value: sha(path(value)), plan={},
                         state={'phases': [], 'package_transactions': [], 'commit_hooks_before': {}, 'final_baseline': 'original-r33-r28'},
                         cohort={'rollback_packages':old, 'forward_packages':new}, backup=backup,
                         original={'/etc/apk/world': metadata('/etc/apk/world')}, repository_files=set(),
                         repository_members_before={}, repository_directories_before={}, persistent_repository_before={},
                         stopped=False, mutation=False, success=False, recovering=False, failure=None, active_child=None,
                         last_verified_kind='rollback', changed_since_verified=False, db_before=before,
                         kernel_before=['fixture-anchor'], current_services={}, promotion_deadline=time.monotonic()+30,
                         overall_deadline=time.monotonic()+40, prepare=prepare, gate=lambda plan:None,
                         quiesce=quiesce, run=command, inspect_files=inspect, probe=probe, idle=lambda:None,
                         faults=lambda:[], versions=lambda:old.copy() if model['kind']=='rollback' else new.copy(),
                         database=database, metadata=metadata, repository_inventory=lambda:{}, atomic=atomic, finish_services=finish)
        namespace['transaction']()
        state = namespace['state']
        assert state['terminal'] and not state['installed'] and not state['candidate_retained']
        assert state['passed'] == (scenario == 'success')
        assert all(row['label'] not in {'forward-final', 'forward-final-packages', 'keep-forward'} for row in model['commands'])
        assert len([row for row in model['commands'] if row['kind']=='forward']) == 1
        if scenario in {'unknown-active-child', 'services-persistent-failure'}:
            assert not state.get('original_recovered') and state['manual_inspection_required'] and state['final_baseline']=='unverified'
        else:
            assert state['original_recovered'] and state['final_baseline']=='original-r33-r28'
            assert json.loads(path('/lib/apk/db/installed').read_text()) == before and path('/etc/apk/world').read_bytes()==world
            assert sha(path('/lib/apk/db/installed')) != baseline_db_hash, 'Fixture must retain native logical DB rather than raw restore'
        if scenario == 'unknown-active-child':
            assert model['commands'] == [{'label':'forward-first-packages','kind':'forward'}]
        if scenario in {'prove-failure', 'services-failure'}:
            assert len(model['commands']) == 2, 'Do not replay APK when exact rollback is already verified'
        if scenario != 'success':
            assert state['failure'] and (root/'failure-private.txt').is_file()
        results.append(dict(case=scenario, passed_contract=True, fixture_transaction_passed=state['passed'],
                            commands=model['commands'], events=model['events'], original_recovered=state.get('original_recovered',False),
                            final_baseline=state['final_baseline'], native_logical_db_not_raw_restore=scenario not in {'unknown-active-child','services-persistent-failure'},
                            fixture_state_sha256=sha(root/'state-private.json')))
    return results


def main():
    # Required guard precedes local WSL/proc subprocess testing and any ext4 access.
    spec = importlib.util.spec_from_file_location('storage461_for491_local', HERE.parent/'kernel461/storage.py')
    storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
    volume = storage.mount.mounted_build().parent
    assert __import__('shutil').disk_usage(volume).free > 2*1024**3
    PRIVATE.mkdir(exist_ok=True)
    number = 1
    while (PRIVATE/f'transaction-{number:03d}').exists(): number += 1
    work = PRIVATE/f'transaction-{number:03d}'; work.mkdir(mode=0o700)
    report = dict(stage=491, passed=False, scope='local owned Python children and fixture-only transaction/authorization checks',
                  device_or_sdk_accessed=False, ssh_usb_pm_accessed=False, actual_apk_or_services_executed=False,
                  target_default_probe_executed=False, private_attempt=work.name)
    sources = {name:(HERE/name).read_text() for name in NAMES}
    report['source_sha256'] = {name:sha(HERE/name) for name in NAMES}
    try:
        report['static_review'] = static_review(sources)
        report['imports'] = import_contract(sources)
        report['authorization'] = owner_contract(sources['owner-gate.py'])
        report['real_owned_child_checks'] = run_contract(sources['runtime-common.py'], work)
        report['fixture_transaction_checks'] = fixture_contract(sources, work)
        assert report['source_sha256'] == {name:sha(HERE/name) for name in NAMES}, 'Reviewed source changed during checks'
        report['passed'] = True
    except BaseException:
        report['failure'] = traceback.format_exc()
        (work/'unexpected-failure-private.txt').write_text(report['failure'])
    report['tool_sha256'] = sha(__file__)
    receipt = work/'result-private.json'; receipt.write_text(json.dumps(report,indent=2)+'\n')
    report['private_receipt_sha256'] = sha(receipt)
    public = HERE/'local-validation.json'
    if public.exists():
        previous = work/'previous-public-validation-private.json'; previous.write_bytes(public.read_bytes())
    public.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stage=491,passed=report['passed'],attempt=work.name,report_sha256=sha(public))))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
