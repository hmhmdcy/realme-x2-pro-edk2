from pathlib import Path
import hashlib, json, re, tarfile

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel163')
out = Path('/mnt/e/edk2-samurai-out/kernel163')
with tarfile.open(out / 'first-evidence-private.tar.gz') as archive:
    read = lambda name: archive.extractfile('k163-' + name).read().decode()
    log = read('first-runtime/dmesg-private.txt')
    early = read('first-startup/early-trace-private.txt')
    early_stats = json.loads(read('first-startup/early-stats.json'))
    ready = json.loads(read('first-startup/ready.json'))
    assert log.count('SOFEF03F boot reset asserted before display takeover') == 1
    assert 'SOFEF03F boot reset unavailable' not in log
    assert log.index('SOFEF03F boot reset asserted') < log.index('DSI firmware stop before PHY:') < log.index('boot CTL0:') < log.index('boot CTL0 cleared:')
    assert log.count('DSI firmware stop before PHY:') == 1
    def stamp(pattern):
        return float(re.search(r'^\[\s*(\d+\.\d+)\].*' + pattern, log, re.M)[1])
    reset = stamp('SOFEF03F boot reset asserted')
    first_smmu = stamp('arm-smmu .*probing hardware configuration')
    apps_smmu = stamp('arm-smmu 15000000.iommu: probing hardware configuration')
    def events(text):
        result = []
        for line in text.splitlines():
            match = re.search(r'(\d+\.\d+): (dpu_first_frame_backlight|drm_panel_backlight|dpu_enc_phys_cmd_pp_tx_done): (.*)', line)
            if match:
                result.append((float(match[1]), match[2], match[3]))
        return sorted(result)
    tx = None
    waits = []
    for instant, name, detail in events(early):
        if name == 'dpu_enc_phys_cmd_pp_tx_done':
            tx = instant
        elif name == 'dpu_first_frame_backlight':
            waits.append(dict(ret=int(re.search(r'ret=(-?\d+)', detail)[1]), tx_done_seen=tx is not None,
                              tx_to_wait_ms=(instant-tx)*1000 if tx is not None else None))
    assert waits and all(row['ret'] == 0 and row['tx_done_seen'] and row['tx_to_wait_ms'] >= 0 for row in waits)
    loss_free = all(int(re.search(r'^' + re.escape(name) + r':\s*(\d+)', item, re.M)[1]) == 0
                    for item in early_stats.values() for name in ['overrun', 'commit overrun', 'dropped events'])
    assert loss_free
    first_gate_count = len(json.loads((out / 'first-cycle-gates-private.json').read_text()))
    with tarfile.open(out / 'dpms-restoration-private.tar.gz') as repeated:
        live = repeated.extractfile('k163-dpms-restoration-wait/display-trace-private.txt').read().decode()
        repeated_stats = json.loads(repeated.extractfile('k163-dpms-restoration-wait/trace-stats.json').read())
    repeated_loss_free = all(int(re.search(r'^' + re.escape(name) + r':\s*(\d+)', item, re.M)[1]) == 0
                             for item in repeated_stats.values() for name in ['overrun', 'commit overrun', 'dropped events'])
    assert repeated_loss_free
    pending = False
    tx = wait = None
    gates = []
    for instant, name, detail in events(live):
        if name == 'dpu_enc_phys_cmd_pp_tx_done':
            tx = instant
        elif name == 'dpu_first_frame_backlight':
            wait = (instant, int(re.search(r'ret=(-?\d+)', detail)[1]))
        elif 'phase=0' in detail:
            pending = True
            tx = wait = None
        elif 'phase=2' in detail:
            pending = False
            tx = wait = None
        elif 'phase=1' in detail:
            gates.append(dict(pending_seen=pending, tx_done_seen=tx is not None,
                              wait_ret=wait[1] if wait else None,
                              tx_to_ready_ms=(instant-tx)*1000 if tx is not None else None))
            pending = False
    (out / 'final-restoration-gates-private.json').write_text(json.dumps(gates, indent=2) + '\n')
    assert len(gates) == 12 and all(row['pending_seen'] and row['tx_done_seen'] and row['wait_ret'] == 0 and row['tx_to_ready_ms'] >= 0 for row in gates)
report = dict(stage=163, actual_kernel_build=163, early_reset_asserted=True,
              reset_uptime=reset, first_smmu_probe_uptime=first_smmu, apps_smmu_probe_uptime=apps_smmu,
              reset_before_smmu=reset < first_smmu, reset_before_native_ctl_takeover=True,
              controller_registration_order_did_not_guarantee_probe_order=True,
              initial_power_capture_wake_gates=first_gate_count,
              final_restore_wait_added_and_capture_repeated=True,
              repeated_power_trace_loss_free=repeated_loss_free,
              first_frame_waits=waits, early_trace_loss_free=loss_free,
              record_start_uptime=float(ready['uptime']), wake_gate_count=len(gates), gates=gates,
              all_wake_ready_after_successful_tx=True, physical_startup_feedback_pending=True,
              goal_complete=False, archive_sha256=hashlib.sha256((out / 'first-evidence-private.tar.gz').read_bytes()).hexdigest())
(ref / 'startup-order-validation.json').write_text(json.dumps(report, indent=2) + '\n')
for name in ['startup-validation.json', 'runtime-validation.json', 'boot-timing-validation.json', 'cycles-validation.json', 'dpms-restoration-validation.json', 'steady-validation.json']:
    (ref / name).write_bytes((out / name).read_bytes())
print(json.dumps(report))
