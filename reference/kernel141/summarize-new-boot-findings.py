from pathlib import Path
import hashlib
import json
import re
import statistics
import tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel141'
out = Path('/mnt/e/edk2-samurai-out/kernel141')
with tarfile.open(out / 'reboot140-startup-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] == (out / 'embedded-boot-id-private.txt').read_bytes()
events = json.loads((out / 'parsed-startup-events-private.json').read_text())
text = data['dmesg-final-private.txt'].decode()
tx = re.search(r'TX DMA diagnostic: state=(\d+) qmi=(\d+) channel=(\d+) device=(\d+) sg=(\d+) config_sg=(\d+) len=(\d+)', text)
assert tx
tx_fields = dict(zip(['state', 'qmi', 'channel', 'device', 'sg', 'config_sg', 'len'], map(int, tx.groups())))
source = Path('/home/cy122/pmos-samurai-kernel136/kernel/drivers/slimbus/qcom-ngd-ctrl.c').read_text()
assert 'QCOM_SLIM_NGD_CTRL_AWAKE,\n\tQCOM_SLIM_NGD_CTRL_IDLE,\n\tQCOM_SLIM_NGD_CTRL_ASLEEP,\n\tQCOM_SLIM_NGD_CTRL_DOWN,' in source
resume = source[source.index('static int qcom_slim_ngd_runtime_resume('):source.index('static int qcom_slim_ngd_enable(')]
assert 'ret = qcom_slim_ngd_power_up(ctrl);' in resume and resume.rstrip().endswith('return 0;\n}')
timeout_rows = []
for timeout in [e for e in events if e['name'] == 'dpu_enc_frame_done_timeout']:
    stamp = timeout['seconds']
    arm = next(e for e in reversed(events) if e['seconds'] < stamp and e['name'] == 'dpu_enc_frame_watchdog' and 'action=arm ' in e['body'])
    pp = next(e for e in events if e['seconds'] > stamp and e['name'] == 'dpu_enc_phys_cmd_pp_tx_done')
    assert not any(e['name'] == 'dpu_enc_kickoff' for e in events if arm['seconds'] < e['seconds'] < pp['seconds'])
    vblanks = [e for e in events if arm['seconds'] < e['seconds'] < pp['seconds'] and e['name'] == 'dpu_crtc_vblank_cb']
    timeout_rows.append(dict(trace_seconds=stamp, configured_timeout_ms=83,
        arm_to_timeout_ms=round((stamp - arm['seconds']) * 1000, 3),
        arm_to_pp_done_callback_ms=round((pp['seconds'] - arm['seconds']) * 1000, 3),
        timeout_to_pp_done_callback_ms=round((pp['seconds'] - stamp) * 1000, 3),
        recorded_vblank_callbacks_before_pp_done=len(vblanks),
        no_intervening_kickoff_before_pp_done=True, resource_control_state_at_kickoff='ON'))
last_arm = None
latencies = []
for e in events:
    if e['name'] != 'dpu_enc_frame_watchdog':
        continue
    if 'action=arm ' in e['body']:
        last_arm = e['seconds']
    elif 'action=complete ' in e['body'] and last_arm is not None:
        latencies.append((e['seconds'] - last_arm) * 1000)
        last_arm = None
report = dict(stage=141, kernel_build=140, same_new_boot_verified=True,
    tx_first_failure=tx_fields, state_3_means_controller_DOWN=True,
    hw_wakeup_failure_during_SSR_precedes_first_prepare_failure=True,
    pdr_listener_timeouts_present=text.count('register listener txn wait failed: -110'),
    rejected_suspend_diagnostic_present='NGD suspend rejected:' in text,
    bam_allocation_failure_diagnostic_present='BAM DMA diagnostic:' in text,
    allocation_policy_failure_not_supported_by_this_diagnostic=True,
    runtime_resume_currently_discards_power_up_error=True,
    runtime_resume_error_fix_not_applied=True,
    recovery_PM_error_semantics_must_be_checked_before_changing_return=True,
    two_later_display_timeouts_have_loss_free_trace=True, timeout_rows=timeout_rows,
    matched_watchdog_completions=len(latencies),
    median_watchdog_completion_ms=round(statistics.median(latencies), 3),
    max_watchdog_completion_ms=round(max(latencies), 3),
    irq_entry_exit_and_cpu_idle_not_in_this_capture=True,
    cpu_irq_delay_or_hardware_delay_not_yet_distinguished=True,
    late_pp_callback_not_proof_of_false_watchdog=True,
    baseline132_gpu_mapping_trace_not_present=True,
    standalone_gpu_ccu_fault_not_retested=True, charging_control_not_accepted=True,
    goal_complete=False)
(ref / 'new-boot-findings-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
