from pathlib import Path
import json
import statistics

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel141'
a = json.loads((ref / 'startup-evidence-validation.json').read_text())
b = json.loads((ref / 'timeout-trace-validation.json').read_text())
assert a['same_boot'] and b['same_current_boot_verified']
assert len(a['startup_dpu_timeouts']) == len(b['timeout_trace_seconds']) == 4
assert b['timeout_event_body'] == ['id=35, event=2'] * 4
pairs = [dict(dmesg_seconds=x['dmesg_seconds'], trace_seconds=y,
              delta_seconds=round(x['dmesg_seconds'] - y, 6))
         for x, y in zip(a['startup_dpu_timeouts'], b['timeout_trace_seconds'])]
offset = statistics.median(p['delta_seconds'] for p in pairs)
spread = max(p['delta_seconds'] for p in pairs) - min(p['delta_seconds'] for p in pairs)
assert spread < 0.00001
source = Path('/home/cy122/pmos-samurai-kernel136/kernel/drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.c').read_text()
assert 'trace_dpu_enc_frame_done_timeout(DRMID(drm_enc), event);\n\tDPU_ERROR_ENC_RATELIMITED(dpu_enc, "frame done timeout\\n");' in source
report = dict(stage=141, only_archived_original140_boot=True,
    paired_same_function_timeout_events=4, trace_call_immediately_precedes_error_print=True,
    paired_events=pairs, observed_median_dmesg_minus_mono_seconds=offset,
    observed_pair_spread_microseconds=round(spread * 1000000, 3),
    calibration_supported_interval_trace_seconds=[min(b['timeout_trace_seconds']), max(b['timeout_trace_seconds'])],
    full_clock_identity_proven=False, all_startup_events_retained=False,
    offset_must_not_be_reused_for_new_or136_boot=True, goal_complete=False)
(ref / 'original140-clock-calibration-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
