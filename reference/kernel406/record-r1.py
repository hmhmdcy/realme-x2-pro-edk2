"""Keep the successful transport/recovery and failed mask-only semantics separate."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
r=json.loads((HERE/'runtime-validation.json').read_text());assert r['state']['passed'] and r['state']['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
rows=json.loads((P/'pixel-probe-private.json').read_text());assert all(not row['different_formats'] for row in rows)
for row in rows:
 if row['mode'] in [2,3,5,6,8,9,10]:assert not row['different_from_pair']
 if row['mode'] in [7,12]:assert row['y_range']==[0,0] and row['uv_range']==[128,128]
assert all(row['different_from_pair'] for row in rows if row['mode']==4)
report=dict(stage=406,attempt=1,hardware_frames=52,widths=[640,650],height=480,formats=['NV12','NV21'],transport_and_normal_recovery_passed=True,ltm_enabled_frames=44,gamma_combined_frames=8,reverse_gamma_zero_y0_uv128=True,reverse_gamma_linear_matches_colour_all_bytes=True,combined_gamma_zero_y0_uv128=True,normalized_formats_all_modes_equal=True,
 mask_only_ip_has_two_pixel_shift_after_first_stripe=True,dc_and_ip_configuration_matches_colour_all_bytes=True,la_zero_1024_2048_had_no_pixel_effect=True,
 root_evidence='Actual original FW generates IP_EN bit10 of0x5c60 from stripe+416. Original HAL geometry gates that full-pass IP field with DC and valid quarter pass. DC0/IP1/mask1 therefore expands geometry while hardware IP is off; only this bit differs from DC1.',
 full_ltm_pixel_correctness_passed=False,normal395_restored=True,normal_four_camera_frames=48,observation_completed=True,passed=False)
(HERE/'pixels-validation-r1.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/'runtime-validation-r1.json').write_bytes((HERE/'runtime-validation.json').read_bytes())
text=(HERE.parent/'kernel402/close-current-r2.py').read_text().replace('stage=402','stage=406').replace('k402-gamma-r2','k406-ltm-r1').replace("json.loads((HERE/'pixels-validation.json').read_text())['passed']","json.loads((HERE/'pixels-validation-r1.json').read_text())['observation_completed']")
text=text.replace("assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_gamma_mode').exists()","assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_gamma_mode').exists()\nassert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_ltm_mode').exists()")
text=text.replace("(HERE/'current-state-validation.json')","(HERE/'current-state-validation-r1.json')").replace('hardware_colour_chain_fixed_modes_verified=True,hardware_nv12_nv21_equivalence_verified=True,off_diagonal_and_signed_offset_effect_verified=True,rgb_domain_proof_limited_to_tested_pair=True','ltm_r1_observed_with_mask_only_problem=True')
text=text.replace('gamma_pixel_checks_passed=True,hardware_scope="Corrected opcode1 fixed Gamma diagnostics passed; full automatic calibration still pending"','ltm_pixel_checks_passed=False,combined_gamma_zero_verified=True,hardware_scope="R1 transport and normal restoration verified; mask-only shift and inactive LA remain unresolved"')
(HERE/'close-current-r1.py').write_text(text);print(json.dumps(report,indent=2))
