from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['ipa-contract-validation.json','reference-regression-validation.json','runtime-ccm-validation.json','probe-r1-validation.json','final-state-validation.json']:assert json.loads((HERE/name).read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text());health=json.loads((HERE/'final-state-validation.json').read_text())
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text());d.update(current_camera_evidence=prefix+'reference/kernel340/README.md',in_progress_stage=340,in_progress_evidence=prefix+'reference/kernel340/README.md',in_progress_installed=False,
  ccm_runtime_aec_integrated=True,ccm_runtime_aec_deployed=False,ccm_runtime_aec_evidence=prefix+'reference/kernel340/runtime-ccm-validation.json',ccm_runtime_aec_per_revision_frozen=True,
  ipa_candidate_source_stage=340,ipa_candidate_source=state['source'],ipa_candidate_source_evidence=prefix+'reference/kernel340/source-state.json',final_health_evidence=prefix+'reference/kernel340/final-state-validation.json',current_adaptation_goal_status='active')
 if 'system_services' in d:d['system_services']=dict(stage=340,services={k:[p['pid'] for p in v] for k,v in health['services'].items()},evidence=prefix+'reference/kernel340/final-state-validation.json')
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：339','# 当前检查点：340',1)
start=s.index('下一步340从339候选推进：');end=s.index('以下保留历史阶段',start)
s=s[:start]+'''340 已完成实时AEC/CCT→CCM联动。源码 /mnt/samurai-full282/libcamera340-runtime-ccm-built/src/libcamera-v0.7.2，0035以339为base，仅CAMSS IPA camss.cpp/colour_correction_profile.{h,cpp}三个文件。colour_correction.aec_source=runtime可选，lux_index或analogue_gain轴；默认reference兼容。runtime可不填reference.aec_value，DRC/HDR/LED仍显式reference。无AEC或CCT保留旧矩阵、无历史unity。每次WB+CCM proposal冻结CCM状态/源Sof/AECfloat/CCT，prepare不再被后续统计改变；硬件字段含offset/q相同不重复传，元数据按ack firstSof。paramsApplied清旧ccmInputs，等待对应最新ISP上下文统计；旧SOF不提议。手动优先/零gainfallback保留。

340候选build57.7sec通过；实际ARM9新case、66份CCM包+metadata5016bytes独立原厂CamX源码零差，另2份前摄disabled启动包；两项335原合同(referenceCCM、reference+staticLSC)通过，96/1888容量不变。新合同初版Werror缩进报错已修，未改功能源码。私有kernel340/profiles从339生成，明确runtimeAEC；gain-axis-diagnostic修改触发域，只诊断不声称真实factorygain轴绑定。front-explicit-ccm-experiment明确override enabled=true；正常sunny_imx471-unit保留factory disabled。检查JSON中的ccm_enabled与factory_ccm_enabled已分开。

340手机R1 worker24203终态，通过4摄*4相位(500us/1x,5000us/1x,25000us/8x[前12000us]/AWB)，222frames/16images；73已生效revision、222矩阵metadata7992bytes与独立源码零差，10组不同CCM的图像对均不同，末AWB锁定。首版分析把image sequence当kernelSof，前摄实际offset1，其余0，改用实际Pair/恢复事件核对全部帧，未重采/未改驱动。sourceAEC以精确float bits日志保存，十进制lux日志差<0.000498。/var/lib/samurai/k340-aec-ccm-r1完成，未装包/换模块，仍338/r26/r21；PW/WP24236/24239 uid10000，taint0、相关故障delta0、3平台休眠9railsdisabled/users0。无活动session或相机worker。详见reference/kernel340/README.md。

下一步341从340候选继续动态LSC全触发树/个体合成/重采样/同revision排队，以及实际曝光表物理模式/主摄供应商绑定和统一发布。340只完成动态CCM，LSC仍启动静态，不要声称已动态LSC。默认手机r26仍没有339/340的实时lux和动态CCM配置；主摄两源未绑定、前摄factoryCCM禁用保持。正常光学、几何同步、连续AF等完整范围仍在。C近满，新候选继续放E ext4，用340/storage.py sdk_candidate临时bind，结束卸载；不要套旧rename-only SDK构建器。

'''+s[end:]
s=s.replace('以本段338为准','以本段340为准',1).replace('339结束为23394/23397 uid10000。','339结束为23394/23397，340结束为24236/24239 uid10000。',1)
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel340/README.md。340候选完成runtimeAEC/CCT→CCM，冻结每revision防后续stats改写；ARM66包+metadata5016bytes原厂源码零差，四摄4相位222帧/16图/73已生效revision，7992bytes矩阵metadata零差，10图对按不同CCM改变，AWB锁定。前摄启用仅显式实验，原factorydisabled保留；image seq≠kernelSof(前offset1)用实际Pair事件。候选未装，现机r26/r21+298/305/325/338，PW/WP24236/24239待机taint0。下一步341动态LSC及物理模式/供应商绑定、统一发布，完整光学/几何同步/连续AF仍未完。源E ext4 /mnt/samurai-full282/libcamera340-runtime-ccm-built/src/libcamera-v0.7.2，用340/storage.py sdk_candidate构建测试临时bind，勿在C建大副本。用户关灯睡觉，继续源码/TPG，复用未变证据。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='340当前：候选IPA已联动实时AEC/CCT与CCM，四摄222帧矩阵按实际内核SOF与模型一致，曝光/增益改变后图像随矩阵改变。已部署CAMSS338，IPA候选未装；动态LSC与模式绑定继续。[340详情](../../reference/kernel340/README.md)。以下为历史记录。\n\n'
if not s.startswith('340当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded340 dynamic CCM and real per-SOF image evidence; complete camera goal remains active.')
