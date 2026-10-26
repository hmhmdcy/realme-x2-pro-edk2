"""Record stage299 evidence without changing the actual kernel or product deployment."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=ROOT/'archive/camera-before299-2026-10-19';manifest=load(archive/'manifest.json')
assert manifest['prior_documented_stage']==298
for row in manifest['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
assert load(HERE/'factory-bls-export-validation.json')['all16_ife_modes_exported']
assert load(HERE/'eeprom-read-validation.json')['passed']
assert load(HERE/'eeprom-transfer-validation.json')['duplicate_reads_equal']
assert load(HERE/'factory-pattern-validation.json')['stage']==299
for name,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/name;d=load(p);d.update(stage=299,actual_kernel_image_stage=298,
  previous_lock_archive=prefix+'archive/camera-before299-2026-10-19/'+name,
  factory_bls_decoded_and_physically_validated=True,factory_full_tuning_accepted=False,
  factory_bls_evidence=prefix+'reference/kernel299/factory-bls-export-validation.json',
  factory_bls_scene_evidence=prefix+'reference/kernel299/factory-scene-validation.json',
  individual_eeprom_read_twice=True,individual_eeprom_full_layout_and_checksum_verified=False,individual_eeprom_values_applied=False,
  individual_eeprom_evidence=prefix+'reference/kernel299/eeprom-transfer-validation.json',
  inline_userspace_candidate_source='reference/kernel299/pipeline/camss_vfe.cpp',inline_userspace_candidate_installed=False,
  inline_candidate_build_evidence=prefix+'reference/kernel299/inline-build-validation.json',
  hardware_pipeline_ipa_integrated=False,product_camera_path='RAW plus CPU ISP',goal_complete=False)
 d.pop('factory_tuning_values_not_yet_accepted',None)
 if 'kernel_image_stage' in d:assert d['kernel_image_stage']==298
 if name.endswith('deployment-lock.json'):d['current_camera_evidence']=prefix+'reference/kernel299/README.md'
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text()
s=s.replace('2026-10-19：[298黑电平映射与暗绿硬件对照](reference/kernel298/README.md)。BLS已实现／实机验证；遮光暗场标定、正式调校、libcamera硬件pipeline／IPA与完整IQ未完成。目标继续推进，应用仍RAW＋CPU ISP。',
 '2026-10-19：[299原厂BLS、EEPROM与在线候选](reference/kernel299/README.md)。实际内核仍#298，产品仍RAW＋CPU ISP。原厂BLS与本机EEPROM双读已取得证据；正式校准、硬件pipeline／IPA与完整IQ未完成。')
a=s.index('已只读提取本机Sunny IMX319');b=s.index('维护树 ',a)
s=s[:a]+'''299：原厂Sunny IMX319全部16个IFE BLS模式／288区域均960 U14、阈值0，独立原厂解析器与直接解码一致；归一化减偏移3840、显式2175/2048范围伸展已做长焦54帧图案及广角54帧实景对照，WB仍临时场景估计。线性BHIST观测为BLS后／WB前，不能替代RGB AWB。EEPROM两次各12287字节相同并传回私人根；完整布局／原厂校验未通过，未应用个体数值，未写EEPROM。用户暂不遮光。

真实r24 libipa编码器通过；新增在线libcamera handler候选在SDK/work/libcamera299-inline，独立构建／显式启用，未替换产品库。保留原始kernel sequence避免各队列独立归零错配，处理请求／三队列／超时／停流重开；目前仅手动单NV12路径，IPA IPC与自动算法未接。先查[构建结果](reference/kernel299/inline-build-validation.json)及实际进程，再完成真实请求测试；不得把构建中／源码存在当验收。然后接IPA、sensor helper／DelayedControls、实测延迟与有效颜色统计，继续多摄、多模式、AE／AWB及EEPROM校验。原厂参考配置不当SensorBlackLevels或暗场标定。

'''+s[b:]
s=s.replace('所有构建和采集已终态，勿盲目重放。私人根E:/edk2-samurai-out/kernel298，','299候选构建可能仍在运行，先核进程句柄；已执行采集勿盲目重放。私人根E:/edk2-samurai-out/kernel299（298保留），')
assert len(s.encode())<=6500;p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[298黑电平与暗绿对照](reference/kernel298/README.md)';assert needle in s
s=s.replace(needle,'[299原厂BLS、EEPROM与在线候选](reference/kernel299/README.md)、'+needle);assert len(s.encode())<=10000;p.write_text(s)
banner='299（2026-10-19）：实际内核仍#298；原厂IMX319 BLS全部16模式／288区域交叉解码与实机对照通过，本机EEPROM双读12287字节一致，完整布局和校验未通过、未应用。真实libipa编码器已验证；在线libcamera handler仅隔离候选，构建／实机状态见299记录，未接正式IPA，产品仍RAW＋CPU ISP。'
for name,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('reference/kernel276/OEM-TUNING.md','../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/name;s=p.read_text();n=s.index('\n')+1;s=s[:n]+'\n'+banner+'[299证据]('+prefix+'reference/kernel299/README.md)。以下旧阶段按历史阅读。\n'+s[n:];p.write_text(s)
p=ROOT/'sessions/299-factory-bls-eeprom-and-inline-libcamera.md';assert not p.exists()
p.write_text('# 299：原厂BLS、本机EEPROM与在线libcamera候选\n\n2026-10-19。实际内核仍#298，未刷写／重启／更新产品包。原厂调校与个体标定分开，用户暂不遮光。\n\n'+banner+'\n\n[详细结果与未完成范围](../reference/kernel299/README.md)、[部署锁](../linux-port/camera/deployment-lock.json)。构建／进程／实机验收以详细记录为准，不能把候选当产品部署。\n')
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
report=dict(stage=299,kernel_build=298,product_userspace_unchanged=True,full_goal_complete=False,
 files={r['path']:dict(bytes=(ROOT/r['path']).stat().st_size,sha256=sha(ROOT/r['path'])) for r in manifest['files']})
(HERE/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Recorded stage299 evidence; actual kernel remains298, candidate uninstalled, full goal active.')
