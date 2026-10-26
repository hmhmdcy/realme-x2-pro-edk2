"""Publish closeout evidence and concise continuation notes; never publish private inputs."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
assert json.loads((HERE/'closeout-device-validation.json').read_text())['passed']
assert json.loads((HERE/'dispatcher-regression-validation.json').read_text())['passed']
runtime=json.loads((HERE/'runtime-validation.json').read_text());assert not runtime['full_candidate_validation_passed']
state=json.loads((HERE/'dispatcher-source-state.json').read_text())
(HERE/'source-state.json').write_text(json.dumps(dict(stage=361,baseline_stage=360,source=state['source'],
    production_change=state['file'],source_sha256=state['sha256'],
    patch_sha256=hashlib.sha256((HERE/'event-dispatcher-reentrancy.patch').read_bytes()).hexdigest(),
    common_dispatcher_regression_passed=True,threaded_factory_contexts_passed=10,
    isolated_request_path_passed=False,known_remaining_failure='CAMSS IspControls queue reentrancy during synchronous applyIspControls',
    runtime_payload='360 packaged r28 core/IPA/proxy plus 361 rebuilt common base; temporary348 driver',
    full_new_packages_built=False,installed=False,full_camera_goal_status='active'),indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
    p=ROOT/relative;d=json.loads(p.read_text());d.update(
        current_camera_evidence=prefix+'reference/kernel361/README.md',in_progress_stage=361,
        in_progress_evidence=prefix+'reference/kernel361/README.md',in_progress_installed=False,
        ipa_candidate_source_stage=361,ipa_candidate_source=state['source'],ipa_candidate_source_evidence=prefix+'reference/kernel361/source-state.json',
        candidate_combined_threaded_factory_contexts_verified=10,candidate_combined_hardware_verified=False,
        candidate_camss_v1_isolated_ipc_verified=False,candidate_common_dispatcher_fix_regression_passed=True,
        candidate_remaining_failure='CAMSS IspControls queue reentrancy in isolated synchronous IPC',
        candidate_r28_packages_include_dispatcher_fix=False,device_current_ssh_status='strict_original_key_usb_restored',
        device_current_taint=0,device_closeout_evidence=prefix+'reference/kernel361/closeout-device-validation.json',
        current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
    p.write_text(json.dumps(d,indent=2)+'\n')
old=ROOT/'NEXT-SESSION.md';archive=ROOT/'archive/NEXT-SESSION-through360-2026-10-20.md'
if not archive.exists():shutil.copyfile(old,archive)
old.write_text('''# 当前检查点：361（收尾交接）

2026-10-20。用户要求收尾、提交、更新文档并交接；本阶段已结束实机实验。完整多摄／骁龙 ISP 目标尚未完成，不能标记完成。按 WORKING-BOUNDARIES.md 选择相关验证，复用未改部分的结果。

## 已交付与未通过

360 将原厂曝光／手动防频闪和 IFE Gamma 合并为 r28／配置 r23 候选，完整构建、签名和 ARM64 组合检查通过，未安装。361 临时使用 348 Gamma 模块实机验证：四摄、五物理模式、十个原厂 Preview／Video 线程上下文均完成五段 EV／频闪／WB 请求，共 274 帧。

隔离 IPA 仍未通过。r4 在公共 EventDispatcherPoll 递归分发中断言；361 公共层补丁保留外层状态、最外层才回收条目，ARM64 旧版失败／新版通过的八组回归符合预期，接口／类布局未改。r5 用新 base 实机越过原断言，随后 CAMSS IspControls 队列重入导致空队列 pop_front。r4／r5 整轮均保留失败，未执行的广角实景不计通过。完整记录及补丁见 [361](reference/kernel361/README.md)。

下一步先修 CamssVfeData 待处理 ISP 队列在同步 applyIspControls() 前后的重入／所有权；r5 同一 source=12 重复处理。不要删断言、空队列跳过或禁用隔离。用新事务验证隔离主摄、一个线程上下文及广角实景，再制作下一版完整包。360 r28 APK 仍含旧 base；361 尚未生成 r29，不能直接把 r28 当隔离合格包安装。

## 当前设备

最后只读观察：原严格密钥 USB 169.254.42.1 SSH 可用；7.3.0-rc6-rmx1931-samurai-k298+，CAMSS338 note SHA256 0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297，taint0。libcamera 五运行包 r27、config／stack r22；PipeWire／WirePlumber 各一个、uid10000；CAMSS／双 CCI suspended；无活动361 worker、无 ICP实验模块或孤儿固件。r5清理九电源 disabled/users0，相关新内核故障0。[最终状态](reference/kernel361/closeout-device-validation.json)。

临时348及候选用户空间已撤回，安装文件未改，无重启／刷写。原版本四摄各4帧的基础检查见360，不重复未改组件全量测试。手机已恢复Linux，无需沿用357的强制重启请求。9008进入过程见357；退出触发未知，pstore为空。旧356 R5状态仍 load-boot-test／terminal=false、worker不存在，不改成成功。

## 源码、构建和私有资料

公共实现／脚本主工作区：E:\\RealmeX2Pro edk2；Git提交位置：WSL /home/cy122/edk2-samurai/repo，子目录 Platform/Realme/sm8150。公共镜像不含个体校准、原厂固件、密钥及认证原始日志。

libcamera候选：/mnt/samurai-full282/libcamera361-event-dispatch-built/src/libcamera-v0.7.2；相对360只改公共 event_dispatcher_poll.cpp。已重建 base，核心／IPA／proxy取360实际打包载荷。临时bundle必须包含 .so.0.7 → .so.0.7.2 相对SONAME链接，r1/r2因遗漏链接误载系统r27。

360完整包／回退仓库、8份完整私有原厂用途配置：E:/edk2-samurai-out/kernel360；361实机原始观察：同级kernel361。手机事务 /var/lib/samurai/k361-request-r1..r5 保留，不重放。host361.ssh沿用host360新guard；private360/recovered-boot-adoption-private.json定位当前启动，旧305/356guard不变。

SDK /home/cy122/x2pro-linux/libcamera214-root；进入E盘ext4前调用storage284.mounted_build()，其mount含flock；SDK /work/libcamera临时bind不能并发，退出释放。已有执行handle只轮询，不因观察超时重复启动。C盘空间紧，不复制大型源码／产物到C。

内核 /mnt/samurai-full282/source354，branch samurai-iommu-node-lifetime357，commit ba61a62293e0f6bc5838c06f2e85e033e3d702a8。357 IOMMU节点引用修正已W1/Werror构建、未装。356第7构建已改Realme板级firmware 0x9ab00000／5MiB命名memory-region，从未发机；旧generic 0x8b700000实验失败，不能复用。尚无完整SYS_INIT／PING／PC_ACK成功。

## 后续范围

先完成隔离队列／新包，再推进正确内存下ICP／HFI及IPE完整会话，接350/351/352后级Gamma／LTM／CCM；动态FrameDurationLimits、自动频率检测、更多模式、光学／几何、多摄同步及连续AF仍待完成。十上下文TPG请求链不等于物理曝光响应或绝对校准，IFE Gamma不等于最终原厂显示色调。未知前摄裁剪保留generic，缺完整IQ的高分辨率不造表。

历史检查点保留在 [360及以前归档](archive/NEXT-SESSION-through360-2026-10-20.md)，各reference按当时记录解释。357认证／360原始日志可能含私密输入，不打印或镜像。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从361收尾交接继续。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel361/README.md。四摄五模式十原厂线程上下文r28 EV/flicker/Gamma请求274帧通过；隔离仍失败。公共EventDispatcherPoll补丁已ARM64回归通过；r5新base暴露CAMSS IspControls队列同步IPC重入，source12重复处理后空deque pop_front。先修队列所有权/重入再新事务测isolated、一个threaded、未执行的wide-optical，之后做新包；360 r28 APK仍旧base，361无r29/未安装。设备已恢复原r27/r22+338/k298，严格USB SSH可用、taint0/PM休眠、服务各1 uid10000、无活动worker。勿重放旧r1..r5/356R5；360新guard沿用。完整目标ICP/HFI/IPE、后级IQ、动态帧长/更多模式、光学同步连续AF未完成。内核source354 branch357 ba61a622，正确9ab00000 build7未发机。SDK bind勿并发，storage284先挂载，私有校准/固件/密钥/认证日志不入公共Git。\n')
entries={
 'linux-port/camera/README.md':('361收尾：四摄五模式十原厂线程上下文完成r28曝光／频闪／Gamma请求274帧；隔离模式仍有CAMSS队列重入错误。公共分发器修复ARM64回归通过，未打新包／未安装；设备已恢复r27/r22、338/k298及服务，taint0、资源休眠。','../../'),
 'linux-port/camera/kernel/README.md':('361收尾：348 Gamma模块仅临时用于请求链验证，已恢复338；k298/taint0/双CCI与CAMSS休眠。公共用户空间分发器已修，隔离CAMSS请求队列仍待修；357 IOMMU补丁及356正确板级内存候选未安装。','../../../'),
 'linux-port/docs/HARDWARE-STATUS.md':('361收尾：已安装r27/r22与CAMSS338/k298；四摄基础取流沿用360，候选十线程上下文274帧请求通过，隔离队列仍失败；新候选未安装。ICP/IPE、完整光学与多摄校准未完成。','../../'),
 'linux-port/packages/libcamera/README.md':('361收尾：正式配方/安装仍r27。360 r28候选完整包已构建但含旧公共base；361修复分发器并过ARM64回归，实机暴露第二处隔离队列错误，尚无下一版完整包。','../../../'),
 'linux-port/packages/samurai-camera-config/README.md':('361收尾：安装及正式配方仍r22，360 r23只作为未安装候选。隔离请求链尚未通过，公共默认配置不加入原厂或个体表。','../../../')}
for relative,(entry,prefix) in entries.items():
    p=ROOT/relative;s=p.read_text();tag='361收尾：'
    if not s.startswith(tag):p.write_text(entry+' [361交接]('+prefix+'reference/kernel361/README.md)。以下为历史。\n\n'+s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('最后整理：2026-10-19','最后整理：2026-10-20').replace('| 当前交接、清理收据、重建方法及续作顺序 |','| 历史清理、保留产物与重建方法 |');link='| 本轮收尾与续作 | [361请求链、分发器修复和交接](reference/kernel361/README.md)、[当前检查点](NEXT-SESSION.md) |\n'
if '361请求链' not in s:s=s.replace('| --- | --- |\n','| --- | --- |\n'+link,1)
p.write_text(s)
p=ROOT/'HANDOVER-NEXT.md';s=p.read_text();notice='361收尾交接：优先读[当前检查点](NEXT-SESSION.md)与[361具体结果和续作](reference/kernel361/README.md)。新候选隔离队列未通过，设备已恢复原版；后文部署身份与提交统计均为历史快照。\n\n'
if notice not in s:s=s.replace('\n\n','\n\n'+notice,1)
p.write_text(s)
p=ROOT/'sessions/INDEX.md';s=p.read_text();line='- [361 请求链实测、公共分发器修复与收尾交接](../reference/kernel361/README.md)\n'
s=s.replace('| [kernel361](../reference/kernel361/README.md) | 请求链实测、公共分发器修复与收尾交接 |\n','')
if line not in s:s=s.replace('## 早期拆分与快照','## 最新交接\n\n'+line+'\n## 早期拆分与快照')
p.write_text(s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
files=[p for p in HERE.iterdir() if p.is_file() and p.suffix in ['.py','.cpp','.patch','.json','.md']]
files += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','HANDOVER-NEXT.md','sessions/INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',*entries]]
files += [archive]
for source in files:
    target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Published361 closeout; isolated/full-candidate failure retained; installed versions unchanged.')
