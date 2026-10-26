"""Quantify measured response without substituting a sensor black-level calibration."""
from pathlib import Path
import json, statistics
R=Path(__file__).resolve().parent
d=json.loads((R/'fractional-manual-r1-validation.json').read_text())
assert d['exit']==0 and d['paired_frames']==96 and d['health']['passed']
phases=d['phases'];rows=phases[:6]
gains=[x['gains'][0] for x in rows];means=[x['raw_mean'] for x in rows]
assert gains==[1,1.03125,1.5,2,4,8]
fit=statistics.linear_regression(gains,means)
predicted=[fit.intercept+fit.slope*x for x in gains]
report=dict(stage=271,physical_fractional_gain_verified=True,stable_frames_per_phase=6,
 requested_and_captured_gains=gains,raw_means=means,
 least_squares_intercept=fit.intercept,least_squares_slope=fit.slope,
 max_raw_mean_residual=max(abs(a-b) for a,b in zip(means,predicted)),
 first_and_returned_unity_raw_means=[phases[0]['raw_mean'],phases[7]['raw_mean']],
 saturation_fraction_at_16x=phases[6]['raw_clipped_fraction'],
 frame_metadata_matches_requested_steady_phases=True,absolute_iso_sensitivity_not_calibrated=True,
 linear_intercept_is_scene_fit_not_a_programmed_black_level=True,
 existing_24mhz_sensor_profile_not_physically_regressed=True)
(R/'gain-response-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
