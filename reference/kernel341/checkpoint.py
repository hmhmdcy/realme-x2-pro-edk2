from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['ipa-contract-validation.json','reference-regression-validation.json','control-method-validation.json','runtime-lsc-validation.json','final-state-validation.json']:assert json.loads((HERE/name).read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text());health=json.loads((HERE/'final-state-validation.json').read_text())
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text());d.update(current_camera_evidence=prefix+'reference/kernel341/README.md',in_progress_stage=341,in_progress_evidence=prefix+'reference/kernel341/README.md',in_progress_installed=False,
  dynamic_lsc_integrated=True,dynamic_lsc_deployed=False,dynamic_lsc_evidence=prefix+'reference/kernel341/runtime-lsc-validation.json',dynamic_lsc_frozen_with_wb_ccm_revision=True,dynamic_lsc_explicit_single_unit_pair=True,
  ipa_candidate_source_stage=341,ipa_candidate_source=state['source'],ipa_candidate_source_evidence=prefix+'reference/kernel341/source-state.json',final_health_evidence=prefix+'reference/kernel341/final-state-validation.json',current_adaptation_goal_status='active')
 if 'system_services' in d:d['system_services']=dict(stage=341,services={k:[p['pid'] for p in v] for k,v in health['services'].items()},evidence=prefix+'reference/kernel341/final-state-validation.json')
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：340','# 当前检查点：341',1);start=s.index('下一步341从340候选继续动态LSC');end=s.index('以下保留历史阶段',start)
s=s[:start]+'''341 已完成候选动态LSC：/mnt/samurai-full282/libcamera341-dynamic-lsc-built/src/libcamera-v0.7.2，0036以340为base；新DynamicLensShading解析完整lens/DRC/HDR/LED/AEC/CCT核心树，mode dynamic可选，其他默认static。AEC实时lux/gain，其他坐标显式reference；五份Default根原厂轴均lux_index/sensitivity_ratio且enabled1，单个golden（已核XML）。仅显式golden/unit主表对，非多光源/供应商自动绑定。复用已有单表合成/GRGB均衡/Hermite/Q10；shared tuning_interpolation.h与CCM共用保留数值规则。每revision冻结LSC+CCM+WB，后续stats不能改准备包；不变网格不重传，1792块/1848或1888容量不变，无内核/板级/传感器改动。

341 build83.29sec；ARM10配置143提交，105LSC+125CCM块193160bytes原LSC源码/独立Hermite零差，38次LSC省略；原CCM+静态LSC两合同兼容/3错误配置通过。原函数oracle私有编译封装缺cstddef已补齐。控制方法proof reference/kernel341/control-method-validation.json。动态配置/profile/table/math库只私有，Public patch0036及通用代码可镜像。

341现场：最终8组（4摄factory/unit）各4相位选定369帧/32图/163LSC状态，追踪值与原函数+独立重采样一致，283帧CCM metadata10188bytes零差；8组AWB均锁定，前摄factory CCM仍disabled。14组可重复图案factory/unit图对不同，PN9随机差异不用于证明个体效果。R1主摄两组49/48通过后前摄渐灰AWB缺有效区域450帧终止，保存failure；R2复用主摄，只补剩余，前摄仅手动3phase14/14通过，广角渐灰AWB451/451失败但保留手动图，长焦50/50全过。算法门槛未降；R3前摄用已有PN9(index4)43/43全过；R4广角PN9 44/42全过。PN9按控制和AWB锁定，不要求图像字节稳定，手动相位是生效快照非全滤波收敛。cases-r1/r2/r3.json保留各清单，当前cases.json仅R4广角2项；analyze-probe.py r1,r2,r3,r4合并已通过案例并保留R1/R2失败。私有images-r1..r4，所有run worker终态。

R4曾在prepare-runtime工具完成前错误发送了半写tar，解包EOF、未启动worker。确认无state/worker后保留目录为/var/lib/samurai/k341-dynamic-lsc-r4-incomplete-transfer，再以完整包启动pid25965并完成。代码已改tmp+atomic replace，但仍须等准备工具返回成功后再launch；不可仅超时就重发。recover-transfer.py只针对已验证未启动的那次目录，不能重放。

341结束无活动build/SDK bind/相机worker。手机仍r26/r21+298/305/325/338，PW/WP25981/25984 uid10000，taint0、故障delta0、CAMSS/CCI休眠9railsdisabled/users0；没有安装新IPA/调校包，也未刷写/重启/写NV。source-state动态LSC仅候选，部署以338内核为准。详见reference/kernel341/README.md。

下一步342：从341候选推进实际曝光表物理模式/主摄模组供应商绑定和统一发布；通用代码可以独立发布，但不能把诊断Default/anchor/primaryunit选择冒充已证明的自动工厂选择。正常照明光学、几何同步、连续AF等完整目标仍在。C近满继续E ext4，用341/storage.py sdk_candidate()临时bind构建测试后卸载；勿向C复制大型源码，不重跑未改组件。

'''+s[end:];s=s.replace('以本段340为准','以本段341为准',1).replace('340结束为24236/24239 uid10000。','340结束为24236/24239，341结束为25981/25984 uid10000。',1);p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel341/README.md。341候选动态LSC与WB/CCM同revision冻结并生效，ARM105LSC+125CCM块193160bytes原源码/独立采样零差；4摄factory/unit8组最终369帧/32图/163LSC状态、283帧CCM10188bytes核对，8组AWB全锁定。前/广渐灰过曝有效区域不足失败保留，改既有PN9不降门槛R3/R4通过，PN9随机图不做字节稳定或unit效果依据。R4有一次半写tar未启动，已保留partial目录并成功重发；等prepare工具完成才launch。无活动worker，现机r26/r21+298/305/325/338，PW/WP25981/25984待机taint0。下一步342模式/主摄供应商绑定、统一发布，正常光学/几何同步/连续AF仍未完。新源E ext4 /mnt/samurai-full282/libcamera341-dynamic-lsc-built/src/libcamera-v0.7.2，用341/storage.py sdk_candidate临时bind，C近满勿大副本。用户关灯，继续源码/TPG。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='341当前：候选IPA的动态LSC已与WB/CCM统一排队；四摄工厂/个体配置最终369帧通过，前摄原厂CCM禁用保持。候选未安装，模式/供应商绑定及发布继续。[341详情](../../reference/kernel341/README.md)。以下为历史记录。\n\n'
if not s.startswith('341当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts];paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded341 dynamic LSC, successful cohorts and retained failures; full goal remains active.')
