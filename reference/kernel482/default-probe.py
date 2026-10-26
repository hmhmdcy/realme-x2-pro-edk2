"""481 callback: finite default installed-stack probes; no action on import."""
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
    'pipeline-smoke': '0d692025b2adaf6b5cbadd7fac24ae3034214f5f262ce811061d1a6ea745f4fc',
    'user-launcher.py': '1d1fb6567439ff600c0116d8561ba9c60914306ebb89ccb9b5e08242f9c52ee6',
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
        files[name] = dict(sha256=digest, resolved=str(path.resolve()))
    assert len(expected['profiles']) == len(expected['modules']) == 4
    for row in expected['profiles'] + expected['modules']:
        assert sha(row['path']) == row['sha256'], row['path']
        if 'note_sha256' in row:
            assert sha(Path('/sys/module', row['name'], 'notes/.note.gnu.build-id')) == row['note_sha256']
    return dict(packages={name: actual[name] for name in expected['packages']}, runtime=files,
                modules=expected['modules'], profiles=expected['profiles'])


def process(pid):
    path = Path('/proc', str(pid))
    stat = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    assert stat[0] != 'Z'
    status = dict(line.split(':', 1) for line in (path / 'status').read_text().splitlines() if ':' in line)
    assert all(int(v) == 10000 for v in status['Uid'].split()) and int(status['CapEff'], 16) == 0
    maps = (path / 'maps').read_text()
    assert '(deleted)' not in maps
    mapped = {line.split(None, 5)[5] for line in maps.splitlines() if len(line.split(None, 5)) == 6 and line.split(None, 5)[5].startswith('/')}
    environment = dict(piece.decode().split('=', 1) for piece in (path / 'environ').read_bytes().split(b'\0') if piece)
    assert not any(key.startswith('LD_') or key.startswith('LIBCAMERA_') and key != 'LIBCAMERA_LOG_LEVELS' for key in environment)
    return dict(pid=pid, start_ticks=int(stat[19]), uid=status['Uid'].strip(), capeff=status['CapEff'].strip(),
                exe=str((path / 'exe').resolve()), exe_sha256=sha(path / 'exe'), maps=maps, mapped=sorted(mapped),
                camera_environment={k: v for k, v in environment.items() if k.startswith(('LIBCAMERA_', 'GST_', 'RAW_', 'PIPELINE_FIXTURE_'))})


def witness(text, userroot, program, expected, processed, seen):
    apps = set(map(int, re.findall(r'APPLICATION_PROCESS pid=(\d+)', text)))
    ipas = set(map(int, re.findall(r'IPA stats pid=(\d+)', text)))
    if len(apps) != 1 or len(ipas) != 1:
        return None
    app_pid, ipa_pid = next(iter(apps)), next(iter(ipas))
    app = process(app_pid)
    assert app['exe'] == str(userroot / program) and app['exe_sha256'] == TOOLS[program]
    identities = [app] if app_pid == ipa_pid else [app, process(ipa_pid)]
    for identity in identities:
        seen[str(identity['pid']) + ':' + str(identity['start_ticks'])] = identity
    runtime = expected['runtime_files']
    for identity in identities:
        assert all(path in identity['mapped'] for path in [CORE, BASE])
        for path in identity['mapped']:
            if any(token in path for token in ['libcamera', 'ipa_camss', 'camss_ipa_proxy']):
                assert path in runtime and sha(path) == runtime[path], path
    if program == 'gst-sustained':
        assert PLUGIN in app['mapped']
    ipa = identities[-1]
    assert IPA in ipa['mapped']
    signature = re.findall(r'IPA module ' + re.escape(IPA) + r' signature is (valid|not valid)', text)
    forced = 'Isolation of IPA module ' + IPA + ' forced through configuration' in text
    # The actual475 cohort retains440's generic configuration with no IPA
    # force-isolation setting. A signature failure is a deployment failure.
    assert signature and set(signature) == {'valid'} and not forced
    assert app_pid == ipa_pid, 'Normal installed policy must use the valid signed native IPA'
    branch = 'native-valid-signature'
    leases = re.findall(r'CAPACITY_START epoch=(\d+) tid=(\d+) status=(-?\d+) reason=(\S+) active=(\d+) users=(\d+) original=(\S+) selected=(\S+)', text)
    if processed and not leases:
        return None
    lease = None
    if leases:
        assert len(leases) == 1
        epoch, tid, status, reason, active, users, original, selected = leases[0]
        current = sorted(os.sched_getaffinity(int(tid)))
        if active == '1':
            assert current == list(map(int, selected.split(',')))
        lease = dict(epoch=int(epoch), tid=int(tid), status=int(status), reason=reason, active=active == '1',
                     users=int(users), original=original, selected=selected, live_affinity=current,
                     thread_start_ticks=int(Path('/proc', str(app_pid), 'task', tid, 'stat').read_text().rsplit(')', 1)[1].split()[19]))
    return dict(passed=True, branch=branch, signature_results=signature, configuration_forced=forced,
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


def installed_proxies():
    found = {}
    for path in Path('/proc').glob('[0-9]*'):
        try:
            if os.readlink(path / 'exe') != PROXY:
                continue
            identity = process(int(path.name))
            found[str(identity['pid']) + ':' + str(identity['start_ticks'])] = identity
        except (FileNotFoundError, ProcessLookupError):
            pass
    return found


def run(root, state, *, phase, expected):
    root = Path(root)
    assert root.is_absolute() and root.resolve() == root and root.name == 'k481-package-adoption-r1'
    assert phase in ['forward-first', 'forward-final']
    assert os.geteuid() == 0
    deadline = expected['deadline_monotonic']
    assert time.monotonic() < deadline
    no_services()
    assert not installed_proxies(), '481 exclusive stopped-services window must have no existing IPA proxy'
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
    audit = runpy.run_path(str(root / 'probe-log-audit.py'))['audit']
    directory = root / ('default-probe-' + phase)
    directory.mkdir(mode=0o700)
    report = dict(stage=482, phase=phase, passed=False, cases={}, force_isolation_overridden=False,
                  private_library_or_profile_override=False)
    state.setdefault('default_probes', {})[phase] = report
    account = pwd.getpwuid(10000)
    try:
        report['installed_before'] = installed(expected)
        report['idle_before'] = idle()
        cases = [(model, 'gst', None) for model in ['s5kgw1', 'imx319', 's5k3m5', 'imx471']]
        cases += [('s5kgw1', 'raw', '4608x3456'), ('s5k3m5', 'raw', '2104x1560'), ('s5kgw1', 'dual', '4608x3456')]
        for model, kind, size in cases:
            # Reserve the fixture's35s worst-case child/reap bound and local
            # cleanup before this481 promotion deadline; never start late.
            assert deadline - time.monotonic() >= 45, 'Insufficient481 promotion time for another bounded probe'
            label = model + '-' + kind
            case = directory / label
            case.mkdir(mode=0o700)
            before_files = installed(expected)
            before = idle()
            userroot = Path('/run/user/10000') / ('k449-user-' + root.name + '-' + phase + '-' + label)
            assert userroot.parent == Path('/run/user/10000') and not userroot.exists() and not related(userroot)
            userroot.mkdir(mode=0o700)
            program = 'gst-sustained' if kind == 'gst' else 'pipeline-smoke'
            child = None
            seen = {}
            started = time.monotonic()
            record = dict(model=model, kind=kind, passed=False, expected_frames=32 if kind == 'gst' else 6)
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
                if kind == 'gst':
                    devices = [p for p in Path('/sys/bus/i2c/drivers', model).iterdir() if (p / 'of_node').exists()]
                    nodes = [p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p / 'name').read_text().startswith(model + ' ')]
                    assert len(devices) == len(nodes) == 1
                    camera_id = '/base' + str((devices[0] / 'of_node').resolve()).split('/base', 1)[1]
                    env.update(GST_TARGET_FRAMES='32', GST_SENSOR_NODE='/dev/' + nodes[0].name)
                    arguments = [camera_id, '640', '480']
                else:
                    env['RAW_TARGET_FRAMES'] = '6'
                    arguments = [model + '@' + size, kind]
                logfile = case / 'client.log'
                evidence = None
                assert deadline - time.monotonic() >= 40
                with logfile.open('xb') as output:
                    child = subprocess.Popen([str(tools['pipeline-fixture']), '/dev/media0', str(tools['user-launcher.py']),
                        str(userroot), program, *arguments], env=env, stdin=subprocess.DEVNULL,
                        stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                    while child.poll() is None and evidence is None and time.monotonic() - started < 20:
                        try:
                            seen.update(installed_proxies())
                            evidence = witness(logfile.read_text(errors='replace'), userroot, program, expected, kind != 'raw', seen)
                        except (FileNotFoundError, ProcessLookupError):
                            pass
                        if evidence is None:
                            time.sleep(.005)
                    record['exit_code'] = child.wait(timeout=max(.1, min(45 - (time.monotonic() - started), deadline - time.monotonic())))
                assert evidence and evidence['passed'], 'Live UID/maps/signature/lease witness missing'
                (case / 'live-witness-private.json').write_text(json.dumps(evidence, indent=2) + '\n')
                assert record['exit_code'] == 0
                text = logfile.read_text(errors='replace')
                profile = next(row['path'] for row in expected['profiles'] if row['model'] == model)
                assert 'Using tuning file ' + profile in text
                assert 'Sensor configuration model=' + model in text
                after = idle()
                record.update(audit(text, model=model, kind=kind, before=before['status'], after=after['status']))
                record.update(branch=evidence['branch'], log_sha256=sha(logfile),
                              idle_before=before, idle_after=after, witness_sha256=sha(case / 'live-witness-private.json'))
                assert installed(expected) == before_files
            except BaseException:
                record['failure'] = traceback.format_exc()
                raise
            finally:
                # The existing fixture owns bounded SIGINT, child reap and graph
                # restoration. Do not blind-kill its process group from here.
                if child is not None and child.poll() is None:
                    # Reap/fixture restoration is cleanup, and still runs if
                    # the promotion deadline has expired during a failure.
                    child.wait(timeout=max(1, 45 - (time.monotonic() - started)))
                cleanup_deadline = time.monotonic() + 5
                seen.update(installed_proxies())
                (case / 'observed-processes-private.json').write_text(json.dumps(list(seen.values()), indent=2) + '\n')
                while (related(userroot) or any(live_identity(row) for row in seen.values()) or installed_proxies()) and time.monotonic() < cleanup_deadline:
                    time.sleep(.05)
                assert not related(userroot), 'Retain directory while its client is live'
                assert not any(live_identity(row) for row in seen.values()) and not installed_proxies(), 'Recorded app/IPA identity still live'
                assert userroot.parent == Path('/run/user/10000') and userroot.name.startswith('k449-user-k481-package-adoption-r1-')
                shutil.rmtree(userroot)
                record['user_directory_removed'] = True
                (directory / 'probe-report-private.json').write_text(json.dumps(report, indent=2) + '\n')
        no_services()
        report['idle_after'] = idle()
        report['installed_after'] = installed(expected)
        assert report['installed_after'] == report['installed_before']
        assert time.monotonic() < deadline, '481 promotion deadline expired'
        report['passed'] = len(report['cases']) == 7 and all(row['passed'] for row in report['cases'].values())
        return report
    except BaseException:
        report['failure'] = traceback.format_exc()
        raise
    finally:
        (directory / 'probe-report-private.json').write_text(json.dumps(report, indent=2) + '\n')
