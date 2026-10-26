"""491 package-only callback: eight finite installed GST cases; inert on import.

No APK, module, profile or service writes. Full installed SHA snapshots bracket
the callback; intervening metadata/maps bind the same files without rehashing
the large core while a short12-frame stream is running.
"""
from pathlib import Path
import hashlib
import json
import os
import pwd
import re
import runpy
import shutil
import subprocess
import time
import traceback

TOOLS = {
    'pipeline-fixture': 'bad0dc79d95d070f089c158b159a21f72a44a459f4c1606f9c27493457863a43',
    'gst-sustained': '7f4d6a1f8527280d8bbe11e6af638348200bd9bc8465be8357cdc0ca732b852a',
    'user-launcher.py': '6c28bc2a9193c4adec64a9c0bde40d44589b360b83640ebe3f8dc1a4297b6446',
}
CORE = '/usr/lib/libcamera.so.0.7.2'
BASE = '/usr/lib/libcamera-base.so.0.7.2'
IPA = '/usr/lib/libcamera/ipa/ipa_camss_vfe.so'
PROXY = '/usr/libexec/libcamera/camss_ipa_proxy'
PLUGIN = '/usr/lib/gstreamer-1.0/libgstlibcamera.so'
GENERIC_CONFIGURATION = '078d4021f6c2cc6412b6668c8bb76e45f4bc7dde00a8abd2ae2de8b380a81a04'
DEVICE = Path('/sys/bus/platform/devices/ac10000.icp')
PM = ['ac10000.icp', 'acb3000.camss', 'ac4a000.cci', 'ac4b000.cci']
RELEASED = ['backing_owned', 'cpu_enabled', 'irq_enabled', 'power_held', 'remaining_groups',
            'remaining_domains', 'mapped_bytes', 'ipe_dma_pending', 'request_fw_mapped',
            'imported_buffers', 'imported_bytes']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_identity(path):
    info = Path(path).stat()
    return dict(dev=info.st_dev, inode=info.st_ino, size=info.st_size,
                ctime_ns=info.st_ctime_ns, mtime_ns=info.st_mtime_ns,
                mode=info.st_mode, uid=info.st_uid, gid=info.st_gid)


def unchanged(snapshot):
    for name, row in snapshot['runtime'].items():
        assert str(Path(name).resolve()) == row['resolved'] and file_identity(name) == row['identity'], name
    for row in snapshot['profiles'] + snapshot['modules']:
        assert file_identity(row['path']) == snapshot['other_identities'][row['path']], row['path']
        if 'note_sha256' in row:
            assert sha(Path('/sys/module', row['name'], 'notes/.note.gnu.build-id')) == row['note_sha256']
    actual = packages()
    assert all(actual[name] == version for name, version in snapshot['packages'].items())


def checked_cases(cases):
    assert isinstance(cases, list) and len(cases) == 8
    actual = set()
    names = set()
    for case in cases:
        assert set(case) == {'name', 'model', 'width', 'height', 'frames', 'isolated'}
        assert isinstance(case['isolated'], bool)
        assert all(type(case[key]) is int for key in ['width', 'height', 'frames'])
        assert 12 <= case['frames'] <= 32
        assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', case['name'])
        assert case['name'] not in names; names.add(case['name'])
        key = (case['model'], case['width'], case['height'], case['isolated'])
        assert key not in actual; actual.add(key)
    wanted = {(model, 640, 480, False) for model in ['s5kgw1', 'imx319', 's5k3m5', 'imx471']}
    wanted |= {('s5kgw1', width, height, isolated) for width, height in [(1280, 720), (1920, 1080)] for isolated in [False, True]}
    assert actual == wanted
    return cases


def packages():
    found = {}
    for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
        fields = dict(line.split(':', 1) for line in block.splitlines() if ':' in line)
        if 'P' in fields:
            found[fields['P']] = fields['V']
    return found


def no_services():
    for entry in Path('/proc').glob('[0-9]*'):
        try:
            if (entry / 'comm').read_text().strip() in ['pipewire', 'wireplumber']:
                assert (entry / 'stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z'
        except (FileNotFoundError, ProcessLookupError):
            pass


def idle():
    deadline = time.monotonic() + 8
    while True:
        status = json.loads((DEVICE / 'm2m_status').read_text())
        core = json.loads((DEVICE / 'state').read_text())
        pm = {name: Path('/sys/bus/platform/devices', name, 'power/runtime_status').read_text().strip() for name in PM}
        if all(value == 'suspended' for value in pm.values()) and not any(status[k] for k in
                ['users', 'running', 'pinned', 'orphans', 'fatal']) and not any(core[k] for k in RELEASED):
            assert not any(status[k] for k in ['failed', 'first_error'])
            assert status['jobs'] == status['completed'] + status['cancelled']
            assert status['direct_completed'] == status['completed']
            assert core['copy_frames'] == 0 and core['direct_frames'] == core['frames_completed']
            return dict(status=status, core=core, pm=pm)
        assert time.monotonic() < deadline, (status, core, pm)
        time.sleep(.05)


def installed(expected):
    runtime = expected['runtime_files']
    assert all(name in runtime for name in [CORE, BASE, IPA, IPA + '.sign', PROXY, PLUGIN, '/etc/libcamera/configuration.yaml'])
    actual = packages()
    assert len(expected['packages']) == 7 and all(actual[name] == version for name, version in expected['packages'].items())
    files = {}
    for name, digest in runtime.items():
        path = Path(name)
        assert path.is_absolute() and path.parts[1] in ['usr', 'etc'], name
        assert sha(path) == digest, name
        files[name] = dict(sha256=digest, resolved=str(path.resolve()), identity=file_identity(path))
    assert len(expected['profiles']) == len(expected['modules']) == 4
    for row in expected['profiles'] + expected['modules']:
        assert sha(row['path']) == row['sha256'], row['path']
        if 'note_sha256' in row:
            assert sha(Path('/sys/module', row['name'], 'notes/.note.gnu.build-id')) == row['note_sha256']
    return dict(packages={name: actual[name] for name in expected['packages']}, runtime=files,
                modules=expected['modules'], profiles=expected['profiles'],
                other_identities={row['path']: file_identity(row['path']) for row in expected['profiles'] + expected['modules']})


def process(pid, isolated):
    path = Path('/proc', str(pid))
    stat = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    assert stat[0] != 'Z'
    status = dict(line.split(':', 1) for line in (path / 'status').read_text().splitlines() if ':' in line)
    assert all(int(v) == 10000 for v in status['Uid'].split()) and int(status['CapEff'], 16) == 0
    maps = (path / 'maps').read_text()
    assert '(deleted)' not in maps
    mapped = {line.split(None, 5)[5] for line in maps.splitlines() if len(line.split(None, 5)) == 6 and line.split(None, 5)[5].startswith('/')}
    environment = dict(piece.decode().split('=', 1) for piece in (path / 'environ').read_bytes().split(b'\0') if piece)
    allowed = {'LIBCAMERA_LOG_LEVELS'} | ({'LIBCAMERA_IPA_FORCE_ISOLATION'} if isolated else set())
    assert not any(key.startswith('LD_') or key.startswith('LIBCAMERA_') and key not in allowed for key in environment)
    assert environment.get('LIBCAMERA_IPA_FORCE_ISOLATION') == ('1' if isolated else None)
    account = pwd.getpwuid(10000)
    assert environment['HOME'] == account.pw_dir and environment['USER'] == environment['LOGNAME'] == account.pw_name
    assert environment['HOME'] != '/root'
    executable = str((path / 'exe').resolve())
    executable_sha256 = sha(path / 'exe')
    end_stat = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    assert end_stat[0] != 'Z' and end_stat[19] == stat[19]
    return dict(pid=pid, start_ticks=int(stat[19]), uid=status['Uid'].strip(), capeff=status['CapEff'].strip(),
                exe=executable, exe_sha256=executable_sha256, maps=maps, mapped=sorted(mapped),
                personal_environment={k: v for k, v in environment.items() if k in ['HOME', 'USER', 'LOGNAME'] or k.startswith('XDG_')},
                camera_environment={k: v for k, v in environment.items() if k.startswith(('LIBCAMERA_', 'GST_', 'RAW_', 'PIPELINE_FIXTURE_'))})


def witness(text, userroot, program, expected, snapshot, isolated, seen, native_signature_proof):
    apps = set(map(int, re.findall(r'APPLICATION_PROCESS pid=(\d+)', text)))
    ipas = set(map(int, re.findall(r'IPA stats pid=(\d+)', text)))
    if len(apps) != 1 or len(ipas) != 1:
        return None
    app_pid, ipa_pid = next(iter(apps)), next(iter(ipas))
    app = process(app_pid, isolated)
    assert app['exe'] == str(userroot / program) and app['exe_sha256'] == TOOLS[program]
    identities = [app] if app_pid == ipa_pid else [app, process(ipa_pid, isolated)]
    for identity in identities:
        seen[str(identity['pid']) + ':' + str(identity['start_ticks'])] = identity
    runtime = expected['runtime_files']
    for identity in identities:
        assert all(path in identity['mapped'] for path in [CORE, BASE])
        for path in identity['mapped']:
            if any(token in path for token in ['libcamera', 'ipa_camss', 'camss_ipa_proxy']):
                assert path in runtime, path
                original = snapshot['runtime'][path]
                assert file_identity(path) == original['identity'] and str(Path(path).resolve()) == original['resolved']
                mappings = [line.split(None, 5) for line in identity['maps'].splitlines()
                            if len(line.split(None, 5)) == 6 and line.split(None, 5)[5] == path]
                info = original['identity']
                assert mappings and all(int(row[4]) == info['inode'] and
                    tuple(int(piece, 16) for piece in row[3].split(':')) == (os.major(info['dev']), os.minor(info['dev'])) for row in mappings), path
    if program == 'gst-sustained':
        assert PLUGIN in app['mapped']
    ipa = identities[-1]
    assert IPA in ipa['mapped']
    signature = re.findall(r'IPA module ' + re.escape(IPA) + r' signature is (valid|not valid)', text)
    forced = 'Isolation of IPA module ' + IPA + ' forced through configuration' in text
    # Matching473 ipa_manager.cpp:293-297 returns before verification on the
    # force branch. A native case must first have verified these same stable
    # installed IPA/sign bytes; do not invent an isolated verification call.
    if isolated:
        assert forced and not signature and native_signature_proof
        assert native_signature_proof['ipa_sha256'] == runtime[IPA]
        assert native_signature_proof['signature_sha256'] == runtime[IPA + '.sign']
        assert app_pid != ipa_pid and ipa['exe'] == PROXY and ipa['exe_sha256'] == runtime[PROXY]
        branch = 'isolated-force-branch-native-signature-proof-reused'
    else:
        assert signature and set(signature) == {'valid'} and not forced
        assert app_pid == ipa_pid, 'Normal installed policy must use the valid signed native IPA'
        branch = 'native-valid-signature'
    leases = re.findall(r'CAPACITY_START epoch=(\d+) tid=(\d+) status=(-?\d+) reason=(\S+) active=(\d+) users=(\d+) original=(\S+) selected=(\S+)', text)
    if not leases:
        return None
    lease = None
    if leases:
        assert len(leases) == 1
        epoch, tid, status, reason, active, users, original, selected = leases[0]
        current = sorted(os.sched_getaffinity(int(tid)))
        assert status == '0' and active == users == '1' and reason == 'selected'
        assert current == list(map(int, selected.split(',')))
        original_cpus = list(map(int, original.split(',')))
        capacity = {cpu: int(Path('/sys/devices/system/cpu', 'cpu' + str(cpu), 'cpu_capacity').read_text()) for cpu in original_cpus}
        assert current == [cpu for cpu in original_cpus if capacity[cpu] > min(capacity.values())]
        lease = dict(epoch=int(epoch), tid=int(tid), status=int(status), reason=reason, active=active == '1',
                     users=int(users), original=original, selected=selected, live_affinity=current,
                     cpu_capacity=capacity, thread_start_ticks=int(Path('/proc', str(app_pid), 'task', tid, 'stat').read_text().rsplit(')', 1)[1].split()[19]))
    return dict(passed=True, branch=branch, signature_results=signature, configuration_forced=forced,
                signature_verification_executed_here=not isolated,
                reused_native_signature_proof=native_signature_proof if isolated else None,
                application_pid=app_pid, ipa_pid=ipa_pid, processes=identities, manager_lease=lease)


def related(userroot):
    result = []
    for entry in Path('/proc').glob('[0-9]*'):
        try:
            if (entry / 'stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z':
                continue
            exe = os.readlink(entry / 'exe')
            args = (entry / 'cmdline').read_bytes().split(b'\0')
            if exe.startswith(str(userroot) + '/') or str(userroot).encode() in args:
                result.append(int(entry.name))
        except (OSError, UnicodeDecodeError):
            pass
    return result


def live_identity(identity):
    try:
        fields = Path('/proc', str(identity['pid']), 'stat').read_text().rsplit(')', 1)[1].split()
        return fields[0] != 'Z' and int(fields[19]) == identity['start_ticks']
    except (FileNotFoundError, ProcessLookupError):
        return False


def installed_proxies(isolated):
    found = {}
    for path in Path('/proc').glob('[0-9]*'):
        try:
            if os.readlink(path / 'exe') != PROXY:
                continue
            identity = process(int(path.name), isolated)
            found[str(identity['pid']) + ':' + str(identity['start_ticks'])] = identity
        except (FileNotFoundError, ProcessLookupError):
            pass
    return found


def run(root, state, *, phase, expected):
    root = Path(root)
    assert root.is_absolute() and root.resolve() == root and root == Path('/var/lib/samurai/k491-package-only-r1')
    assert root.name == expected['window_id'] == 'k491-package-only-r1'
    assert phase in ['forward-first', 'forward-only']
    cases = checked_cases(expected['cases'])
    assert os.geteuid() == 0
    deadline = expected['deadline_monotonic']
    assert time.monotonic() < deadline
    no_services()
    assert not installed_proxies(False), '491 exclusive stopped-services window must have no existing IPA proxy'
    configuration = Path('/etc/libcamera/configuration.yaml')
    assert sha(configuration) == expected['runtime_files'][str(configuration)] == GENERIC_CONFIGURATION
    assert not re.search(r'^\s*(?:ipa|force_isolation|module_paths)\s*:', configuration.read_text(), re.M)
    tools = {}
    for name, digest in TOOLS.items():
        row = expected['probe_tools'][name]
        path = root / row['path']
        assert path.resolve().is_relative_to(root) and row['sha256'] == digest and sha(path) == digest
        assert os.access(path, os.X_OK)
        tools[name] = path
    auditor = runpy.run_path(str(root / 'probe-log-audit.py'))
    audit = auditor['audit']
    directory = root / ('default-probe-' + phase)
    directory.mkdir(mode=0o700)
    report = dict(stage=491, phase=phase, passed=False, cases={}, explicit_cases=cases,
                  private_library_or_profile_override=False)
    state.setdefault('default_probes', {})[phase] = report
    account = pwd.getpwuid(10000)
    try:
        report['installed_before'] = installed(expected)
        report['idle_before'] = idle()
        for specification in cases:
            model = specification['model']; width = specification['width']; height = specification['height']
            frames = specification['frames']; isolated = specification['isolated']; kind = 'gst'
            if isolated:
                assert report.get('native_signature_proof'), 'Native installed signature verification must precede isolation'
            # Reserve the fixture's35s worst-case child/reap bound and local
            # cleanup before this491 promotion deadline; never start late.
            assert deadline - time.monotonic() >= 45, 'Insufficient491 promotion time for another bounded probe'
            label = specification['name']
            case = directory / label
            case.mkdir(mode=0o700)
            unchanged(report['installed_before'])
            before = idle()
            userroot = Path('/run/user/10000') / ('k449-user-' + root.name + '-' + phase + '-' + label)
            assert userroot.parent == Path('/run/user/10000') and not userroot.exists() and not related(userroot)
            userroot.mkdir(mode=0o700)
            program = 'gst-sustained'
            child = None
            completed = False
            seen = {}
            started = time.monotonic()
            record = dict(specification, kind=kind, passed=False, expected_frames=frames)
            report['cases'][label] = record
            try:
                shutil.copyfile(tools[program], userroot / program)
                (userroot / program).chmod(0o700)
                os.chown(userroot / program, 10000, account.pw_gid)
                os.chown(userroot, 10000, account.pw_gid)
                env = dict(os.environ)
                for key in list(env):
                    if key.startswith(('LD_', 'LIBCAMERA_', 'GST_', 'CAPTURE_', 'RAW_', 'MEASURE_', 'PIPELINE_FIXTURE_')) or key in ['PYTHONPATH', 'PYTHONHOME']:
                        env.pop(key)
                env.update(LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG,IPAManager:DEBUG,IPAModule:DEBUG',
                           PIPELINE_FIXTURE_TIMEOUT_SECONDS='30')
                if isolated:
                    env['LIBCAMERA_IPA_FORCE_ISOLATION'] = '1'
                devices = [p for p in Path('/sys/bus/i2c/drivers', model).iterdir() if (p / 'of_node').exists()]
                nodes = [p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p / 'name').read_text().startswith(model + ' ')]
                assert len(devices) == len(nodes) == 1
                camera_id = '/base' + str((devices[0] / 'of_node').resolve()).split('/base', 1)[1]
                env.update(GST_TARGET_FRAMES=str(frames), GST_SENSOR_NODE='/dev/' + nodes[0].name)
                arguments = [camera_id, str(width), str(height)]
                logfile = case / 'client.log'
                evidence = None
                assert deadline - time.monotonic() >= 40
                with logfile.open('xb') as output:
                    child = subprocess.Popen([str(tools['pipeline-fixture']), '/dev/media0', str(tools['user-launcher.py']),
                        str(userroot), program, *arguments], env=env, stdin=subprocess.DEVNULL,
                        stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                    while child.poll() is None and evidence is None and time.monotonic() - started < 20:
                        try:
                            seen.update(installed_proxies(isolated))
                            evidence = witness(logfile.read_text(errors='replace'), userroot, program, expected, report['installed_before'], isolated, seen, report.get('native_signature_proof'))
                        except (FileNotFoundError, ProcessLookupError):
                            pass
                        if evidence is None:
                            time.sleep(.005)
                    record['exit_code'] = child.wait(timeout=max(.1, min(45 - (time.monotonic() - started), deadline - time.monotonic())))
                assert evidence and evidence['passed'], 'Live UID/maps/signature/lease witness missing'
                (case / 'live-witness-private.json').write_text(json.dumps(evidence, indent=2) + '\n')
                assert record['exit_code'] == 0
                text = logfile.read_text(errors='replace')
                record['warnings'] = auditor['warning_summary'](text)
                profile = next(row['path'] for row in expected['profiles'] if row['model'] == model)
                assert 'Using tuning file ' + profile in text
                assert 'Sensor configuration model=' + model in text
                after = idle()
                record.update(audit(text, model=model, width=width, height=height, frames=frames, before=before['status'], after=after['status']))
                record['passed'] = False  # Set true only after identity/fixture cleanup below.
                record.update(branch=evidence['branch'], log_sha256=sha(logfile),
                              idle_before=before, idle_after=after, witness_sha256=sha(case / 'live-witness-private.json'))
                unchanged(report['installed_before'])
                if not isolated and 'native_signature_proof' not in report:
                    report['native_signature_proof'] = dict(case=label, witness_sha256=record['witness_sha256'],
                        ipa_sha256=expected['runtime_files'][IPA], signature_sha256=expected['runtime_files'][IPA + '.sign'],
                        core_sha256=expected['runtime_files'][CORE], application_pid=evidence['application_pid'],
                        signature_results=evidence['signature_results'])
                completed = True
            except BaseException:
                record['passed'] = False
                record['failure'] = traceback.format_exc()
                raise
            finally:
                record['passed'] = False
                # The existing fixture owns bounded SIGINT, child reap and graph
                # restoration. Do not blind-kill its process group from here.
                if child is not None and child.poll() is None:
                    # Reap/fixture restoration is cleanup, and still runs if
                    # the promotion deadline has expired during a failure.
                    child.wait(timeout=max(1, 45 - (time.monotonic() - started)))
                if (case / 'client.log').exists():
                    record['log_sha256'] = sha(case / 'client.log')
                    record['warnings'] = auditor['warning_summary']((case / 'client.log').read_text(errors='replace'))
                cleanup_deadline = time.monotonic() + 5
                seen.update(installed_proxies(isolated))
                (case / 'observed-processes-private.json').write_text(json.dumps(list(seen.values()), indent=2) + '\n')
                while (related(userroot) or any(live_identity(row) for row in seen.values()) or installed_proxies(isolated)) and time.monotonic() < cleanup_deadline:
                    time.sleep(.05)
                assert not related(userroot), 'Retain directory while its client is live'
                assert not any(live_identity(row) for row in seen.values()) and not installed_proxies(isolated), 'Recorded app/IPA identity still live'
                record['observed_processes_exited'] = [{'pid': row['pid'], 'start_ticks': row['start_ticks'], 'live': live_identity(row)} for row in seen.values()]
                assert userroot.parent == Path('/run/user/10000') and userroot.name.startswith('k449-user-k491-package-only-r1-')
                shutil.rmtree(userroot)
                record['user_directory_removed'] = True
                record['passed'] = completed
                (directory / 'probe-report-private.json').write_text(json.dumps(report, indent=2) + '\n')
        no_services()
        report['idle_after'] = idle()
        report['installed_after'] = installed(expected)
        assert report['installed_after'] == report['installed_before']
        assert time.monotonic() < deadline, '491 promotion deadline expired'
        report['passed'] = len(report['cases']) == 8 and all(row['passed'] for row in report['cases'].values())
        return report
    except BaseException:
        report['failure'] = traceback.format_exc()
        raise
    finally:
        (directory / 'probe-report-private.json').write_text(json.dumps(report, indent=2) + '\n')
