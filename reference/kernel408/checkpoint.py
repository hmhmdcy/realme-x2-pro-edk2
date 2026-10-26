"""Record offline temporal math without inventing another hardware epoch."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for name in ['temporal','api']:
    assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert not json.loads((HERE/'model-r1-validation.json').read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text())
state.update(new_temporal_math_pending=False,portable_temporal_primitive_verified=True,
             complete_curve_phase_with_temporal_verified=True,
             temporal_control_field_identities_fully_verified=False,
             product_state_commit_hook_integrated=False,full_ltm_numeric_math_complete=False,
             new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),
                   ('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
    path=ROOT/rel;d=json.loads(path.read_text())
    assert d['latest_work_stage']==407 and d['current_device_revalidated_stage']==406
    for key in ['stage','in_progress_stage','latest_work_stage']:d[key]=408
    d.update(latest_stage_device_mutated=False,latest_stage_phone_accessed=False,
             current_device_revalidated_stage=406,ipe_latest_hardware_stage=406,
             kernel_source_scope='406 maintained clean explicit-IP candidate unchanged.408 adds portable target Face smoothing and separates407 curve phases;no kernel/board/sensor/default/product changes.',
             in_progress_installed_scope='408 offline only,zero phone frames/workers/module changes;last406 restored formal395/393 four cameras48.',
             ipe_ltm_oem_temporal_primitive_math_verified=True,
             ipe_ltm_oem_temporal_primitive_evidence=prefix+'kernel408/temporal-validation.json',
             ipe_ltm_oem_temporal_api_evidence=prefix+'kernel408/api-validation.json',
             ipe_ltm_oem_temporal_scope='SmoothingForFace:90 recalculation updates at0.05 after sign transition;BPS or rawAEC140==1 skips state update;history precedes attenuation.3931valid/47invalid,2135factory,96auto,5x240offline sequences;hostASanUBSan/ARM exact. Raw124/140 tag names and product trigger/commit integration unverified.',
             ipe_ltm_oem_temporal_smoothing_verified=False,
             ipe_ltm_oem_temporal_hardware_verified=False,
             ipe_ltm_oem_temporal_upstream_tags_verified=False,
             ipe_ltm_oem_temporal_product_state_commit_integrated=False,
             ipe_ltm_curve_phase_order_verified=True,
             ipe_ltm_curve_phase_order='strength->Face smoothing->save proposed history->exposure attenuation->quantize;not full LTM/ADRC',
             ipe_ltm_legacy_curve_api_regression_evidence=prefix+'kernel408/temporal-validation.json',
             ipe_ltm_full_factory_numeric_math_verified=False,
             ipe_ltm_adrc_numeric_math_verified=False,
             ipe_ltm_curve_trigger_tree_interpolation_verified=False,
             ipe_ltm_curve_product_integrated=False,
             ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,
             ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,
             ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,
             ipe_latest_stage_frames_scope='408 zero hardware frames;3931 tests include1200 offline variant updates,not camera captures. Last real406 evidence not counted again.',
             current_health_scope='Last physically checked406-r2 restored formal395/393,four cameras48,resources released.407/408 offline only,not fresh phone health checks.',
             icp_next_step='Recover ADRC and DRC/HDR/AEC trigger interpolation;compose remaining LA/mask/weights/scalars/inverseGamma. Resolve target input124/140 identities and recalculation/commit semantics,IFE/IPE domain/stats. Then nonzero hardware/continuous/recovery and standard media request/libcamera;full363 scope remains.')
    path.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through407-2026-10-21.md'
assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：408（本机Face平滑与曲线顺序通过；实机仍406）

先读WORKING-BOUNDARIES.md、reference/kernel408/README.md及407/406证据。完整多摄/骁龙ISP目标active，407归档archive/NEXT-SESSION-through407-2026-10-21.md。用户已开灯出门，现场样本按实际照明解释。

## 本轮408

reference/kernel408/libipa/ltm_face_smoothing.{h,cpp}恢复原HAL SmoothingForFace。目标对象448从输入首指针对象+124复制float；452为parentNode==0x10003(BPS)；456从原+140复制u32。较新headers不足以证明原124/140上游标签名，保留raw信号/门控，不猜HDR/闪光等。BPS或raw140==1跳过且历史计数均不更新（2/UINTMAX不等于1）。非跳过：signal>0状态改变重置90次计算更新，99float previous+(current-previous)*0.05，计数减1，随后存历史；0计数直接保存。90不是未经重算条件核对的相机帧数。

顺序strength->smoothing->save history->exposure attenuation->quantization，历史不可用衰减输出。407公共模块新增prepare/attenuate阶段，旧calculate接口保持。API传const上一状态，返回候选下一状态，禁止输入状态/输出别名；未来由各pipeline和请求生命周期决定何时提交。原HAL全局状态的跨对象生命周期不声称复现，产品未接入/未默认启用。中间volatilefloat保留乘法/加法舍入，FPcontract=fast仍等同目标独立FSUB/FMUL/FADD。

3931valid+47invalid：500direct、全部2135factory区域、96auto、五模组各240离线连续更新。原HAL360560..360ac8 primitive，35ec64..360c3c完整曲线阶段共4161408指令，327skip、1218reset、3099filter、2062history!=attenuated。hostASanUBSan/ARM SDKQEMU output/state/quantized及invalid共4741776B零差；旧4076630条5224440B保持。api-validation再次以当前源码核对3978新记录及已知history90/output45、LCE±52.5/±26.25、null/alias/NaN拒绝。powf12480次hostlibm、memcpy3604provider；不是targetBionic、最终HAL LUT packer/整Execute/硬件调校。原HALfloat按407验证规则量化。

初始模型3631项后由完整区间切primitive，Unicorn复用长TB越过短终点误入360d50日志；model-r1-validation失败保留/输入私存。step hook显式在stop_pc停，未改原指令/数学；修正后通过。检查脚本已终态，无手机worker。

407已有自动/手动/强度/曝光衰减/scale-LCE量化，149根2135区域x3曝光+48manual+96auto共6549，host/ARM/原HAL片段99float零差；源doublepow仅auto4float字节不同/最大6.1035e-5，量化零差。LCE负delta仅mask，不共用LTM负delta sign-force，首轮208B失败保留。原生encoder typed2800/IQ8944页2514816B零差/3536非零项，未硬件。408没有重做或声称其余表/完整LTM数值完成。

## 源与下一步

内核仍406 samurai-ipe-full-pass-ip406 HEAD b4f382affa9a8be089ccec6170c34d74005103ce干净未永久安装。408只改用户空间数学（含407公共.h/.cpp和其README），板级/传感器/主线/DMA/产品默认不变。source-state原厂字段/ADRC/fullmath/product/硬件边界均保留false。公共mirror仅本地提交，保护无关index，不push/PR；原厂coeff/source/ASM/log/图像/密钥私存/mnt/e/edk2-samurai-out/kernel408及前序。

继续ADRC、DRC/HDR/AEC动态树、其余LA/mask/weights/scalars与352逆Gamma，明确124/140字段来源、触发重算/状态提交、IFE/IPE域与统计粗级，再非零LTM实像素/连续参数/故障恢复和标准media request/libcamera。363全部范围继续：第五2MP身份/mux、多模式/帧长防频闪、连续AF/光学、几何多摄同步；implicit fence/SSC/旋转未全面复验。

## 必须保留的406底层与最后实机

stripe+416驱动物理reg5c60bit10 IP_EN。原HAL DC&&IP&&有效quarter策略移到当前单全帧显式API导致DC0/IP1硬件IP关但mask crop扩2，R1条带移位2px/LA无效。406修416=explicit image_processing；勿恢复DC-quarter gate，不据此判原HAL多pass有错。IP&&mask324step/6halo/处理扩2，else328/4，输出crop保持。32native/FW checks其余CDM/job不变/IP0旁路全等，小128/282仅离线。W1/Werror0diag。正确核心private406/core-intree-r1.ko415720B SHA b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4；test-intree旧405 ec8bf38d…勿误用。

406R1 rootk406-ltm-r1 worker20269/collector20313终态，52transport+48restore但像素失败保留；R2 rootk406-ltm-r2 worker21352/collector21413及clients终态，换core同adapter/client，52固定请求44LTM+8Gamma，640/650x480 NV12/21 p8/c2，13模式。IP/mask/linearRGamma/DC+IP对转换对全图零差，位移消失；LAzero/RGammazero/combinedGammazero全Y0UV128；LA2048/1024灰块128/64零误差，不是彩色全图常量；LTM+linearGamma最大差1；所有模式NV12/21归一化全等。两轮200只transport不是全像素通过，最后normal epoch48；407/408手机帧0不得重复计入。

最后实际406正式core395/adapter393/CAMSS389恢复，r30/r25四摄IMX471/IMX319/S5K3M5/GW1各12共48direct,error/cancel/extra0。CPU/IRQ/PM/maps/import释放，ICP/CAMSS/双CCI suspended，17clks0/9railsdisabled-users0/taint0，PW21581/WP21584 uid10000单例，owner_refs53桌面句柄；无测试参数/dump/timeout/新增相关fault/重启/刷写。407/408未重新访问，不作新健康声明。

host406→405…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，同boot394。保留394丢ACK失败reboot/206061Bramoops与395 reset assert2us/deassert/readback及双IPE freshACK后释放修复。未知状态先查不重复旧事务。Image363 release7.3.0-rc6-rmx1931-samurai-k363+、静态DT389/logdump365/SGowner/FW不变。405typedLTM2800、lock内copy/check再MAP、IQ/DMI/LUT同request/未知DMA整parcel保留，组合IQ8944/pre32/post96、type1/opcode1/reg5c08、13LUT2736B，逆Gamma输入IFEgreen64不可IPE256。其它布局见406/407。

source/build先root reference/kernel284/storage.py mounted_build()挂原32GiB ext4，勿格式化/重建。rootPYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。保护NV/OTP/个体备份/密钥及电池温控。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从408继续完整多摄/骁龙ISP目标active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md和reference/kernel408/README.md。新Face smoothing raw信号124/门控140标签未完全定位，BPS或140==1跳过且状态不动，signal正状态切换重置90计算更新，0.05分开舍入，历史在曝光衰减前存。新候选状态只返回不原地提交/禁止state与输出别名；原HAL全局生命周期不外推。3931valid/47invalid（2135factory,96auto,5x240离线更新）hostASanUBSan/ARM及原HAL两范围输出状态量化全等；旧4076630记录保持。Unicorn混长短TB越终点模型失败已保留并用stop_pc hook修正，未改原指令。完整ADRC/动态树/其余表/产品状态提交仍未做。源码仍406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久安装，保持416=explicitIP勿恢复DC-quarter条件。407/408手机0，最后406R2fixed52和正式395/393四摄48释放/taint0/同guard394，旧worker全终态。下一步ADRC/DRC-HDR-AEC树/LA-mask-weights-scalars逆Gamma、124-140来源/重算及提交/IFE-IPE域统计，再非零硬件/连续恢复/标准media request-libcamera，363全范围继续。source/build先storage284挂原ext4，原厂表密钥私存，公共本地提交不push/PR。\n')
note='408当前：本机LTM Face平滑及历史先于曝光衰减的顺序已移植，3931项有效／47项非法与原HAL、主机及ARM对照通过，旧接口保持；ADRC与动态树继续，最后手机实证仍406。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel408/README.md'),
                 ('linux-port/camera/kernel/README.md','../../../reference/kernel408/README.md'),
                 ('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel408/README.md')]:
    path=ROOT/rel;first,tail=path.read_text().split('\n\n',1);assert first.startswith('407当前：')
    path.write_text(note+'[408证据]('+link+')。以下为历史。\n\n'+tail)
path=ROOT/'DOCS-INDEX.md'
path.write_text(path.read_text().replace('[407 LTM曲线与曝光衰减](reference/kernel407/README.md)',
                                       '[408 LTM Face平滑与状态顺序](reference/kernel408/README.md)'))
print(json.dumps(dict(stage=408,checkpoint_updated=True,last_device_stage=406,
                      next_session_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_active=True)))
