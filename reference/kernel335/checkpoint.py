from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['ipa-contract-validation.json','ccm-metadata-image-validation.json','probe-r1-validation.json','final-state-validation.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
assert not json.loads((HERE/'build-validation.json').read_text())['exit_code']
source=json.loads((HERE/'source-state.json').read_text());source.update(temporary_four_sensor_hardware_tested=True,installed=False);(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text());d.update(current_camera_evidence=prefix+'reference/kernel335/README.md',in_progress_stage=335,in_progress_evidence=prefix+'reference/kernel335/README.md',in_progress_installed=False,
  colour_temperature_ccm_linked=True,colour_temperature_ccm_deployed=False,colour_temperature_ccm_evidence=prefix+'reference/kernel335/ccm-metadata-image-validation.json',ccm_candidate_userspace_source=source['source'],
  ccm_non_cct_trigger_inputs='explicit diagnostic reference coordinates',front_factory_ccm_enabled=False,front_ccm_experimental_enable_hardware_verified=True)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：334','# 当前检查点：335').replace('reference/kernel334/host.py提供raw_ssh。','reference/kernel335/host.py提供raw_ssh。').replace('334后PW/WP pid18338/18365、uid10000。','335后PW/WP pid19667/19708、uid10000。')
start=s.index('下一步335从332候选libcamera332-cct-built');end=s.index('继续动态AEC/CCT触发',start)
s=s[:start]+'''335已完成332 IPA与333 CCM数学/完整触发树、334硬件后端联动，候选源SDK/work/libcamera335-ccm-built/src/libcamera-v0.7.2，未安装。增量0033-camss-colour-correction-coupling.patch，累积330/332基线；核心库CAMSS request predicate增加ColourCorrectionMatrix，IPA可选colour_correction配置/控制/包/有效矩阵元数据，通用数学仍333，未改板级/传感器/内核。触发树DRC→HDR→显式LED→AEC→CCT保留；reference_triggers为DRC1/HDRsens1/LED0/lux100诊断，只有CCT跟revision动态更新，不把Exposure EV当lux。

335 profile每mode: colour_correction.enabled/qfactor/aec_control(lux_index|analogue_gain)/hdr_control(exposure_time_ratio|sensitivity_ratio|exposure_gain_ratio)/reference_triggers(drc_gain,hdr_ratio,led_index,aec_value)/core完整333树。原厂Default UID37均存在，前摄sunny_imx471 enabled=0；十个factory/unit正常profile保留该标志，另外两份*-ccm-experiment明确启用，仅实验。主摄两供应商仍未绑定。WB仍UID117/79个体校准，原厂表/个体/期望二进制只留private335。

335策略：可选表启用才公开ColourCorrectionMatrix；AWBoff显式手动矩阵优先，CCT或ColourGains请求无矩阵则清覆盖恢复表；AWBon清手动矩阵/CCTtag。按同revision显式手动K或硬件有效WB逆推K选表，零通道无法估K时保留上矩阵/start unity，不伪造CCT。startup预编码校验后commit；手动runtime预选后commit；prepareParameters给context存ColourCorrectionState(data/parameters/effective)，SOF ack后frame/stats都报告量化有效RGB矩阵。普通包96，WB/BHIST/LSC/CCM startup1888；无CCM保留56/1848。未改IPA ABI。

335核心+签名IPA构建119.46秒通过/SDK原work恢复，fullbasewerror=false、工具Werror。20实际ARMDSO案例全过：12profiles、合并LSC与不足容量、5parser错误、syntheticAWB→CCM+delayedSOF、legacy。独立oracle新编译333固定源GetIndexPtTrigger/CalculateInterpolationRatio+原InterpolationData/CalculateHWSetting，所有10501整数K期望供矩阵核对；不是移植实现自测，也不冒充原厂HAL指令。源码准备Meson匹配与合同80bytestruct/76byte磁盘记录padding问题修正，失败日志私有留存。

335手机R1 worker19479终态complete，临时334 CAMSS+335core/signedIPA，五组unit四摄6阶段6500→2850→asymmanual→6500restore→gain1.25/.75→AWBon，全过。253帧/30图，所有矩阵与独立oracle/explicitmanual一致，147估K帧与331原厂指令wrapper整数K误差0，AWB锁定；五组6500恢复图逐字节等于初始，矩阵与AWB各有真图差。不是光学校准。原模块/媒体/控制恢复、faultdelta0/taint0/休眠/9rails off，PW/WP19667/19708 uid10000。installed仍r26/r21+298/305/318/325；未刷/重启/NV/EEPROM/OTP/persist写。worker摘要沿用temporary_module_only名字，真实同时临时核心/IPA；future335worker字段已改temporary_userspace_and_module_only，仅字段名无新测试需重跑。

下一步从335/334源继续AEC lux实际语义、动态LSC与CCM非CCT触发、模组供应商绑定与统一发布；无需重跑未变的335四摄/20DSO或334模块测试。当前没有活动构建/采集session；335 raw_ssh沿旧严格USB链。不要从旧321/318生成器覆盖新源，也不要宣称已默认部署CCM或正常照明校准完成。

'''+s[end:];p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel335/README.md。335已把332个体CCT/手动矩阵/增益/AWB接到333完整CCM树和334硬件后端；20ARMDSO+四摄五配置六阶段253帧30图通过。临时模块/core/IPA已全部恢复、worker19479终态、PW/WP19667/19708。候选源libcamera335-ccm-built+camera334-ccm-kernel，未安装，仍r26/r21+298/305/318/325。前摄原厂CCM disabled保留，强制启用只实验；主摄供应商未绑，非CCT触发用显式参考DRC1/HDR1/LED0/lux100。下一步AEC lux真实语义/动态LSC/CCM触发/供应商与统一发布，不用重复全量验证。用户关灯继续，不要求开灯。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='335当前：手动矩阵/色温/通道增益/自动WB与硬件CCM已联动，20项ARM IPA检查与四摄五配置六阶段通过；候选临时运行后恢复，尚未安装，非CCT触发仍为诊断值。[335联动](../../reference/kernel335/README.md)。以下为历史记录。\n\n'
if not s.startswith('335当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded335 CCM coupling and restored deployment; complete goal remains active.')
