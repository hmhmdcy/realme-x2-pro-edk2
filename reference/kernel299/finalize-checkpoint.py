"""Record verified candidate results while preserving the unchanged product deployment."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not load(HERE/'checkpoint-validation.json').get('inline_manual_candidate_verified'), 'Already finalized; inspect existing checkpoint instead of replaying.'
capture=load(HERE/'inline-capture-r3-validation.json');association=load(HERE/'inline-request-association-validation.json');health=load(HERE/'final-health-validation.json')
assert capture['passed'] and association['independent_log_crosscheck_passed']
assert capture['application_frames']==72 and len(capture['exact_sof_pairs'])==72 and capture['before']==capture['after']
assert health['checked_runtime_healthy'] and health['all778_modules_verified'] and health['current50_payloads_verified']==50
assert health['kernel_build']==298 and not health['whole_system_healthy']
if 'hardware_isp_userspace_not_integrated' in health:health['product_hardware_isp_userspace_not_integrated']=health.pop('hardware_isp_userspace_not_integrated')
health['experimental_inline_handler_real_requests_passed']=True
(HERE/'final-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')
tree='/home/cy122/x2pro-linux/camera279-isp-kernel';git=lambda *a:subprocess.check_output(['git','-C',tree,*a],text=True).strip()
assert git('rev-parse','HEAD')=='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117' and not git('status','--porcelain')
build=load(HERE/'inline-build-validation.json');assert build['build_exit']==0
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline/src/libcamera/pipeline/camss-vfe')
assert sha(sdk/'camss_vfe.cpp')==sha(HERE/'pipeline/camss_vfe.cpp')==build['source_sha256']['camss_vfe.cpp']
for name,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/name;d=load(p);assert d['stage']==299 and d['actual_kernel_image_stage']==298
 d.update(inline_manual_candidate_real_requests_verified=True,inline_manual_candidate_scope='IMX319, single320x240NV12, startup manual WB/BLS, three24-frame restart epochs; not IPA or per-request controls',
  inline_manual_candidate_evidence=prefix+'reference/kernel299/inline-request-association-validation.json',
  final_health_evidence=prefix+'reference/kernel299/final-health-validation.json',inline_userspace_candidate_installed=False,hardware_pipeline_ipa_integrated=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=HERE/'README.md';s=p.read_text();s=s.replace('以上代码仍需实机验收，不能用代码存在代替通过。','已在IMX319完成三轮真实请求，每轮24帧，72帧均完成CPU DMA同步读取且亮度非恒定；72组图像／统计与观测SOF事件及应用序号独立交叉核对，参数均从SOF0生效。每轮停流后不重新配置即可启动。该验收不覆盖逐请求控制、错误取消、晚启动统计、严重IRQ延迟或其它传感器／模式。[实机](inline-capture-r3-validation.json)、[独立关联及包读回](inline-request-association-validation.json)')
s=s.replace('构建和实机状态以[构建结果](inline-build-validation.json)、[测试工具](inline-smoke-tools-validation.json)及后续采集记录为准。','完整候选库和测试程序Werror构建通过；状态见[构建结果](inline-build-validation.json)、[测试工具](inline-smoke-tools-validation.json)、[实机记录](inline-capture-r3-validation.json)。')
s=s.replace('下一步：完成候选构建与真实请求／停流／重开验证，再接IPA、sensor helper和DelayedControls，','下一步：补晚启动统计／取消／丢失SOF／逐请求参数及更多模式验收，再接IPA、sensor helper和DelayedControls，')
s+='''

## 实机收尾与保留的失败

R1仅枚举传感器，测试应用按设备树camera ID寻找型号而未进入采集；原始私有报告中硬编码的actual_libcamera_requests标志已在公开派生报告纠正为false，原始记录保留。改用Model属性后R2三轮72图像／72配对成功，但固定1秒采样仍看到CCI活跃，总验收未通过。读取该设备1000ms自动休眠配置并确认随后休眠后，R3改为5秒以内的纯观察轮询，在1305ms取得前后完全相同的休眠状态；没有强制挂起或更改延迟。R1／R2失败报告与包均保留。

最终核对：5传感器／镜头、两CCI及CAMSS休眠，9相机供电与共享IO关闭、用户0，MCLK／CCI时钟0，fault／taint／pstore／CCI错误0；961包、50相机载荷和778模块校验一致。桌面／PipeWire／WirePlumber进程未替换，SensorProxy、Wi-Fi、HCI和三个DSP维持正常。[最终检查](final-health-validation.json) 四摄RAW＋CPU产品回归引用先前298的18段233帧结果，本阶段没有重跑，也没有把候选采集等同四摄产品验收。

所有本轮构建与采集已核终态；R3 worker与fixture均无匹配活进程。只同步脱敏源码／证据，不提交或推送、不安装候选库。正式目标仍未完成。
'''
p.write_text(s)
p=ROOT/'NEXT-SESSION.md';s=p.read_text()
s=s.replace('先查[构建结果](reference/kernel299/inline-build-validation.json)及实际进程，再完成真实请求测试；不得把构建中／源码存在当验收。','[候选构建](reference/kernel299/inline-build-validation.json)与IMX319三轮各24帧通过，72图像／统计／SOF及参数回执独立核对，重开不重新配置；[关联证据](reference/kernel299/inline-request-association-validation.json)。R1选错ID、R2固定1秒采样CCI尚活跃均保留；R3轮询1305ms自然休眠，未强制挂起。')
s=s.replace('然后接IPA、sensor helper／DelayedControls、实测延迟与有效颜色统计，','接下来补晚启动统计、取消／丢失SOF及逐请求参数验收，再接IPA、sensor helper／DelayedControls、实测延迟与有效颜色统计，')
s=s.replace('299候选构建可能仍在运行，先核进程句柄；已执行采集勿盲目重放。','本轮构建／采集均终态且worker／fixture均无匹配活进程；新动作前核当前身份，已执行采集勿盲目重放。')
s=s.replace('见[最终检查](reference/kernel298/final-health-validation.json)','见[最终检查](reference/kernel299/final-health-validation.json)')
assert len(s.encode())<=6500;p.write_text(s)
p=ROOT/'sessions/299-factory-bls-eeprom-and-inline-libcamera.md';s=p.read_text();s+='\n在线候选完整构建及IMX319真实请求验证通过：三轮各24帧，72精确SOF配对／参数SOF0、DMA同步读取、停流不重新配置重开；CCI1305ms自然休眠，资源／媒体图恢复，原产品50载荷和778模块不变。R1／R2准备及观察问题保留。未安装候选，正式IPA／自动算法／其它模式仍未完成。\n';p.write_text(s)
notes=dict(stage=299,preserved_attempts=[
 dict(attempt='inline-build-r2',outcome='Explicitly interrupted O2 qemu build; switched isolated candidate to O0, never treated as success'),
 dict(attempt='inline-build-r3',outcome='Missing existing kernel QCOM metadata FourCCs in retained SDK header; synchronized two definitions; later full Werror builds pass'),
 dict(attempt='inline-r1',outcome='Application selector used OF camera ID, no capture; Model selection fixed; original static actual-request flag corrected in derived report'),
 dict(attempt='inline-r2',outcome='72 images and72 exact pairs; fixed1s idle sample precedes eventual CCI autosuspend, aggregate false retained'),
 dict(attempt='inline-r3',outcome='Same tested bundle as r2; bounded observational idle polling, all72 pairs and resources passed, idle1305ms')],
 model_property_string_view_compile_failure_preserved=True,eeprom_parser_r1_cpu_limit_and_r2_incomplete_layout_preserved=True,
 no_kernel_or_board_firmware_or_system_package_change=True,no_eeprom_data_writes=True,full_goal_not_complete=True)
(HERE/'preparation-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
p=HERE/'checkpoint-validation.json';d=load(p)
for name in d['files']:d['files'][name]=dict(bytes=(ROOT/name).stat().st_size,sha256=sha(ROOT/name))
d.update(inline_manual_candidate_verified=True,actual_kernel_build=298,product_packages_unchanged=True,full_goal_complete=False,generated_index_finalized=True)
p.write_text(json.dumps(d,indent=2)+'\n')
print('Candidate72-frame request association and idle health recorded; nine entrypoint hashes finalized; full goal remains active.')
