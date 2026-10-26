"""Record offline TMC10 evidence without advancing the physical-device epoch."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['factory-tmc10','tmc','chain']:
    assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
for name in ['model-r1','tmc-r1']:
    assert not json.loads((HERE/(name+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text())
state.update(tmc_sampling_pending=False,tmc10_factory_tree_extraction_verified=True,
    tmc_gain_sampling_verified=True,tmc10_gain_sampling_target_verified=True,
    tmc10_knee_and_percentage_source_verified=True,tmc10_knee_generation_target_verified=False,
    tmc10_mix_target_verified=True,tmc10_numeric_chain_to_native_lut_verified=True,
    tmc_trigger_and_mix_policy_verified=False,tmc_runtime_version_selection_verified=False,
    tmc11_verified=False,tmc_aec_trigger_interpolation_verified=False,
    disabled_tmc10_roots_kept_disabled=True,full_ltm_numeric_math_complete=False,
    phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
    path=ROOT/rel;d=json.loads(path.read_text());assert d['latest_work_stage']==409 and d['current_device_revalidated_stage']==406
    for k in ['stage','in_progress_stage','latest_work_stage']:d[k]=410
    d.update(latest_stage_device_mutated=False,latest_stage_phone_accessed=False,
        current_device_revalidated_stage=406,ipe_latest_hardware_stage=406,
        kernel_source_scope='406 clean explicit-IP kernel unchanged.410 offline TMC10 factory extraction, source knee policy, target sampling/mix and numeric ADRC-LUT chain. No device/default integration.',
        in_progress_installed_scope='410 offline only;last406 restored formal395/393 and four cameras48;zero new phone frames/workers/module changes.',
        ipe_ltm_tmc_gain_sampling_verified=True,ipe_ltm_tmc10_factory_extraction_verified=True,
        ipe_ltm_tmc10_knee_source_verified=True,ipe_ltm_tmc10_knee_target_verified=False,
        ipe_ltm_tmc10_mix_target_verified=True,ipe_ltm_tmc10_numeric_lut_chain_verified=True,
        ipe_ltm_tmc10_factory_evidence=prefix+'kernel410/factory-tmc10-validation.json',
        ipe_ltm_tmc10_sampling_evidence=prefix+'kernel410/tmc-validation.json',
        ipe_ltm_tmc10_chain_evidence=prefix+'kernel410/chain-validation.json',
        ipe_ltm_tmc10_scope='5 supplier variants/18regions matched OEM XML;not5physical cameras.1301source-policy cases;1298target sampler calls,hostlibm powf.1254boost chains642048native LUT bytes equal;47reject incl2finite subunity. Disabled roots preserved;not runtime or hardware.',
        ipe_ltm_tmc_version_mix_policy_verified=False,ipe_ltm_tmc11_verified=False,
        ipe_ltm_adrc_numeric_math_verified=False,ipe_ltm_full_factory_numeric_math_verified=False,
        ipe_ltm_curve_trigger_tree_interpolation_verified=False,ipe_ltm_curve_product_integrated=False,
        ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,
        ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,
        ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,
        ipe_latest_stage_frames_scope='410 offline only;no new hardware frames.Last406 not counted again.',
        current_health_scope='Last physical check406-r2 restored formal395/393 four cameras48/resources released.407-410 no device access.',
        icp_next_step='Verify runtime TMC10/11 selection,target knees and DRC-HDR-AEC interpolation;compose LA-mask-weights-scalars/inverseGamma,IFE-IPE domain/stats. Resolve408 raw124/140 and request-state commit. Then nonzero hardware/continuous/recovery and media request-libcamera;full363 scope remains.')
    path.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through409-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：410（TMC10采样与ADRC数值链路；实机仍406）

先读WORKING-BOUNDARIES.md、reference/kernel410/README.md及409/408/406证据。完整多摄/骁龙ISP目标active。409归档archive/NEXT-SESSION-through409-2026-10-21.md。用户已开灯出门，现场按实际光照/曝光解释。

## 410新增与证据边界

五份原厂供应商调校TMC10共5根18区，BIN控制/保留字段/全部AEC区域与原厂ParameterParser XML全等。qtech/sunny GW1各5区、前摄IMX471/长焦S5K3M5各3区、IMX319两区。前摄/长焦TMC10原关闭，未启用；同时有TMC11，不能推断实际版本。qtech GW1未绑定当前物理模式，仅数值夹具；五份供应商文件不是第五物理摄像头。

kernel410/libipa/tmc10计算4膝点/6系数、LTM/GTM百分比、65点GainQ10及mix。膝点/百分比仅固定CamxChi源码对照，未执行本机膝点生成！原HAL sampler3c6328是64段特化，Qfactor10在W5；mix3626f8..36273c。1301项=18区x10gainx6dark1080+200synthetic+21edge，另33invalid；1298目标采样1391456指令/84370powf provider（hostlibm非Bionic），有限输出/mix零差。hostASanUBSan与ARM SDKQEMU各453560B零差，fp-contractfast。41退化非有限采样拒绝，3零归一化端点拒绝（即使rate0原函数得有限unity）。原始oracle与API有效域映射分存。

model-r1误查源BOOL返回：目标特化不写W0/调用者不用，改检查STOP/输出/保护区；原指令不改。tmc-r1两架构各261B差仅零端点/rate0有效域映射，原始输出仍保留，不冒充数值通过。

chain1301中1254成功/47拒绝；其中2项有限首gain<1024因下游契约拒绝，不夹值。TMC source膝点+目标核对采样/mix，接409实际HAL ADRC转换混合12323438指令/memcpy1254，源packer，再host/ARM及现有native typed LUT共642048B零差。关闭根未激活/其余IQ和LUT填0，仅数值链路，不是全原厂流水线/硬件；最终HAL LUTpacker仍未执行。

## 底层与接续

维护内核406 samurai-ipe-full-pass-ip406 HEAD b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装；410仅用户空间数值层，板级DT/传感器/主线/DMA/请求/default不改。407-410手机0、新worker/帧0，不重复406。公共mirror本地提交不push/PR，保护无关index；原厂/source/系数/ASM/XML/程序/log/图像/密钥私存/mnt/e/edk2-samurai-out/kernel410及前序。

下一步实际TMC10/11选择、本机膝点生成、DRC/HDR/AEC动态插值；LA/mask/weights/scalars和352inverseGamma，IFE/IPE输入域/统计粗级、408raw124/140身份与候选状态提交；再非零调校实像素/连续参数/恢复及标准media request/libcamera。完整ADRC/LTM仍false。reference/kernel363/REMAINING-CAMERA-SCOPE.md全部范围继续：第五2MP/OV02A1B身份/mux（勿猜OV02A10）、多模式/帧长防频闪、连续AF/光学、几何多摄同步，implicitfences/SSC/旋转未全面复验。

## 409/408/407保留

409 sampledGain/equivalent12/forwardGamma10各65->ADRC scale/curve->mix->LUT；2783valid40invalid target/source/host/ARM2591514B零差，gain/mix当时合成。插值整数/小数拆分放大1e6/double分别舍入，不能普通lerp/FMA；后缀max与顺序3scale/4curve平滑使用已更新左邻；mix>0curve比例3else1，curve round/scale max后truncate。2935pack/native LUT1502720B全等。407signed scale delta<0或>=32768都置bit11，旧漏大正差首轮698B失败保留已修；LCE独立clamp/mask。旧4076630与4083978两架构保持。

408Face smoothing signal原input首指针+124float，BPSparent10003或raw140==1跳过且state不动，字段标签未全定位勿猜HDR/flash。signal>0状态切换重置90次计算更新，非相机90帧；previous+(current-previous)*.05，count0直接新值。strength->smoothing->save proposed history->attenuation->quant，ADRC后；history不能存atten后。API输入/输出/next不alias，候选state需请求生命周期提交。3931valid47invalid原HAL/host/ARM全等，长短Unicorn TB越界误入日志首轮失败保留，stop_pc hook修正无原指令改动。407曲线强度/曝光衰减细节与source/HAL精度边界见原证据。

## 406最后物理设备与恢复保护

stripe416驱动reg5c60bit10 IP_EN。原HAL DC&&IP&&quarter策略直接用于当前单fullframe显式API，DC0/IP1硬件IP关但mask crop扩2，R1移位2px/LA无效。406设416=explicit image_processing，勿恢复DC-quarter gate，不据此判断原multipass有错。IP&&mask324step/6halo/处理扩2，else328/4，outputcrop保持；32native/FW checks只IPbit可变，小128/282仅离线。正确private406/core-intree-r1.ko415720B SHA b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4；test-intree仍旧405415752/ec8bf38d…勿混。

406R1 worker20269/collector20313终态，52transport+48restore但像素失败保留；R2 worker21352/collector21413/clients终态，同adapter/client换core，52fixed=44LTM+8combinedGamma，640/650x480 NV12/21 p8c2/13模式。IP/mask/linearRGamma/DC+IP全图转换零差/位移消失；LAzero/RGammazero/Gammazero Y0UV128；LA2048/1024灰块128/64零差，非彩色全图常量。LTM+linearGamma最大差1；NV12/21归一化全等。两轮200仅transport非全像素通过；最后normal epoch48。

最后406正式core395/adapter393/CAMSS389，r30/r25四摄IMX471/IMX319/S5K3M5/GW1各12=48direct，error/cancel/extra0，CPU/IRQ/PM/maps/import释放、ICP/CAMSS/双CCI suspended、17clks0/9railsdisabled-users0/taint0。PW21581/WP21584 uid10000单例，owner_refs53桌面句柄；无test参数/dump/timeout/新增fault/reboot/flash。407-410未访问，不作新健康声明。

host406→405…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，同boot394。保护394丢ACK失败reboot/206061Bramoops、395reset assert2us/deassert/readback/双IPE freshACK后退役修复；未知状态先查不重启旧事务。Image363 release7.3.0-rc6-rmx1931-samurai-k363+，DT389/logdump365/SGownerFW不变。405typed2800锁内copy/check再MAP，IQ8944/pre32/post96/type1-opcode1-reg5c08/13LUT2736，同request/未知DMA整parcel保留。

访问source/build先root reference/kernel284/storage.py mounted_build()挂原32GiB ext4，勿格式化重建；rootPYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。保护NV/OTP/工厂个体备份/密钥与电池温控。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从410继续完整多摄/骁龙ISP目标active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel410/README.md。新原厂TMC10五供应商根18区与XML全等（非第五相机，前摄/长焦关闭保持），膝点/百分比仅source核对，目标sampler/mix通过；1301+33invalid两架构453560B零差，powf hostlibm。链路1254成功/47拒绝含2有限subunity，native LUT642048B全等，非产品/硬件；首轮ABI和零端点有效域失败保留。下一步实际TMC10/11选择/目标膝点/DRC-HDR-AEC插值，其余表与输入域统计、408raw124/140/候选state提交，再非零硬件/连续恢复/media request-libcamera。409signed大正delta规则、408history在atten前、406416=explicitIP勿恢复DCquarter。内核仍406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装；407-410手机0，最后406fixed52及正式395/393四摄48恢复。同guard394/旧worker终态，363完整范围保持，用户开灯出门。先storage284挂原ext4，原厂系数密钥私存，公共本地提交不push/PR。\n')
note='410当前：原厂TMC10五供应商变体18区提取、采样与ADRC数值链路通过，1254份原生LUT共642048字节零差；实际版本/动态树/实机接入继续，最后实机仍406。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel410/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel410/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel410/README.md')]:
    p=ROOT/rel;first,tail=p.read_text().split('\n\n',1);assert first.startswith('409当前：');p.write_text(note+'[410证据]('+link+')。以下为历史。\n\n'+tail)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[409 ADRC转换混合与量化](reference/kernel409/README.md)','[410 TMC10采样与ADRC数值链路](reference/kernel410/README.md)'))
print(json.dumps(dict(stage=410,checkpoint_updated=True,last_device_stage=406,next_session_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_active=True)))
