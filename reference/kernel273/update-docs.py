from pathlib import Path
R=Path(__file__).resolve().parent;W=R.parents[1]
next_text='''# Realme X2 Pro 当前检查点

2026-10-18：[273 GW1主摄实机接入](reference/kernel273/README.md)。现前摄IMX471及后摄GW1/IMX319/S5K3M5均可原生取流，四摄18段238帧交替通过；GW1已有RAW/RGB和600帧实景JPEG。完整控制测试失败、AF/画质/GUI/录像/Spectra仍未完成，目标active。当前SSC启动失败，自动旋转不可用；桌面临时恢复。

## 当前部署与启动身份

boot273/Image183，`7.3.0-rc6-rmx1931-samurai-k132+`，775模块/961包。boot SHA256 `dd4c34e4f18a4292cb70dd9b3d87ad710ce4f6e4e4048fe85c7b94eee911d475`，DTB `615f7523df579313f514d0dfa809fcde96355a419ad24dbb62b1eaa60955d252`。只刷boot、仅改变内嵌DT；Image183/logdump和其它774模块保持。GW1模块`0c907b122065b8657dc9f9e68ff17784c5419ed1994fe9f1ced5ccfa60c90ade`已加载，八相机模块note匹配磁盘。

五个libcamera组件r21、config/stack-r16；PW/SPA/Gst仍1.6.9-r3，其它954包记录保持。S5K3M5原生32…512与helper code/32配套仍保留；GW1普通模式32…1024对应1…32倍。当前CPU ISP/system heap、Snapshot Cairo/禁用GL、Vulkan、offload回退保持，默认GPU故障未修。

运输改用`reference/kernel273/host.py`，原严格SSH密钥与新USB接口已核；guard `/var/lib/samurai/k273-work/boot-id-private.txt`。旧270/271/272 guard均为旧启动。当前Phoc4610/start66605、Phosh4682/start66754、PW6088/start67241、WP6095/start67244，手机`/var/lib/samurai/k273-services-current-private.json`；续作重核。当前[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)已更新并现机读回。

## 本轮已经验证

- GW1本机0x10/ID0x0971真实识别，标准静态DT/driver资源接入，CCI0 master0/CSIPHY0 C-PHY已出RAW；没有Android HAL包装或新实验供电provider。源码、主机测试及构建见[272](reference/kernel272/README.md)，该文“未部署”属于上一阶段。
- 正常abuild从保留r20源/对象构建13个完整功能签名APK，五IPA及ARM入口QA通过；原214工作和r20缓存保持。实际r21 helper993码与旧r20缺GW1负向对照通过。七包只升级一次，原774模块保持，只新增GW1为775。
- 主摄标准cam RAW/RGB各12帧；普通libcamerasrc/CPU JPEG600帧、PTS跨度19.92985秒，后期更明亮并有真实场景，仍明显虚焦、AF和颜色/噪声未验收。四摄18段238帧，含主摄SIGINT/重开全部通过，无强杀。[主摄](reference/kernel273/main-capture-validation.json)、[四摄](reference/kernel273/four-camera-regression-validation.json)。
- 同request RAW4608×3456/RGB2048×1536取得66组、序号/时间戳对应；2/8/32ms和1/1.5/2倍有物理响应。但4倍阶段元数据未在窗口匹配，原96组完整测试失败，不能算控制延迟通过。probe全帧统计负载有跳序，按sensor序号差归一约30.055fps/1.91995GHz，匹配默认FLL的1.92GHz候选；不外推其它时序。[失败](reference/kernel273/main-manual-r1-validation.json)、[分析](reference/kernel273/main-evidence-analysis.json)。
- 最终四sensor/双CCI/CAMSS suspended，九rails OFF/users0、四MCLK关闭，无客户端，fault0/taint0/pstore空，49载荷及775模块/961包重核。[最终状态](reference/kernel273/final-health-validation.json)。旧Snapshot/modem watchdog未修。

安装实际成功后，降级检查误用不支持的apk参数而中止；保留原失败，未重复安装，独立核验及七包显式版本降级模拟通过后才重启。当前packages-verified状态与旧packages-state失败分别保留。原构建规则/AST解析错误均发生对应提交前，详见273记录。

## 源码、回退与下一步

维护WSL `/home/cy122/x2pro-linux/camera270-kernel`，分支`samurai-main-camera272`，提交`3184c56b7f206ab000ab79bc99eb83d35c3e1d65`；本轮未改内核代码/未推送。Windows libcamera/config配方已为r21/r16；旧r20/r15及部署/源码锁归档`archive/camera-before273-2026-10-18`。公开pmaports分支未同步/发布。269完整Image/模块候选仍未部署，完整最新rootfs未重建。

当前SSC默认启动失败：文件服务attach返回Operation not permitted/exit4，SLPI已停、sensor-power OFF；FastRPC加载note与磁盘匹配，未证实原因。greetd依赖SensorProxy因此原未启动，已一次`rc-service --nodeps greetd start`临时恢复桌面，永久依赖配置保持。**当前自动旋转不可用，SSC/正常开机链未修。** 保留`/run/samurai-ssc/state.json`和日志，不用269旧通过替代当前状态，不盲目清记录重试共享池停启。

优先定位高分辨率控制/元数据：第60…65个交付请求仍报2倍，停止后driver控件缓存code128/4倍，不能单凭缓存判根因。可继续核IPA目标产生、统计回调/DelayedControls及真实SOF对应，保留原失败而非放宽断言。probe在`/run/samurai-camera273-probes/main-control-probe273`，`k273-main-manual-r1`已终态。其后继续AF/校准、AE速度/画质、更多模式、四摄GUI/录像、GPU和长稳；前摄纯色目标仍按用户延期。

匹配回退手机/PC双份26116631字节，SHA256 `209908a882a9508b49adc6b7eed3cf1f4fc726ae0a8d4da4b745a32217aabeac`，含boot270/r20/r15和原配置/depfiles；只做验签/降级模拟，未实际往返。私人资料`E:/edk2-samurai-out/kernel273`，手机`/var/lib/samurai/k273-main-transaction`等；所有旧事务终态，不重放。当前Qualcomm CSIPHY/CSID/VFE RDI采RAW，成像仍CPU软件ISP，Spectra硬件成像未接通。其它硬件见[清单](linux-port/docs/HARDWARE-STATUS.md)，规则见[边界](WORKING-BOUNDARIES.md)。
'''
assert len(next_text.encode())<=6500
(W/'NEXT-SESSION.md').write_text(next_text)
for name in ['linux-port/camera/README.md','linux-port/camera/kernel/README.md']:
 p=W/name;link='../../reference/kernel273/README.md' if name.endswith('camera/README.md') else '../../../reference/kernel273/README.md'
 p.write_text('273已部署：GW1主摄已实机绑定并经C-PHY取得RAW/RGB和实景JPEG，前摄＋三后摄238帧交替通过。当前boot273/Image183、775ko/961包、libcamera r21/config-r16；完整控制切换仍失败，AF/画质/GUI/Spectra及SSC开机问题未完成。[实际状态]('+link+')。以下272及更早内容按当时状态解释。\n\n'+p.read_text())
p=W/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text();title,rest=t.split('\n',1)
p.write_text(title+'\n\n273：GW1主摄已实机C-PHY RAW/RGB取流，前摄＋三后摄238帧交替通过、主摄600帧实景JPEG；boot273/Image183、775模块/961包、r21/r16。手动控制测试在4倍阶段失败、AF/画质/GUI/Spectra未完成。新启动SSC/FastRPC attach失败，自动旋转不可用，桌面仅临时nodeps恢复；不能用旧SSC通过覆盖本次失败。[273证据与当前限制](../../reference/kernel273/README.md)。\n'+rest)
p=W/'reference/kernel272/README.md';t=p.read_text();title,rest=t.split('\n',1)
p.write_text(title+'\n\n后续[273](../kernel273/README.md)已实际部署本候选并取得主摄RAW/RGB及实景；下文“未部署/未上电”描述272当时状态。完整控制切换测试、AF/Spectra及SSC开机问题仍开放。\n'+rest)
p=W/'HANDOVER-NEXT.md';t=p.read_text();needle='未部署GW1驱动/DT/helper候选及验证见[272](reference/kernel272/README.md)，';assert t.count(needle)==1
p.write_text(t.replace(needle,'当前GW1实机接入、四摄及新失败见[273](reference/kernel273/README.md)，此前候选见[272](reference/kernel272/README.md)，'))
p=W/'reference/kernel270/LAYERING-AUDIT.md';t=p.read_text();title,rest=t.split('\n',1)
p.write_text(title+'\n\n后续[273](../kernel273/README.md)已加入主摄GW1/C-PHY并部署r21/r16，现三颗后摄可原生取流；控制切换、AF/Spectra和SSC开机失败仍未完成。本文其余源码规模、包数、身份和审计结果属于270阶段。\n'+rest)
print('Updated current boot273 checkpoint; bytes',len(next_text.encode()))
