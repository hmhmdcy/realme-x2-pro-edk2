"""One package-only forward/capture/rollback transaction; no driver/profile writes."""


def inspect_files(kind):
    assert versions() == cohort[kind + '_packages']
    unchanged_other_packages()
    assert trust_inventory() == trust_before, 'Original APK trust set changed'
    for path, row in plan['package_files'][kind].items():
        actual = metadata(path)
        assert actual['uid'] == actual['gid'] == 0
        if 'symlink' in row:
            assert actual['type'] == 'symlink' and actual['target'] == row['symlink']
        else:
            assert actual['type'] == 'file' and actual['sha256'] == row['sha256'] and actual['mode'] == row['mode'], path
    for family in ['modules', 'profiles']:
        for row in cohort[family]:
            path = Path(row['path'])
            assert str(path.resolve()) == row['resolved_path']
            actual = metadata(path)
            assert actual['type'] == 'file' and actual['sha256'] == row['rollback_sha256']
            assert actual['uid'] == actual['gid'] == 0 and actual['mode'] == 0o644
            if protected_before:
                assert actual == protected_before[row['path']], 'Untouched protected file changed'
        if family == 'modules':
            for row in cohort[family]:
                assert sha('/sys/module/' + row['name'] + '/notes/.note.gnu.build-id') == row['rollback_note_sha256']
    return dict(kind=kind, packages=versions(), noncohort_database_entries_unchanged=True,
                installed_database_sha256=sha('/lib/apk/db/installed'), world_sha256=sha('/etc/apk/world'),
                modules_and_private_profiles_unchanged=True, package_files_checked=len(plan['package_files'][kind]))


def repository_inventory():
    result = {}
    for directory in plan['preserve_repository_directories']:
        path = Path(directory)
        assert path.is_dir() and not path.is_symlink()
        result[directory] = metadata(path)
        for item in sorted(path.rglob('*')):
            assert not item.is_symlink() and (item.is_dir() or item.is_file())
            result[str(item)] = metadata(item)
    return result


def restore_config():
    budget()
    for path, attrs in original.items():
        if path == '/etc/apk/world' or path in repository_files:
            assert attrs['type'] == 'file'
            atomic(path, (backup / path.lstrip('/')).read_bytes(), attrs)
    # No persistent repository is created or deleted by491. In particular the
    # existing61 r33 repository and its signed payload directory remain intact.
    for directory, before in repository_members_before.items():
        assert {item.name: metadata(item) for item in Path(directory).iterdir()} == before
        assert metadata(directory) == repository_directories_before[directory]
    assert repository_inventory() == persistent_repository_before
    assert Path('/etc/apk/world').read_bytes() == (backup / 'etc/apk/world').read_bytes()


def apk_args(kind):
    return ['/sbin/apk', '--no-network', '--repositories-file', str(root / (kind + '.list')),
            '--cache-dir', str(root / 'cache'), '--logfile=no', '--progress=no', '--interactive=no']


def package_phase(kind, label):
    global mutation
    mutation = True
    save(label + '-native-apk-start', native_apk_attempted=True)
    pins = [name + '=' + version for name, version in sorted(cohort[kind + '_packages'].items())]
    run(apk_args(kind) + ['add'] + pins, label + '-packages', timeout=90)
    state['package_transactions'].append(dict(phase=label, kind=kind, pins=cohort[kind + '_packages'], native_apk_exit_code=0))


def probe(label):
    spec = importlib.util.spec_from_file_location('default_probe491', root / 'default-probe.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    expected = dict(plan['expected_forward'], deadline_monotonic=promotion_deadline)
    result = module.run(root, state, phase=label, expected=expected)
    assert result['passed']
    idle(); assert not camera_fds()
    save(label + '-probe-passed', default_probe=result)


def phase(kind, label, do_probe=False):
    global last_verified_kind, changed_since_verified
    budget(); quiesce(label + '-quiescent')
    changed_since_verified = True
    package_phase(kind, label)
    if kind == 'rollback':
        restore_config()
    evidence = inspect_files(kind); idle()
    if do_probe:
        probe(label); evidence = inspect_files(kind)
    (root / (label + '-installed-db-forensic.txt')).write_bytes(Path('/lib/apk/db/installed').read_bytes())
    (root / (label + '-world-forensic.txt')).write_bytes(Path('/etc/apk/world').read_bytes())
    (root / (label + '-proof-private.json')).write_text(json.dumps(evidence, indent=2) + '\n')
    state['phases'].append(dict(phase=label, kind=kind, verified=True, default_probe=do_probe))
    last_verified_kind = kind; changed_since_verified = False
    save(label + '-verified')


def prove_restored():
    inspect_files('rollback')
    assert database() == db_before, 'Original logical APK database entries were not restored'
    assert all(metadata(path) == attrs for path, attrs in original.items()), 'Rollback file/attribute mismatch'
    assert repository_inventory() == persistent_repository_before
    assert {str(path): metadata(path) for path in Path('/etc/apk/commit_hooks.d').glob('*')} == state['commit_hooks_before']
    save('rollback-proven', exact_rollback_verified=True, rollback_database_semantics_verified=True)


def finish_services(label):
    restart(consumers, label, current_services); idle()
    for name, item in current_services.items():
        found = processes(name)
        assert len(found) == 1 and found[0].name == str(item['pid'])
        assert identity(item['pid'])['start_ticks'] == item['start_ticks']
        values = dict(line.split(':', 1) for line in Path('/proc', str(item['pid']), 'status').read_text().splitlines() if ':' in line)
        assert [int(value) for value in values['Uid'].split()] == [10000] * 4 and int(values['CapEff'].strip(), 16) == 0
    deadline = time.monotonic() + 8
    lines = []; maps = ''
    while time.monotonic() < deadline:
        maps = Path('/proc', str(current_services['wireplumber']['pid']), 'maps').read_text()
        lines = [line for line in maps.splitlines() if '/usr/lib/libcamera.so.0.7.2' in line]
        if lines:
            break
        time.sleep(.2)
    assert lines and all('(deleted)' not in line and int(line.split()[4]) == Path('/usr/lib/libcamera.so.0.7.2').stat().st_ino for line in lines)
    (root / (label + '-wireplumber-maps-private.txt')).write_text(maps)
    assert not faults() and charging() == plan['handoff']['charging']


def prepare():
    global db_before, trust_before, consumers, kernel_before, repository_files
    global repository_members_before, repository_directories_before, persistent_repository_before
    assert root.name == plan['window_id'] and os.geteuid() == 0 and plan['deployable']
    assert not backup.exists() and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    assert charging() == plan['handoff']['charging']
    assert shutil.disk_usage('/').free >= plan['minimum_target_free_bytes']
    for name, digest in plan['payload_sha256'].items():
        assert sha(root / name) == digest, name
    (root / 'tmp').mkdir(mode=0o700); (root / 'cache').mkdir(mode=0o700)
    db_before = database(); trust_before = trust_inventory()
    for family in ['modules', 'profiles']:
        for row in cohort[family]:
            protected_before[row['path']] = metadata(row['path'])
    repository_members_before = {}; repository_directories_before = {}; repository_files = set()
    for directory in ['/etc/apk/repositories.d', '/usr/share/apk/repositories.d']:
        path = Path(directory)
        assert path.is_dir() and not path.is_symlink()
        repository_directories_before[directory] = metadata(path)
        repository_members_before[directory] = {item.name: metadata(item) for item in path.iterdir()}
        assert all(row['type'] == 'file' for row in repository_members_before[directory].values())
        repository_files.update(str(item) for item in path.iterdir())
    if Path('/etc/apk/repositories').exists():
        repository_files.add('/etc/apk/repositories')
    persistent_repository_before = repository_inventory()
    consumers = services(); current_services.update(consumers)
    for item in consumers.values():
        assert item['uid'] == 10000
        assert not any(key == 'LD_LIBRARY_PATH' or key.startswith('LIBCAMERA_') and key != 'LIBCAMERA_LOG_LEVELS' for key in item['env'])
        values = dict(line.split(':', 1) for line in Path('/proc', str(item['pid']), 'status').read_text().splitlines() if ':' in line)
        assert [int(value) for value in values['Uid'].split()] == [10000] * 4 and int(values['CapEff'].strip(), 16) == 0
    inspect_files('rollback'); idle()
    kernel_before = subprocess.check_output(['dmesg'], text=True).splitlines()
    assert kernel_before
    state['kernel_anchor'] = kernel_before[-1]
    backup.mkdir(mode=0o700)
    paths = set(plan['package_files']['rollback']) | repository_files | {'/etc/apk/world'}
    for path in sorted(paths):
        original[path] = metadata(path)
        if path == '/etc/apk/world' or path in repository_files:
            assert original[path]['type'] == 'file'
        if original[path]['type'] == 'file':
            target = backup / path.lstrip('/')
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(Path(path).read_bytes())
            assert sha(target) == original[path]['sha256']
    forensic = backup / 'forensic-apk-db'; forensic.mkdir(mode=0o700)
    for source in Path('/lib/apk/db').iterdir():
        if source.is_file() and not source.is_symlink():
            (forensic / source.name).write_bytes(source.read_bytes())
    state['scripts_hooks_policy'] = 'native APK defaults enabled; absent cohort scripts are not claimed exercised'
    state['commit_hooks_before'] = {str(path): metadata(path) for path in Path('/etc/apk/commit_hooks.d').glob('*')}
    for name, value in [('original-attributes', original), ('services', consumers), ('original-trust', trust_before),
                        ('protected-files', protected_before), ('persistent-repository', persistent_repository_before),
                        ('repository-members', repository_members_before)]:
        (backup / (name + '-private.json')).write_text(json.dumps(value, indent=2) + '\n')
    for entry in backup.rglob('*'):
        if entry.is_file():
            descriptor = os.open(entry, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    for directory in sorted([entry for entry in backup.rglob('*') if entry.is_dir()] + [backup, root], key=lambda entry: len(entry.parts), reverse=True):
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    for kind in ['forward', 'rollback']:
        (root / (kind + '.list')).write_text('ndx file://' + str(root / kind / 'repository/packages.adb') + '\n')
        run(apk_args(kind) + ['verify'] + [str(path) for path in sorted((root / kind / 'repository').iterdir())], 'verify-' + kind, timeout=50)
    run(apk_args('forward') + ['add', '--simulate'] + [name + '=' + version for name, version in sorted(cohort['forward_packages'].items())], 'fresh-forward-solver', timeout=40)
    save('fresh-backup-complete')


def transaction():
    global success, failure, recovering
    try:
        prepare()
        gate(plan)
        phase('forward', 'forward-first', True)
        phase('rollback', 'rollback-exact')
        prove_restored()
        finish_services('final')
        assert not faults() and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
        success = True
        state.update(final_baseline='original-r33-r28', original_recovered=True)
    except BaseException:
        failure = traceback.format_exc()
        (root / 'failure-private.txt').write_text(failure)
    finally:
        if failure and stopped:
            try:
                recovering = True; budget()
                assert active_child is None, 'Owned child still live; observe the same handle without replay'
                if mutation:
                    quiesce('recovery-quiescent')
                    if changed_since_verified or last_verified_kind != 'rollback':
                        package_phase('rollback', 'recovery')
                        restore_config()
                    prove_restored()
                else:
                    inspect_files('rollback')
                finish_services('recovery')
                state.update(original_recovered=True, final_baseline='original-r33-r28')
            except BaseException:
                state.update(cleanup_failure=traceback.format_exc(), manual_inspection_required=True, final_baseline='unverified')
        try:
            state.update(packages=versions(), new_faults=faults() if kernel_before else [],
                         taint_after=int(Path('/proc/sys/kernel/tainted').read_text()))
            state['final_services'] = {name: {key: item[key] for key in ['pid', 'start_ticks', 'uid']} for name, item in current_services.items()}
        except BaseException:
            state['final_observation_failure'] = traceback.format_exc(); success = False
        state.update(failure=failure, installed=False, candidate_retained=False,
                     passed=bool(success and not failure), terminal=True)
        save('complete' if state['passed'] else 'failed')


def main():
    global root, plan, cohort, backup, dev, state, original, protected_before
    global consumers, current_services, mutation, stopped, success, failure, active_child
    global db_before, kernel_before, trust_before, promotion_deadline, overall_deadline
    global recovering, last_verified_kind, changed_since_verified
    global repository_files, repository_members_before, repository_directories_before, persistent_repository_before
    os.umask(0o077)
    root = Path(sys.argv[1]); plan = json.loads((root / 'plan-private.json').read_text())
    assert str(root) == plan['target_root']
    gate(plan)
    assert not (root / 'state-private.json').exists(), 'Inspect an existing transaction; do not restart it'
    cohort = plan['cohort']; backup = root / 'backup'; dev = Path('/sys/bus/platform/devices/ac10000.icp')
    state = dict(stage=491, pid=os.getpid(), terminal=False, passed=False, phases=[], quiescence=[],
                 package_transactions=[], final_baseline='original-r33-r28', manual_inspection_required=False,
                 package_database_restore_method='native APK only; raw DB is forensic', active_child=None)
    original = {}; protected_before = {}; consumers = {}; current_services = {}
    mutation = stopped = success = recovering = False
    failure = active_child = db_before = kernel_before = trust_before = None
    repository_files = set(); repository_members_before = {}; repository_directories_before = {}; persistent_repository_before = {}
    last_verified_kind = 'rollback'; changed_since_verified = False
    promotion_deadline = time.monotonic() + plan['promotion_deadline_seconds']
    overall_deadline = time.monotonic() + plan['diagnostic_budget_seconds']
    state.update(promotion_deadline_monotonic=promotion_deadline, diagnostic_budget_monotonic=overall_deadline)
    save('preflight'); transaction()
    return 0 if state['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
