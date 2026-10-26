from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel212')
health=json.loads((here/'final-health-validation.json').read_text());assert health['taint']==0 and health['default_cpu_capture_post_warmup_pass']
archive=json.loads((here/'final-evidence-archive-validation.json').read_text());assert archive['private_archive_all_members_verified']
(here/'README.md').write_text('''# 212：同一boot镜像第二次启动与默认CPU ISP

boot211未修改、未刷写。以当前211身份完成分区/产品程序/786文件模块树核对、正常停用相机和三个DSP、关闭显示音频后，执行一次restart2和一次经新fastboot身份核对的reboot；两个请求marker均闭环。旧GPU告警及全部失败证据已保留，不能重放切换。[停用](quiesce-validation.json)、[停用归档](prewarmboot-archive-validation.json)、[新启动](runtime-validation.json)。

旧启动printk环形缓冲区从保存的349条变为可见348条，首轮严格总数检查在任何停用动作前拒绝。逐条带时间戳比较证明只是旧行被淘汰、没有新告警，修正检查后才继续；不是放宽到允许新增告警。所有原始日志保留。

新启动自动绑定IMX471/PM8008，加载新sensor模块及heap，CROP/TRY/ACTIVE均正确，sensor供电域存在，三个DSP running，taint/五类fault0。首轮普通用户取流发现`/etc/libcamera`目录被部署umask变成0700，CPU配置不可读，再次落入GPU的CMA不足；未取流、无新增fault。修复目录0755/文件0644并保留原失败。[首次失败](default-cpu-capture-validation.json)、[目录修复](config-directory-fix-validation.json)。

随后以真实桌面UID10000、不设置`LIBCAMERA_SOFTISP_MODE`，运行系统默认配置取得6帧1920×1088 RGB888。strace证明读取系统CPU配置且未打开DRM节点；日志没有EGL renderer。首帧全黑，随后5帧非全黑，后四帧预热窗口通过；没有超时、强杀或新增五类fault，测试图案均0。**不是六帧全通过，也不代表拍照质量已验收。** [6帧证据](default-cpu-capture-r2-validation.json)。

226秒最终健康：sensor/CAMSS/CCI休眠，VDIG/VANA disabled/users0、MCLK0、自身MMCX vote0；桌面相机监视进程未暂停。三个DSP running、taint和五类fault均0。GPS0/Signalsfalse/rate30，BT关闭无连接，NV及产品程序核对保持。GNSS自动UTC第8次准备成功、chrony Normal，没有人为补时或新增收星实验。[健康](final-health-validation.json)。

96份原生文件已私下快照归档并逐成员核对；原始场景图像、端点、私人标识与归档指纹不公开。未新增kernel源码变更，语法/diff检查通过，没有暂存或提交。[归档](final-evidence-archive-validation.json)、[源码](source-final-validation.json)。

当前运输`reference/kernel212/host.py`，guard为`/var/lib/samurai/k212-runtime/boot-id-private.txt`；boot211 c3bf043f…/DTB6f9f5b0f…/Image183、logdump183保持。CPU配置为当前兼容路径，GPU ISP的CMA不足/黑帧/IOMMU unmap仍需修复；首帧黑、IMX471增益helper/延迟/静态属性、方向/tuning、完整16MP及后置四颗摄像头均未完成。完整外设goal继续active。
''')
checkpoint='''# Realme X2 Pro 当前检查点

2026-10-15，阶段212完成有限默认CPU ISP验证，完整外设goal active。普通桌面用户取得6帧1920×1088 RGB888：首帧黑、后5帧非全黑；系统CPU配置跨启动生效，未走DRM/EGL，最终taint/五类fault0。它不是完整拍照质量验收，后置四摄仍待接入。[212报告](reference/kernel212/README.md)、[211完整快照](archive/NEXT-SESSION-through211-2026-10-15.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 当前运输reference/kernel212/host.py，新guard为/var/lib/samurai/k212-runtime/boot-id-private.txt。212执行一次正常停用/restart2/fastboot reboot，没有刷写，两个marker已闭环；211的三个marker也已闭环，不可重放。k212-before-reboot及全部211 guard是旧启动。
- 当前boot211 c3bf043f…/DTB6f9f5b0f…；Image183 bfa72dd9…/logdump183 e73754c7…保持。IMX471模块a28dd67a…，CCI f9c9272a…/PM8008 d1ff82c0…/CAMSS82cbc052…/BT185保持；模块树772ko/786文件。TFTP207 b3bb82b9…/wifi854c9a8c…/MCFG helperd4c62be6…/MM191/helper421/init54/SSC9a1保持。
- IMX471/PM8008静态自动绑定，media0为23实体，sensor有独立TITAN_TOP域。前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/200MHz、CSIPHY2。PMIC源码&i2c4为0x890000，运行i2c-1不等于源码&i2c1。210两轮6帧1928×1088 RAW10及211独立sensor PM/裁剪接口修复保持。
- heap自动加载/权限跨启动通过，通用堆root/video0660、FastRPC专用池root0600。/etc/libcamera/configuration.yaml选择CPU，目录0755/文件0644。212首轮目录0700导致配置不可读/CMA不足，原失败保留；修正后默认配置6帧中首帧黑/后5帧非全黑、无新增fault。没有借环境变量隐藏配置问题。
- 226秒最终健康：三个DSP running，sensor/CAMSS/CCI suspended，VDIG/VANA disabled/users0，MCLK0、MMCX vote0；taint/五类fault0。GPS0/Signalsfalse/rate30，BT关闭无连接，NV及产品程序保持。自动UTC第8次准备成功、chrony Normal，无手动补时/收星。96份本轮原生文件私人快照归档并逐成员核对。

## 源码、产物与回退依据

- 内核/home/cy122/pmos-samurai-kernel136/kernel。211只改IMX471源码、板级DTS、sensor binding三文件，212无kernel源码变更。其余33份已保存改动保持，25 tracked/11 untracked未暂存。配置fbde3690…、16798符号/order772、Image183及旧canonical DTB22c1…保持；旧canonical不能刷作当前树。[211源码核对](reference/kernel211/source-final-validation.json)。
- 私人211保留source-before、原模块/14元数据、190文件原生归档；当前镜像为boot-partition-k211-sensor-domain.img。回退私人210/boot-partition-k210-front.img，哈希89242ade…；正常回退需新身份核对，不使用旧marker。完整kernel/camera APK及新rootfs尚未整合。
- 211旧boot清理的两次MCLK WARN及恢复证据保留，随后新boot独立PM已验证供电域修复。211 GPU ISP又出现CMA不足、全黑帧及IOMMU unmap告警（保存环形日志可见349条/taint512），与MCLK问题不同，仍未修复。212 CPU默认路径干净，不把旧GPU问题改写成通过。
- 207 TFTP回绕已修，原厂MCFG173文件8,807,671B自动RAM复制/mdtime可读，mcfg.tmp仍0B；PDC1平台/25软件活动无pending为207证据，没有选择/激活和NV写入。radio/Mesa打包债保持。

## 续作与已知风险

前摄下一步处理首帧黑、真实增益helper/控制延迟/静态属性和tuning，验曝光色彩方向及拍照应用；GPU路径需单独修CMA预算/黑帧/IOMMU释放。五摄分别验收：前摄完整16MP未完成，后置6400万主摄/1300万长焦/800万超广角/200万人像四路未接入；未知四路PLDO输入、其它模式、冷启/长稳保持开放。不能用非全黑RGB统计证明图像质量。

GNSS真实fix/正CNR仍未解决。用户已确认手机室内窗边，无无遮挡户外验收；209较小UTC误差输入未改善约6秒报告周期，候选未部署。208 ADC变化不能证明RF正常，不重复同一UTC/CNR实验。NTP延迟、GeoClue晚到Signals、原厂初始化/RF/LNA、精度冷启/SSR开放。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。

保留完整目标：蜂窝真实SIM注册/数据/通话/SMS，传感器精度/FastRPC共享池与SSR/SSC首次204退出，BT phase5，Wi-Fi/USB PM，充电闭环及其它外设，radio/Mesa可复现APK和新rootfs均未完成。[全硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
(repo/'NEXT-SESSION.md').write_text(checkpoint)
path=repo/'archive/NEXT-SESSION-through212-2026-10-15.md';assert not path.exists();path.write_text(checkpoint)
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text();start=text.index('用途：');end=text.index('\n\n',start)
text=text[:start]+'用途：当前硬件验收清单。最后核对2026-10-15，阶段212。默认CPU ISP跨启动取6帧RGB，首帧黑/后5帧非全黑；裁剪和独立供电修复保持，最终taint/fault0。完整五摄、图像质量和完整外设goal仍开放。[212报告](../../reference/kernel212/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+text[end:]
text=text.replace('CPU ISP对照没有新增告警，已安装CPU配置，212跨启动验证中。','212默认CPU ISP跨启动取流没有新增告警，最终taint/fault0；GPU路径仍未修复。')
lines=text.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 210静态前摄两轮6帧1928×1088 RAW10；211修复CROP/TRY/ACTIVE及sensor独立TITAN_TOP域，独立PM通过。212默认CPU配置跨启动，普通用户取6帧1920×1088 RGB，首帧黑/后5帧非全黑；结束电源/时钟/休眠与taint/fault0 | 首帧黑、sensor helper/增益/延迟/方向/tuning、图像质量/应用和完整16MP未完成。后置四路未接入；GPU ISP的CMA不足/全黑/IOMMU unmap未修，未知PLDO输入/冷启/长稳开放 |'
path.write_text('\n'.join(lines)+'\n')
path=repo/'linux-port/camera/README.md';text=path.read_text();start=text.index('211新增`configuration.yaml`')
text=text[:start]+'''211新增`configuration.yaml`，安装到`/etc/libcamera/configuration.yaml`，通过libcamera全局配置选择CPU ISP。目录必须0755、文件0644；212首次目录0700导致不可读，修复并保留失败记录。212正常重启后，真实UID10000不设置CPU环境变量，取得6帧1920×1088 RGB888：首帧黑、后5帧非全黑，无DRM/EGL、无新增fault，最终taint0。GPU路径的CMA不足/黑帧/IOMMU unmap仍未修；sensor helper/延迟/tuning及完整拍照质量仍待验收。[212证据](../../reference/kernel212/README.md)、[libcamera官方源码](https://gitlab.freedesktop.org/camera/libcamera/-/blob/v0.7.2/src/libcamera/global_configuration.cpp)。\n''';path.write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='212 closed as verified limited progress: one no-flash warm boot; default system CPU config, directory-mode fix and user6 RGB frames (first black, next5 nonconstant); resources restored, three DSPs running, taint/fault0,96 native files privately archived/member-verified. All historical GPU/MCLK/config failures retained.',guard='/var/lib/samurai/k212-runtime/boot-id-private.txt',transition_pending=False,next='Fix sensor helper/gain/control delays/first black frame and validate actual quality/application; all five cameras and full GNSS/cellular/BT/sensors/power/packaging goal active. User indoors by window; no unchanged UTC/CNR repeats.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('212 current clean boot, limited CPU RGB success, all five cameras and remaining full goal documented. No pending transition.')
