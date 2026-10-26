from pathlib import Path
import hashlib, json, re, tarfile

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel165')
out = Path('/mnt/e/edk2-samurai-out/kernel165')
with tarfile.open(out / 'first-evidence-private.tar.gz') as archive:
    read = lambda name: archive.extractfile('k165-' + name).read().decode()
    log = read('first-runtime/dmesg-private.txt')
    early = read('first-startup/early-trace-private.txt')
    live = read('standard-dpms/display-trace-private.txt')
    early_stats = json.loads(read('first-startup/early-stats.json'))
    live_stats = json.loads(read('standard-dpms/trace-stats.json'))
    firmware = json.loads(read('firmware-log-mmap/result.json'))
    assert firmware['callback_success_observed'] and firmware['ring_drops'] == 0
    assert log.index('DSI firmware stop before PHY: CTRL=0x1f5 -> 0x0') < log.index('boot CTL0:') < log.index('boot CTL0 cleared:')
    assert log.count('DSI firmware stop before PHY:') == 1
    assert not any(word in log for word in ['WARNING:', 'gpu fault:', 'dsi_err_worker', 'frame done timeout', 'kms hw init failed'])
    def loss_free(stats):
        return all(int(re.search(r'^' + re.escape(name) + r':\s*(\d+)', item, re.M)[1]) == 0
                   for item in stats.values() for name in ['overrun', 'commit overrun', 'dropped events'])
    assert loss_free(early_stats) and loss_free(live_stats)
    def events(text):
        rows = []
        for line in text.splitlines():
            match = re.search(r'(\d+\.\d+): (dpu_first_frame_backlight|drm_panel_backlight|dpu_enc_phys_cmd_pp_tx_done): (.*)', line)
            if match:
                rows.append((float(match[1]), match[2], match[3]))
        return sorted(rows)
    tx = None
    initial = []
    for stamp, name, detail in events(early):
        if name == 'dpu_enc_phys_cmd_pp_tx_done':
            tx = stamp
        elif name == 'dpu_first_frame_backlight':
            initial.append(dict(ret=int(re.search(r'ret=(-?\d+)', detail)[1]), tx_seen=tx is not None,
                                tx_to_wait_ms=(stamp-tx)*1000 if tx is not None else None))
    assert initial and all(row['ret'] == 0 and row['tx_seen'] and row['tx_to_wait_ms'] >= 0 for row in initial)
    tx = wait = None
    pending = False
    gates = []
    for stamp, name, detail in events(live):
        if name == 'dpu_enc_phys_cmd_pp_tx_done':
            tx = stamp
        elif name == 'dpu_first_frame_backlight':
            wait = int(re.search(r'ret=(-?\d+)', detail)[1])
        elif 'phase=0' in detail:
            pending = True
            tx = wait = None
        elif 'phase=2' in detail:
            pending = False
            tx = wait = None
        elif 'phase=1' in detail:
            gates.append(dict(pending_seen=pending, tx_seen=tx is not None, wait_ret=wait,
                              tx_to_ready_ms=(stamp-tx)*1000 if tx is not None else None))
            pending = False
    (out / 'wake-gates-private.json').write_text(json.dumps(gates, indent=2) + '\n')
    print(json.dumps(dict(observed_wake_gates=len(gates), gates=gates)))
    assert len(gates) >= 12 and all(row['pending_seen'] and row['tx_seen'] and row['wait_ret'] == 0 and row['tx_to_ready_ms'] >= 0 for row in gates)
report = dict(stage=165, actual_kernel_build=163, firmware_stage=164, same_firmware_second_boot=True,
              firmware_before_exit_callback_success_observed=True, one_shot_dsi_stop_before_ctl=True,
              initial_tx_wait_after_pp_done=initial, early_and_power_traces_loss_free=True,
              wake_gate_count=len(gates), all_observed_gates_after_successful_tx=True,
              gates=gates, physical_startup_white_corruption_feedback_pending=True,
              first164_audio_warning_cause_still_unknown=True, goal_complete=False,
              archive_sha256=hashlib.sha256((out / 'first-evidence-private.tar.gz').read_bytes()).hexdigest())
(ref / 'startup-order-validation.json').write_text(json.dumps(report, indent=2) + '\n')
for name in ['runtime-validation.json', 'boot-timing-validation.json', 'startup-validation.json', 'cycles-validation.json', 'firmware-log-validation.json']:
    (ref / name).write_bytes((out / name).read_bytes())
print(json.dumps(report))
