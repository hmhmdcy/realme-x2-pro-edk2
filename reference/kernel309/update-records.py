"""Update the two current locks from completed stage309 results; no device actions."""
from pathlib import Path
import json, shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel309')
source=json.loads((HERE/'source-state.json').read_text())
capture=json.loads((HERE/'capture-validation.json').read_text())
install=json.JSONDecoder().raw_decode((PRIVATE/'install-observation.txt').read_text().lstrip())[0]
assert install['terminal'] and install['summary']['passed'] and capture['passed']
assert capture['health']['camss_sha256']==source['module_sha256']==install['summary']['module_sha256']
install['worker_live']=False
install['original_module_backup']='/var/lib/samurai/k309-module-install-r1/qcom-camss-before.ko'
install['module_note_sha256']=source['module_note_sha256']
(HERE/'install-validation.json').write_text(json.dumps(install,indent=2)+'\n')
health=dict(stage=309, **capture['health'], resources_restored=capture['resources_restored'],
            evidence='capture-validation.json', whole_system_healthy=False,
            scope='Camera resources and targeted fault deltas; existing GPU/modem/SSC issues remain open')
(HERE/'final-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')

for relative,prefix in [('linux-port/camera/kernel/source-lock.json','../../../'),
                        ('linux-port/camera/deployment-lock.json','../../')]:
    path=ROOT/relative
    archive=ROOT/'archive/camera-before309-2026-10-19'/relative
    if not archive.exists():
        archive.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,archive)
    data=json.loads(path.read_text())
    evidence=lambda name:prefix+'reference/kernel309/'+name
    data.update(stage=309, maintained_branch=source['branch'], maintained_commit=source['commit'],
        source_worktree_branch=source['branch'],source_worktree_commit=source['commit'],
        kernel_source_branch=source['branch'],kernel_source_commit=source['commit'],
        candidate_kernel_source_branch=source['branch'],candidate_kernel_source_commit=source['commit'],
        source_worktree=source['tree'],candidate_source_clean=True,
        candidate_source_evidence=evidence('source-state.json'),
        previous_lock_archive=prefix+'archive/camera-before309-2026-10-19/'+relative,
        current_camss_module_stage=309,current_camss_module_sha256=source['module_sha256'],
        current_camss_module_note_sha256=source['module_note_sha256'],
        current_camss_install_evidence=evidence('install-validation.json'),
        current_camss_original_backup=install['original_module_backup'],
        source_and_deployment_split='298 Image; 305 S5K3M5 module; 309 CAMSS module; remaining776 baseline reused',
        only_s5k3m5_module_changed=False,other777_modules_preserved=False,
        other776_modules_preserved=True,unchanged_modules_validation_reused_from_stage=305,
        full_kernel_rebuild_with309_camss_pending=True,
        module_build_evidence=evidence('kernel-build-validation.json'),
        sensor_module_build_evidence=prefix+'reference/kernel305/kernel-build-validation.json',
        current_camera_evidence=evidence('README.md'),final_health_evidence=evidence('final-health-validation.json'),
        current_boot_evidence=evidence('capture-validation.json'),
        current_product_four_camera_regression_frames=16,
        current_product_four_camera_regression_evidence=evidence('capture-validation.json'),
        current_product_four_camera_regression_scope='Run3: four RAW plus CPU ISP frames per camera on CAMSS309; installer adds four front frames',
        candidate_hardware_ae_real_frames_total=1599,
        candidate_ae_target_convergence_verified=True,
        experimental_hardware_ae_scope='IMX319 and S5K3M5 current modes: run4 joint AE/AWB target reached in present scene; run2 low-light upper bound preserved; main/front AE timing pending',
        candidate_ae_evidence_from_prior_boot=True,
        hardware_awb_implemented=True,rgb_statistics_hardware_implemented=True,
        hardware_awb_scope='Experimental four-camera current modes, nine successful streams in stage309; algorithm lock does not establish calibrated white point',
        hardware_awb_evidence=evidence('capture-validation.json'),
        hardware_awb_stage309_frames=355,hardware_awb_stage309_parameter_updates=130,
        joint_ae_awb_stage309_frames=159,joint_ae_awb_evidence=evidence('capture-validation.json'),
        candidate_pipeline_generic_source_unchanged=False,candidate_pipeline_source_stage=308,
        inline_userspace_candidate_source=prefix+'reference/kernel308/pipeline/camss_vfe.cpp',
        inline_candidate_build_evidence=prefix+'reference/kernel308/build-validation.json',
        experimental_ipa_source_evidence=prefix+'reference/kernel308/source-state.json',
        rgb_statistics_source_evidence=prefix+'reference/kernel307/rgb-capture-validation.json',
        statistics_ready_for_automatic_exposure=True,
        factory_main_front_bls_evidence=evidence('factory-bls-validation.json'),
        receiver_clock_evidence=evidence('source-state.json'),
        current_adaptation_goal_status='active',goal_complete=False,whole_system_healthy=False,
        current_boot_tele_hardware_frames=1319,current_boot_tele_ae_frames=561)
    for key in ['current_boot_tele_ae_effective_revisions','current_boot_tele_ae_control_writes']:
        if key in data:data[key+'_stage306']=data.pop(key)
    data['experimental_hardware_ae_verified_frames_by_sensor']={
        'imx319_prior_boot':960,'s5k3m5_current_boot_stage306':480,
        'imx319_current_boot_joint_stage309':78,'s5k3m5_current_boot_joint_stage309':81}
    data['experimental_sensor_profiles']={
        'imx319':dict(profile=evidence('imx319.yaml'),timing=prefix+'reference/kernel302/runtime-association-validation.json',boot_scope='current305; measured delay retained from302',joint=evidence('capture-validation.json')),
        's5k3m5':dict(profile=evidence('s5k3m5.yaml'),timing=prefix+'reference/kernel306/delay-analysis-r1-validation.json',boot_scope='current305',joint=evidence('capture-validation.json')),
        's5kgw1':dict(profile=evidence('s5kgw1.yaml'),control_delay_measured=False,scope='4608x3456 AWB, OEM common IFE reference; per-unit calibration pending'),
        'imx471':dict(profile=evidence('imx471.yaml'),control_delay_measured=False,scope='2304x1728 AWB, OEM common IFE reference; per-unit calibration pending')}
    modules=data.get('deployed_camera_modules',data.get('kernel_modules'))
    modules['qcom_camss'].update(sha256=source['module_sha256'],loaded=True,loaded_note_matches_disk=True,intree='Y',parameters={})
    # The deployment table inherited a pre305 hash despite its current_sensor_module field.
    modules['s5k3m5']['sha256']=data['current_sensor_module_sha256']
    if 'system_services' in data:data['system_services']['historical_stage298_identity_not_current_pids']=True
    if 'spectra_hardware_image_processing_supported_scope' in data:
        data['spectra_hardware_image_processing_supported_scope']='Experimental four-camera current-mode hardware RGB/BHIST plus AWB; wide/tele joint AE/AWB reaches target in run4. Product RAW plus CPU ISP; full IQ, additional modes and main/front control timing remain incomplete.'
    if 'physical_hardware_isp_image_validation_pending_scope' in data:
        data['physical_hardware_isp_image_validation_pending_scope']='Four current modes produce experimental hardware output; full IQ and additional modes pending'
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
runtime=HERE/'prepare-runtime.py'
text=runtime.read_text()
if 'factory=json.loads' in text:
    text=text[:text.index('factory=json.loads')]+text[text.index("stage=SDK/'private/camss309-runtime'"):]
    runtime.write_text(text)
print('Updated current source/deployment records from terminal results; unchanged baselines reused.')
