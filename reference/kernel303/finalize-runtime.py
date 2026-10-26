"""Record actual phone evidence without promoting the opt-in candidate to a product package."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
pre=json.loads((HERE/'current-preflight-validation.json').read_text())
joint=json.loads((HERE/'joint-physical-validation.json').read_text())
ae=[json.loads((HERE/f'ae-r{i}-association-validation.json').read_text()) for i in [1,2]]
assert pre['same_298_guard'] and joint['passed'] and all(r['passed'] for r in ae)
assert sum(r['frames'] for r in ae)==960 and sum(r['aligned_physical_domains'] for r in ae)==81
source=(HERE/'ae-smoke.cpp').read_text().replace('int32_t(epoch ? 30000 : 5000)','int32_t(5000)').replace('epoch ? 16.0f : 2.0f','2.0f')
r1=json.loads((HERE/'runtime-tools-r1-validation.json').read_text())
assert hashlib.sha256(source.encode()).hexdigest()==r1['applications']['ae']['source_sha256']
(HERE/'ae-smoke-r1.cpp').write_text(source)
shutil.copyfile(HERE/'runtime-tools-validation.json',HERE/'runtime-tools-r2-validation.json')
captures=[json.loads((HERE/f'{kind}-{run}-capture-validation.json').read_text()) for kind,run in [('joint','r1'),('ae','r1'),('ae','r2')]]
assert all(c['passed'] and c['before']==c['after'] and not any(c['fault_delta'].values()) for c in captures)
report=json.loads((HERE/'checkpoint-validation.json').read_text())
report.update(phone_reachable=True,phone_ssh_attempts_initially_failed=2,phone_current_boot_not_reverified=False,
              actual_kernel_build=298,hardware_experiments=3,real_hardware_frames=1440,
              joint_changes=18,joint_control_writes=36,hardware_ae_frames=960,
              hardware_ae_effective_revisions=17,hardware_ae_real_control_writes=34,
              useful_physical_ae_domains=81,aligned_physical_ae_domains=81,
              isolated_ipc_pending=False,joint_sensor_latch_pending=False,
              joint_latch_scope='current IMX319 mode; no mixed-EV transient in BHIST and four Y quarters; not pixelwise proof',
              hardware_ae_pending=True,hardware_ae_current_mode_low_light_bound_verified=True,
              hardware_ae_target_convergence_not_yet_verified=True,
              all_graph_controls_pm_restored=True,new_recorded_faults=0,taint=0,
              not_installed=True,product_camera_path='RAW plus CPU ISP',
              usb_port_reset_error=True,strict_original_key_wifi_transport=True)
(HERE/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
notes=json.loads((HERE/'preparation-notes.json').read_text())
notes.update(gain_analysis_six_significant_digit_log_tolerance_fixed=True,
             unchanged_control_member_writes_in_automatic_pairs_accounted=True,
             initial_loose_target_threshold_replaced_with_strict_target_or_explicit_sensor_bound=True,
             no_device_fix_required_for_analysis_issues=True)
(HERE/'preparation-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='shared_libipa_source_sha256'},indent=2))
