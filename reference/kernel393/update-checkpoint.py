from pathlib import Path
import copy,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
current=json.loads((HERE/'current-state-validation.json').read_text());assert current['passed']
source=json.loads((HERE/'source-state.json').read_text());build=json.loads((HERE/'intree-build-validation.json').read_text());new={r['name'].replace('-','_'):r for r in build['modules'] if r['runtime_candidate']}
archive=ROOT/'archive/NEXT-SESSION-through392-2026-10-21.md';assert not archive.exists();shutil.copyfile(ROOT/'NEXT-SESSION.md',archive)
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(stage=393,in_progress_stage=393,latest_work_stage=393,current_device_revalidated_stage=393,icp_latest_device_experiment_stage=393,ipe_latest_hardware_stage=393,ipe_latest_stage_actual_frames=54,ipe_latest_stage_RT_frames=54,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_frames_scope='393 verified r4 window:55 jobs=53completed+1cancelled+1local rejection;54 hardware frame completions. Earlier r3 two frames remain a failed window, not included. Normal module reload starts a fresh counter epoch.',ipe_input_validation_error_affects_peer=False,ipe_preflight_error_isolation_verified=True,ipe_same_fd_recovery_while_peer_running_verified=True,ipe_hardware_error_concurrency_verified=False,ipe_core_result_api='camss_a5_ipe_run_status',current_icp_pair_deployment_stage=393,current_boot_auto_af_retest_scope='393 local rejection/cancel and default four-camera regression only; no new optical/AF calibration.',kernel_source_commit=source['commit'],kernel_source_branch=source['branch'],icp_next_step='True hardware-error/unknown-completion concurrency remains unverified; preserve retention and reset-ACK requirements. Then OEM Gamma/LTM/CCM full IQ and all363 camera scope. Proven local pre-transfer-MAP rejection is now isolated393 and same fd recovers while peer remains live. Keep r30/r25, boot389/Image363/logdump365; same390 guard.')
 for key in ['maintained_commit','candidate_kernel_source_commit']:
  if key in d:d[key]=source['commit']
 for key in ['maintained_branch','candidate_kernel_source_branch']:
  if key in d:d[key]=source['branch']
 d['kernel_source_scope']='Image363 and normal CAMSS composite389 unchanged; only core+adapter393 pair rebuilt/installed from maintained source64aaf4f. No complete Image rebuild393.'
 if 'full_image_and_all_modules_candidate_built' in d:d['full_image_and_all_modules_candidate_built']=False
 for key,name in [('current_camera_evidence','README.md'),('in_progress_evidence','README.md'),('device_closeout_evidence','current-state-validation.json'),('current_readonly_device_evidence','current-state-validation.json')]:d[key]=prefix+'kernel393/'+name
 d['ipe_local_rejection_evidence']=prefix+'kernel393/hardware-validation.json';d['ipe_installed_default_camera_recovery_evidence']=prefix+'kernel393/runtime-r4-validation.json';d['icp_pair_module_build_evidence']=prefix+'kernel393/intree-build-validation.json'
 d['ipe_current_cumulative_counters']={k:current['m2m'][k] for k in ['jobs','completed','direct_completed','cancelled','failed','first_error']}
 d['ipe_current_counter_epoch']='393-r4 normal module load; old392 values archived before unload'
 d['ipe_current_failed_counter_scope']='1 expected local alias rejection393, first_error=-22 cumulative; peer not failed, fatal=false, same-fd repair and default four-camera48 verified'
 key='kernel_modules' if relative.endswith('deployment-lock.json') else 'deployed_camera_modules'
 for name,row in new.items():d[key][name].update(sha256=row['sha256'],bytes=row['bytes'],targeted_validation_stage=393,loaded=True,loaded_note_matches_disk=True)
 if relative.endswith('deployment-lock.json'):
  d['final_health_evidence']=prefix+'kernel393/current-state-validation.json';d['system_services']=dict(stage=393,services=current['services'],evidence=prefix+'kernel393/current-state-validation.json',current_boot_revalidated=True)
 p.write_text(json.dumps(d,indent=2)+'\n')
for relative,link in [('linux-port/camera/README.md','../../reference/kernel393/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel393/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel393/README.md')]:
 p=ROOT/relative;s=p.read_text().split('\n\n',1)[1]
 p.write_text('393当前：核心明确区分提交前局部拒绝，匹配core/adapter已正式更新；别名错误不再连带peer，同fd可在peer会话存活时修复。28模型用例与并发取消、四摄默认48帧通过；Image/板级/r30-r25保持。真实硬件错误并发、完整IQ与多摄校准仍未完成。[393证据]('+link+')。以下为历史。\n\n'+s)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[392 在途取消与输入错误恢复实机](reference/kernel392/README.md)','[393 IPE局部错误隔离与正式模块更新](reference/kernel393/README.md)'))
print(json.dumps(dict(stage=393,locks_and_docs_updated=True,only_core_adapter_deployment_updated=True,previous_checkpoint_archived=True,passed=True)))
