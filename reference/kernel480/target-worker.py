"""One-shot target APK verification and simulation; never commits packages."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, stat, subprocess, sys, traceback

SHA = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
WINDOW = 'k480-target-deps-r1'
ROOT = Path('/var/lib/samurai') / WINDOW


def save(path, value):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n'); temp.chmod(0o600); temp.replace(path)


def gate(plan):
    assert plan['deployable'] and plan['window_id'] == WINDOW
    handoff, owner, scoped = [plan[k] for k in ['handoff', 'owner', 'scoped_owner']]
    assert handoff['fresh_preflight_verified'] and handoff['window_owner'] == 'camera'
    assert handoff['window_id'] == 'k476-control-delay-r2'
    for record, maximum in [(handoff, 600), (owner, 480), (scoped, 480)]:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(record['issued_at_utc'].replace('Z', '+00:00'))).total_seconds()
        assert 0 <= age <= maximum, ('stale authorization', age)
    assert owner['authorized_window_ids'] == ['k476-control-delay-r2', WINDOW]
    assert scoped['authorized_window_ids'] == ['k476-control-delay-r2']
    ignored = {'authorized_window_ids', 'issued_at_utc'}
    assert {k:v for k,v in owner.items() if k not in ignored} == {k:v for k,v in scoped.items() if k not in ignored}
    for k in ['released','original_key_verified','charging_worker_exited','no_concurrent_owner']:
        assert owner[k] is True
    assert owner['from_owner'] == 'charging' and owner['to_owner'] == 'camera'
    assert owner['boot_guard_path'] == handoff['boot_guard_path']
    assert owner['charging_manifest_sha256'] == handoff['charging']['manifest_sha256']
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert boot == owner['boot_id'] == Path(owner['boot_guard_path']).read_text().strip()
    assert os.uname().release == handoff['expected_uname']['release']
    assert os.uname().version == handoff['expected_uname']['version']


def inventory():
    # Bytes, names, symlinks and ownership/modes; exclude atime/mtime changed by reads.
    paths = ['/lib/apk/db', '/etc/apk/world', '/etc/apk/repositories',
             '/etc/apk/repositories.d', '/usr/share/apk/repositories.d',
             '/etc/apk/keys', '/usr/share/apk/keys', '/etc/apk/arch',
             '/var/log/apk.log', '/etc/apk/commit_hooks.d', '/etc/apk/protected_paths.d']
    result = {}
    def visit(p):
        name = str(p)
        if not p.exists() and not p.is_symlink(): result[name] = {'absent': True}; return
        s = p.lstat(); row = dict(mode=stat.S_IMODE(s.st_mode), uid=s.st_uid, gid=s.st_gid)
        if p.is_symlink():
            row.update(type='symlink', target=os.readlink(p))
            resolved = p.resolve(); row['resolved'] = str(resolved)
            if resolved.is_file(): row.update(resolved_sha256=SHA(resolved), resolved_bytes=resolved.stat().st_size)
            elif resolved.is_dir():
                for child in sorted(resolved.iterdir()): visit(child)
        elif p.is_file(): row.update(type='file', sha256=SHA(p), bytes=s.st_size)
        elif p.is_dir():
            row['type'] = 'directory'
            for child in sorted(p.iterdir()): visit(child)
        else: row['type'] = 'other'
        result[name] = row
    for item in paths: visit(Path(item))
    assert result['/lib/apk/db/installed']['type'] == 'file'
    assert result['/etc/apk/world']['type'] == 'file'
    return result


def run(argv, label, records):
    stdout, stderr = ROOT/(label+'-stdout-private.txt'), ROOT/(label+'-stderr-private.txt')
    env = {'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':str(ROOT),'LANG':'C','LC_ALL':'C','TMPDIR':str(ROOT/'tmp')}
    with stdout.open('xb') as out, stderr.open('xb') as err:
        try:
            done = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                  env=env, timeout=90, cwd=ROOT)
            code = done.returncode
        except subprocess.TimeoutExpired: code = 124
    row = dict(argv=argv, exit_code=code, stdout_sha256=SHA(stdout), stderr_sha256=SHA(stderr))
    records.append(row); save(ROOT/(label+'-result-private.json'), row)
    return code


def main():
    os.umask(0o077)
    assert os.geteuid() == 0 and Path(sys.argv[1]) == ROOT
    plan = json.loads((ROOT/'plan-private.json').read_text())
    # Reject stale/unbound input before inventory, APK invocation, or state mutation.
    gate(plan)
    fd = os.open(ROOT/'worker-once-private', os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600); os.close(fd)
    state = dict(stage=480, terminal=False, passed=False, package_transaction_performed=False,
                 pid=os.getpid(), commands=[])
    before = None
    try:
        for name, digest in plan['payload_sha256'].items(): assert SHA(ROOT/name) == digest, name
        (ROOT/'cache').mkdir(mode=0o700); (ROOT/'tmp').mkdir(mode=0o700)
        repos = ROOT/'repositories-private.list'
        repos.write_text('ndx file://'+str(ROOT/'repository/packages.adb')+'\n'); repos.chmod(0o600)
        before = inventory(); save(ROOT/'apk-before-private.json', before)
        save(ROOT/'state-private.json', state)
        common = ['/sbin/apk','--no-network','--repositories-file',str(repos),
                  '--cache-dir',str(ROOT/'cache'),'--logfile=no','--progress=no','--interactive=no']
        assert run(['/sbin/apk','--version'], 'version', state['commands']) == 0
        assert (ROOT/'version-stdout-private.txt').read_text() == 'apk-tools 3.0.8-r0, compiled for aarch64.\n'
        files = [str(ROOT/'repository/packages.adb')] + [str(ROOT/'repository'/p['file']) for p in plan['packages']]
        verify = run(common + ['verify'] + files, 'verify', state['commands'])
        state['signature_verification_passed'] = verify == 0
        if verify == 0:
            gate(plan)
            command = common + ['add','--simulate','--scripts=no','--commit-hooks=no'] + plan['pins']
            state['solver_executed'] = True
            code = run(command, 'simulate', state['commands'])
            state['solver_passed'] = code == 0
        else: state.update(solver_executed=False, solver_passed=False)
    except BaseException as error:
        state['error'] = type(error).__name__ + ': ' + str(error)
        (ROOT/'exception-private.txt').write_text(traceback.format_exc())
    finally:
        try:
            if before is not None:
                after = inventory(); save(ROOT/'apk-after-private.json', after)
                state['global_apk_inventory_byte_identical'] = before == after
        except BaseException as error: state['inventory_error'] = repr(error)
        state['terminal'] = True
        state['passed'] = bool(state.get('signature_verification_passed') and state.get('solver_passed') and state.get('global_apk_inventory_byte_identical') and not state.get('error'))
        save(ROOT/'state-private.json', state)
    return 0 if state['passed'] else 1


if __name__ == '__main__': sys.exit(main())
