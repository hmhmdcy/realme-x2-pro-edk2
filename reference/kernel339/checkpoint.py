from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['ipa-contract-validation.json','runtime-lux-validation.json','probe-r1-validation.json','final-state-validation.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
state=json.loads((HERE/'source-state.json').read_text());state.update(temporary_four_camera_runtime_verified=True,physical_mode_factory_binding_verified=False,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
health=json.loads((HERE/'final-state-validation.json').read_text())
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text());d.update(current_camera_evidence=prefix+'reference/kernel339/README.md',in_progress_stage=339,in_progress_evidence=prefix+'reference/kernel339/README.md',in_progress_installed=False,
  aec_lux_runtime_integrated=True,aec_lux_runtime_deployed=False,aec_lux_runtime_evidence=prefix+'reference/kernel339/runtime-lux-validation.json',aec_lux_ipa_contract_evidence=prefix+'reference/kernel339/ipa-contract-validation.json',aec_lux_factory_mode_binding_verified=False,
  ipa_candidate_source_stage=339,ipa_candidate_source=state['source'],ipa_candidate_source_evidence=prefix+'reference/kernel339/source-state.json',final_health_evidence=prefix+'reference/kernel339/final-state-validation.json',current_adaptation_goal_status='active')
 if 'system_services' in d:d['system_services']=dict(stage=339,services={k:[p['pid'] for p in v] for k,v in health['services'].items()},evidence=prefix+'reference/kernel339/final-state-validation.json')
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：338','# 当前检查点：339',1)
start=s.index('下一步339：');end=s.index('以下保留历史阶段',start)
s=s[:start]+'''339 已完成：在335候选IPA集成337四个libipa源，新增可选aec_lux模式节点及LuxProfile包装，私有Statistics返回luxValid/exposureIndex/luxLuma/luxIndex，不使用标准物理Lux控制。每统计帧使用其已生效SOF WB上下文和真实曝光行/增益码；ns=llround(lines*lineUs*1000)。缺失/错误/不兼容/重复统计不推进滤波，start/stop重置。默认配置未改，没有自动选择工厂/供应商。

339 候选 /mnt/samurai-full282/libcamera339-lux-built/src/libcamera-v0.7.2；0034以335为base。首次DSO加载发现ValueNode无uint64 accessor（虽然链接通过），改string+from_chars解析64bit纳秒，重建签名；最终build attempt2成功。实际ARM DSO11cases通过，7组63有效记录共756bytes与原指令完全一致，亮度可359.018；8个配置含禁用+3拒绝配置。真实四摄+广角补偿5采集122frames全部实时lux，AWB稳定、恢复完成。原厂指令对曝光/滤波日志最大误差0.000507（六位日志，容差0.003）；120帧匹配338稳定TPG亮度模型。前摄SOF0/1亮度.1，保留滤波核对但不冒充338稳定raw；分析首版错误假定从首帧稳定，已修正记录，未重采。没有改手机安装文件/模块，338继续加载。所有worker终态，PW/WP23394/23397 uid10000，taint0/3平台休眠/9rails关闭users0。详见reference/kernel339/README.md。

339私有profiles-private.json：5个工厂来源unit profile来自335，Metering106/Arbitration110 table0/first knee的显式诊断anchor；另广角开启颜色补偿/关闭滤波/禁用3种配置，不宣称物理模式已绑定。安装系统依旧r26/r21无这些默认。profiles及expected/actual、算法和样本不镜像。339/storage.py sdk_candidate()临时bind E候选到SDK work/libcamera，exit卸载，不要套用旧rename-only构建器或在C复制541MB。

下一步340从339候选推进：真实曝光表物理模式/供应商绑定，lux→动态LSC/CCM联动，统一发布。339当前只计算实时lux，CCM仍335的CCT联动+显式AEC/DRC/HDR/LED参考值，LSC仍静态；不要声称lux已驱动IQ表。主摄Qtech/Sunny未绑定，前摄原厂CCM disabled仍保留。正常光学、几何同步、连续AF等完整范围仍在。

'''+s[end:]
s=s.replace('PW/WP22627/22630 uid10000。没有活动构建/采集/安装worker。','338当时PW/WP22627/22630；339结束为23394/23397 uid10000。没有活动构建/采集/安装worker。',1)
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel339/README.md。339已把337原厂Bayer→luma→exposure/lux接335候选IPA，ARM实际DSO11case/63有效records756bytes零差，四摄+广角补偿5次122帧现场通过；前摄头2帧亮度.1保留滤波核对，稳定raw比较120帧。候选未装，系统r26/r21+298/305/325/338，PW/WP23394/23397待机taint0。下一步340真实模式/供应商绑定、lux→动态LSC/CCM和统一发布；339只是实时数值，未动态选IQ。候选源码E ext4 /mnt/samurai-full282/libcamera339-lux-built/src/libcamera-v0.7.2，用339/storage.py sdk_candidate临时bind构建/测试，结束卸载；C近满勿大副本。用户关灯睡觉，继续源码/TPG，复用不变证据。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='339当前：候选IPA已计算逐帧曝光/亮度/lux index，四摄内部图案与原厂指令核对通过；已安装CAMSS338，IPA仍r26。物理模式绑定及lux动态LSC/CCM待继续。[339详情](../../reference/kernel339/README.md)。以下为历史记录。\n\n'
if not s.startswith('339当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded339 runtime lux integration and actual four-camera results; full goal remains active.')
