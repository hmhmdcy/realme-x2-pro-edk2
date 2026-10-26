"""One bounded pixel probe with VM history and existing submission tracepoints."""
from pathlib import Path
import errno
import hashlib
import json
import os
import re
import subprocess
import time

out = Path('/var/lib/samurai/k136-legacy-vm-trace')
work = Path('/tmp/k136-legacy-gpu-tools')
boot_path = Path('/proc/sys/kernel/random/boot_id')
boot = (out / 'boot-id-private.txt').read_text()
assert boot_path.read_text() == boot
assert os.uname().release == '7.3.0-rc6-rmx1931-samurai-k132+'
assert os.uname().version.startswith('#136 ')
assert not (out / 'run-started.txt').exists()
param = Path('/sys/module/msm/parameters/vm_log_shift')
assert param.read_text().strip() == '0'
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '512'
trace = Path('/sys/kernel/tracing/instances/k136-legacy-evidence')
assert not trace.exists()

def capture(args, name, timeout=60, check=True):
    with (out / name).open('w') as log:
        return subprocess.run(args, stdout=log, stderr=subprocess.STDOUT,
                              check=check, timeout=timeout).returncode

def pids():
    return {name: subprocess.check_output(['pgrep', '-x', name], text=True)
            for name in ['phosh', 'phoc']}

def guard():
    assert boot_path.read_text() == boot
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '512'
    assert pids() == before_pids

before_pids = pids()
(out / 'desktop-pids-before.json').write_text(json.dumps(before_pids))
capture(['dmesg'], 'dmesg-before-private.txt')
d = (out / 'dmesg-before-private.txt').read_text()
assert d.count('WARNING:') == 1 and 'at wcd934x_comp_probe' in d
assert d.count('unable to prepare channel') == 31
assert 'dsi_err_worker' not in d and 'Failed to read' not in d
before = (out / 'dmesg-before-private.txt').read_text()
fault_re = re.compile(r'gpu.*fault|FAULT.*gpu|CCU.*TRANSLATION|CP.*FAULT', re.I)
assert not fault_re.search(before), 'Do not apply GPU load after an existing fault'
capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-before-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/encoder-0/status'], 'encoder-before.txt')
capture(['cat', '/sys/kernel/debug/dri/1/gem'], 'gem-before-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/gpu'], 'gpu-before-private.txt')
capture(['su', '-s', '/bin/sh', 'cy122', '-c',
         'env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr'],
        'output-before.txt')
was_enabled = 'Enabled: yes' in (out / 'output-before.txt').read_text()
samples = []
started = time.monotonic()
(out / 'run-started.txt').write_text(str(started) + '\n')
trace.mkdir()
events = [('drm_msm_gpu', n) for n in ['msm_gpu_submit', 'msm_gpu_submit_flush',
          'msm_gpu_submit_retired', 'msm_gpu_suspend', 'msm_gpu_resume',
          'msm_gpu_vm_update', 'msm_gpu_vm_switch_enqueue']]
events += [('drm', 'drm_vblank_event'), ('drm', 'drm_vblank_event_delivered')]
events += [('dpu', n) for n in ['dpu_enc_frame_done_timeout', 'dpu_enc_trigger_kickoff',
           'dpu_enc_phys_cmd_kickoff', 'dpu_crtc_commit_kickoff']]
enabled_events = []
result = None
error = None
try:
    (trace / 'tracing_on').write_text('0')
    (trace / 'buffer_size_kb').write_text('1024')
    (trace / 'trace_clock').write_text('mono')
    for system, name in events:
        path = trace / 'events' / system / name / 'enable'
        if path.exists():
            path.write_text('1')
            enabled_events.append(system + '/' + name)
    assert 'drm_msm_gpu/msm_gpu_vm_update' in enabled_events
    assert 'drm_msm_gpu/msm_gpu_vm_switch_enqueue' in enabled_events
    (out / 'enabled-events.json').write_text(json.dumps(enabled_events))
    (trace / 'tracing_on').write_text('1')
    (trace / 'trace_marker').write_text('K136_BEGIN\n')
    # Normal compositor output management, once; preserve its previous state.
    if not was_enabled:
        capture(['su', '-s', '/bin/sh', 'cy122', '-c',
                 'env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 '
                 'wlr-randr --output DSI-1 --on'], 'output-on-private.txt', timeout=10)
    guard()
    # Legacy VM mapping events are traced; the VM_BIND log parameter stays at zero.
    assert param.read_text().strip() == '0'
    (out / 'vm-log-parameter-during.txt').write_text(param.read_text())
    (trace / 'trace_marker').write_text('K136_SINGLE_FIXED_FBO_START\n')
    args = ['timeout', '-s', 'TERM', '-k', '2', '20', 'su', '-s', '/bin/sh',
            'cy122', '-c', 'ulimit -t 10; ulimit -v 786432; exec env '
            'XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 '
            'strace -f -qq -s 96 -e trace=ioctl,close '
            '-o /tmp/k136-legacy-gpu-tools/ioctl-private.txt '
            '/tmp/k136-legacy-gpu-tools/glmark2-es2-wayland-fixed '
            '--off-screen --validate --debug --benchmark build:use-vbo=true '
            '--data-path /tmp/k136-legacy-gpu-tools/usr/share/glmark2']
    try:
        result = capture(args, 'pixel-validation-private.txt', timeout=25, check=False)
    finally:
        param.write_text('0')
        (out / 'vm-log-parameter-restored.txt').write_text(param.read_text())
    (out / 'pixel-exit.txt').write_text(str(result) + '\n')
    (out / 'exit-uptime.txt').write_text(Path('/proc/uptime').read_text())
    (trace / 'trace_marker').write_text('K136_SINGLE_FIXED_FBO_EXIT\n')
    capture(['dmesg'], 'dmesg-immediate-private.txt')
    for index in range(13):
        guard()
        item = dict(index=index, monotonic_seconds=time.monotonic(), properties={})
        psy = Path('/sys/class/power_supply/mp2650-input')
        for prop in ['online', 'status', 'voltage_now', 'current_now', 'uevent']:
            try:
                item['properties'][prop] = dict(value=(psy / prop).read_text())
            except OSError as e:
                item['properties'][prop] = dict(errno=e.errno)
        item['taint'] = Path('/proc/sys/kernel/tainted').read_text().strip()
        samples.append(item)
        (out / 'power-samples-private.json').write_text(json.dumps(samples, indent=2))
        if index < 12:
            time.sleep(4)
    capture(['dmesg'], 'dmesg-delayed-private.txt')
except BaseException as e:
    error = dict(type=type(e).__name__, message=str(e))
finally:
    param.write_text('0')
    (trace / 'tracing_on').write_text('0')
    (out / 'vm-log-final.txt').write_text(param.read_text())
    capture(['cat', str(trace / 'trace')], 'submission-trace-private.txt')
    stats = {}
    for p in (trace / 'per_cpu').glob('cpu*/stats'):
        stats[str(p.parent.name)] = p.read_text()
    (out / 'trace-stats.json').write_text(json.dumps(stats, indent=2))
    (trace / 'events/enable').write_text('0')
    trace.rmdir()
    # Keep the normally enabled output on for the delayed desktop observation.
    capture(['dmesg'], 'dmesg-final-private.txt')
    capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-final-private.txt')
    capture(['cat', '/sys/kernel/debug/dri/1/encoder-0/status'], 'encoder-final.txt')
    capture(['cat', '/sys/kernel/debug/dri/1/gem'], 'gem-final-private.txt')
    try:
        final_pids = pids()
    except subprocess.CalledProcessError:
        final_pids = {}
    (out / 'desktop-pids-final.json').write_text(json.dumps(final_pids))
    capture(['su', '-s', '/bin/sh', 'cy122', '-c',
             'env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr'],
            'output-final-private.txt', timeout=10, check=False)
    (out / 'taint-final.txt').write_text(Path('/proc/sys/kernel/tainted').read_text())
    if (work / 'ioctl-private.txt').exists():
        (out / 'ioctl-private.txt').write_bytes((work / 'ioctl-private.txt').read_bytes())
    for dev in Path('/sys/class/devcoredump').glob('devcd*'):
        if dev.is_dir():
            capture(['cat', str(dev / 'data')], dev.name + '-private.data', timeout=20, check=False)
    capture(['sha256sum', '-c', str(out / 'package-db-before.sha256')], 'package-db-check.txt')
    capture(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-check.txt')
    capture(['sha256sum', '-c', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'], 'source-check.txt')
    capture(['sha256sum', '-c', '/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256'], 'vendor-check.txt')
    report = dict(test_exit=result, error=error, elapsed_seconds=time.monotonic()-started,
                  parameter_restored=param.read_text().strip() == '0', trace_removed=not trace.exists(),
                  display_output_previously_enabled=was_enabled, output_kept_enabled=True,
                  diagnostic_only_preexisting_audio_taint=512, goal_complete=False)
    (out / 'run-result.json').write_text(json.dumps(report, indent=2))
    (out / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name + '\n'
            for p in sorted(out.iterdir()) if p.is_file() and p.name != 'SHA256SUMS'))
    subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k136-legacy-evidence-private.tar.gz', '.'], check=True, timeout=30)
    capture(['sha256sum', '/tmp/k136-legacy-evidence-private.tar.gz'], 'archive.sha256')
    print(json.dumps(report), flush=True)
