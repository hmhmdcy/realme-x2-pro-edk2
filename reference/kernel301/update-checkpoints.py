"""Publish measured response scope while keeping deployment and open work explicit."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=load(ROOT/'archive/camera-before301-2026-10-19/manifest.json');assert manifest['prior_documented_stage']==300
for r in manifest['files']:assert sha(ROOT/r['path'])==r['sha256']
capture=load(HERE/'delay-capture-r1-validation.json');analysis=load(HERE/'delay-analysis-r1-validation.json')
assert capture['passed'] and analysis['paired_images']==240 and analysis['control_steps']==9
assert all(s['useful_response'] and s['first_observed_changed_offset']==s['first_three_frame_plateau_offset']==2 for s in analysis['steps'])
kernel='/home/cy122/x2pro-linux/camera279-isp-kernel'
assert subprocess.check_output(['git','-C',kernel,'rev-parse','HEAD'],text=True).strip()=='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117'
assert not subprocess.check_output(['git','-C',kernel,'status','--porcelain'],text=True).strip()
for name,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/name;d=load(p);assert d['stage']==300 and d['actual_kernel_image_stage']==298
 d.update(stage=301,previous_lock_archive=prefix+'archive/camera-before301-2026-10-19/'+name,
  sensor_control_timing_evidence=prefix+'reference/kernel301/delay-analysis-r1-validation.json',
  sensor_control_timing_scope='IMX3191632x1224 only; nine standard V4L2 control steps; post-BLS/pre-WB Y statistics response SOF+2; not full-frame/multimode latching proof',
  experimental_delayed_controls_integrated=False,experimental_hardware_ae_integrated=False,goal_complete=False)
 if name.endswith('deployment-lock.json'):d['current_camera_evidence']=prefix+'reference/kernel301/README.md'
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text()
s=s.replace('2026-10-19：[300硬件IPA与生命周期](reference/kernel300/README.md)。IMX319手动硬件IPA候选两执行模式通过；','2026-10-19：[301曝光／增益时序](reference/kernel301/README.md)。IMX319本模式9次写入均在SOF＋2观察到统计变化；')
s=s.replace('300/host.py沿用','301/host.py沿用')
anchor='- 当前只是IMX319';pos=s.index(anchor)
s=s[:pos]+'- 301复用300库／IPA／配置，仅新建时序工具；240帧与统计配对、233个SOF事件、9个控制阶跃通过，均从写入SOF＋2观察到变化。写入在事件后约0.23—0.43ms，耗时约0.55—0.90ms；图与控制恢复、约1.02秒休眠。仅本模式BHIST响应，尚非整帧／嵌入数据／跨模式证明，未提交delay属性。[实测](reference/kernel301/delay-analysis-r1-validation.json)\n'+s[pos:]
s=s.replace('sensor helper／DelayedControls、实测延迟、AE／AWB','sensor helper／DelayedControls集成、其它模式延迟、AE／AWB')
s=s.replace('复用sensor helper／DelayedControls实测曝光／增益延迟，再接AE','将本模式实测延迟用于sensor helper／DelayedControls接入及有效帧关联验证，再接AE')
s=s.replace('私人根E:/edk2-samurai-out/kernel300（299／298保留）','私人根E:/edk2-samurai-out/kernel301（300／299／298保留）')
assert len(s.encode())<=6500;p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();anchor='[300硬件IPA与生命周期](reference/kernel300/README.md)';assert s.count(anchor)==1
s=s.replace(anchor,'[301曝光／增益时序](reference/kernel301/README.md)、'+anchor);assert len(s.encode())<=10000;p.write_text(s)
banner='301（2026-10-19）：实际内核仍#298，产品RAW＋CPU ISP不变；IMX319本模式240图像／统计配对、233个SOF事件、9次曝光／增益写入均在SOF＋2观察到BHIST响应。原图／控制恢复、资源自然休眠；未接DelayedControls或AE／AWB，未证明跨模式延迟或完整校准。'
for name,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('reference/kernel276/OEM-TUNING.md','../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/name;s=p.read_text();s=banner+'[301证据]('+prefix+'reference/kernel301/README.md)。以下旧阶段按历史阅读。\n\n'+s;p.write_text(s)
p=ROOT/'sessions/301-imx319-control-response-timing.md';assert not p.exists()
p.write_text('# 301：IMX319控制响应时序\n\n2026-10-19。'+banner+'\n\n[源码、构建、实机、分析与边界](../reference/kernel301/README.md)。本机EEPROM完整布局与校验仍未确认；正常场景不替代暗场标定。完整目标继续。\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
out=dict(stage=301,actual_kernel_build=298,measured_control_response_frames=2,delay_properties_not_committed=True,full_goal_complete=False,generated_index_finalized=True,
 files={r['path']:dict(bytes=(ROOT/r['path']).stat().st_size,sha256=sha(ROOT/r['path'])) for r in manifest['files']})
(HERE/'checkpoint-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('Recorded301 measured control response; current298 deployment and300 candidate unchanged. Goal remains active.')
