"""Record verified sensor control integration, retaining the full open objective."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=load(ROOT/'archive/camera-before302-2026-10-19/manifest.json');assert manifest['prior_documented_stage']==301
for row in manifest['files']:assert sha(ROOT/row['path'])==row['sha256']
evidence=load(HERE/'runtime-association-validation.json');assert evidence['independent_crosscheck_passed'] and evidence['total_verified_application_frames']==960
build=load(HERE/'build-validation.json');tree=Path(build['isolated_source'])
for name,digest in build['source_sha256'].items():assert sha(tree/name)==digest
kernel='/home/cy122/x2pro-linux/camera279-isp-kernel'
assert subprocess.check_output(['git','-C',kernel,'rev-parse','HEAD'],text=True).strip()=='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117'
assert not subprocess.check_output(['git','-C',kernel,'status','--porcelain'],text=True).strip()
next_source=(HERE/'NEXT-TEMPLATE.md').read_text();assert len(next_source.encode())<=6500
for name,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/name;d=load(p);assert d['stage']==301 and d['actual_kernel_image_stage']==298
 d.update(stage=302,previous_lock_archive=prefix+'archive/camera-before302-2026-10-19/'+name,
  experimental_delayed_controls_integrated=True,experimental_sensor_helper_integrated=True,experimental_hardware_ae_integrated=False,
  experimental_current_mode_statistics_have_effective_sensor_context=True,
  sensor_control_timing_evidence=prefix+'reference/kernel302/runtime-association-validation.json',
  sensor_control_timing_scope='IMX3191632x1224/209066666pixelrate/2080line/min3350frame only; actual writes SOF+2; source request may take one further image frame under isolated IPC',
  inline_userspace_candidate_source=prefix+'reference/kernel302/pipeline/camss_vfe.cpp',inline_candidate_build_evidence=prefix+'reference/kernel302/build-validation.json',
  inline_manual_candidate_evidence=prefix+'reference/kernel302/runtime-association-validation.json',experimental_ipa_source_evidence=prefix+'reference/kernel302/README.md',
  inline_manual_candidate_scope='Current IMX319 mode; standard Manual ExposureTime/AnalogueGain modes, quantized effective SOF metadata; R3 isolated/R4 signed-threaded480frames each; no AE/AWB',
  candidate_runtime_restoration_evidence=prefix+'reference/kernel302/controls-capture-r4-validation.json',
  inline_userspace_candidate_installed=False,hardware_pipeline_ipa_integrated=False,full_automatic_hardware_pipeline_ipa_integrated=False,
  product_camera_path='RAW plus CPU ISP',goal_complete=False)
 if name.endswith('deployment-lock.json'):d['current_camera_evidence']=prefix+'reference/kernel302/README.md'
 p.write_text(json.dumps(d,indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text(next_source)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();anchor='[301曝光／增益时序](reference/kernel301/README.md)';assert s.count(anchor)==1
s=s.replace(anchor,'[302硬件IPA控制／有效帧](reference/kernel302/README.md)、'+anchor);assert len(s.encode())<=10000;p.write_text(s)
banner='302（2026-10-19）：实际仍#298／产品RAW＋CPU ISP。候选复用SensorHelper／DelayedControls，标准Manual曝光增益及有效SOF元数据接入；隔离／签名线程共960帧、36控制变化、144图像分区响应通过，均从真实写入SOF＋2变化。媒体图／控制恢复，资源自然休眠；AE／AWB、多摄及完整校准未完成。'
for name,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('reference/kernel276/OEM-TUNING.md','../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/name;p.write_text(banner+'[302证据]('+prefix+'reference/kernel302/README.md)。以下旧阶段按历史阅读。\n\n'+p.read_text())
p=ROOT/'sessions/302-sensor-controls-and-effective-sof-context.md';assert not p.exists()
p.write_text('# 302：硬件IPA传感器控制与有效SOF上下文\n\n2026-10-19。'+banner+'\n\n[源码、真实模块与实机验证、失败和待完成范围](../reference/kernel302/README.md)。隔离模式部分控制落在后一个图像帧，元数据按真实生效值；不是完整AE／AWB或多摄校准验收。\n')
notes=dict(stage=302,previous_goal_turn_classification='progress:301 physical timing changed the next implementation action',
  yaml_uint64_accessor_missing_at_real_dso_load_fixed=True,runtime_generator_ambiguous_reuse_anchor_fixed=True,
  manual_mode_enum_compare_werror_fixed=True,initial_r1_r2_preserved_but_not_final_mode_interface_acceptance=True,
  r3_pack_terminal_observed_after_launch_but_actual_final_bundle_independently_verified=True,
  no_kernel_or_dt_or_generic_helper_or_product_changes=True,full_goal_complete=False)
(HERE/'preparation-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
out=dict(stage=302,actual_kernel_build=298,verified_effective_sensor_control_frames=960,experimental_delayed_controls_integrated=True,hardware_ae_awb_incomplete=True,
 full_goal_complete=False,generated_index_finalized=True,files={r['path']:dict(bytes=(ROOT/r['path']).stat().st_size,sha256=sha(ROOT/r['path'])) for r in manifest['files']})
(HERE/'checkpoint-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('Recorded302 verified controls; current298 product unchanged. Full goal remains active.')
