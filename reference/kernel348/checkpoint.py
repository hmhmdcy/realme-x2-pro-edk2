from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['register-validation.json','pattern-r1-image-validation.json','pattern-r1-capture-validation.json','final-state-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text());assert state['tracked_clean'] and state['temporary_hardware_tested']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel348/README.md',in_progress_stage=348,
  in_progress_evidence=prefix+'reference/kernel348/README.md',in_progress_installed=False,
  factory_ife_gamma_driver_implemented=True,factory_ife_gamma_driver_evidence=prefix+'reference/kernel348/source-state.json',
  factory_ife_gamma_temporary_hardware_tested=True,factory_ife_gamma_hardware_evidence=prefix+'reference/kernel348/pattern-r1-image-validation.json',
  factory_ife_gamma_ipa_integrated=False,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：347','# 当前检查点：348',1)
start=s.index('下一步：把原厂IFE Gamma');end=s.index('\n\n原严格密钥USB',start)
s=s[:start]+'''348已补原生Gamma typed params并实机通过，尚未安装。源/mnt/samurai-full282/source348，从338 e3aa81b...创建，提交见reference/kernel348/source-state.json，tracked clean。七文件：UAPI、175gamma.c/h、pixel.c/h、LSC注释、17x容量；无板级/传感器/主线框架改动。新CAMSS_PARAMS_IFE_GAMMA=7，776bytes，header8+RGB各64段，每段u16base0..1023/s16delta-512..511；不要求段间连续，不把旧OPE256 type4重解释。enable上传开启、flags0上传保留enable、header-onlydisable不读payload；开流standard初始化并gamma_enabled=true，stopfalse。非活动bank/DMI/CGC保存恢复沿Gamma旧helper抽公共upload，output_lock与LSC串行，正常paramsqueue发PIX RUP，不私有ioctl。params_max_payload改IFE_GAMMA_MAX，类型数组8。公共代码无原厂曲线。

348函数测试主机/ARM各24场景，八bank/576fields越界拒绝/flags/header guard/标准初始化/两个Gamma-LSC交错顺序通过。最初测试缺挂载和LSC声明已修；prepare首次注释匹配失败前无文件改动，复用干净worktree；checkpatch屏障注释补齐，最终0error0warning。构建r1/r2成功，r2仅补屏障注释后的最终源，29.84sec/无诊断，依赖闭包和共享build输出恢复。模块private/kernel348/qcom-camss-gamma348-r2.ko，proof/runtime JSON；无活动hostbuild或SDKbind。

348实机/var/lib/samurai/k348-gamma-r1 worker30625终态成功，临时348模块，原338note已恢复，安装文件不改。mainShadeTPG2十phase28frames：709/linear/Rhalf/factory/off/uploadfactorywhileoff/factoryenable/+unityLSC/+1.5LSC/709LSCoff。稳定条件图像>=paramsackfirstSof且连续hash同，不固定帧配额，不额外+2。10NV12图在privatekernel348/pattern-r1；QBUF后mutate触内核snapshot，四无效pack拒绝。factory3=6=7、linear1=off4=updateoff5、7090=9均逐字相同，Rhalf/factory/非unityLSC有变化。独立linearNV12逆RGB+sourceGamma64段近似：factorymean.333/p991.419，LSC1.5mean.504/p992.378，非光学精度。实际格式colorspace8/xfer2/ycbcr1/quant1，测试显式曲线不按广告sRGB反推。10图SOF>=对应firstSOF，参数与图像报告见348两个pattern-r1 JSON。

临时348下现r27/r22四摄Gst各12帧全部通过并恢复图，76totalframes；相关faultdelta0/taint0/CAMSS和2CCI suspended/9rails disabled users0。最终服务PW30772/WP30836 uid10000，四摄344etc私有WB/LSC/CCM（frontCCMdisabled）保持。preflight第一简易shell因PowerShell展开$?和busybox ps uid失败，不作为身份依据；已用独立inspect-phone.py Python观察证明bootguard/338note/服务/taint/idle。正式worker再次guard并vermagic/loadednote核对。此类普通观察不重复全量hash或NV读取。

下一步349：在342r27正式源的E盘隔离候选集成可选static Gamma配置及347通用编码器、native type7参数编码，与WB/LSC/CCM同revision/ack/SOF历史；无曲线配置保持standard输出，前1928未知mode不新增factory绑定。原厂51curve同一条，14context UID36不需要虚构动态算法。IPAcapacity增大必须与348内核组合，旧内核要明确能力拒绝/回退，不能静默假启用。先候选DSO/原厂payload与实机验证再持久部署组合。已有344etcprofiles需显式合入私有曲线，数据不公共。也继续346AE表antibanding/sensorlimits、正常光学/其它模式/同步/连续AF；完整goal未完成。用户已开灯无色卡，优先原厂固件反编译取文件/调校；不要求色卡，不重复下载BIN/读EEPROM。''' +s[end:]
path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。用户更新目标：优先现有仓库/方案，优先反编译原厂固件获取文件和校准，分清SoC/板级/主线/驱动/用户空间。读WORKING-BOUNDARIES、NEXT-SESSION、reference/kernel348/README.md。348原生IFE Gamma type7/776bytes底层已实现，两架构实际函数测试/完整CAMSS Werror构建/临时实机10phase28frame+4摄Gst48frames通过；DMI与LSC共享锁，SOF对应，原厂曲线真实生效。源E ext4/source348提交见source-state，手机已恢复338模块、344etc/r27r22默认，未安装348。下一步349集成IPA静态Gamma配置/编码/同revision和SOF，候选测试后部署内核+用户空间组合；旧Gamma type4仍是OPE256不混用。347原厂51curves完全相同、14contextUID36，只私存；front1928未知不新增绑定。PW30772/WP30836 uid10000，相机idle/故障0/taint0，worker终态，无build/bind；C近满用E ext4。完整AE防频闪/更多模式/光学/同步/连续AF仍未完。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('348当前：原厂Gamma已通过新增原生IFE参数在VFE175实机生效，四摄取流兼容；尚未接入默认IPA，实验后恢复338。下一步用户空间配置与组合部署。[348详情](../../reference/kernel348/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded348 native Gamma hardware result; deployed344/338 baseline preserved; full goal remains active.')
