"""Record target-specific TMC10 correction and AEC interpolation evidence."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['knee','aec','chain']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed']
for n in ['model-r1','prior-source-r1','aec-r1']:assert not json.loads((HERE/(n+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text())
state.update(tmc_target_knee_pending=False,tmc10_knee_generation_target_verified=True,
    tmc10_knee_and_percentage_source_verified=False,tmc10_knee_policy_matches_pinned_source=False,
    tmc10_source_version_difference_corrected=True,tmc10_aec_interpolation_target_verified=True,
    tmc_aec_trigger_interpolation_verified=True,tmc_aec_trigger_interpolation_scope='TMC10 single AEC axis only;not TMC11 DRC/HDR tree or full LTM13 triggers',
    tmc10_numeric_chain_to_native_lut_verified=True,tmc_runtime_version_selection_verified=False,
    tmc_trigger_and_mix_policy_verified=False,tmc11_verified=False,full_ltm_numeric_math_complete=False,
    phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
    p=ROOT/rel;d=json.loads(p.read_text());assert d['latest_work_stage']==410 and d['current_device_revalidated_stage']==406
    for key in ['stage','in_progress_stage','latest_work_stage']:d[key]=411
    d.update(latest_stage_device_mutated=False,latest_stage_phone_accessed=False,
        current_device_revalidated_stage=406,ipe_latest_hardware_stage=406,
        kernel_source_scope='406 clean explicit-IP kernel unchanged.411 target TMC10 knees/percentage correction and complete AEC interpolation,offline numeric ADRC-LUT chain. No device/default integration.',
        in_progress_installed_scope='411 offline only;last406 restored formal395/393 four cameras48;no new phone workers/frames/module changes.',
        ipe_ltm_tmc10_knee_source_verified=False,ipe_ltm_tmc10_knee_target_verified=True,
        ipe_ltm_tmc10_source_version_difference_corrected=True,ipe_ltm_tmc10_aec_interpolation_verified=True,
        ipe_ltm_tmc10_sampling_evidence=prefix+'kernel411/knee-validation.json',
        ipe_ltm_tmc10_aec_evidence=prefix+'kernel411/aec-validation.json',
        ipe_ltm_tmc10_chain_evidence=prefix+'kernel411/chain-validation.json',
        ipe_ltm_tmc10_scope='Target float-log quotient and fine-only unity bump differ from pinned source;corrected shared410 math.2643knees/sampler+33invalid,837AEC+11invalid target/host/ARM equal.2596chains1329152native LUT bytes equal;prior1301 changed58LUT/4044B. Disabled roots preserved;version/runtime/hardware unverified.',
        ipe_ltm_tmc_version_mix_policy_verified=False,ipe_ltm_tmc11_verified=False,
        ipe_ltm_adrc_numeric_math_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
        ipe_ltm_curve_trigger_tree_interpolation_verified=False,ipe_ltm_curve_product_integrated=False,
        ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,
        ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,
        ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,
        ipe_latest_stage_frames_scope='411 offline only;last406 device evidence not counted again.',
        current_health_scope='Last physical check406-r2 restored formal395/393 four cameras48/resources released.407-411 no device access.',
        icp_next_step='Verify actual runtime TMC10/11 selection and TMC11 DRC-HDR-AEC tree;compose remaining LA-mask-weights-scalars/inverseGamma,IFE-IPE domain/stats. Resolve408 raw124/140 and request state commit. Then nonzero hardware/continuous/recovery and media request-libcamera;full363 scope remains.')
    p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through410-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：411（本机TMC10膝点修正与AEC插值；实机仍406）

先读WORKING-BOUNDARIES.md、reference/kernel411/README.md及410/409/408/406证据。完整多摄/骁龙ISP目标active。410归档archive/NEXT-SESSION-through410-2026-10-21.md。用户已开灯出门，现场按实际光照/曝光解释。

## 411本机差异与新插值

原HAL TMC10完整入口3774b0，膝点段377a08..377d50；实际logf/float商后取整，只有1e-9 unity比较，无固定源码额外0.0001扩张。修正共享kernel410/libipa/tmc10.cpp，旧410报告/哈希描述修正前源码，不冒称当前目标。prior-source-r1保留1301中100curve/70gain不同12421B；最终58LUT改变4044B。knee2643=原1301+95半索引x7邻floatx普通/暗部1330+12unity，另33invalid；target/hostASanUBSan/ARM SDKQEMU各909840B零差，fp-contractfast。2640finite knees/2598sample success，3371838目标指令，logf7929/powf176886为hostlibm非Bionic。sampler3c6328是64段65点/Q10，W5=10；mix3626f8..36273c保持。41退化非有限/零归一化端点等仍原子拒绝。

kernel411/libipa/tmc10_aec新增全部11字段与选区indices/ratio，区内copy、区间gap插值，double差求ratio再float，字段整数/小数拆分放大1e6分别舍入，勿普通lerp/FMA。factory5根均lux控制；未使用realGain轴重叠默认区按原序firstmatch，不排序改写。837=687factory触发扫点+150synthetic树，另11invalid，完整HAL函数及采样1329895指令，两架构各339200B零差，输入不变/失败输出保持。237项关闭根只数值检查；强制gain控制仅夹具。只TMC10 AEC，不是TMC11 DRC/HDR/AEC树或全部LTM13触发树。

model-r1最初kneeX/Y读反（实际out+16 X/+32 Y）；aec-r1最初inputrealGain/lux写反（实际+16gain/+20lux），两架构各108196B差，修夹具未改原指令/数学；原始参考/输出私存，失败报告保留。最初inspect.py影子标准库已改inspect-tmc.py。原HAL不修改。

chain2643中2596成功/47拒绝含2有限firstGain<1024不夹值。实际ADRC25612307指令/provider memcpy2596，sourcepacker、host/ARM、维护树native typed LUT1329152B零差。其余IQ/LUT填0，非完整原厂流水线/硬件；原HAL最终packer未执行。

## 原厂数据与当前层级

410五供应商TMC10根18区BIN全部字段与OEM ParameterParser XML全等；qtech/sunny GW1各5区、IMX471/S5K3M5各3、IMX319两区，前摄/长焦TMC10原关闭保持。qtech GW1未绑定物理模式只数值夹具，5文件非第五摄像头。原厂有TMC11，固定仓库SWTMC11关闭回退TMC10，但本机实际版本配置/模式选择未证，勿以文件存在推断。

维护内核406 samurai-ipe-full-pass-ip406 HEAD b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装；411只用户空间数值，不改SoC/板级DT/传感器/主线/DMA/请求/default。407-411手机访问/worker/新帧0，不重复406。公共mirror本地提交不push/PR，保留无关index；原厂/source/系数/ASM/XML/程序/log/图像/密钥私存/mnt/e/edk2-samurai-out/kernel411及前序。

下一步实际TMC10/11选择及TMC11 DRC/HDR/AEC插值，LA/mask/weights/scalars、352inverseGamma，IFE/IPE输入域/统计粗级、408raw124/140与请求候选state提交；再非零调校实像素/连续参数/恢复/media request-libcamera。完整ADRC/LTM仍false。reference/kernel363/REMAINING-CAMERA-SCOPE.md完整范围：第五2MP/OV02A1B身份/mux勿猜OV02A10、多模式/帧长防频闪、连续AF/光学、几何多摄同步，implicitfences/SSC/旋转未全面复验。

## 409/408/407规则

409已采样ADRC转换/混合2783valid40invalid零差；后缀max与顺序3scale/4curve平滑用更新左邻，mix>0curveRatio3else1，curve round/scale max后truncate。407 signed scale delta<0或>=32768都置bit11；首轮漏大正delta698B保留已修，LCE独立clamp/mask，旧4076630/4083978两架构保持。typed2935LUT1502720B全等属历史数值证据。

408Face信号input首指针+124float，BPS10003或raw140==1跳过且state不动，标签未全定位勿猜HDR/flash。signal>0切换重置90次计算更新非90相机帧；previous+(current-previous)*.05，count0新值。strength->smoothing->save proposed history->attenuation->quant，ADRC后；history勿存atten后，state不alias且需请求生命周期提交。3931valid47invalid原HAL/host/ARM全等，长短Unicorn TB越界首轮失败保留，stop_pc hook修正原指令未改。

## 406最后物理设备与保护

stripe416驱动reg5c60bit10 IP_EN。原HAL DC&&IP&&quarter移至单fullframe显式API，DC0/IP1硬件IP关但mask扩2，R1移位2px/LA无效。406改416=explicit image_processing勿恢复DCquarter，不据此判原multipass有错。IP&&mask324step/6halo/处理扩2 else328/4，outputcrop保持，32native/FW仅IPbit变，小128/282仅离线。正确private406/core-intree-r1.ko415720B SHA b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4；test-intree仍旧405415752/ec8bf38d…勿混。

406R1 worker20269/collector20313终态，52transport+48restore但像素失败；R2 worker21352/collector21413/clients终态，52fixed44LTM+8Gamma，640/650x480 NV12/21 p8c2/13模式。IP/mask/linearRGamma/DC+IP全图转换零差/位移消失；LAzero/RGammazero/Gammazero Y0UV128；LA2048/1024灰块128/64零差非彩色全图常量，LTM+linearGamma最大差1，NV12/21归一化全等。两轮200仅transport非全像素通过，最后normal48。

最后406正式core395/adapter393/CAMSS389，r30/r25四摄各12=48direct error/cancel/extra0；CPU/IRQ/PM/maps/import释放、ICP/CAMSS/双CCI suspended、17clks0/9railsdisabled-users0/taint0，PW21581/WP21584 uid10000单例/owner_refs53桌面句柄；无test参数/dump/timeout/新增fault/reboot/flash。407-411未访问，不作新健康声明。host406→405…394，同boot394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt。保护394丢ACK失败reboot/206061Bramoops、395reset assert2us/deassert/readback/双IPE freshACK后退役修复；未知状态先查不重启旧事务。Image363 release7.3.0-rc6-rmx1931-samurai-k363+、DT389/logdump365/SGownerFW不变。405typed2800锁内copy/check再MAP，IQ8944/pre32/post96/type1-opcode1-reg5c08/13LUT2736，同request/未知DMA整parcel保留。

访问source/build先root reference/kernel284/storage.py mounted_build()挂原32GiB ext4，勿格式化重建；rootPYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。保护NV/OTP/个体备份/密钥及电池温控。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从411继续完整多摄/骁龙ISP目标active。读NEXT-SESSION/WORKING-BOUNDARIES/reference/kernel411/README。新目标TMC10膝点段377a08..377d50揭示410源码差异：floatlog商/无coarse unity，已修共享410数学；旧1301中100curve/70gain/58LUT4044B变化失败保留。2643+33invalid target/host/ARM909840B零差，2596链路native LUT1329152B零差；837+11invalid完整3774b0 AEC插值+膝点+gain339200B全等。factory全lux，realgain重叠按序firstmatch；关闭根不启用，强制gain仅夹具。model-r1 X/Y与aec-r1 realGain/lux ABI夹具失败保留，实际+16gain/+20lux。下一步实际TMC10/11选择、TMC11多层DRC/HDR/AEC、其余表/输入域统计/408raw124/140/request state，再非零硬件连续恢复和libcamera。内核仍406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装，416=explicitIP勿恢复DCquarter，395reset修复保持。407-411手机0，最后406fixed52/正式395393四摄48恢复，同guard394，363完整范围保持。先storage284挂原ext4，原厂系数私存，公共本地提交不push/PR，用户开灯出门。\n')
note='411当前：按本机HAL修正TMC10膝点与增益量化，补齐AEC插值；2596份LUT共1329152字节零差。实际版本/TMC11动态树及实机接入继续，最后实机仍406。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel411/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel411/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel411/README.md')]:
    p=ROOT/rel;first,tail=p.read_text().split('\n\n',1);assert first.startswith('410当前：');p.write_text(note+'[411证据]('+link+')。以下为历史。\n\n'+tail)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[410 TMC10采样与ADRC数值链路](reference/kernel410/README.md)','[411 本机TMC10膝点与AEC插值](reference/kernel411/README.md)'))
print(json.dumps(dict(stage=411,next_session_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,last_device_stage=406,full_goal_active=True)))
