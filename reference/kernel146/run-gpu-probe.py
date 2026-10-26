"""Bounded fixed-size GPU regression, with delayed faults and private evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument('label')
p.add_argument('--debug', default='')
p.add_argument('--repeat', type=int, default=1)
p.add_argument('--delay', type=int, default=35)
p.add_argument('--scene', default='build:use-vbo=true')
p.add_argument('--known-audio-warning', action='store_true')
p.add_argument('--rd', action='store_true')
p.add_argument('--release-existing-core', action='store_true')
a = p.parse_args()
assert a.label.replace('-', '').isalnum() and 1 <= a.repeat <= 20
assert 5 <= a.delay <= 180
os.umask(0o077)
out = Path('/var/lib/samurai') / ('k146-' + a.label)
out.mkdir(mode=0o700)
work = Path('/tmp/k146-gpu-tools')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)

def capture(cmd, name, timeout=30, check=True):
    with (out / name).open('wb') as log:
        return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                              timeout=timeout, check=check).returncode

def counts():
    d = subprocess.check_output(['dmesg'], text=True)
    return dict(gpu_faults=d.count('gpu fault:'), warnings=d.count('WARNING:'),
                dpu_timeouts=d.count('frame done timeout'),
                dsi_errors=d.count('dsi_err_worker'),
                dma_prepare=d.count('unable to prepare channel'))

def desktop():
    return {n: subprocess.check_output(['pgrep', '-x', n], text=True).strip()
            for n in ['phoc', 'phosh']}

def user_cmd(cmd):
    return ['su', '-s', '/bin/sh', 'cy122', '-c', cmd]

def guard():
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
    assert desktop() == before_pids, 'Desktop process changed'
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == taint

taint = Path('/proc/sys/kernel/tainted').read_text().strip()
initial_dmesg = subprocess.check_output(['dmesg'], text=True)
if a.known_audio_warning:
    assert taint == '512' and initial_dmesg.count('WARNING:') == 1
    assert 'at wcd934x_comp_probe' in initial_dmesg
else:
    assert taint == '0', 'Require untainted baseline'
before_counts = counts()
before_pids = desktop()
capture(['dmesg'], 'dmesg-before-private.txt')
capture(['uname', '-a'], 'kernel.txt')
capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-before-private.txt')
capture(['sha256sum', '/etc/apk/world', '/lib/apk/db/installed'], 'packages-before.txt')
if a.release_existing_core:
    for dev in Path('/sys/class/devcoredump').glob('devcd*'):
        if not dev.is_dir():
            continue
        capture(['cat', str(dev / 'data')], 'preexisting-' + dev.name + '-private.data')
        (dev / 'data').write_text('1')
binary = Path('/var/lib/samurai/k131-native-build/glmark2-es2-wayland-fixed')
assert hashlib.sha256(binary.read_bytes()).hexdigest() == '0df9560877295140d00b0a3e7d7931598acf7958d7c63475d907dd107f4f7095'
if not work.exists():
    work.mkdir(mode=0o755)
    package = '/var/lib/samurai/k119-benchmark-source/glmark2-2023.01-r1.apk'
    capture(['apk', 'verify', package], 'apk-verify.txt')
    capture(['apk', 'extract', '--destination', str(work), package], 'apk-extract.txt')
    (work / binary.name).write_bytes(binary.read_bytes())
    (work / binary.name).chmod(0o755)
    subprocess.run(['chown', '-R', '10000:10000', str(work)], check=True)
env = 'env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 '
rd = work / ('rd-' + a.label)
if a.rd:
    rd.mkdir(mode=0o700)
    os.chown(rd, 10000, 10000)
    env += 'FD_RD_DUMP=combine,full FD_RD_DUMP_PATH=' + shlex.quote(str(rd)) + ' '
capture(user_cmd(env + 'wlr-randr'), 'output-before.txt')
was_on = 'Enabled: yes' in (out / 'output-before.txt').read_text()
trace = Path('/sys/kernel/tracing/instances') / ('k146-' + a.label)
trace.mkdir()
results = []
error = None
started = time.monotonic()
try:
    (trace / 'tracing_on').write_text('0')
    (trace / 'buffer_size_kb').write_text('2048')
    (trace / 'trace_clock').write_text('boot')
    for event in ['msm_gpu_submit', 'msm_gpu_submit_flush', 'msm_gpu_submit_retired',
                  'msm_gpu_suspend', 'msm_gpu_resume', 'msm_gpu_vm_update',
                  'msm_gpu_vm_switch_enqueue']:
        enable = trace / 'events/drm_msm_gpu' / event / 'enable'
        if enable.exists():
            enable.write_text('1')
    (trace / 'tracing_on').write_text('1')
    if not was_on:
        capture(user_cmd(env + 'wlr-randr --output DSI-1 --on'), 'output-on.txt', timeout=15)
    for i in range(a.repeat):
        guard()
        (trace / 'trace_marker').write_text('PROBE_START_%d\n' % i)
        cmd = ('ulimit -t 20; ulimit -v 1048576; exec ' + env +
               ('FD_MESA_DEBUG=' + shlex.quote(a.debug) + ' ' if a.debug else '') +
               str(work / binary.name) + ' --off-screen --validate --debug --benchmark ' +
               shlex.quote(a.scene) + ' --data-path ' + str(work / 'usr/share/glmark2'))
        rc = capture(['timeout', '-s', 'TERM', '-k', '3', '30'] + user_cmd(cmd),
                     'pixel-%02d.txt' % i, timeout=35, check=False)
        (trace / 'trace_marker').write_text('PROBE_EXIT_%d\n' % i)
        log = (out / ('pixel-%02d.txt' % i)).read_text()
        results.append(dict(index=i, exit=rc, pixel_success='Validation: Success' in log,
                            renderer_fd640='FD640' in log,
                            fixed_fbo='800x600' in log or '800 x 600' in log))
        for _ in range(a.delay):
            time.sleep(1)
            guard()
        capture(['dmesg'], 'dmesg-%02d-private.txt' % i)
        if counts()['gpu_faults'] > before_counts['gpu_faults']:
            break
except BaseException as e:
    error = dict(type=type(e).__name__, message=str(e))
finally:
    (trace / 'tracing_on').write_text('0')
    capture(['cat', str(trace / 'trace')], 'submission-trace-private.txt')
    stats = {x.parent.name: x.read_text() for x in (trace / 'per_cpu').glob('cpu*/stats')}
    (out / 'trace-stats-private.json').write_text(json.dumps(stats, indent=2))
    (trace / 'events/enable').write_text('0')
    trace.rmdir()
    capture(['dmesg'], 'dmesg-final-private.txt')
    capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-final-private.txt')
    for dev in Path('/sys/class/devcoredump').glob('devcd*'):
        capture(['cat', str(dev / 'data')], dev.name + '-private.data', check=False)
    if a.rd:
        for file in rd.iterdir():
            if file.is_file():
                (out / ('rd-' + file.name)).write_bytes(file.read_bytes())
    capture(['sha256sum', '/etc/apk/world', '/lib/apk/db/installed'], 'packages-after.txt')
    report = dict(label=a.label, kernel=os.uname().version.split()[0],
                  debug=a.debug, scene=a.scene, results=results, error=error,
                  known_preexisting_audio_warning=a.known_audio_warning,
                  raw_command_dump=a.rd,
                  saved_then_released_preexisting_coredump=a.release_existing_core,
                  before=before_counts, after=counts(),
                  desktop_preserved=desktop() == before_pids,
                  taint=Path('/proc/sys/kernel/tainted').read_text().strip(),
                  packages_preserved=(out / 'packages-before.txt').read_bytes() ==
                                     (out / 'packages-after.txt').read_bytes(),
                  elapsed_seconds=time.monotonic() - started,
                  delayed_observation_seconds_per_probe=a.delay,
                  trace_removed=not trace.exists())
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'SHA256SUMS').write_text(''.join(hashlib.sha256(x.read_bytes()).hexdigest() +
        '  ./' + x.name + '\n' for x in sorted(out.iterdir()) if x.is_file() and x.name != 'SHA256SUMS'))
    archive = '/tmp/k146-' + a.label + '-private.tar.gz'
    subprocess.run(['tar', '-C', str(out), '-czf', archive, '.'], check=True, timeout=45)
    print(json.dumps(report), flush=True)
    print('ARCHIVE_SHA256 ' + hashlib.sha256(Path(archive).read_bytes()).hexdigest(), flush=True)
    if error:
        raise SystemExit(2)
