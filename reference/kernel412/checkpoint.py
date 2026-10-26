"""Record TMC11 factory/mode and model2 primitive evidence without a device epoch."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['factory-tmc11','mode-tmc','sampling','chain']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed']
for n in ['sampling-r1','source-helper-r1']:assert not json.loads((HERE/(n+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text())
state.update(tmc11_recovery_pending=False,tmc11_factory_tree_extraction_verified=True,
    tmc10_tmc11_ordinary_mode_root_selection_verified=True,tmc11_all_factory_roots_use_pchip5=True,
    tmc11_ltm_normalization_pchip_contrast_target_verified=True,tmc11_ltm_numeric_lut_chain_verified=True,
    tmc11_knee_generation_target_verified=False,tmc11_histogram_generation_target_verified=False,
    tmc11_drc_hdr_aec_interpolation_verified=False,tmc_runtime_version_selection_verified=False,
    tmc11_verified=False,tmc_trigger_and_mix_policy_verified=False,full_ltm_numeric_math_complete=False,
    phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
    p=ROOT/rel;d=json.loads(p.read_text());assert d['latest_work_stage']==411 and d['current_device_revalidated_stage']==406
    for key in ['stage','in_progress_stage','latest_work_stage']:d[key]=412
    d.update(latest_stage_device_mutated=False,latest_stage_phone_accessed=False,
        current_device_revalidated_stage=406,ipe_latest_hardware_stage=406,
        kernel_source_scope='406 clean explicit-IP kernel unchanged.412 offline complete TMC11 factory extraction/mode binding and model2 normalization/PCHIP/contrast;ADRC/native LUT connection.No device/default integration.',
        in_progress_installed_scope='412 offline only;last406 restored formal395/393 four cameras48;no new phone workers/frames/module changes.',
        ipe_ltm_tmc11_factory_extraction_verified=True,ipe_ltm_tmc11_model2_all_roots_verified=True,
        ipe_ltm_tmc_ordinary_mode_selection_verified=True,ipe_ltm_tmc11_ltm_sampling_verified=True,
        ipe_ltm_tmc11_ltm_native_lut_chain_verified=True,ipe_ltm_tmc11_knee_target_verified=False,
        ipe_ltm_tmc11_histogram_generation_verified=False,ipe_ltm_tmc11_drc_hdr_aec_interpolation_verified=False,
        ipe_ltm_tmc11_factory_evidence=prefix+'kernel412/factory-tmc11-validation.json',
        ipe_ltm_tmc_mode_evidence=prefix+'kernel412/mode-tmc-validation.json',
        ipe_ltm_tmc11_sampling_evidence=prefix+'kernel412/sampling-validation.json',
        ipe_ltm_tmc11_chain_evidence=prefix+'kernel412/chain-validation.json',
        ipe_ltm_tmc11_scope='68roots198regions matched OEM XML;4physical/14ordinary contexts/28queries match original selector.Tele TMC10off/TMC11on,front both off;not runtime metadata.All model2/order5.1192+16invalid target/host/ARM961568B equal;source knees and synthetic histogram fixtures,not target generation.1026chains525312native LUT bytes equal;166finite subunity rejected.No hardware.',
        ipe_ltm_tmc_version_mix_policy_verified=False,ipe_ltm_tmc11_verified=False,
        ipe_ltm_adrc_numeric_math_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
        ipe_ltm_curve_trigger_tree_interpolation_verified=False,ipe_ltm_curve_product_integrated=False,
        ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,
        ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,
        ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,
        ipe_latest_stage_frames_scope='412 offline only;last406 device evidence not counted again.',
        current_health_scope='Last physical check406-r2 restored formal395/393 four cameras48/resources released.407-412 no device access.',
        icp_next_step='Verify target TMC11 knee/histogram generation and DRC-HDR-AEC interpolation plus actual runtime version metadata;compose remaining LA-mask-weights-scalars/inverseGamma,IFE-IPE domain/stats.Resolve408 raw124/140 and request state commit.Then nonzero hardware/continuous/recovery/media request-libcamera;full363 scope remains.')
    p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through411-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：412（TMC11树/模式与PCHIP对比度采样；实机仍406）

先读WORKING-BOUNDARIES.md、reference/kernel412/README.md及411/410/409/408/406证据。完整多摄/骁龙ISP目标active。411归档archive/NEXT-SESSION-through411-2026-10-21.md。用户开灯出门，现场按实际光照/曝光解释。

## 412新增与边界

原厂TMC11五供应商共68根198区，28字段44scalar及控制/reserve/DRC-HDR-AEC完整树全与OEM ParameterParser XML一致。原payload/mode tree不变，关闭根保持；全部curve_model2/order5=PCHIP5；Bezier非这些根的选择，未实现/验证。

用原厂GetModule和独立mode_tree核对4物理摄像头14普通Preview/Video上下文28查询。都选TMC10 root66/TMC11 root63；主摄/广角两版enabled，前摄两版off，长焦TMC10off但TMC11on。qtechGW1未绑定物理模式，仅供应商数值夹具；五文件非第五摄像头。原选择器只保name/UID/mode；普通上下文无Feature/Scene/Effect，不证明Android实际版本。已定位版本元数据layout分支2dffe4附近，但不能据静态树推断最终生效版。

kernel412/libipa/tmc11_ltm：actual normalize362588..3626dc前64等效节点(eq+1)/4095，只clip node63，node64固定初始化1；TMC10无+1勿混。PCHIP3c7070三段/9coef、gain[0]=gain[1]，mix=clamp(2-y1/x1,0,1)非直接darkGain。contrast3c7c98始终读hist曲线，保留推进hi，powf后Q10裁剪0..8191；固定源码有HEflag条件且没应用上限。本机下界<=unity在linear<1时与源码<不同，不能std::clamp倒置bounds，API支持有限非负linear。

sampling1192=198区x3gainx2dark1188+4有限subunity线性边界，另16invalid，target/hostASanUBSan/ARM SDKQEMU各961568B零差，fp-contractfast；13171655目标指令/77480powf hostlibm非Bionic。**膝点/9coef是原厂anchors+固定源码辅助函数夹具，未执行本机TMC11膝点/直方图生成！HE曲线合成非现场统计。** sourcePCHIP普通1188零差、边界7B差；sourcecontrast16692B差，source-helper-r1保留不冒称源码全等。sampling-r1两架构526B差仅非法夹具错改Y0期望Y1拒绝（280->284），参考/原输出私存。

chain1192中1026有效、166finite firstGain<1024沿既有ADRC契约拒绝不夹unity。targetADRC9855335指令/memcpy1026，sourcepacker/host/ARM/native typed LUT525312B全等。其余IQ/LUT填0，仅数值，原HAL最终packer未执行/无硬件提交。

## 当前层级与后续

内核仍406 samurai-ipe-full-pass-ip406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装；412只用户空间数值，SoC/板级DT/主线/传感器/DMA/请求/default不改。407-412手机访问/新worker/新帧0，不重复406；公共mirror本地提交不push/PR，保留无关index，原厂材料private /mnt/e/edk2-samurai-out/kernel412及前序。

下一步本机TMC11完整膝点/直方图生成、DRC/HDR/AEC多层插值与实际版本metadata；LA/mask/weights/scalars、352inverseGamma，IFE/IPE域/统计粗级、408raw124/140与候选state提交；再非零调校实像素/连续参数/恢复及media request-libcamera。完整LTM/ADRC仍false。reference/kernel363/REMAINING-CAMERA-SCOPE.md完整范围：第五2MP/OV02A1B身份mux勿猜OV02A10、多模式/帧长防频闪、连续AF/光学、几何多摄同步，implicitfences/SSC/旋转未全复验。

## 411至407保留规则

411已按本机修正共享410 TMC10：logf/float商、只1e-9unity，无公开源coarse0.0001；旧1301中100curve/70gain/58LUT4044B变化保留。AEC11字段/选区indices/ratio已完整HAL核对，区内copy/gap插值，double ratio与整数/小数拆分1e6，按序firstmatch不排序。实际input+16gain/+20lux、out+16X/+32Y，首轮ABI失败保留。TMC10前/长焦关闭不等于TMC11状态；全部数值与边界见411。

409 ADRC后缀max/顺序3scale与4curve平滑用更新左邻，mix>0curveRatio3else1，curve round/scale max后truncate。407signed scale delta<0或>=32768都置bit11，首轮漏大正delta698B保留已修；LCE独立clamp/mask，旧4076630/4083978保持。

408Face信号input首指针+124float，BPS10003或raw140==1跳过state不动，标签未全定位勿猜HDR/flash；signal>0切换重置90次计算更新非90相机帧。previous+(current-previous)*.05；strength->smoothing->save proposed history->attenuation->quant，ADRC后。history勿存atten后；state不alias且需请求生命周期提交。3931valid47invalid全等，Unicorn TB长短越界首轮保留，stop_pc hook修正原指令未改。

## 406最后物理设备/保护

stripe416驱动reg5c60bit10 IP_EN。原HAL DC&&IP&&quarter移至单fullframe显式API导致DC0/IP1硬件IP关而mask扩2，R1移位2px/LA无效。406改416=explicit image_processing勿恢复DCquarter，不据此判原multipass有错；IP&&mask324step/6halo/处理扩2 else328/4，outputcrop保持。32native/FW仅IPbit变，小128/282仅离线。正确private406/core-intree-r1.ko415720B SHA b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4；test-intree旧405415752/ec8bf38d…勿混。

406R1 worker20269/collector20313终态，52transport+48restore但像素失败；R2 worker21352/collector21413/clients终态，52fixed44LTM+8Gamma，640/650x480 NV12/21 p8c2/13模式。IP/mask/linearRGamma/DC+IP全图零差/位移消失；LAzero/RGammazero/Gammazero Y0UV128；LA2048/1024灰块128/64零差非彩色全图常量；LTM+linearGamma最大差1，NV12/21归一化全等。两轮200仅transport非全像素通过；最后normal48。正式core395/adapter393/CAMSS389，r30/r25四摄各12=48direct/error/cancel/extra0，CPU/IRQ/PM/maps/import释放、ICP/CAMSS/双CCI suspended、17clks0/9railsdisabled-users0/taint0，PW21581/WP21584 uid10000单例/owner_refs53桌面句柄，无test参数/dump/timeout/新增fault/reboot/flash。407-412未访问不作新健康声明。

host406→405…394同boot394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt；保护394丢ACK失败reboot/206061Bramoops、395reset assert2us/deassert/readback/双IPE freshACK后退役修复，未知状态先查不重启旧事务。Image363 release7.3.0-rc6-rmx1931-samurai-k363+、DT389/logdump365/SGownerFW不变。405typed2800锁内copy/check再MAP，IQ8944/pre32/post96/type1-opcode1-reg5c08/13LUT2736，同request/未知DMA整parcel保留。

source/build先root reference/kernel284/storage.py mounted_build()挂原32GiB ext4，勿格式化重建；rootPYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。保护NV/OTP/个体备份/密钥/电池温控。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从412继续完整多摄/骁龙ISP目标active。读NEXT-SESSION/WORKING-BOUNDARIES/reference/kernel412/README。新TMC11 68根198区XML全等，原模式选择器4物理14普通上下文28queries匹配：前两版off，长焦TMC10off/TMC11on，主/广两版on，非实际运行版观测。全model2/order5，PCHIP/normalize/HE按原HAL核对1192+16invalid两架构961568B零差，1026chain native LUT525312B全等/166subunity拒绝。source生成膝点coef夹具+合成HE，未执行本机TMC11膝点/直方图/动态树；下一步补这些和实际版本metadata、其余表/输入域统计/408state，再非零硬件连续恢复/libcamera。TMC11eq+1/4095只clip63/64固定1，mix y1/x1，HE始终读hist并clip8191，PCHIP<=1边界；source7/16692B差与首轮非法fixture偏移280->284失败保留。411TMC10/AEC证据保持。内核406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装，416explicitIP勿恢复DCquarter，395reset修复保持；407-412手机0最后406正式395393四摄48资源释放，同guard394。363完整范围/开灯条件保持；先storage284挂原ext4，原厂材料私存，公共只本地提交不push/PR。\n')
note='412当前：原厂TMC11共68根198区及四摄模式绑定核对，PCHIP/对比度采样通过；1026份LUT共525312字节零差。完整膝点/直方图/动态树与实机接入继续，最后实机仍406。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel412/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel412/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel412/README.md')]:
    p=ROOT/rel;first,tail=p.read_text().split('\n\n',1);assert first.startswith('411当前：');p.write_text(note+'[412证据]('+link+')。以下为历史。\n\n'+tail)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[411 本机TMC10膝点与AEC插值](reference/kernel411/README.md)','[412 TMC11原厂树与PCHIP采样](reference/kernel412/README.md)'))
print(json.dumps(dict(stage=412,next_session_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,last_device_stage=406,full_goal_active=True)))
