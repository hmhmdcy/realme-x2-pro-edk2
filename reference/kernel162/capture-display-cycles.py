"""Capture bounded compositor display cycles without changing persistent setup."""
from pathlib import Path
import hashlib, json, os, re, subprocess, sys, time

os.umask(0o077)
label = sys.argv[1]
assert re.fullmatch(r'k162-[a-z0-9-]+', label)
out = Path('/var/lib/samurai') / label
trace = Path('/sys/kernel/tracing/instances') / label
assert not out.exists() and not trace.exists()
boot_path = Path('/proc/sys/kernel/random/boot_id')
boot = boot_path.read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert hashlib.sha256(Path('/usr/lib/libvulkan_freedreno.so').read_bytes()).hexdigest() == '97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e'
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
card = Path('/dev/dri/by-path/platform-ae01000.display-controller-card').resolve(strict=True)
drm_debug = Path('/sys/kernel/debug/dri') / card.name.removeprefix('card')

def capture(args, name, timeout=15):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    (out/name).write_bytes(result.stdout + result.stderr)
    result.check_returncode()
    return result.stdout.decode()

def user(command, name):
    return capture(['su', '-s', '/bin/sh', 'cy122', '-c',
        'env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 ' + command], name)

def pids():
    return {n: subprocess.run(['pgrep', '-x', n], capture_output=True, text=True).stdout.split()
        for n in ['phoc', 'phosh']}

def counts(log):
    return {k:log.count(v) for k,v in dict(kms_init_failures='kms hw init failed',dpu_timeouts='frame done timeout',
        dsi_errors='dsi_err_worker', gpu_faults='gpu fault:', warnings='WARNING:',
        dma_prepare='unable to prepare channel').items()}

before = counts(capture(['dmesg'], 'dmesg-before-private.txt'))
original_pids = pids()
assert all(original_pids.values())
power_tool = ['python3', '/var/lib/samurai/k162-tools/display-power.py']
was_on = '<0>' in capture(power_tool+['get'], 'outputs-before-private.txt')
events = [('drm_msm_dsi', n) for n in ['msm_dsi_error_irq', 'msm_dsi_error_status', 'msm_dsi_error_work']]
events += [('drm_panel','drm_panel_backlight'),('dpu','dpu_first_frame_backlight')]
events += [('dpu', n) for n in ['dpu_enc_frame_watchdog','dpu_enc_frame_done_timeout',
    'dpu_enc_frame_done_cb','dpu_enc_phys_cmd_pp_tx_done','dpu_enc_kickoff',
    'dpu_enc_rc','dpu_crtc_disable']]
rows, error = [], None
started = time.monotonic()
trace.mkdir()
try:
    (trace/'tracing_on').write_text('0')
    (trace/'buffer_size_kb').write_text('4096')
    (trace/'trace_clock').write_text('boot')
    for system, name in events:
        (trace/'events'/system/name/'enable').write_text('1')
    (trace/'tracing_on').write_text('1')
    for index in range(12):
        for on in [True, False]:
            assert boot_path.read_bytes() == boot and pids() == original_pids
            assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
            state = 'on' if on else 'off'
            (trace/'trace_marker').write_text(f'{label} cycle={index} {state} begin\n')
            capture(power_tool+[state], f'cycle-{index}-{state}-private.txt')
            time.sleep(0.4)
            drm = (drm_debug/'state').read_text()
            (out/f'drm-{index}-{state}-private.txt').write_text(drm)
            row = dict(index=index, requested_on=on, active='\n\tactive=1\n' in drm,
                elapsed=time.monotonic()-started, counts=counts(subprocess.check_output(['dmesg'], text=True)))
            rows.append(row)
            (out/'samples.json').write_text(json.dumps(rows, indent=2))
            assert row['active'] == on, row
            assert row['counts'] == before, row
except BaseException as exc:
    error = dict(type=type(exc).__name__, message=str(exc))
finally:
    capture(power_tool+['on' if was_on else 'off'], 'restore-output-private.txt')
    (trace/'tracing_on').write_text('0')
    capture(['cat', str(trace/'trace')], 'display-trace-private.txt')
    stats = {p.parent.name:p.read_text() for p in (trace/'per_cpu').glob('cpu*/stats')}
    (out/'trace-stats.json').write_text(json.dumps(stats, indent=2))
    (trace/'events/enable').write_text('0')
    trace.rmdir()
    after_log = capture(['dmesg'], 'dmesg-after-private.txt')
    report = dict(label=label, kernel_build=os.uname().version.split()[0],
        elapsed_seconds=time.monotonic()-started, completed_transitions=len(rows),
        counts_before=before, counts_after=counts(after_log), error=error,
        same_boot=boot_path.read_bytes()==boot, pids_preserved=pids()==original_pids,
        taint=int(Path('/proc/sys/kernel/tainted').read_text()), trace_removed=not trace.exists(),
        prior_output_on=was_on, output_restored=True,
        power_mode_9c_messages=after_log.count('power mode 0x9c')-(out/'dmesg-before-private.txt').read_text().count('power mode 0x9c'),
        optical_visibility_verified=False, startup_test=False)
    (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'
        for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
    print(json.dumps(report), flush=True)
    if error: sys.exit(1)
