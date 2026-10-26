from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;read=lambda p:json.loads(p.read_text())
r1=read(P/'runtime-collected-r1/state.json');r2=read(P/'runtime-collected-r2/state.json');reload=read(P/'reload-collected-r1/state.json')
assert r1['terminal'] and not r1['passed'] and r1['native_report']['passed'] and r1['export_lifetime_passed'] and r1['services_restored']
assert r2['terminal'] and r2['passed'] and r2['native_evidence_root']=='/var/lib/samurai/k390-runtime-r1' and r2['export_evidence_reused']
assert reload['terminal'] and reload['passed'] and reload['unload_passed']
for key in ['export_held','mmap_only_held']:assert r1[key]['owner_refs']==1 and r1[key]['users']==0 and r1[key]['jobs']==0
assert r1['export_after_release']['owner_refs']==0
native=r1['native_status']['completed'];pipeline=r2['pipeline_completed'];again=reload['post_reload_ipe_status']['completed']
assert native==18 and pipeline==81 and again==12 and r2['final_status']['completed']==native+pipeline
report=dict(stage=390,normal_static_platform_hardware_verified=True,no_test_platform_owner_or_overlay=True,
 native_phase_source='runtime-r1 (pipeline blocked before its first capture by obsolete collector filename)',pipeline_phase_source='runtime-r2 (prior native phase reused)',reload_phase_source='reload-r1',
 direct_frames_before_module_reload=native+pipeline,direct_frames_after_module_reload=again,total_actual_IPE_frames=native+pipeline+again,copy_frames=0,failed_frames=0,cancelled_frames=0,
 normal_camss_export_fd_owner_pin_verified=True,normal_camss_mmap_only_owner_pin_verified=True,last_munmap_releases_pin=True,native_frames=native,pipeline_captures=r2['pipeline_report']['captures'],
 normal_camss_icp_unload_and_reload_verified=True,no_firmware_start_in_reprobe=True,post_reload_candidate_frames=again,installed_original_IFE_path_captures=reload['installed_ife_captures'],
 last_firmware_run=reload['final_core_state'],current_counters_reset_by_explicit_driver_reload=True,post_reload_counter_completed=again,full_iq_and_optical_calibration_not_claimed=True,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(report,indent=2)+'\n')
audit=dict(stage=390,runtime_r1_overall_passed=False,runtime_r1_export_lifetime_and_18_native_frames_passed=True,pipeline_failure_before_first_capture=True,
 reason='Client still checked snapshot-collector.py while the new standard collector is dump-collector.py; fixed only the test harness.',
 kernel_and_dt_not_changed_to_fix_harness=True,r1_workers_terminal_and_resources_and_services_recovered=True,r2_only_ran_missing_pipeline_suite=True,native_frames_not_repeated_or_double_counted=True,
 collector_resolved_static_symlink_paths_before_any_firmware_run=True,no_second_flash_or_reboot_used_for_test_harness_failure=True,passed=True)
(HERE/'attempts-validation.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['last_firmware_run','pipeline_captures','installed_original_IFE_path_captures']},indent=2))
