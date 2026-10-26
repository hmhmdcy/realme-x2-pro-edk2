"""Early post-reboot DPU capture; no application workload or output request."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import threading
import select
import time

out = Path('/var/lib/samurai/k142-reboot140-startup')
trace = Path('/sys/kernel/tracing/instances/k142-startup')
boot_path = Path('/proc/sys/kernel/random/boot_id')
old_boot = Path('/var/lib/samurai/k142-preflash/boot-id-private.txt').read_bytes()
boot = boot_path.read_bytes()
assert os.geteuid() == 0 and os.uname().version.startswith('#140 ')
assert boot != old_boot and not out.exists() and not trace.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
assert int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:'))) > 1024**2

def capture(args, name, timeout=20, check=False):
    with (out / name).open('w') as file:
        return subprocess.run(args, stdout=file, stderr=subprocess.STDOUT, timeout=timeout, check=check).returncode

def counts(text):
    return {name: text.count(pattern) for name, pattern in [('gpu_faults', 'gpu fault:'),
        ('dpu_timeouts', 'frame done timeout'), ('dsi_errors', 'dsi_err_worker'),
        ('warnings', 'WARNING:'), ('tx_dma_errors', 'unable to prepare channel')]}

capture(['dmesg'], 'dmesg-early-private.txt', check=True)
capture(['cat', '/sys/kernel/tracing/instances/display/trace'], 'default-display-early-private.txt', timeout=25)
capture(['cat', '/sys/kernel/tracing/instances/display/trace_clock'], 'default-display-clock.txt')
(out / 'default-display-early-stats-private.json').write_text(json.dumps({p.parent.name: p.read_text()
    for p in Path('/sys/kernel/tracing/instances/display/per_cpu').glob('cpu*/stats')}, indent=2) + '\n')
capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-early-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/encoder-0/status'], 'encoder-early.txt')
events = [('dpu', n) for n in ['dpu_enc_frame_watchdog', 'dpu_enc_frame_done_timeout',
    'dpu_enc_frame_done_cb', 'dpu_enc_frame_done_cb_not_busy', 'dpu_enc_phys_cmd_pp_tx_done',
    'dpu_enc_kickoff', 'dpu_enc_trigger_start', 'dpu_enc_trigger_flush', 'dpu_hw_ctl_trigger_start',
    'dpu_enc_wait_event_timeout', 'dpu_enc_irq_wait_success', 'dpu_intf_connect_ext_te',
    'dpu_enc_phys_cmd_connect_te', 'dpu_crtc_vblank_cb', 'dpu_crtc_frame_event_cb',
    'dpu_crtc_frame_event_done', 'dpu_crtc_frame_event_more_pending', 'dpu_enc_rc',
    'dpu_crtc_disable', 'dpu_enc_disable', 'dpu_enc_phys_cmd_irq_enable', 'dpu_enc_phys_cmd_irq_disable',
    'dpu_hw_ctl_clear_pending_flush', 'dpu_hw_ctl_trigger_prepare', 'dpu_core_perf_update_clk',
    'dpu_kms_commit', 'dpu_enc_prepare_kickoff']]
events += [('drm', n) for n in ['drm_vblank_event', 'drm_vblank_event_delivered']]
events += [('drm_msm', n) for n in ['msm_atomic_commit_tail_start', 'msm_atomic_commit_tail_finish',
    'msm_atomic_flush_commit', 'msm_atomic_wait_flush_start', 'msm_atomic_wait_flush_finish']]
events += [('drm_msm_gpu', n) for n in ['msm_gpu_submit', 'msm_gpu_submit_flush', 'msm_gpu_submit_retired']]
events += [('irq', n) for n in ['irq_handler_entry', 'irq_handler_exit', 'softirq_entry', 'softirq_exit']]
events += [('power', n) for n in ['cpu_idle', 'cpu_frequency', 'cpu_frequency_limits',
    'suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end']]
events += [('timer', n) for n in ['timer_expire_entry', 'timer_expire_exit']]
trace.mkdir()
reader_stop = threading.Event()
reader_errors = []
reader = None

def drain_pipe():
    fd = None
    try:
        fd = os.open(trace / 'trace_pipe', os.O_RDONLY | os.O_NONBLOCK)
        with (out / 'startup-stream-private.txt').open('wb') as stream:
            while not reader_stop.is_set():
                ready, _, _ = select.select([fd], [], [], 0.2)
                if not ready:
                    continue
                try:
                    chunk = os.read(fd, 262144)
                except BlockingIOError:
                    continue
                if chunk:
                    stream.write(chunk)
            while True:
                try:
                    chunk = os.read(fd, 262144)
                except BlockingIOError:
                    break
                if not chunk:
                    break
                stream.write(chunk)
    except BaseException as exc:
        reader_errors.append(dict(type=type(exc).__name__, message=str(exc)))
    finally:
        if fd is not None:
            os.close(fd)

started = time.monotonic()
samples = []
error = None
stable_since = None
last_pids = None
try:
    (trace / 'tracing_on').write_text('0')
    (trace / 'buffer_size_kb').write_text('16384')
    (trace / 'trace_clock').write_text('mono')
    enabled = []
    for system, name in events:
        # Derive the existing subsystem from the kernel instead of assuming aliases.
        matches = list((trace / 'events').glob('*/' + name + '/enable'))
        assert len(matches) == 1, name
        matches[0].write_text('1')
        enabled.append(str(matches[0].relative_to(trace)))
    (out / 'enabled-events.json').write_text(json.dumps(enabled, indent=2) + '\n')
    reader = threading.Thread(target=drain_pipe, name='trace-reader')
    reader.start()
    (trace / 'tracing_on').write_text('1')
    (trace / 'trace_marker').write_text('K142_EARLY_BOOT_IRQ_IDLE_CAPTURE_BEGIN\n')
    print('K142_CURRENT140_NEW_BOOT_STARTUP_TRACE_STARTED', flush=True)
    while time.monotonic() - started < 240:
        assert boot_path.read_bytes() == boot
        capture(['dmesg'], 'dmesg-latest-private.txt', check=True)
        current_pids = {name: subprocess.run(['pgrep', '-x', name], capture_output=True, text=True).stdout.strip().splitlines()
                        for name in ['phosh', 'phoc']}
        if all(current_pids.values()) and current_pids == last_pids:
            if stable_since is None:
                stable_since = time.monotonic()
        else:
            stable_since = None
        last_pids = current_pids
        row = dict(index=len(samples), elapsed_seconds=round(time.monotonic() - started, 3),
            uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
            taint=int(Path('/proc/sys/kernel/tainted').read_text()), desktop_pids=current_pids,
            counts=counts((out / 'dmesg-latest-private.txt').read_text()),
            active=Path('/sys/kernel/debug/dri/1/state').is_file() and 'active=1' in Path('/sys/kernel/debug/dri/1/state').read_text())
        samples.append(row)
        (out / 'startup-samples-private.json').write_text(json.dumps(samples, indent=2) + '\n')
        if stable_since is not None and time.monotonic() - stable_since >= 25:
            break
        time.sleep(5)
    (trace / 'trace_marker').write_text('K142_STARTUP_CAPTURE_END\n')
except BaseException as exc:
    error = dict(type=type(exc).__name__, message=str(exc))
finally:
    (trace / 'tracing_on').write_text('0')
    reader_stop.set()
    if reader is not None:
        reader.join(timeout=5)
        assert not reader.is_alive(), 'trace reader did not stop'
    capture(['cat', str(trace / 'trace')], 'startup-trace-private.txt', timeout=30)
    (out / 'trace-stats-private.json').write_text(json.dumps({p.parent.name: p.read_text()
        for p in (trace / 'per_cpu').glob('cpu*/stats')}, indent=2) + '\n')
    (trace / 'events/enable').write_text('0')
    trace.rmdir()
    capture(['dmesg'], 'dmesg-final-private.txt', check=True)
    capture(['cat', '/sys/kernel/tracing/instances/display/trace'], 'default-display-final-private.txt', timeout=30)
    capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-final-private.txt')
    capture(['cat', '/sys/kernel/debug/dri/1/encoder-0/status'], 'encoder-final.txt')
    capture(['cat', '/sys/kernel/debug/clk/clk_summary'], 'clocks-final-private.txt')
    capture(['cat', '/proc/interrupts'], 'interrupts-final-private.txt')
    capture(['cat', '/home/cy122/.local/state/samurai-phosh-session.log'], 'session-final-private.txt')
    report = dict(stage=142, current_kernel=140, new_boot=True, same_new_boot=boot_path.read_bytes() == boot,
        error=error, trace_stream_reader_errors=reader_errors, early_boot_service=True, sample_count=len(samples), elapsed_seconds=round(time.monotonic() - started, 3),
        taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        counts=counts((out / 'dmesg-final-private.txt').read_text()),
        phosh_present_final=bool(last_pids and last_pids['phosh']),
        phoc_present_final=bool(last_pids and last_pids['phoc']),
        trace_instance_removed=not trace.exists(), no_output_or_application_workload_requested=True,
        physical_pixel_visibility_not_verified=True, instrumentation_may_change_timing=True, goal_complete=False)
    (out / 'startup-result.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name + '\n'
        for p in sorted(out.iterdir()) if p.is_file() and p.name != 'SHA256SUMS'))
    subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k142-reboot140-startup-private.tar.gz', '.'], check=True, timeout=30)
    (out / 'complete-private.txt').write_text('K142_RECORDER_COMPLETE\n')
    print(json.dumps(report, indent=2), flush=True)
