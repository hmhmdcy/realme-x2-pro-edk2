"""Record the deployed common fix and keep current navigation consistent."""
from pathlib import Path
import json
R=Path(__file__).parent;repo=R.parents[1]
assert json.loads((R/'evidence-validation.json').read_text())['archive_and_all_member_sha256_verified']
current=repo/'NEXT-SESSION.md';saved=repo/'archive/NEXT-SESSION-through263-2026-10-18.md';assert not saved.exists();saved.write_bytes(current.read_bytes())
text='''# Realme X2 Pro 当前检查点

264相机：同260启动/961包，已原生安装PipeWire核心＋libcamera SPA 1.6.9-r2，撤去Snapshot复制开关。标准系统共享路径2704次保留检查0变化/错误；真实窗口预览39秒2254缓冲、快门1920×1080 JPEG解码通过。内核boot235/Image183、libcamera r15/config-r10及GStreamer r1保持；CPU显示配置保留，默认GPU未修。公共层修复无需逐应用改代码；画质/后摄/切换/录像仍待办，目标active。[补丁、包、失败与验收](reference/kernel264/README.md)、[源配方](linux-port/packages/pipewire-common/README.md)。

先读[操作边界](WORKING-BOUNDARIES.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)和264。当前guard为`/var/lib/samurai/k260-work/boot-id-private.txt`；运输资料仅私人`E:/edk2-samurai-out/kernel260/host.py`，264包装它，严格固定原主机密钥。257/259、Android251—256及旧RAM guard均已失效，不能以旧身份执行切换。

## 相机当前部署与续作

公共核心870b7077…、SPA0c3471e6…系统路径已映射，两项r2精确配对，原r0可信APK及成对降级模拟保留。只有两个APK记录变化，仍961包；49项框架保持。原GStreamer插件d7a55006…未改，262复制功能默认关闭；启动项哈希/包约束/完整回退见264。源码增量编译＋保留官方载荷打包已完成，完整abuild尚未跑；配方5patch/10项摘要/精确源码应用通过，不能写成完整源重建通过。

最终PW PID29640/start4321604、WP PID30425/start4360372、Phosh PID2261/start1967。五轮生产测试＋实际GUI共用这些身份，无每次关闭重启服务。旧测试器外部恢复media graph导致libcamera缓存失配，6000071失败保留，修正测试器后仅刷新一次WP。生产应由libcamera正常释放，不在其背后写回媒体链接/格式/AE。25个有状态上下文全终态、PM休眠/MCLK关/trace无、新增fault0/taint0；728个私人归档成员SHA通过。手机/PC证据在k264与E:/edk2-samurai-out/kernel264；测试目录已有结果，不盲目重跑一发式安装/重启/快门/导出。

后续先处理IMX319近黑、曝光/增益/裁剪与前后切换，再其余后摄S5K3M5/GW1、噪声/颜色、录像/长稳及全新rootfs。实际窗口渲染与快门通过不代替人工光学画质验收；GPU历史480fault和GPU ISP退出IOMMU WARN仍开放。没有永久取消锁屏；本轮验证时screensaver已非active。263 Busy计数清零实验已否决；SDK旧broadcast树的SPA曾被失败实验改写，不能直接重建该SPA。按264公开补丁与已核哈希复现。

## 用户态维护与桌面

10月18日full upgrade：55包升级、3依赖新增，现961包；未重启，同260启动。Phoc仍0.57，键盘待重登加载新版。[升级与回退](reference/full-upgrade-20261018/README.md)。下述958包为升级前历史验收。

261检查：缺中文字体、主要桌面翻译和locale，输入源US；UIM已有拼音需接入。商店APK插件在而Alpine应用目录缺失，AppStream/CDN超时。GTK编辑焦点显隐通过，搜索误弹/不收起复现；Phoc0.57只宣告版本1。上游Phoc MR813已合并并随0.58发布，新接口版本2区分enable与show/hide；优先上游及匹配wlroots，未部署或实机验收。[261详情](reference/kernel261/README.md)

## GNSS已验收与待办

260普通桌面GNSS-only室外300秒280次更新、262次严格校验、GPS去重9颗TRACK/46.7dB-Hz，停止后自动LOW_POWER并恢复设置；无额外HIGH客户端。验收boot235/Image183、958包，GeoClue2.8.2-r1/helper2-r1/MM203-r1。旧采集器错误要求Accuracy>0，上游HDOP≤1可映射0；18个余下事件没存字段，不能追认或直接算丢星。PGA未观测不能记0。[260](reference/kernel260/README.md)

用户已拿回接USB，260室外worker及inhibitor已退出，22个导出文件SHA核对；源配置/隐私/Wi-Fi省电恢复，最终GPS0/Signalsfalse/rate30/Power2/taint0。首次严格更新12.97秒不是冷启TTFF。下一步冷启、PM、长稳和绝对精度，不重跑已完成worker。无线SSH不稳定，USB原密钥可用，无remoteproc/WLAN崩溃证据；临时代理排除撤回。

GeoClue r1修复来源位所有权/异步取消协调，10项回归通过。辅助服务2-r1只对本机缺SIM且无SIM对象，在真实GPS请求管理自己的在线租约；显式OFFLINE保持，回收LOW_POWER、不写Reset/RF/NV。14项回归及实机四轮通过。259 OFFLINE失败不能当ONLINE对照；260重启后独立GET确认ONLINE↔LOW通过。258原生室外287份/286秒、去重12颗TRACK/44.4dB-Hz/PGA+2；256原厂302份、去重10颗/45.5dB-Hz/PGA+2，位置/启动/辅助并非单变量。完整5MiB MEMSHARE/SCM provider及室内PGA根因仍待办。[258](reference/kernel258/README.md)、[256](reference/kernel256/README.md)

## 其它硬件与源码

其余见[240交接](reference/kernel240/HANDOFF.md)和硬件清单：充电闭环、传感器精度/旋转、SLPI重启、真实SIM业务与外围完整适配开放。模块权威清单237为775ko/789项；NV/GPT/persist未回刷，248完整返回备份保留。遵循上游＋最小功能补丁＋原生APK。

[pmaports](https://github.com/hmhmdcy/pmaports)默认samurai-userspace最后推送4aeae3b3；[内核](https://github.com/hmhmdcy/linux/tree/samurai-bringup)04d4d4f9。249独立源复现、882包rootfs与38项MM测试只属PC候选；259/260GNSS与262—264相机修复仍本地未推送。旧栈约束在reference/kernel260/legacy-stack，不混入249默认候选。

249构建卷D:/samurai249-build/build-ext4-private.img（32GiB）挂载/home/cy122/x2pro-linux/pmos249-build，不能mkfs；SDK github-only/sdk-r2。原内核/SDK、私人回退及未提交DTB保留，内核清理/PMIC/provider/DTS待办见[249](reference/kernel249/README.md)。上个检查点全文已[归档](archive/NEXT-SESSION-through263-2026-10-18.md)。
'''
assert len(text.encode())<=6500,len(text.encode());current.write_text(text)
p=repo/'DOCS-INDEX.md';s=p.read_text();s=s.replace('最后整理：2026-10-17','最后整理：2026-10-18');s=s.replace('| Camera应用、实体前后摄与内部TPG | ','| Camera应用、实体前后摄与内部TPG | [264公共修复部署与实际快门](reference/kernel264/README.md)、[公共源码配方](linux-port/packages/pipewire-common/README.md)、',1);p.write_text(s)
p=repo/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text();start=s.index('263相机');end=s.index('\n\n',start)
s=s[:start]+'''264相机（2026-10-18）：已原生安装PipeWire核心＋libcamera SPA 1.6.9-r2，撤去Snapshot复制开关；同260启动/961包，内核与r15/r10保持。系统标准共享路径2704次保留检查0变化/错误，实际窗口预览约39秒2254缓冲及1920×1080快门JPEG解码通过。应用二进制未改，CPU显示设置保留；公共层修复供标准客户端共用。25个有状态上下文全终态、PM/MCLK恢复、新增fault0/taint0。画质/后摄/切换/录像和默认GPU问题仍待完成。见[264补丁、失败与部署验收](../../reference/kernel264/README.md)、[源配方](../packages/pipewire-common/README.md)。'''+s[end:]
s=s.replace('历史libcamera r15/config-r10、Snapshot CPU前摄预览通过，拍照/切换/缓冲回收仍开放','libcamera r15/config-r10、Snapshot CPU前摄预览及实际快门、264公共缓冲修复所测场景通过，切换/后摄/画质仍开放')
rows=s.splitlines()
for i,line in enumerate(rows):
 if line.startswith('| 摄像头 |'):
  rows[i]='| 摄像头 | 264同260启动，公共核心/SPA 1.6.9-r2已成对部署、撤去Snapshot复制开关；系统共享路径2704次保留检查0变化/错误，实际窗口约39秒2254缓冲/0回收错误、快门1920×1080 JPEG完整解码；正常退出、崩溃、跨框架/双客户端通过；49项r15/r10保持、PM/MCLK恢复/新增fault0 | 前摄曝光/噪声/颜色尚未作光学验收，前后切换、IMX319近黑、S5K3M5共享电源/未编译候选、GW1/人像、录像/长稳/完整abuild与rootfs待完成；CPU显示回退保留，240默认Vulkan480fault及GPU ISP退出IOMMU WARN未修；Megapixels配置/后端仍待接入 |'
p.write_text('\n'.join(rows)+'\n')
print(json.dumps(dict(current_docs_updated=True,next_session_bytes=len(text.encode()),previous_checkpoint_archived=True)))
