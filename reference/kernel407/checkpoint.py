"""Record portable LTM primitives without claiming another hardware epoch."""
from pathlib import Path
import hashlib, json
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for name in ['curves', 'float-comparison', 'kernel-luts']:
    assert json.loads((HERE / (name + '-validation.json')).read_text())['passed']
assert not json.loads((HERE / 'curves-r1-validation.json').read_text())['passed']
state = json.loads((HERE / 'source-state.json').read_text())
state.update(new_hardware_verification=False, hardware_fixed_diagnostics_origin_stage=406,
             portable_curve_primitives_verified=True,
             portable_curve_primitives_integrated_into_product=False,
             full_ltm_numeric_math_complete=False, last_device_evidence_stage=406)
(HERE / 'source-state.json').write_text(json.dumps(state, indent=2) + '\n')
prior_sources = json.loads((HERE.parent / 'kernel403/primary-sources.json').read_text())
row = next(r for r in prior_sources['files'] if r['path'].endswith('/ltm13setting.cpp'))
source_path = Path('/mnt/e/edk2-samurai-out/kernel403/sources/ltm13setting.cpp')
assert hashlib.sha256(source_path.read_bytes()).hexdigest() == row['sha256']
primary = dict(stage=407, commit=prior_sources['commit'], files=[row],
               reused_factory_tree_evidence='../kernel351/factory-colour-chain-validation.json',
               reused_actual_target_hal_evidence='../kernel403/contract-validation.json',
               implementation_reference_scope='AutoManualCalculate,DarkBrightRegionTreatment,AttenuateCurves,and two signed packers;not full LTM CalculateHWSetting or ADRC',
               upstream_reuse_references=[
                   dict(url='https://lists.libcamera.org/pipermail/libcamera-devel/2026-April/058088.html', scope='CAMSS pipeline abstraction;not target LTM math'),
                   dict(url='https://patchwork.libcamera.org/patch/26514/', scope='Different OPE backend;not SM8150 IPE proof')])
(HERE / 'primary-sources.json').write_text(json.dumps(primary, indent=2) + '\n')
for relative, prefix in [('linux-port/camera/deployment-lock.json', '../../reference/'),
                         ('linux-port/camera/kernel/source-lock.json', '../../../reference/')]:
    path = ROOT / relative
    d = json.loads(path.read_text())
    assert d['latest_work_stage'] == 406 and d['current_device_revalidated_stage'] == 406
    for key in ['stage', 'in_progress_stage', 'latest_work_stage']:
        d[key] = 407
    d.update(latest_stage_device_mutated=False, latest_stage_phone_accessed=False,
             current_device_revalidated_stage=406, ipe_latest_hardware_stage=406,
             kernel_source_scope='406 maintained clean candidate unchanged:explicit full-pass IP_EN.407 adds portable userspace curve treatment/attenuation/signed LUT math,not installed or integrated into product.',
             in_progress_installed_scope='407 offline math only;last device406 restored formal395/393,four cameras48. No new frames,module changes or worker in407.',
             ipe_ltm_curve_primitives_implemented=True, ipe_ltm_curve_primitives_verified=True,
             ipe_ltm_curve_primitives_evidence=prefix+'kernel407/curves-validation.json',
             ipe_ltm_curve_float_evidence=prefix+'kernel407/float-comparison-validation.json',
             ipe_ltm_curve_native_lut_evidence=prefix+'kernel407/kernel-luts-validation.json',
             ipe_ltm_curve_primitives_scope='6549 cases:all2135 factory regions x3 exposure deltas,48manual,96auto. HostASanUBSan/AArch64 source packed zero difference;target curve fragments99float exact using hostlibm powf. Native signed LUT pages zero difference. Not full Execute/ADRC/OEM temporal/trigger tree/all LUTs.',
             ipe_ltm_nonzero_scale_lce_curve_primitives_verified=True,
             ipe_ltm_nonzero_scale_lce_math_verified=False,
             ipe_ltm_nonzero_scale_lce_hardware_verified=False,
             ipe_ltm_full_factory_numeric_math_verified=False,
             ipe_ltm_oem_temporal_smoothing_verified=False,
             ipe_ltm_adrc_numeric_math_verified=False,
             ipe_ltm_curve_trigger_tree_interpolation_verified=False,
             ipe_ltm_curve_product_integrated=False,
             ipe_ltm_runtime_submission_enabled=False, ipe_ltm_product_default_enabled=False,
             ipe_latest_stage_actual_frames=0, ipe_latest_stage_RT_frames=0,
             ipe_latest_stage_non_RT_frames=0, ipe_latest_stage_native_cc_frames=0,
             ipe_latest_stage_normal_restored_frames=0,
             ipe_latest_stage_frames_scope='407 offline only,zero hardware frames. Last406 two epochs52+48 each,200transport including R1 failed pixels;R2 fixed52 passed and final restored48. Do not count again in407.',
             current_health_scope='Last physically checked406-r2:restored formal395/393 four cameras48 and resources released.407 no new device access;not a fresh407 health check.',
             icp_next_step='Recover target OEM temporal/adaptive LTM and ADRC;compose DRC/HDR/AEC interpolation and remaining LA/mask/weights/scalars/inverseGamma;resolve IFE/IPE domain/stats. Then nonzero hardware/continuous requests/recovery and standard media request/libcamera. Full363 camera scope remains.')
    path.write_text(json.dumps(d, indent=2) + '\n')
archive = ROOT / 'archive/NEXT-SESSION-through406-2026-10-21.md'
assert not archive.exists()
archive.write_bytes((ROOT / 'NEXT-SESSION.md').read_bytes())
(ROOT / 'NEXT-SESSION.md').write_text('''# 当前检查点：407（LTM曲线与曝光衰减移植；实机仍为406）

先读WORKING-BOUNDARIES.md、reference/kernel407/README.md及406/README.md。完整多摄／骁龙ISP目标active。406交接归档archive/NEXT-SESSION-through406-2026-10-21.md。用户已开灯出门，现场样本按实际照明解释。

## 本轮407

新增reference/kernel407/libipa/ltm_curves.{h,cpp}，可移植用户空间自动/手动曲线、暗亮区域、LTM/LCE强度、曝光变化衰减、64段scale及两组16段LCE量化。输入已插值，不包含触发树/OEM时域块/ADRC/其余LA-mask-weights-scalars/完整CalculateHWSetting。浮点留用户空间，内核仅接类型化量化请求；尚未产品接入/安装。

五份原厂BIN全部149根2135区域，每区域3曝光条件6405项，加48manual边界与96auto，共6549。主机ASan/UBSan、现有AArch64 SDK/QEMU与私有固定源码参考量化零差；81非法计算+14非法编码保持输出，输入保持。actualHAL 35ec64..360560及360ac8..360c3c两片段运行6549项6587698指令，明确跳过中间OEM时域/自适应；外部powf12480次用hostlibm，不是targetBionic。99float对host/ARM全字节零差；源参考doublepow相对auto分支4float字节不同/最大6.1035e-5，量化不差。未执行原HAL最终LUT packer，此处将HAL浮点按源规则再量化核对。

首轮泛化sign规则错误：LTM scale显式强制负delta符号位，LCE仅掩码，超signed12bit负差值不能统一。208表字节失败保留curves-r1-validation.json及私有原输出；修正后全过。现有交叉g++缺失，复用原SDK而非安装工具链。check-kernel-luts.py编译与维护源相同的colour编码器，全部6549项转2800B typed请求，8944B IQ页scale/LCE共2514816B零差/3536非零项，未提交硬件/其余零表不代表完整配置。报告curves/float-comparison/kernel-luts-validation.json。

源码仍406 samurai-ipe-full-pass-ip406 HEAD b4f382affa9a8be089ccec6170c34d74005103ce，干净未永久安装，405typed所有权不变。407手机帧/worker/安装均0，不得把406恢复48重复计入407。公共mirror仅本地提交，保护无关index、不push/PR。原厂/表/ASM/图像/log/密钥都私存/mnt/e/edk2-samurai-out/kernel407及前序。

## 406必须保留的底层修正

stripe+416驱动reg5c60 bit10物理IP_EN。原HAL把它绑定DC&&IP&&有效quarter，当前显式单全帧DC0/IP1时硬件IP关而crop按IP+mask扩2，R1后续条带移位2px/LA无效。406直接416=image_processing；是原HAL多pass策略移植到单全帧API不适合，不判原完整流程有错。勿恢复DC/quarter gate。IP&&mask324step/6halo/处理扩2，否则328/4，输出crop等保持。

40632native/FW完整准备检查，至多只改5c60bit10，IP0与旁路全字节一致；128/282仅离线。W1/Werror0diag。修正核心private406/qcom-camss-icp-a5-core-intree-r1.ko 415720B SHA b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4；test-intree旧核心仍405 ec8bf38d…勿误用。

R1 rootk406-ltm-r1/worker20269/collector20313终态，52transport+48恢复但像素失败保留；R2 rootk406-ltm-r2/worker21352/collector21413及client终态，换核心/同adapter client，52固定请求44LTM+8组合Gamma，640/650x480 NV12/21 p8/c2，13模式。IP/mask零scale和linearRGamma/DC+IP均对转换对全图零差、位移消失；LAzero/RGammazero/combinedGammazero全Y0UV128；LA2048/1024灰块分别128/64误差0，不是全彩色图常量。LTM+linearGamma最大差1；全部13模式NV12/21归一化全字节等。两轮200仅transport总数，不是全像素通过；最后正常epoch48。

## 最后实际设备证据406

正式core395/adapter393/CAMSS389恢复，r30/r25四摄IMX471/IMX319/S5K3M5/GW1各12共48direct,error/cancel/extra0。CPU/IRQ/PM/maps/import释放，ICP/CAMSS/双CCI suspended，17clks0/9railsdisabled-users0/taint0，PW21581/WP21584 uid10000单例，owner_refs53桌面句柄。无测试参数/dump/timeout/新增相关fault/重启/刷写。这是406观察，407未重新访问。

host406→405…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，同boot394。保留394丢ACK失败reboot/206061Bramoops和395 reset assert2us/deassert/readback及双IPE freshACK后释放修复。旧事务已终态，未知状态先查不重启。Image363 release7.3.0-rc6-rmx1931-samurai-k363+、静态DT389/logdump365/SGowner/FW不变。

## 下一步及契约

优先本机OEM时域/自适应块360560..360ac8与ADRC、DRC/HDR/AEC动态树、其余LA/mask/weights/scalars及352逆Gamma组合，明确IFE/IPE域、统计/粗级；后做非零scale/LCE实像素、连续参数/故障恢复及标准media request/libcamera。406固定诊断不是完整调校/DCstats/全部尺寸证明。

405LTM类型2800B，lock内copy/check再coherent/MAP，IQ/DMI/LUT同request，所有出口CPUcopy释放，未知DMA保留整parcel/images至quiescent。NULL回旧Gamma/colour。组合IQ8944/PAGE12288，arraybase2592/pre32最多CST20+LTM11/post96最多CC-CV20+Gamma12；旧Gamma6016/pre32/post64独立。CST2784 CC2840 CV2884，GammaDMI2928/LUT2976，LTMDMI6048/LUT6208。13LUT2736B/type1/opcode1/reg5c08/selectors1..13，resource3296额外560用途未知。原逆Gamma输入IFEgreen64，不可用IPE256。HAL ANR440==1或topology2624==3是上层策略不自动复刻。

363全部范围继续：第五2MP身份/mux、多模式、帧长防频闪、连续AF/光学、几何多摄同步，implicit fence/SSC/旋转未全面复验。source/build先root reference/kernel284/storage.py mounted_build()挂原32GiB ext4，勿格式化/重建。rootPYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。保护NV/OTP/个体备份及电池温控。
''')
(ROOT / 'NEXT-SESSION-PROMPT.md').write_text('从407继续完整多摄/骁龙ISP目标active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel407/README.md及406证据。407新增用户空间LTM自动/手动/强度/曝光衰减及scale/LCE量化，6549项source/hostASanUBSan/ARM通过，actualHAL两片段99float零差（powf用hostlibm、跳过OEM时域、未跑最终packer），源doublepow仅4float字节不同/量化零差；原厂149根2135区域各3曝光、48manual、96auto；LCE负delta掩码不同于LTM sign-force首轮208B失败已修正保留。原生编码器6549typed请求2514816B LUT零差/3536非零项。尚未触发树/OEM时域/ADRC/完整LTM其余表/产品接入/新硬件。源码仍406 b4f382affa9a8be089ccec6170c34d74005103ce干净未永久装，保留416=explicitIP，勿还原DC-quarter gate。407手机0，最后406 R2 fixed52与正式395/393四摄48恢复、资源释放、taint0，workers全终态，同guard394，不把406帧重复计入407。下一步OEM时域360560..360ac8与ADRC/动态树/其余表输入域，再非零硬件/连续请求与恢复/标准media request-libcamera，363全部范围保留。先storage284挂原ext4，原厂/个体表密钥私存，公共仅本地提交不push/PR。\n')
note = '407当前：已移植LTM自动／手动曲线、强度、曝光衰减及scale／LCE量化，6549项原厂／边界对照和原生编码连接通过；完整动态树、OEM时域与ADRC仍待，手机最后实证保持406，完整多摄目标继续。'
for relative, link in [('linux-port/camera/README.md', '../../reference/kernel407/README.md'),
                       ('linux-port/camera/kernel/README.md', '../../../reference/kernel407/README.md'),
                       ('linux-port/docs/HARDWARE-STATUS.md', '../../reference/kernel407/README.md')]:
    path = ROOT / relative
    first, tail = path.read_text().split('\n\n', 1)
    assert first.startswith('406当前：')
    path.write_text(note + '[407证据](' + link + ')。以下为历史。\n\n' + tail)
path = ROOT / 'DOCS-INDEX.md'
path.write_text(path.read_text().replace('[406 LTM实像素与显式IP修正](reference/kernel406/README.md)',
                                       '[407 LTM曲线与曝光衰减](reference/kernel407/README.md)'))
print(json.dumps(dict(stage=407, checkpoint_updated=True, last_device_stage=406,
                      next_session_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size, full_goal_active=True)))
