"""Record sampled ADRC math and packing correction; device evidence stays406."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['adrc','packing','kernel-luts']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert not json.loads((HERE/'packing-r1-validation.json').read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text())
state.update(new_adrc_conversion_pending=False,adrc_sampled_gain_conversion_verified=True,
             adrc_curve_blend_and_quantization_verified=True,tmc_gain_sampling_verified=False,
             tmc_trigger_and_mix_policy_verified=False,full_ltm_numeric_math_complete=False,
             portable_signed_large_positive_delta_corrected=True,phone_accessed=False,
             new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
    path=ROOT/rel;d=json.loads(path.read_text());assert d['latest_work_stage']==408 and d['current_device_revalidated_stage']==406
    for k in ['stage','in_progress_stage','latest_work_stage']:d[k]=409
    d.update(latest_stage_device_mutated=False,latest_stage_phone_accessed=False,
        current_device_revalidated_stage=406,ipe_latest_hardware_stage=406,
        kernel_source_scope='406 maintained clean explicit-IP kernel unchanged.409 portable sampled ADRC conversion/blend/LUT encoding;407 large positive signed delta fix. No new device/default integration.',
        in_progress_installed_scope='409 offline only;last406 restored formal395/393 and four cameras48;zero new phone frames/workers/module changes.',
        ipe_ltm_adrc_sampled_gain_conversion_verified=True,ipe_ltm_adrc_blend_verified=True,
        ipe_ltm_adrc_conversion_evidence=prefix+'kernel409/adrc-validation.json',
        ipe_ltm_adrc_packing_evidence=prefix+'kernel409/packing-validation.json',
        ipe_ltm_adrc_native_lut_evidence=prefix+'kernel409/kernel-luts-validation.json',
        ipe_ltm_adrc_scope='2783 sampled-gain cases incl2135 factory LTM bases+648synthetic;source/targetHAL/hostASanUBSan/ARM exact. Gain curves/mix are synthetic,not recovered TMC outputs.2935typed LUT cases1502720B equal;not hardware or wholeADRC.',
        ipe_ltm_large_positive_signed_delta_fixed=True,ipe_ltm_large_positive_signed_delta_rule='delta>=32768 also forces bit11,as does delta<0;LCE separate clamp/mask retained',
        ipe_ltm_tmc_gain_sampling_verified=False,ipe_ltm_tmc_version_mix_policy_verified=False,
        ipe_ltm_adrc_numeric_math_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
        ipe_ltm_curve_trigger_tree_interpolation_verified=False,ipe_ltm_curve_product_integrated=False,
        ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,
        ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,
        ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,
        ipe_latest_stage_frames_scope='409 offline only;no new hardware frames. Last406 evidence is not counted again.',
        current_health_scope='Last physical check406-r2 restored formal395/393 four cameras48/resources released.407-409 no new device access.',
        icp_next_step='Recover TMC gain sampling/version/percentage/mix policy and DRC-HDR-AEC interpolation;compose LA-mask-weights-scalars/inverseGamma and IFE-IPE domain/stats. Resolve408 raw124/140 and request state commit. Then nonzero hardware/continuous/recovery and standard media request-libcamera;full363 scope remains.')
    path.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through408-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：409（ADRC转换混合量化通过；实机仍406）

先读WORKING-BOUNDARIES.md、reference/kernel409/README.md及408/407/406证据。完整多摄/骁龙ISP目标active。408归档archive/NEXT-SESSION-through408-2026-10-21.md。用户已开灯出门，现场样本按实际照明解释。

## 409新增

reference/kernel409/libipa/ltm_adrc.{h,cpp}：输入65个equivalent12、已采样GainQ10和forwardGamma10，转换65点scale/curve、显式mix混合、两组64段LUT。firstGain>=unity，所有有限非负Gain可用，含floatMax边界；Gamma65个节点显式，不能把IPE256当IFE。曲线做后缀max、3轮顺序scale平滑、平坦区/4轮顺序curve平滑，均用更新后的左邻值。Interpolation按原厂整数/小数拆分、小数放大1e6/double、分别舍入；不能普通lerp/FMA。mix>0 curveRatio3否则1；curve最近round，scale max后truncate int16。baseScale需已按原407-408强度/平滑/attenuation结果round成int16。

原HAL converter362774..3642d4、blend3642d4..364598完整执行27076690指令，唯一provider memcpy2783，不需替代Bionic数学。2783valid/40invalid：全部2135原厂LTM基准区域+648合成边界，source/hostASanUBSan/ARM SDKQEMU共2591514B零差，原HAL也零差。ADRC gain/mix是合成！尚未恢复TMC sampling/版本/百分比/混合策略/trigger树。IFE green来自348 packed64base+末delta推endpoint、352已核对inverse base /4整数产生equivalent[64]并补4095。

新LUT API与原source packers核对2935valid（2783ADRC+24boundary+128random）/2invalid。发现407旧signed encoder漏delta>=32768也需置bit11规则，首轮698B差只在旧407scale，409新API当时0差，packing-r1-validation及两架构原输出私存；已修407条件delta<0||delta>=32768，LCE独立mask不改。packing各2279112B零差；旧4076630条5224440B保持，4083978条4741776B在两架构保持。kernel-luts以维护源同字节colour.c/h编译host编码器，2935typed2800请求/IQ8944中curve+scale1502720B零差、输入和尾canary保持。其余IQ/表填0仅布局验证，不代表完整原厂流水线/硬件；未执行原HAL最终LUT packer。

核心source仍406 samurai-ipe-full-pass-ip406 HEAD b4f382affa9a8be089ccec6170c34d74005103ce，干净未永久装；409只用户空间数值与407共享量化器，不改板级/传感器/主线/DMA/产品默认。409手机帧/worker/模块切换0，脚本全终态。原厂/系数/source/ASM/log/图像/密钥私存/mnt/e/edk2-samurai-out/kernel409及前序；公共mirror本地提交不push/PR，保护无关index。

## 后续核心任务

TMC gain sampling/版本与百分比mix策略、DRC/HDR/AEC动态触发树，LA/mask/weights/scalars及352逆Gamma组合，明确IFE/IPE域、统计粗级、408原字段124/140与重算/候选状态提交；再非零LTM实像素/连续参数/故障恢复和标准media request/libcamera。完整LTM/ADRC仍false，不能以合成gain输入替代TMC。363全部范围继续：第五2MP身份/mux、多模式/帧长防频闪、连续AF/光学、几何多摄同步，implicit fence/SSC/旋转未全面复验。

## 408与407必须保留

Face平滑为原HAL SmoothingForFace，signal来自输入首指针+124 float，BPS(parent0x10003)或raw+140==1跳过且历史计数不动（2/UINTMAX不是TRUE）。124/140标签未完整定位不可猜HDR/闪光等。signal>0状态切换重置90次计算更新，99float previous+(current-previous)*0.05，减count并存历史，count0直接存新值。90不是未经重算条件核对的相机帧数。顺序strength->smoothing->save proposed history->exposure attenuation->quantize，ADRC在后；历史不可存atten后值。API输入state不可与输出/next alias，候选state由后续请求生命周期提交；原HAL全局跨对象生命周期不声称复现。

4083931valid/47invalid：500direct/2135factory/96auto/5x240离线更新，原HAL对照及provider边界见408。最初混长短Unicorn TB越终点3631项后误入日志，model-r1保留，stop_pc hook修正未改原指令。407通用曲线/强度/衰减及量化已核对，LCE独立mask；原source/HAL差异与失败见407。

## 406底层与最后物理设备

stripe416驱动物理reg5c60bit10 IP_EN。原HAL DC&&IP&&有效quarter策略移至单全帧显式API，DC0/IP1时硬件IP关而mask crop扩2，R1条带移位2px/LA无效。406改416=explicit image_processing，勿恢复DC-quarter gate；不据此判原多pass有错。IP&&mask324step/6halo/处理扩2，else328/4，output crop保持。32native/FW checks其余CDM/job不变/IP0旁路全等，小128/282仅离线。W1/Werror0diag；正确core private406/qcom-camss-icp-a5-core-intree-r1.ko415720B SHA b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4；test-intree旧405 ec8bf38d…勿误用。

406R1 rootk406-ltm-r1 worker20269/collector20313终态，52transport+48restore但像素失败保留；R2 rootk406-ltm-r2 worker21352/collector21413/clients终态，换core同adapter/client，52固定44LTM+8Gamma，640/650x480 NV12/21 p8/c2，13模式。IP/mask/linearRGamma/DC+IP对转换对全图零差/位移消失；LAzero/RGammazero/combinedGammazero Y0UV128；LA2048/1024灰块128/64零差，不是彩色全图常量；LTM+linearGamma最大差1；所有NV12/21归一化全等。两轮200仅transport，不是全像素通过；最后normal epoch48；407-409无手机帧不得重复。

最后实际406正式core395/adapter393/CAMSS389，r30/r25四摄IMX471/IMX319/S5K3M5/GW1各12共48direct,error/cancel/extra0。CPU/IRQ/PM/maps/import释放，ICP/CAMSS/双CCI suspended，17clks0/9railsdisabled-users0/taint0，PW21581/WP21584 uid10000单例，owner_refs53桌面句柄；无测试参数/dump/timeout/新增fault/重启/刷写。407-409未重新访问，不作新健康声明。

host406→405…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，同boot394。保护394丢ACK失败reboot/206061Bramoops及395 reset assert2us/deassert/readback/双IPE freshACK后释放修复，未知状态先查不重复旧事务。Image363 release7.3.0-rc6-rmx1931-samurai-k363+、静态DT389/logdump365/SGowner/FW不变。405typedLTM2800锁内copy/check再MAP，IQ/DMI/LUT同request/未知DMA整parcel保留；IQ8944/pre32/post96/type1-opcode1-reg5c08/13LUT2736，其他布局见406。

source/build先root storage284.mounted_build()挂原32GiB ext4，勿格式化/重建。rootPYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。保护NV/OTP/个体备份/密钥及电池温控。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从409继续完整多摄/骁龙ISP目标active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel409/README.md。新sampledGainQ10/equivalent12/forwardGamma10各65点->ADRC curve-scale->显式mix混合->量化，2783valid/40invalid source/原HAL27076690指令/hostASanUBSan/ARM全等；Gain/mix仍合成，TMCsampling/版本/百分比/动态树未做。2935pack+native typed LUT1502720B全等，407 delta>=32768也置bit11旧漏修正/首轮698B失败保留；旧4076630与4083978记录保持。408历史必须在atten前存，候选state不原地提交，raw124/140标签未全定位。核心仍406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装，保留416=explicitIP勿恢复DC-quarter；407-409手机0，最后406fixed52及正式395/393四摄48恢复/资源释放/taint0，同guard394/旧worker终态。下一步TMC gain sampling/动态树及其余表/输入域统计/请求提交，再非零硬件/连续恢复/标准media request-libcamera，363全部范围保持。先storage284挂原ext4，原厂系数密钥私存，公共本地提交不push/PR。\n')
note='409当前：已采样ADRC增益到LTM转换、混合与量化通过，2783项数值和2935项原生LUT对照零差，补正大正差值规则；TMC采样与动态树继续，最后实机仍406。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel409/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel409/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel409/README.md')]:
    p=ROOT/rel;first,tail=p.read_text().split('\n\n',1);assert first.startswith('408当前：');p.write_text(note+'[409证据]('+link+')。以下为历史。\n\n'+tail)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[408 LTM Face平滑与状态顺序](reference/kernel408/README.md)','[409 ADRC转换混合与量化](reference/kernel409/README.md)'))
print(json.dumps(dict(stage=409,checkpoint_updated=True,last_device_stage=406,next_session_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_active=True)))
