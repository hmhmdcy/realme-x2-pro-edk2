from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for leaf in ['source','platform','binding','artifact','intree-build','dt-build','deployment-package','current-state']:assert read(HERE/(leaf+'-validation.json'))['passed']
boot=read(HERE/'build-package-validation.json');assert boot['firmware_build_pass'] and boot['hardware_not_deployed']
failures=[read(HERE/('intree-build-r'+str(n)+'-validation.json')) for n in [1,2]];assert all(not d['passed'] for d in failures)
audit=dict(stage=389,initial_attribute_group_name_corrected=True,second_modpost_missing_existing_isp_provider_target_corrected=True,third_build_passed_then_empty_firmware_validation_added=True,fourth_final_build_passed=True,
 dt_validator_expanded_existing_reference_properties_but_still_checks_each_changed_target=True,dt_no_semantic_changes_outside_declared_icp_and_iova_nodes=True,
 schema_base_path_and_supported_keyword_fixed=True,schema_diagnostic_text_checked_even_on_zero_exit=True,model_provider_address_warning_and_devm_allocation_tracking_fixed=True,no_failed_build_or_schema_attempt_deployed=True,passed=True)
(HERE/'attempts-validation.json').write_text(json.dumps(audit,indent=2)+'\n')
state=read(HERE/'source-state.json')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==388
 d.update(stage=389,latest_work_stage=389,current_camera_evidence=prefix+'reference/kernel389/README.md',current_device_revalidated_stage=389,
  current_readonly_device_evidence=prefix+'reference/kernel389/current-state-validation.json',in_progress_stage=389,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel389/README.md',
  a5_icp_candidate_source_commit=state['commit'],a5_icp_candidate_source_branch=state['branch'],a5_icp_candidate_source_installed=False,
  ipe_candidate_platform_integrated_with_camss_module=True,ipe_candidate_static_board_enabled=True,ipe_candidate_formal_platform_hardware_verified=False,
  ipe_candidate_module_evidence=prefix+'reference/kernel389/intree-build-r4-validation.json',ipe_candidate_binding_evidence=prefix+'reference/kernel389/binding-validation.json',
  ipe_candidate_board_evidence=prefix+'reference/kernel389/dt-build-validation.json',ipe_candidate_boot_evidence=prefix+'reference/kernel389/build-package-validation.json',
  icp_next_step='Deploy the prepared389 normal CAMSS/ICP module set and actual EDK2 DT carrier with original366 boot/module rollback, after checking initramfs/load paths and live state; then prove normal binding, export lifetime and four-camera/RAW/isolated-IPA paths. Keep Image363/logdump365. Stage389 built and packaged only, no device transition or formal driver runtime claim. Continue explicit in-flight cancel/hardware errors and full OEM IQ and all remaining multi-camera calibration.',
  latest_stage_device_mutated=False,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 assert d['ipe_latest_hardware_stage']==388 and d['icp_latest_device_experiment_stage']==388
 if 'maintained_commit' in d:d.update(maintained_branch=state['branch'],maintained_commit=state['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through388-2026-10-21.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text((HERE/'handoff.md').read_text())
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel389/README.md。389正式ICP平台driver集成qcom-camss同一模块owner，正常DT匹配、per-device bound回调、NULL built-in owner支持；最终源a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07 branch samurai-icp-platform389。r4 W1/Werror构建/26模型/实际DTB/新schema四负例通过；Samurai候选启用七SID和五个仅IOVA保留，原固件物理内存不变。实际EDK2 boot载体已构建，仅DT模块变，回退boot366；5模块/原厂FW/boot完整包及分离模块小包均private389，未上传安装。下一步先查当前boot/module/initramfs与回退，部署精确5模块和正式DT，保留Image363/logdump365/r29/r24；然后实测正式绑定/导出生命周期/四摄RAW隔离IPA。手机仍378guard，原CAMSS/SG与disabledICP，389没有实机帧，不能借388的99帧冒称正式平台验证。owner_refs是整个CAMSS模块引用数，包含普通相机桌面FD。继续在途取消/硬件错误并发、完整IQ及363全部剩余范围；目标active未完成。低照度黑噪点不单独判故障。\n')
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[388 IPE直接DMA、导出所有权与99帧实机](reference/kernel388/README.md)','[389 正式CAMSS/ICP平台与板级部署候选](reference/kernel389/README.md)',1))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;first,rest=p.read_text().split('\n',1);assert first.startswith('388当前：')
 p.write_text('389当前：正常CAMSS/ICP共享模块owner、板级七SID/IOVA候选与实际EDK2 DT载体已构建验证，尚未部署；手机保持388收尾状态，最近实机仍为388。下一步正式启用及回归，完整IQ/多摄校准目标active。[389证据]('+prefix+'reference/kernel389/README.md)。以下为历史。\n'+rest)
print('Stage389 source/build/deployment candidate saved; actual hardware evidence remains388 and full goal stays active.')
