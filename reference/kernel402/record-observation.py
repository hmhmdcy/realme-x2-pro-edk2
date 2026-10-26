"""Separate successful transport/recovery from the failed Gamma pixel result."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel402')
d=json.loads((P/'pixel-probe-private.json').read_text());r=json.loads((HERE/'runtime-validation.json').read_text());s=r['state']
assert s['passed'] and s['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
assert d['generic20_vs_previous_generic0_different_bytes']==0 and d['formats'][0]['nv12_nv21_normalized_different']==d['formats'][1]['nv12_nv21_normalized_different']==0
report=dict(stage=402,hardware_execution=True,frames=20,formats=['NV12','NV21'],width=640,height=480,host_crc_verified=True,synthetic_patch_input_and_canary_checked_by_client=True,generic20_conversion_matches400_all460800_bytes=True,generic20_nv12_nv21_normalized_equal=True,
 gamma_pixel_checks_passed=False,gamma_identity_max_abs_byte_error=d['identity_gamma_vs_pair_max_abs'],gamma_zero_lut_produced_black=False,gamma_constant_lut_produced_constant=False,gamma_normalized_format_mismatch_bytes=[row['nv12_nv21_normalized_different'] for row in d['formats'][2:]],gamma_half_twice_error_max={p:v['max_abs_twice_error'] for p,v in d['half_about_zero'].items()},
 gamma_problem_scope='Enabling Gamma produces incorrect, spatially varying output even for zero and constant LUTs; transport completion is not image correctness. Cause not yet established. LUT load/selection and downstream command handling are next hypotheses, not proven diagnoses.',
 transport_and_resource_recovery_passed=True,normal395_restored=True,normal_four_camera_frames=48,new_faults=s['new_unexpected_fault_count'],candidate_permanently_installed=False,observation_completed=True,passed=False)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n')
text=(HERE.parent/'kernel400/close-current.py').read_text().replace('stage=400','stage=402').replace('k400-chain-r1','k402-gamma-r1')
text=text.replace("and json.loads((HERE/'pixels-validation.json').read_text())['passed']","and json.loads((HERE/'pixels-validation.json').read_text())['observation_completed']")
text=text.replace("assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_cc_mode').exists()","assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_cc_mode').exists()\nassert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_gamma_mode').exists()")
text=text.replace('hardware_colour_chain_fixed_modes_verified=True,hardware_nv12_nv21_equivalence_verified=True,off_diagonal_and_signed_offset_effect_verified=True,rgb_domain_proof_limited_to_tested_pair=True','generic20_conversion_pair_verified=True,gamma_pixel_checks_passed=False,hardware_scope="Gamma pixels failed; successful transport and normal recovery only"')
(HERE/'close-current.py').write_text(text)
source=json.loads((HERE/'source-state.json').read_text());source['temporary_adapter_source_restored']=True;(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
print(json.dumps(report,indent=2))
