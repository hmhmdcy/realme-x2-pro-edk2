"""Record the verified manual hardware IPA candidate, not a product deployment."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=ROOT/'archive/camera-before300-2026-10-19';manifest=load(archive/'manifest.json')
assert manifest['prior_documented_stage']==299
resume='--resume' in sys.argv
for row in manifest['files']:
 if sha(ROOT/row['path'])!=row['sha256']:
  assert resume and row['path'] in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']
  state=load(ROOT/row['path']);assert state['stage']==300 and state['actual_kernel_image_stage']==298
association=load(HERE/'runtime-association-validation.json');health=load(HERE/'final-health-validation.json');build=load(HERE/'build-validation.json')
assert association['independent_crosscheck_passed'] and association['total_verified_application_frames']==144
assert health['checked_runtime_healthy'] and health['all778_modules_verified'] and not health['whole_system_healthy']
assert build['build_exit']==0
tree=Path(build['isolated_source'])
for name,digest in build['source_sha256'].items():assert sha(tree/name)==digest
kernel='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',kernel,*a],text=True).strip()
assert git('rev-parse','HEAD')=='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117' and not git('status','--porcelain')
oldbundle=Path('/mnt/e/edk2-samurai-out/kernel299/inline-bundle-r2-private.tar.gz')
assert sha(oldbundle)=='4519b7009383e815e9073256a3bc5a1592abf484d1b28c7859a5b7e492974ba4'
for name,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/name;d=load(p);assert d['stage'] in ([299,300] if resume else [299]) and d['actual_kernel_image_stage']==298
 d.update(stage=300,actual_kernel_image_stage=298,previous_lock_archive=prefix+'archive/camera-before300-2026-10-19/'+name,
  experimental_manual_hardware_pipeline_ipa_integrated=True,hardware_pipeline_ipa_integrated=False,full_automatic_hardware_pipeline_ipa_integrated=False,
  inline_userspace_candidate_installed=False,inline_userspace_candidate_source=prefix+'reference/kernel300/pipeline/camss_vfe.cpp',
  inline_candidate_build_evidence=prefix+'reference/kernel300/build-validation.json',
  inline_manual_candidate_evidence=prefix+'reference/kernel300/runtime-association-validation.json',
  inline_manual_candidate_scope='IMX3191632x1224 to320x240NV12; startup WB/BLS and BHIST IPA; signed-threaded and forced-isolated3x24frames each; no per-request controls or AE/AWB',
  experimental_ipa_source_evidence=prefix+'reference/kernel300/README.md',final_health_evidence=prefix+'reference/kernel300/final-health-validation.json',
  product_camera_path='RAW plus CPU ISP',goal_complete=False)
 if 'kernel_image_stage' in d:assert d['kernel_image_stage']==298
 if name.endswith('deployment-lock.json'):d['current_camera_evidence']=prefix+'reference/kernel300/README.md'
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=(HERE/'NEXT-TEMPLATE.md').read_text();assert len(s.encode())<=6500;p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[299原厂BLS、EEPROM与在线候选](reference/kernel299/README.md)';assert needle in s
s=s.replace(needle,'[300硬件IPA与生命周期](reference/kernel300/README.md)、'+needle);assert len(s.encode())<=10000;p.write_text(s)
banner='300（2026-10-19）：实际内核仍#298、产品RAW＋CPU ISP；IMX319标准手动硬件IPA候选接通。签名线程／独立进程各三轮24帧，共144图像／统计／SOF／ColourGains元数据通过；修复重复init线程归属与测试图恢复顺序，原图／资源恢复。候选未安装，自动算法／多摄完整校准／逐帧控制与EEPROM校验仍未完成。'
for name,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('reference/kernel276/OEM-TUNING.md','../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/name;s=p.read_text();n=s.index('\n')+1;s=s[:n]+'\n'+banner+'[300证据]('+prefix+'reference/kernel300/README.md)。以下旧阶段按历史阅读。\n'+s[n:];p.write_text(s)
p=ROOT/'sessions/300-hardware-ipa-and-lifecycle.md';assert not p.exists()
p.write_text('# 300：标准硬件IPA与生命周期收敛\n\n2026-10-19。'+banner+'\n\n[源码、构建、实机和未完成范围](../reference/kernel300/README.md)。R3用户空间断言与单链接恢复过程保留；内核、DT和产品载荷未变。不能将手动IPA候选当成完整校准完成。\n')
notes=dict(stage=300,actual_kernel_build=298,default_mode_failure='R3 repeated IPAinit moved an already-thread-bound object; fixed once-per-proxy init, configure/start on restart, release resets proxy',
 graph_failure='R3 old fixture enabled original input before removing competing link; one link restored by guarded standard MC call and exact graph readback',
 r2_force_variable_presence_semantics_observed=True,r2_derived_report_flag_corrected=True,
 checkpoint_size_guard_intercepted=True,checkpoint_resumed_only_known_lock_changes=resume,
 final_r4_signed_threaded_passed=True,final_r5_forced_isolated_passed=True,all_failed_attempts_preserved=True,
 no_kernel_or_dt_or_firmware_or_product_package_changes=True,no_individual_calibration_applied=True,full_goal_complete=False)
(HERE/'preparation-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
out=dict(stage=300,kernel_build=298,manual_ipa_candidate_verified=True,product_userspace_unchanged=True,full_goal_complete=False,generated_index_finalized=True,
 files={r['path']:dict(bytes=(ROOT/r['path']).stat().st_size,sha256=sha(ROOT/r['path'])) for r in manifest['files']})
(HERE/'checkpoint-validation.json').write_text(json.dumps(out,indent=2)+'\n')
print('Recorded tested manual IPA candidate300; actual kernel298, unchanged product, full calibration goal active.')
