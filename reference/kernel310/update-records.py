"""Update current mode profiles and experiment results; deployment stays309."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
joint=json.loads((HERE/'joint-r1-validation.json').read_text())
health=json.loads((HERE/'final-health-validation.json').read_text())
if not joint['passed'] or not health['passed']:raise RuntimeError('Inspect the incomplete result before updating current records')
for rel,prefix in [('linux-port/camera/kernel/source-lock.json','../../../'),('linux-port/camera/deployment-lock.json','../../')]:
    path=ROOT/rel;data=json.loads(path.read_text());evidence=lambda name:prefix+'reference/kernel310/'+name
    data.update(stage=310,current_camera_evidence=evidence('README.md'),
        final_health_evidence=evidence('final-health-validation.json'),current_boot_evidence=evidence('joint-r1-validation.json'),
        candidate_hardware_ae_real_frames_total=1908,
        experimental_hardware_ae_scope='All four current modes: low/high initial EV joint AE/AWB, eight streams reached target in310. Prior309 dark-scene upper-bound results preserved; dynamic illumination and additional modes pending.',
        experimental_hardware_ae_verified_frames_by_sensor={
            'imx319_prior_boot':960,'s5k3m5_current_boot_stage306':480,
            'imx319_current_boot_joint_stage309':78,'s5k3m5_current_boot_joint_stage309':81,
            's5kgw1_current_boot_joint_stage310':76,'imx471_current_boot_joint_stage310':81,
            'imx319_current_boot_joint_stage310':76,'s5k3m5_current_boot_joint_stage310':76},
        hardware_awb_scope='Experimental four current modes; eight joint streams reached algorithm stability from opposing initial gains in310; not formal white-point or colour calibration',
        hardware_awb_evidence=evidence('joint-r1-validation.json'),joint_ae_awb_evidence=evidence('joint-r1-validation.json'),
        joint_ae_awb_stage310_frames=309,joint_ae_awb_stage310_wb_updates=114,
        main_front_control_timing_evidence=evidence('delay-r1-validation.json'),
        current_boot_tele_hardware_frames=1395,current_boot_tele_ae_frames=637,
        factory_main_front_bls_evidence=prefix+'reference/kernel309/factory-bls-validation.json',
        current_product_four_camera_regression_reused_from_stage=309,
        full_automatic_hardware_pipeline_ipa_integrated=False,
        full_automatic_hardware_pipeline_ipa_incomplete_scope='Four mode-scoped joint AE/AWB experiments implemented; product integration, runtime mode controls, extra modes and full IQ remain incomplete',
        goal_complete=False,current_adaptation_goal_status='active',whole_system_healthy=False)
    for model in ['s5kgw1','imx471','imx319','s5k3m5']:
        profile=data['experimental_sensor_profiles'][model]
        profile.update(profile=evidence(model+'.yaml'),joint=evidence('joint-r1-validation.json'),boot_scope='current305')
        if model in ['s5kgw1','imx471']:
            profile.update(control_delay_measured=True,exposure_delay=2,gain_delay=2,
                           timing=evidence('delay-r1-validation.json'),scope='Current binned mode; measured controls plus OEM common IFE reference; individual IQ calibration pending')
    if 'spectra_hardware_image_processing_supported_scope' in data:
        data['spectra_hardware_image_processing_supported_scope']='Four current modes: hardware RGB/BHIST, joint AE/AWB from low/high initial EV, measured two-frame main/front controls. Product RAW plus CPU ISP; full IQ, extra modes and product integration pending.'
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
print('Current experiment records now310; kernel source and deployed CAMSS remain309.')
