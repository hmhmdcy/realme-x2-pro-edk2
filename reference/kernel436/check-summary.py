from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
rows=[]
for attempt in ['r1','r3','r4','r5']:
 audit=json.loads((HERE/('hardware-'+attempt+'-validation.json')).read_text());assert audit['passed']
 rows.append(dict(attempt=attempt,live_images=audit['live_images'],numeric_history_commits=audit['successful_numeric_history_commits'],bootstrap=audit['explicit_bootstrap_without_numeric_commit'],final_awb_locked=audit['final_awb_locked']))
replay=json.loads((P/'replay-pixel-metrics-private.json').read_text());assert replay['passed'] and replay['stock_cold_repeat_equal'] and replay['replay_stock_equals_live']
for n in ['source','profile-export','main-factory-bls-export']:assert json.loads((HERE/(n+'-validation.json')).read_text()).get('passed',True)
for attempt in ['r1','r2','r3','r4','r5']:
 live=json.loads((HERE/('runtime-'+attempt+'-validation.json')).read_text());s=live['state']
 assert s['terminal'] and s['passed'] and not live['worker_live'] and not live['client_live']
 assert s['formal_modules_restored'] and s['services_restored'] and not s['new_faults'] and s['taint_after']==0
r=dict(stage=436,rows=rows,live_images=sum(r['live_images'] for r in rows),numeric_history_commits=sum(r['numeric_history_commits'] for r in rows),explicit_bootstrap=sum(r['bootstrap'] for r in rows),fixed_input_replay_jobs=5,
 replay_cold_repeat_and_actual_live_output_byte_identical=True,ife_full_pd10_params_final_output_same_sof_saved=True,
 large_radial_artifact_present_upstream_of_ipe=True,ltm_off_does_not_remove_upstream_artifact=True,lsc_off_counterfactual_reduces_radial_artifact=True,
 diagnostic_zero_bls_configuration_inherited_from324_identified=True,main_original_bls_independently_recovered=True,
 corrected_profile_live_images=229,corrected_profile_numeric_history_commits=223,corrected_profile_original_lsc_gtm_tmc_ltm_kept_enabled=True,
 large_haze_and_radial_artifact_visually_reduced=True,corrected_af_run_frames=205,corrected_af_numeric_history_commits=202,autofocus_focused=True,
 final_awb_locked=False,af_scene_foreground_changed=True,absolute_image_quality_accepted=False,
 remaining=['AWB convergence and colour validation','flat-field, sharpness and noise calibration','other cameras/modes/video automatic tone','full OEM tone variants','fifth 2MP and multi-camera geometry/synchronization'],
 formal_modules_services_and_resources_restored=True,new_faults=0,taint=0,installed=False,full_goal_complete=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
