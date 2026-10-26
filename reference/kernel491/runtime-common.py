"""Durable state, exact process identity and owned-child handling for491."""
from pathlib import Path
import hashlib, importlib.util, json, os, pwd, re, runpy, select, signal, shutil, stat, subprocess, sys, time, traceback


def save(phase, **values):
    state.update(phase=phase, **values)
    temporary = root / 'state.tmp'
    with temporary.open('w') as stream:
        stream.write(json.dumps(state, indent=2) + '\n')
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, root / 'state-private.json')
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def identity(pid):
    path = Path('/proc', str(pid))
    values = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=int(pid), start_ticks=values[19], process_state=values[0],
                uid=path.stat().st_uid, comm=(path / 'comm').read_text().strip())


def processes(name):
    result = []
    for path in Path('/proc').glob('[0-9]*'):
        try:
            row = identity(int(path.name))
            if row['comm'] == name and row['process_state'] != 'Z':
                result.append(path)
        except (FileNotFoundError, ProcessLookupError):
            pass
    return result


def services():
    result = {}
    for name in ['pipewire', 'wireplumber']:
        found = processes(name)
        assert len(found) == 1, 'Expected one ' + name
        path = found[0]; row = identity(int(path.name))
        row.update(argv=[value.decode() for value in (path / 'cmdline').read_bytes().split(b'\0') if value],
                   cwd=os.readlink(path / 'cwd'),
                   env=dict(value.decode().split('=', 1) for value in (path / 'environ').read_bytes().split(b'\0') if value))
        assert identity(row['pid'])['start_ticks'] == row['start_ticks']
        result[name] = row
    return result


def stop_services(items):
    for name in ['wireplumber', 'pipewire']:
        if name not in items:
            continue
        item = items[name]
        try:
            descriptor = os.pidfd_open(item['pid'])
        except ProcessLookupError:
            continue
        try:
            try:
                actual = identity(item['pid'])
            except (FileNotFoundError, ProcessLookupError):
                continue
            assert actual['start_ticks'] == item['start_ticks'] and actual['comm'] == name
            if actual['process_state'] == 'Z':
                continue
            signal.pidfd_send_signal(descriptor, signal.SIGTERM)
            assert select.select([descriptor], [], [], 8)[0], name + ' did not exit'
        finally:
            os.close(descriptor)


def demote(item):
    account = pwd.getpwuid(item['uid'])
    def callback():
        os.initgroups(account.pw_name, account.pw_gid)
        os.setgid(account.pw_gid); os.setuid(account.pw_uid)
    return callback


def restart(items, label, started):
    for name in ['pipewire', 'wireplumber']:
        found = processes(name)
        if found:
            assert len(found) == 1 and name in started, 'Unexpected existing ' + name
            actual = identity(int(found[0].name))
            assert actual['pid'] == started[name]['pid'] and actual['start_ticks'] == started[name]['start_ticks']
            continue
        item = items[name]; environment = item['env'].copy()
        environment.pop('PIPEWIRE_NOTIFICATION_FD', None)
        with (root / (label + '-' + name + '.log')).open('xb') as output:
            child = subprocess.Popen(item['argv'], env=environment, cwd=item['cwd'], preexec_fn=demote(item),
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        actual = identity(child.pid)
        started[name] = {**item, 'pid': child.pid, 'start_ticks': actual['start_ticks']}
        time.sleep(.6)
        assert child.poll() is None, name + ' restart failed'
    return started


def budget():
    if recovering:
        state['diagnostic_budget_overrun'] = time.monotonic() > overall_deadline
    else:
        assert time.monotonic() < promotion_deadline, 'Promotion deadline expired; restore original'


def run(arguments, label, timeout=30, env=None, preexec_fn=None):
    global active_child
    assert re.fullmatch(r'[A-Za-z0-9_.-]+', label)
    budget()
    if not recovering:
        timeout = min(timeout, max(1, promotion_deadline - time.monotonic()))
    output_path, error_path = [root / (label + suffix) for suffix in ['-stdout-private.txt', '-stderr-private.txt']]
    assert not output_path.exists() and not error_path.exists(), 'No replay of an existing command'
    clean = dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin', HOME=str(root), LANG='C', LC_ALL='C', TMPDIR=str(root / 'tmp'))
    with output_path.open('xb') as output, error_path.open('xb') as errors:
        active_child = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=output, stderr=errors,
                                        env=env or clean, preexec_fn=preexec_fn)
        try:
            try:
                ticks = identity(active_child.pid)['start_ticks']
            except (FileNotFoundError, ProcessLookupError):
                # Popen.wait remains authoritative for a very short-lived child.
                ticks = None
            save('owned-child', active_child=dict(pid=active_child.pid, start_ticks=ticks, argv=arguments, label=label))
            late = False
            try:
                code = active_child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                late = True
                if ticks is None:
                    try:
                        ticks = identity(active_child.pid)['start_ticks']
                    except (FileNotFoundError, ProcessLookupError):
                        pass
                save('awaiting-same-owned-child', unknown_state=True, manual_inspection_required=True,
                     active_child=dict(pid=active_child.pid, start_ticks=ticks, argv=arguments, label=label))
                while active_child.poll() is None:
                    time.sleep(1)
                code = active_child.returncode
        except BaseException:
            # Even a logging/identity failure cannot authorize a rollback while
            # this possibly-committing child is live. Keep its original handle.
            try:
                save('awaiting-same-owned-child-after-observation-error', unknown_state=True,
                     manual_inspection_required=True,
                     active_child=dict(pid=active_child.pid, start_ticks=locals().get('ticks'), argv=arguments, label=label))
            except BaseException:
                pass
            active_child.wait()
            active_child = None
            raise
        else:
            active_child = None
    record = dict(argv=arguments, exit_code=code, stdout_sha256=sha(output_path), stderr_sha256=sha(error_path),
                  finished_after_deadline=late)
    (root / (label + '-result-private.json')).write_text(json.dumps(record, indent=2) + '\n')
    save('owned-child-complete', active_child=None, unknown_state=False, last_command=record)
    if code or late:
        raise RuntimeError(label + ' failed or exceeded its bound; same child is now terminal')
    return subprocess.CompletedProcess(arguments, code, output_path.read_bytes(), error_path.read_bytes())
