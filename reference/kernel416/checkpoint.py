"""Record complete offline TMC11 flow; next milestone is runnable candidate requests."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['input','execute']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text())
state.pop('tmc_ipe_request_version_global_table_owner_verified',None)
state.update(tmc_ipe_request_version_global_table_claim_retracted=True,tmc_ipe_input_stack_base_verified=True,
    tmc_ipe_request_version_binding_verified=True,tmc11_hdr_input_field_identities_verified=True,
    tmc11_hdr_input_domain='AEC exposure slot1/slot0 time and sensitivity ratios;long/short enum names not assumed',
    tmc11_full_execute_offline_verified=True,tmc11_continuous_state_and_ipe_cache_composition_verified=True,
    tmc_runtime_metadata_actually_observed=False,tmc_runtime_version_selection_verified=False,
    tmc11_verified=False,full_ltm_numeric_math_complete=False,phone_accessed=False,
    new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
    p=ROOT/rel;d=json.loads(p.read_text());assert d['latest_work_stage']==415 and d['current_device_revalidated_stage']==406
    for key in ['stage','in_progress_stage','latest_work_stage']:d[key]=416
    d.update(latest_stage_device_mutated=False,latest_stage_phone_accessed=False,
        kernel_source_scope='406 clean explicit-IP kernel unchanged.416 correct IPE stack base/version binding,AEC HDR domains,whole target SWTMC11 Execute and portable composed continuous step.No product/device/default integration.',
        in_progress_installed_scope='416 offline only;last406 restored formal395/393 four cameras48;no new phone workers/frames/module changes.',
        ipe_ltm_tmc_ipe_request_version_binding_verified=True,ipe_ltm_tmc11_hdr_input_domain_verified=True,
        ipe_ltm_tmc11_full_execute_offline_verified=True,ipe_ltm_tmc11_continuous_composition_verified=True,
        ipe_ltm_tmc_input_evidence=prefix+'kernel416/input-validation.json',
        ipe_ltm_tmc_execute_evidence=prefix+'kernel416/execute-validation.json',
        ipe_ltm_tmc11_scope='416 retracts415 global-version-table claim:SP240 is256B before ISPInputSP340;field actual2760 tuning manager.Actual binder2d6564..2d6590 sets1 only cache.version1 otherwise initial0.HDR88/92 time/sensitivity slot1/0 ratios.1002+4 input20120B equal.154whole native Execute calls/14contexts/4physical/72calculations;host+ARM1316392B equal including fullADRC/cache/binding/LTMgate;12module/property-version mismatches preserve old output.Synthetic stats/transitions,not Android/product/hardware.',
        ipe_ltm_tmc_version_mix_policy_verified=False,ipe_ltm_tmc11_verified=False,
        ipe_ltm_adrc_numeric_math_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
        ipe_ltm_curve_product_integrated=False,ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,
        ipe_latest_stage_frames_scope='416 offline only;last406 device evidence not counted again.',
        current_health_scope='Last physical check406-r2 restored formal395/393 four cameras48/resources released.407-416 no device access.',
        icp_next_step='Prioritize runnable candidate request/IPA path using405/406 typed diagnostics and407..416 verified math;identify only needed remaining LA/mask/weights/scalars/inverseGamma/domain/stats gaps.Then nonzero hardware/continuous/recovery and request-state lifecycle/libcamera;do not repeat passed TMC expansions.Full363 camera scope remains.')
    p.write_text(json.dumps(d,indent=2)+'\n')
prior=(ROOT/'NEXT-SESSION.md').read_text();archive=ROOT/'archive/NEXT-SESSION-through415-2026-10-21.md'
assert not archive.exists();archive.write_text(prior)
tail=prior.split('## 414/413/412/411保留',1)[1].replace('407-415','407-416').replace('kernel415及前序','kernel416及前序')
tail='''

414 actual三层383cdc..384048，2846+15两架构514980B等；68根198区全ctrl[0,0]且DRC/HDR各1段，forcedgain/HDR1/2/多层只夹具，qtechGW1未绑定不是第五相机。136动态chain/51gap/131LUT67072B等、5subunity拒绝，最终原HALpacker未跑。root136/DRC24/HDR40/AEC192、rootctrl68/72 core120/128，X23=SP64；完整细节见414。

413gen384048..38565c，31组覆盖198区156+12两架构1393056B等，154finite/2nonfinite拒绝；142LUT72704B等/12subunity拒绝。X24=module112编译Gamma257末1023，controlledGamma非运行证据；darkY=anchor2/ratio不clipanchor1，r1 26项251B失败已修；model-r1 X23错/r2漏X24保留。nohist是BYTE1不是float1；hist4轮原地平滑左值已更新，coeff b按/h再/h。412模式树/411TMC10差异详其README；旧测试复用。

## 底层与设备'''+tail.split('## 底层与设备',1)[1]
prefix='''# 当前检查点：416（真实版本绑定/HDR域/完整TMC11执行通过；实机仍406）

先读WORKING-BOUNDARIES.md、reference/kernel416/README.md。完整多摄/骁龙ISP目标active。415归档archive/NEXT-SESSION-through415-2026-10-21.md。用户开灯上班，问完成时间；已答全scope粗估数周且可能更长，未承诺日期。后续优先可运行候选请求/实机闭环，不再扩展已通过TMC离线矩阵。

## 416新增与415纠正

真实ISPInput在IPE主函数SP+340，2cf504..2cf514 memset19928B、2d7a64传模块Execute。415错用SP240早256B，把2cfa9c管理器指针写入当作版本；actual为input2760 TuningManager，公共415README已更正，不再追全局版本表。真实binder2d6564..2d6590读node149a8+4 version，仅==1写请求1，否则保持初始化0；始终指向node149a8缓存到input3024。16版号/初值组合执行原指令核对。

HDR377120..3771b8：AEC槽0 time/gain/sens偏移0/8/12，槽1为24/32/36；2872/2876/2880为槽1/0的时间/增益/灵敏度比。time0==0或float分母abs<1e-9保持1。TMC11 module88←2872曝光时间比、92←2880灵敏度比，身份/域已证；Long/Short枚举名未假定。control2仍零，不是2876增益比。1002valid+4invalid，两架构20120B等；两target溢出结果拒绝，16memset/35588target指令。

execute-model实际call383728到RET非拼接片段，已有清零ADRC4236存储，原factory root/完整reserve；不测分配。execute-runner单进程组合415policy/414tree/413gen/415cache/416binding/LTMgate，对4物理14普通上下文各11步=154完整调用/72重算，两架构1316392B0差。原Execute17899720指令；math logf/expf/powf hostlibm非Bionic。两不可变合成hist，仅UID/enable副本和14次缺失属性为明确合成，根选择器复用412不重跑。

序列涵盖hist-only/force相等不换hist/锁缓存更新/解锁不重算/force用旧hist/缺属性/新UID关闭恢复/同UID翻enable不刷新/敏感度变化。12次module.version0但ADRC旧version1，IPE按对象头仍bind1；wire一致不是硬件有效性证明。整个IFE发布/整个IPE Execute未执行，Android实际metadata/产品request未接，fullTMC11产品/fullLTM/default仍false。

415原状态733+7/consumer1152+3/cache63+1两架构44400/18480/271360B等保持。policy仅UID变刷新，raw enable→3016，六floatabs→double<1e-9；禁用仍发布旧ADRC3024/清module104，双锁在缓存/版本更新后抑calc；metadata缺失只清enable/未知版留旧knees，v0拷32/v1拷40。此前ISPInput112标签也已纠正为node14938辅助基址+112=node149a8缓存头。LTM own10 gate rootenable1/useLtm1/requestversion0，否则copyupstreamLtm，无globalenable/version再gate，自身10分配/完整计算未跑。

## 下一步以候选请求和实机验收推进

先读405/406 typed LTM接口及固定诊断客户端、现有r30/r25分发/IPA路径，落实407..416数值接入候选request的状态/表生成接口；逐项确认非零调校真正需要的LA/mask/weights/scalars、352inverseGamma、IFE/IPE输入域/统计缺口，针对该缺口补，避免再重复TMC已通过用例。408raw124/140身份、state候选随完成提交/失败丢弃仍需解决。随后受控非零LTM/颜色/曝光实机、连续参数/资源恢复/标准media request-libcamera；不把离线通过写成实机完成。

reference/kernel363/REMAINING-CAMERA-SCOPE.md全目标保持：第五2MP/OV02A1B身份mux勿猜OV02A10、多模式/帧长/防频闪、自动与连续AF/光学、几何多摄同步，implicitfences/SSC/旋转未全复验。

## 414/413/412/411保留'''
(ROOT/'NEXT-SESSION.md').write_text(prefix+tail)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从416继续完整多摄/骁龙ISP目标active。读NEXT-SESSION/WORKING-BOUNDARIES/reference/kernel416/README。优先可运行候选请求/实机闭环，不再扩TMC已通过矩阵。真实IPE ISPInput=SP340，415误用SP240把input2760调校管理器当版本已更正；真实binder2d6564缓存version1才设请求1，否则初始0，指向node149a8。HDR module88/92为AEC槽1/0时间/灵敏度比，control2零，1002+4两架构20120B等。完整native SWTMC11 Execute383728到RET，4物理14context×11=154/72calc，两架构1316392B等含policy/ADRC/cache/binder/LTMgate；12module版0/旧对象版1差保留，合成stats/UID/缺失，非Android或硬件。接405/406typed诊断/r30IPA路径，用407..416数值补候选request，仅定位必要LA/mask/weights/scalars/inverseGamma/域统计缺口；408身份/statecommit后非零硬件/连续恢复/libcamera及363全scope保持。内核406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装；stripe416 explicitIP勿恢复DCquarter，395reset修复保持。407-416 phone0，last406正式395/393四摄48 guard394。已开灯；用户问工期答数周粗估无承诺。先storage284挂原ext4；原厂私存，公共仅本地提交不push/PR。\n')
note='416当前：已纠正IPE请求基址并验证真实版本绑定/HDR输入域；完整原厂TMC11 Execute与连续状态154次调用两架构一致。下一步候选请求/实机调校，最后实机仍406。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel416/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel416/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel416/README.md')]:
    p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('415当前：')
    p.write_text(note+'[416证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[415 TMC状态与版本门槛](reference/kernel415/README.md)','[416 完整TMC11执行与真实绑定](reference/kernel416/README.md)'))
print(json.dumps(dict(stage=416,next_session_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,last_device_stage=406,full_goal_active=True)))
