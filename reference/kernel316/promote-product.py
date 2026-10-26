"""Record a successful installed product and promote its exact package recipes."""
from pathlib import Path
import hashlib,json,shutil,sys
import host

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
install_run=sys.argv[1] if len(sys.argv)>1 else 'r2'
install_file='install-'+install_run+'-validation.json'
evidence='../../reference/kernel316/'+install_file
result=json.loads((HERE/install_file).read_text())
assert result['passed'] and result['transaction']['installed']
artifacts=json.loads((HERE/'package-artifact-validation.json').read_text())
proof=json.loads((host.PRIVATE/'install-proof.json').read_text())
for package in ['libcamera','samurai-camera-config']:
    destination=ROOT/'linux-port/packages'/package
    changed=['APKBUILD','0029-camss-hardware-pipeline.patch'] if package=='libcamera' else ['APKBUILD',*[f'camss-{model}.yaml' for model in ['s5kgw1','imx471','imx319','s5k3m5']]]
    for name in changed:shutil.copyfile(HERE/'recipes'/package/name,destination/name)
    path=destination/'source-lock.json';lock=json.loads(path.read_text())
    lock.update(stage=316,build_stage=316,package_version='99990.7.2-r25' if package=='libcamera' else '0.1.0-r20',
        actual_signed_build_validation='reference/kernel316/package-build-validation.json',
        native_install_validation='reference/kernel316/'+install_file,
        actual_current_payload_validation='reference/kernel316/'+install_file,
        default_hardware_pipeline=True,matched_camss_driver_stage=314,
        standard_af_validation='reference/kernel315/raw-r3-validation.json',
        auto_exposure_af_validation='reference/kernel315/raw-r3-validation.json')
    lock.pop('build_attempt',None)
    for name in changed:lock['source_files_sha256'][name]=hashlib.sha256((destination/name).read_bytes()).hexdigest()
    path.write_text(json.dumps(lock,indent=2)+'\n')
    readme=destination/'README.md';old=readme.read_text()
    readme.write_text('316当前：r25/config-r20与314 CAMSS已部署，默认选择硬件管线。四摄GStreamer NV12、主1080p／前720p、四摄RAW和安装后PipeWire NV12通过；315的双流／AE／AWB／单次AF证据沿用。完整画质校准、多摄同步与连续AF未完成。[316证据](../../../reference/kernel316/README.md)。以下为历史。\n\n'+old)

path=ROOT/'linux-port/camera/deployment-lock.json';lock=json.loads(path.read_text())
# Keep old inventory fingerprints explicitly historical, without rescanning
# unrelated packages/modules merely to refresh this camera transaction.
lock['historical_pre316_package_payloads']=lock.pop('installed_package_payloads',[])
lock['historical_pre316_package_payloads_stage']=278
lock['installed_camera_packages']=result['transaction']['packages']
lock['built_packages']=artifacts['packages']
lock.update(stage=316,framework_version='99990.7.2-r25',configuration_version='0.1.0-r20',
    current_camera_evidence='../../reference/kernel316/README.md',
    final_health_evidence=evidence,
    current_boot_evidence=evidence,
    current_stack_four_camera_regression='../../reference/kernel316/consumer-r5-validation.json',
    current_product_four_camera_regression_evidence='../../reference/kernel316/consumer-r5-validation.json',
    current_product_four_camera_regression_reused_from_stage=316,
    current_product_four_camera_regression_scope='Four cameras individually: GStreamer640x480NV12; main1920x1080/front1280x720; RAW-only four base modes. Installed GStreamer and PipeWire wide NV12640x480.',
    product_camera_path='CAMSS hardware NV12 with AE/AWB; direct RDI RAW; CPU contrast AF',
    default_product_hardware_isp_selected=True,
    inline_userspace_candidate_source='../../reference/kernel316/pipeline/camss_vfe.cpp',
    inline_userspace_candidate_installed=True,
    inline_candidate_build_evidence='../../reference/kernel316/package-build-validation.json',
    candidate_pipeline_source_stage=316,candidate_camss_streams_installed=True,
    current_camss_module_stage=314,current_camss_module_sha256=proof['module_sha256'],
    current_camss_module_note_sha256=proof['module_note_sha256'],
    current_camss_install_evidence=evidence,
    current_camss_original_backup='/var/lib/samurai/k316-install-'+install_run+'/qcom-camss-before.ko',
    full_automatic_hardware_pipeline_ipa_integrated=True,
    full_automatic_hardware_pipeline_ipa_incomplete_scope='Formal image quality, individual EEPROM checksum/binding/application, multi-camera geometry/synchronization, exposure timestamps, continuous AF and deliberate event-loss recovery remain incomplete.',
    gstreamer_hardware_consumer_verified=True,pipewire_hardware_consumer_verified=True,
    goal_status='active_incomplete',current_adaptation_goal_status='active',goal_complete=False,
    in_progress_stage=316,in_progress_installed=True)
lock['kernel_modules']['qcom_camss'].update(sha256=proof['module_sha256'],loaded=True,loaded_note_matches_disk=True)
lock['system_services']={'stage':316,'services':result['transaction']['services'],'evidence':evidence}
if 'maintenance_handoff' in lock:lock['maintenance_handoff'].update(adaptation_goal_status='active',latest_experimental_candidate=316)
path.write_text(json.dumps(lock,indent=2)+'\n')
print('Promoted the installed316 recipes and current deployment evidence; complete adaptation remains active.')
