"""Analyze delivered timestamp/sequence timing without hiding the failed phase test."""
from pathlib import Path
import hashlib,json,statistics
import host
R=Path(__file__).resolve().parent
q=host.ssh('cat /var/lib/samurai/k273-main-manual-r1/stdout-private.json',timeout=25)
(host.PRIVATE/'main-manual-pairs-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);frames=d['frames']
assert len(frames)==66 and all(f['sequence']==f['raw_sequence'] and f['timestamp_ns']==f['raw_timestamp_ns'] for f in frames)
periods=[(b['timestamp_ns']-a['timestamp_ns'])/(b['sequence']-a['sequence']) for a,b in zip(frames,frames[1:])]
period=statistics.median(periods);expected=17824*3584/1920000000*1e9
assert abs(period-expected)/expected<.001
manual=json.loads((R/'main-manual-r1-validation.json').read_text());assert manual['exit']==1 and manual['health']['passed']
samples=[manual['phases'][i]['raw_mean'] for i in range(5)]
assert samples==sorted(samples) and len(set(samples))==5
ae=json.loads((R/'main-ae-validation.json').read_text());assert ae['passed']
report=dict(stage=273,paired_frames_before_failure=66,raw_rgb_sequence_and_timestamp_pairs_match=True,
 median_period_per_sensor_sequence_ns=period,expected_period_ns=expected,observed_fps=1e9/period,
 inferred_vt_pixel_rate=17824*3584*1e9/period,vt_candidate_agrees_with_observed_frame_timing=True,
 frame_timing_scope='mode2 at current default FLL; other frame lengths/exposure delay remain unverified',
 manual_response_at_2ms_8ms_32ms_and_gain1_1p5_2_observed=True,
 full96_frame_control_phase_validation_passed=False,failed_at_4x_gain_phase=True,control_transition_or_metadata_issue_unresolved=True,
 ordinary_600_frame_cpu_jpeg_completed=True,ordinary_jpeg_pts_span_seconds=(ae['runs'][0]['last_pts']-ae['runs'][0]['first_pts'])/1e9,
 optical_review=dict(early_frame=36,late_frame=600,both_show_real_scene=True,late_frame_brighter=True,
 scene_detail_visible_but_soft=True,autofocus_not_implemented=True,colour_noise_and_geometry_not_calibrated=True),
 software_isp_cpu=True,spectra_image_processing_supported=False,private_pixels_not_published=True)
(R/'main-evidence-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
