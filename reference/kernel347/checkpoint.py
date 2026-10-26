"""Record Gamma extraction and the preceding completed EV/FPS work."""
from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['factory-gamma-validation.json','gamma-mode-validation.json','gamma-math-validation.json']:
 assert json.loads((HERE/n).read_text())['passed']
assert json.loads((HERE.parent/'kernel346/active-program-validation.json').read_text())['passed']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel347/README.md',in_progress_stage=347,
  in_progress_evidence=prefix+'reference/kernel347/README.md',in_progress_installed=False,
  factory_active_ev_fps_table_construction_implemented=True,
  factory_active_ev_fps_table_evidence=prefix+'reference/kernel346/active-program-validation.json',
  factory_exposure_program_ipa_integrated=False,factory_exposure_program_actual_sensor_limit_application_pending=True,
  factory_ife_gamma_extracted=True,factory_ife_gamma_evidence=prefix+'reference/kernel347/factory-gamma-validation.json',
  factory_ife_gamma_mode_evidence=prefix+'reference/kernel347/gamma-mode-validation.json',
  factory_ife_gamma_encoder_evidence=prefix+'reference/kernel347/gamma-math-validation.json',
  factory_ife_gamma_ipa_integrated=False,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：345','# 当前检查点：347',1)
s=s.replace('用户关灯休息，继续源码与内部图案；正常照明光学、几何同步、连续AF及完整系统目标仍未完成。',
 '用户已起床开灯，没有色卡，要求继续反编译原厂刷机包获取校准数据；正常照明光学、几何同步、连续AF及完整系统目标仍未完成。',1)
start=s.index('下一步346：');end=s.index('\n\n原严格密钥USB',start)
s=s[:start]+'''346已完成UpdateEVKnee与ApplyActiveTableEVFPSKnees，reference/kernel346/libipa/aec_exposure_table.{h,cpp}。224来源表去重59 table/policy context，主机/ARM各2515case368836bytes与完整原FPS/EV/active指令零差，含全部活动knee数组、FPS/EVknee、EVindex偏移。OnExposureCompChange经DataManager虚表+264、RELR原槽位证明额外flag是getHDR3Enable@1e300。EV表开关由caller决定；普通正EV可放gain，HDR3保留FPSgain；负EV不简单截短活动表，FPS截短后还可能追加原最大gain。math用host powf/log10/exp2、memcpy/log桩，非Android服务；尚未接IPA/antibanding/真实sensor limits。SetParamFPSRange原厂预算1e9f/fps取uint64，blanking严格小于duration才减，尚未封装。私有kernel346，SDK/private/camss346-math无work bind。README346和两报告已保存。

347按用户无色卡指示继续原厂调校包。复用333索引对应的五BIN（来源kernel299/323/324，以index为准），只新取固定CamxChi commit9f17f1b...的Gamma schema/interpolation/setting/header/titan17x五文件。decode-gamma.py独立读取IFE全部17roots/51channelcurves*65节点，与保留原厂ParameterParser XML全部树/开关/控制轴一致。分析副本只改非选根versionmetadata，载荷和模式树未动；曲线/源/XML私存kernel347及/home/cy122/x2pro-linux/parser-k347-*-gamma-r1。二进制leaf每channel272bytes（typeQ+65f+padding），root136bytes17Q：enable0/control11,12/LEDfloat13,14/count15,ref16，树DRC/HDR/LED/AEC/CCT/channel，不能按XSD int字样把曲线float字节解成int。

347Gamma tag复用343 stock-selection-manager，511上下文与独立ModeTree0diff；七模式*Preview/Video14context全部UID36/enabled1。未知front1928未绑定，实际mainSunny沿用342。所有五BIN的51条Gamma跨通道/触发完全相同，可先静态配置，不需虚构动态算法；不代表BPS/IPE全部tonechain等价。通用libipa/gamma_curve.{h,cpp}将0..1024有限float65点→原生64uint32，base10bit/delta signed10，末端可1024，roundf/clamp；非法输入拒绝。私有编译原GenerateGammaLUT+原round/clamp函数作参考，非HAL指令oracle；主机/ARM各41case10660bytes0diff，51条相同factorycurve去重只测一次。SDK/private/camss347-math小工具，无work bind/电话worker，现机344基线保持，没有安装或手机操作。

下一步：把原厂IFE Gamma接入通用typed params/IPA。当前CAMSS_PARAMS_GAMMA=4是OPE256项直接表，不能当本机65节点/64段；VFE175现有gamma仅prepare时standard xfer，需明确原生IFE语义、DMI共享与SOFbank生效管理，不加私有ioctl或把曲线硬编码SoC/DT。核对当前338源对应gamma validator再实现。也可继续346曝光math的antibanding/实际sensor限幅接入。正常光学、其它模式、同步及连续AF仍未完；用户已开灯可实拍，但无色卡不要求用户准备，优先原厂数据。不要重下载BIN或重读已取得EEPROM。''' +s[end:]
path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续多摄/骁龙ISP goal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel347/README.md。用户已起床开灯但无色卡，要求从原厂刷机包取校准数据。347新增全部IFE Gamma17roots/51curves提取/完整树与OEM XML一致、511modequery0diff；五BIN全部curve相同，14物理context都UID36。通用65point→64word编码两架构41case10660bytes0diff，未接IPA/硬件。当前Gamma type4是OPE256直接表，下一步应补本机原生IFE语义/typedparams/VFE175 DMI和SOF管理后接IPA，不硬编码曲线进DT/SoC。346EV/FPS活动表已完成，两架构2515case368836bytes零差，HDR3flag已沿vtable/RELR证明；未接antibanding/sensorlimits。手机347无操作，保持344etc四摄私有校准五模式、r27/r22+298/305/325/338。无活动worker/bind/build，C近满用E ext4。私有曲线/图像/EEPROM/vendor不镜像。完整光学/同步/AF/更多模式仍未完。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('347当前：原厂IFE Gamma全部提取，模式对应和两架构编码通过，尚未接入硬件；346 EV/FPS活动表数学也已完成。344默认四摄私有WB/LSC/CCM保持。[347详情](../../reference/kernel347/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[]
for directory in [HERE.parent/'kernel346',HERE]:paths.extend(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded346 EV/FPS and347 factory Gamma; deployed344 calibration preserved; full goal active.')
