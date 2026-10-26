from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['ipa-contract-validation.json','runtime-iq-validation.json','gamma-image-validation.json','startup-boundary-validation.json','final-state-validation.json','downstream-gamma-inventory.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
state=json.loads((HERE/'source-state.json').read_text());state.update(candidate_combined_hardware_tested=True,installed=False,
 runtime_iq_evidence='runtime-iq-validation.json',gamma_image_evidence='gamma-image-validation.json',
 downstream_gamma_role_pending=True,production_gamma_source_unchanged_during_r2=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel349/README.md',in_progress_stage=349,
  in_progress_evidence=prefix+'reference/kernel349/README.md',in_progress_installed=False,
  factory_ife_gamma_ipa_integrated=True,factory_ife_gamma_ipa_candidate_integrated=True,
  factory_ife_gamma_ipa_evidence=prefix+'reference/kernel349/ipa-contract-validation.json',
  factory_ife_gamma_combined_hardware_evidence=prefix+'reference/kernel349/runtime-iq-validation.json',
  factory_ife_gamma_default_enabled=False,factory_downstream_gamma_role_pending=True,
  factory_downstream_gamma_inventory_evidence=prefix+'reference/kernel349/downstream-gamma-inventory.json',current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：348','# 当前检查点：349',1)
start=s.index('下一步349：');end=s.index('\n\n原严格密钥USB',start)
s=s[:start]+'''349已完成IFE Gamma候选IPA集成并组合实测，但未安装。源/mnt/samurai-full282/libcamera349-gamma-built/src/libcamera-v0.7.2，baseline342正式r27源。0037-camss-static-ife-gamma.patch有11个源文件，generic gamma_curve沿用347，ipa gamma_profile读取optional gamma{mode:static,curves:RGB3*65有限0..1024}，enabledfalse/absent保留formatcurve。Native type7 encoder尾部追加776block；初始revision0与WB/BHIST/LSC/CCM一起上传，之后immutable不重传，ParameterContext gammaEnabled随ack/SOF历史，重开流重传/切回legacy清旧state；无IPC签名改动，核心只因header/version重链接。启动栈最大2664，mapped最低WB/BHIST+Gamma832，实际完整包按buffer容量检查。无内核/DT/sensor改动，使用348模块临时组合。

349build128.35sec成功，核心保持baseline werror=false，合同/设备工具Werror。真实AArch64 DSO15cases（5factorymode+RGBasym+disabled+absent+7bad）通过，12Gamma blocks9312bytes与347/348原参考对应；WB revision无Gamma、restart重传、reconfigurelegacy清状态、shortmap拒绝、ACK前metadata验证。首轮profile跨main两mode复用列表造成YAMLalias，实际解析失败；deepcopy per mode并assert无alias后通过，失败log保留。首次分析venv无yaml已加/usr/lib/python3/dist-packages，不重建算法。

349runtime/private-k349：四份model-factory.yaml从343当前Preview profiles只给既有五匹配模式加Gamma，front1928不加，frontCCMdisabled保留。两个main-linear/main-rgb(R.5,G.75,B.25)诊断文件。R1/var/lib/samurai/k349-gamma-r1 worker31564终态pass，temporary348+candidatecore/signedIPA，7组*4phase323frames/28images，Gamma每组仅revision0ACK，7AWBlock。旧338先negative maincurvefullprofile启动-ENOSPC(-28)，无GammaACK/图像且fixture恢复，无故障；不是静默绕过。libcamera/probe/IPA/config都私有前缀，不改系统文件。最初phase0RGB模型mean18/p9967被保留gamma-image-r1-validation.json为failed，不算通过。

R1异常是旧capture只看图片相同、不要求CCM状态稳定，启动矩阵变化时可能过早保存。R2仅mainfactory0/mainlinear/mainrgb，probe新加previousMatrix稳定条件和startup逐帧私有图，不改生产IPA/内核，复用旧kernelnegative。/var/lib/samurai/k349-gamma-r2 worker32258终态pass，54+53+48=155frames/12phase图+13startup图；其它四组复用R1。相同seq0..3 startup RGB模型p99 .986..1.207/255，证明Gamma启动通道响应一致；不据此声称所有硬件模块锁存时序已证。startup-boundary-validation.json。Pimages-r1/r2、probe-observations、phase-signatures/selected-runs私存，startup-comparison-private.png仅TPG。

analyze-runtime.py r1,r2生成明确derived_not_worker_observation的probe-r1-r2-combined私有观察，并记录selected_case_run/source_runs，不伪称单一worker。选定337frames/151LSC states trace对应原函数+独立重采样，294CCMframes10584bytes零差；总实际观察478frames，七AWBlock/frontCCMfalse。Gamma每组仅一个initialACK，所有已应用revision gamma1，按actual Pair/Recovered SOF关联。gamma-image最终只比相同前Gamma状态：phase0/1 RGBmean.448/.455,p99 1.207/1.116；factorymean.401/.357,p99 2.000/1.790，最大6.46近似NV12逆RGB非RAW精度。phase2状态不同明确skip，PN9不跨时刻比较。runtime-iq/gamma-image/startup-boundary都pass；旧R1差异保留。

349最终恢复338note，现机仍344etcprivate五模式+r27/r22+Image298/sensor305/325/CAMSS338，未安装Gamma。PW32441/WP32475各uid10000，相机/2CCI suspended、9railsdisabled/users0，相关faultdelta0/taint0，两个worker终态，无hostbuild/SDKbind。source349候选+patch/state保存并镜像通用代码/脱敏报告，private factory/unit/图像/vendor不镜像。

新发现决定下一步350：原厂包还存在后级gamma15_ipe，不能把本轮IFE曲线冒充最终显示tonecurve。349 inspect-ipe-gamma.py从原BIN独立遍历，固定schema gamma_1_5_0（gitshow9f17f1b...，私有kernel349/gamma_1_5_0-reference-private.xsd），root136/17Q，treeDRC32/HDR64/LED24/AEC48/CCT32，channel1040(typeQ+257f+pad)，所选channels=3表示commonRGB，并非R/G/B各三。14actualmode/usecase对stock genericmanager零差，全部UID55/enabled1；main根6curves、front3、wide/tele8，各都非线性。完整模块根/树/curve XML核对和IFE→IPE域/顺序仍待。公开downstream-gamma-inventory是inventory不是完整解码证明。不要现在直接安装IFE曲线为最终默认。

下一步优先从保留BIN完整提取Gamma15_IPE、对原厂parser XML，并查gamma15setting/interpolation及Camx IFE/IPE处理链，确定最终tonecurve及合成/硬件表达（VFE64段与IPE256段不可混同）；可能还需GTM/LTM相关状态。复用347decode结构扩展257点/1040stride/commonRGBtype3，保留全部触发/模式，勿盲改数据或把Curve最多点数当相同语义。C近满，新的parser工作目录/大analysisBIN放既有E ext4，不在C复制大型源码/BIN。原厂通用IQ与EEPROMunit分层。之后组合发布内核348与用户空间Gamma方案，再继续AE表antibanding/sensorlimits、其它模式、正常光学、多摄几何同步/连续AF；完整goal仍active。用户目标最新：优先已有仓库方案，优先反编译原厂固件获取文件和校准，尽量底层收敛。''' +s[end:]
path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel349/README。349 Gamma已接候选IPA，15AArch64合同通过，组合348kernel实机R1七组323frames+R2只补三主摄155frames，最终选337frames/151LSCstates/10584CCMbytes对应，7AWBlock，GammaACK/SOF/像素验证。启动旧snapshot判定漏CCM稳定导致R1phase0模型异常已保留failed，R2采集条件修复，same-seq启动RGBp99<1.21，未改生产Gamma。仍未安装，恢复338+r27/r22+344etc，PW32441/WP32475 uid10000、idle/fault0/taint0，无worker/build/bind。新的优先下一步350：原厂还有gamma15_IPE257点后级，14模式usecase选UID55/enabled1、有非线性curves；349 inventory仅独立binary+manager，无完整XML/域顺序核对。优先从原固件完整提取Gamma15及processing chain、必要GTM/LTM，核清IFE→IPE再决定默认最终曲线，不能把已测IFE当最终OEM画质。schema私有kernel349，source refs9f17f1b，复用347 decoder扩1040channel/257points/commonRGBtype3，parser大工作放E ext4（C近满）。全目标AE/防频闪/模式/光学/同步/连续AF未完成。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('349当前：IFE Gamma候选IPA与348内核组合实测通过，尚未安装；原厂后级IPE Gamma已发现，继续核对最终色调链后再更新默认。[349详情](../../reference/kernel349/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded349 Gamma IPA/hardware progress and downstream Gamma discovery; deployed baseline preserved, full goal active.')
