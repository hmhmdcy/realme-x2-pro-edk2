"""One normal compositor wake, a bounded trace, and delayed passive checks."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

out = Path('/var/lib/samurai/k141-normal-wake')
trace = Path('/sys/kernel/tracing/instances/k141-normal-wake')
boot_path = Path('/proc/sys/kernel/random/boot_id')
boot = Path('/var/lib/samurai/k140-first-runtime/boot-id-private.txt').read_bytes()
assert os.geteuid() == 0 and os.uname().version.startswith('#140 ')
assert boot_path.read_bytes() == boot and not out.exists() and not trace.exists()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)

def capture(args, name, timeout=20, check=True):
    with (out / name).open('w') as file:
        return subprocess.run(args, stdout=file, stderr=subprocess.STDOUT, timeout=timeout, check=check).returncode

def user(command, name):
    return capture(['su', '-s', '/bin/sh', 'cy122', '-c',
        'env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 ' + command], name, timeout=12)

def pids():
    return {name: subprocess.check_output(['pgrep', '-x', name], text=True).strip().splitlines()
            for name in ['phosh', 'phoc']}

def counts(d):
    return {name: d.count(pattern) for name, pattern in [('gpu_faults', 'gpu fault:'),
        ('dpu_timeouts', 'frame done timeout'), ('dsi_errors', 'dsi_err_worker'),
        ('warnings', 'WARNING:'), ('tx_dma_errors', 'unable to prepare channel')]}

before_pids = pids()
(out / 'pids-before-private.json').write_text(json.dumps(before_pids, indent=2))
capture(['dmesg'], 'dmesg-before-private.txt')
before = counts((out / 'dmesg-before-private.txt').read_text())
assert before == dict(gpu_faults=0, dpu_timeouts=4, dsi_errors=0, warnings=0, tx_dma_errors=0)
user('wlr-randr', 'outputs-before-private.txt')
was_enabled = 'Enabled: yes' in (out / 'outputs-before-private.txt').read_text()
assert not was_enabled, 'This attempt is only the first normal wake from current idle'
capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-before-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/encoder-0/status'], 'encoder-before.txt')
capture(['cat', '/proc/interrupts'], 'interrupts-before-private.txt')
capture(['cat', '/sys/kernel/debug/clk/clk_summary'], 'clocks-before-private.txt', check=False)
capture(['sha256sum', '/etc/apk/world', '/lib/apk/db/installed'], 'package-before.sha256')
events = [('dpu', n) for n in ['dpu_enc_frame_watchdog', 'dpu_enc_frame_done_timeout',
    'dpu_enc_frame_done_cb', 'dpu_enc_phys_cmd_pp_tx_done', 'dpu_enc_kickoff',
    'dpu_enc_trigger_start', 'dpu_enc_trigger_flush', 'dpu_hw_ctl_trigger_start',
    'dpu_enc_wait_event_timeout', 'dpu_enc_irq_wait_success', 'dpu_intf_connect_ext_te',
    'dpu_crtc_vblank_cb', 'dpu_crtc_frame_event_cb', 'dpu_enc_rc', 'dpu_crtc_disable',
    'dpu_enc_phys_cmd_irq_enable', 'dpu_enc_phys_cmd_irq_disable']]
events += [('drm', n) for n in ['drm_vblank_event', 'drm_vblank_event_delivered']]
events += [('drm_msm_gpu', n) for n in ['msm_gpu_submit', 'msm_gpu_submit_flush', 'msm_gpu_submit_retired']]
samples = []
error = None
started = time.monotonic()
trace.mkdir()
try:
    (trace / 'tracing_on').write_text('0')
    (trace / 'buffer_size_kb').write_text('4096')
    (trace / 'trace_clock').write_text('mono')
    enabled = []
    for system, name in events:
        path = trace / 'events' / system / name / 'enable'
        assert path.exists(), system + '/' + name
        path.write_text('1'); enabled.append(system + '/' + name)
    (out / 'enabled-events.json').write_text(json.dumps(enabled))
    (trace / 'tracing_on').write_text('1')
    (trace / 'trace_marker').write_text('K141_NORMAL_OUTPUT_ON_BEGIN\n')
    user('wlr-randr --output DSI-1 --on', 'output-on-private.txt')
    user('wlr-randr', 'outputs-after-on-private.txt')
    (trace / 'trace_marker').write_text('K141_NORMAL_OUTPUT_ON_RETURNED\n')
    for index in range(7):
        assert boot_path.read_bytes() == boot and pids() == before_pids
        assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
        row = dict(index=index, elapsed_seconds=round(time.monotonic() - started, 3),
                   active='active=1' in Path('/sys/kernel/debug/dri/1/state').read_text(),
                   encoder=Path('/sys/kernel/debug/dri/1/encoder-0/status').read_text(),
                   backlights={})
        for bl in Path('/sys/class/backlight').iterdir():
            row['backlights'][bl.name] = {name: (bl / name).read_text().strip()
                for name in ['brightness', 'actual_brightness', 'bl_power'] if (bl / name).exists()}
        samples.append(row)
        (out / 'samples-private.json').write_text(json.dumps(samples, indent=2) + '\n')
        if index < 6:
            time.sleep(2)
    (trace / 'trace_marker').write_text('K141_BOUNDED_WAKE_END\n')
except BaseException as exc:
    error = dict(type=type(exc).__name__, message=str(exc))
finally:
    (trace / 'tracing_on').write_text('0')
    capture(['cat', str(trace / 'trace')], 'wake-trace-private.txt', timeout=25, check=False)
    stats = {p.parent.name: p.read_text() for p in (trace / 'per_cpu').glob('cpu*/stats')}
    (out / 'trace-stats-private.json').write_text(json.dumps(stats, indent=2) + '\n')
    (trace / 'events/enable').write_text('0')
    trace.rmdir()
    capture(['dmesg'], 'dmesg-immediate-private.txt')
    delayed = []
    for index in range(8):
        capture(['dmesg'], 'dmesg-delayed-private.txt')
        row = dict(index=index, elapsed_seconds=round(time.monotonic() - started, 3),
                   same_boot=boot_path.read_bytes() == boot, desktop_pids=pids(),
                   taint=int(Path('/proc/sys/kernel/tainted').read_text()),
                   counts=counts((out / 'dmesg-delayed-private.txt').read_text()))
        delayed.append(row)
        (out / 'delayed-private.json').write_text(json.dumps(delayed, indent=2) + '\n')
        if index < 7:
            time.sleep(3)
    capture(['dmesg'], 'dmesg-final-private.txt')
    capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-final-private.txt')
    capture(['cat', '/sys/kernel/debug/dri/1/encoder-0/status'], 'encoder-final.txt')
    capture(['cat', '/proc/interrupts'], 'interrupts-final-private.txt')
    capture(['cat', '/sys/kernel/debug/clk/clk_summary'], 'clocks-final-private.txt', check=False)
    user('wlr-randr', 'outputs-final-private.txt')
    capture(['sha256sum', '-c', str(out / 'package-before.sha256')], 'package-check.txt')
    capture(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-check.txt')
    capture(['sha256sum', '-c', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'], 'source-check.txt')
    capture(['sha256sum', '-c', '/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256'], 'vendor-check.txt')
    report = dict(stage=141, current_kernel=140, same_boot=boot_path.read_bytes() == boot,
        error=error, elapsed_seconds=round(time.monotonic() - started, 3),
        exactly_one_normal_output_on_requested=True, prior_output_enabled=False,
        output_enabled_after_request='Enabled: yes' in (out / 'outputs-after-on-private.txt').read_text(),
        trace_instance_removed=not trace.exists(), counts_before=before,
        counts_after=counts((out / 'dmesg-final-private.txt').read_text()),
        pids_unchanged=pids() == before_pids, taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        no_standalone_gpu_benchmark=True, physical_pixel_visibility_not_yet_verified=True,
        display_accepted=False, gpu_accepted=False, charging_accepted=False, goal_complete=False)
    (out / 'wake-result.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name + '\n'
        for p in sorted(out.iterdir()) if p.is_file() and p.name != 'SHA256SUMS'))
    subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k141-normal-wake-private.tar.gz', '.'], check=True, timeout=25)
    print(json.dumps(report, indent=2))
