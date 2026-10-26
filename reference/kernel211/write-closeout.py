from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1]
assert json.loads((here/'capture-evidence-archive-validation.json').read_text())['private_archive_all_members_verified']
(here/'README.md').write_text('''# 211：前摄裁剪、独立供电域与用户态取流

已修复并实机验证IMX471的TRY/ACTIVE裁剪接口，以及传感器独立唤醒时缺少TITAN_TOP供电域的问题。boot211只更新这一处设备树属性；Image183保持，安装树只替换IMX471模块。一次boot刷写及启动读回已闭环，三个211切换请求均已结束，不可重放。[新启动](runtime-validation.json)、[源码核对](source-final-validation.json)。

裁剪修复保留原寄存器表，模拟窗口为`(8,408) 4640×2644`，输出仍是1928×1088 RAW10。原CROP赋值后落入EINVAL，现返回成功并初始化TRY/ACTIVE状态，busy检查先于状态修改。两种状态及非法target均实测。[补丁](imx471-selection.patch)、[libcamera接口要求](https://docs.libcamera.org/master/sensor_driver_requirements.html)。

旧启动卸载曾触发两次MCLK stuck-off WARN/taint512：sensor卸载及解绑失败均保留，CCI正常PM保持对照才恢复成功。修复给sensor增加自己的TITAN_TOP引用，绑定允许一个power-domain；925节点语义比较只有这一属性改变，sensor节点schema及负例通过。新启动时CAMSS/CCI仍休眠，单独sensor唤醒得到19.2MHz MCLK及正常VDIG/VANA，随后全部释放且taint/新增fault0，证明修复并非仅靠重启清除告警。[供电域补丁](imx471-clock-domain.patch)、[独立PM](independent-sensor-pm-validation.json)、[旧启动恢复](pre-reboot-recovery-validation.json)。

SYSTEM/CMA heap自动加载及权限已部署，UID10000完成64KiB分配、映射、同步和读回；FastRPC专用池保持root/0600。新启动自动加载及权限复查通过。[配置](../../linux-port/camera/README.md)、[权限验证](heap-access-validation.json)。

普通用户libcamera 0.7.2真实取流仍有缺口：

- 默认GPU ISP在第四个输出缓冲区申请时，reserved CMA返回ENOMEM；普通内存充足。[strace](user-libcamera-trace-validation.json)。
- 临时不给普通用户打开CMA，选中system heap后退出0但三帧全黑；GPU退出路径出现`__arm_lpae_unmap`告警，保存的环形日志中可见349条，taint512。临时权限已finally恢复。**这是失败，不是RGB拍照通过。** [结果](system-heap-capture-validation.json)。
- 显式CPU ISP在原CMA权限下输出三份1920×1088 RGB：首帧黑、后两帧非全黑；无DRM节点打开、无EGL renderer、无新增五类fault。旧GPU告警仍在当前启动，未声称taint0。[CPU对照](cpu-isp-capture-validation.json)。
- 已安装`/etc/libcamera/configuration.yaml`选择CPU，没有覆盖既有配置。IMX471静态属性、sensor helper/增益、控制延迟、方向和tuning仍缺失，亮度/色彩/帧率未验收。[配置部署](cpu-configuration-deployment-validation.json)。

190份原生文件（含私有场景图像及完整失败日志）已一致快照、分块传回、逐成员核对，归档指纹不公开。[归档](capture-evidence-archive-validation.json)。211结束现场是已知GPU告警后的taint512；212正在执行新身份检查、正常停用及无刷写重启，验证CPU默认路径。不能把最初新启动的taint0当作最后状态。212检查还发现printk环形缓冲区淘汰一条旧告警；后续按完整时间戳与已归档行比较，拒绝新增告警，未据计数下降声称修复。

整机五摄：前摄1600万；后置6400万主摄、1300万长焦、800万超广角、200万人像。当前只有前摄单一RAW模式及有限CPU RGB证据，后置四路尚未接入验收。完整分辨率、其它模式、冷启、四路未知PLDO输入及长期稳定性开放。[厂商规格](https://www.realme.com/in/realme-x2-pro/specs)。

boot211 `c3bf043f…`、部署DTB `6f9f5b0f…`、IMX471模块 `a28dd67a…`；私人输出树保留boot210回退。Image183、旧canonical DTB、配置、16798符号及772模块order保持，kernel源码25 tracked/11 untracked、未暂存。完整kernel/camera APK和新rootfs尚未整合。
''')
checkpoint='''# Realme X2 Pro 当前检查点

2026-10-15，阶段211有限修复已验，完整外设goal active。CROP/TRY/ACTIVE和sensor独立TITAN_TOP供电域修复通过；默认GPU ISP仍失败，CPU仅后两帧非全黑、首帧黑。190份原生证据已私人归档核对；最终taint512来自新GPU IOMMU释放告警，不能称完整拍照可用。[211报告](reference/kernel211/README.md)、[210快照](archive/NEXT-SESSION-through210-2026-10-15.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- boot211 c3bf043f…/DTB6f9f5b0f…；Image183 bfa72dd9…/logdump183 e73754c7…保持。IMX471模块a28dd67a…，CCI f9c9272a…、PM8008 d1ff82c0…、CAMSS82cbc052…、BT185保持；完整树772ko/786文件。
- 当前运输reference/kernel211/host.py，当前211启动guard为/var/lib/samurai/k211-runtime/boot-id-private.txt。211三个切换marker均闭环，不可重放。当前GPU诊断后taint512；日志归档可见349条__arm_lpae_unmap，未发生Oops/DSP fatal等五类其它fault，CPU对照未新增告警。
- IMX471/PM8008静态绑定，media0为23实体。前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/200MHz、CSIPHY2。PMIC源码&i2c4为0x890000，运行i2c-1不等于源码&i2c1。210两轮共6帧1928×1088 RAW10已通过。
- 211独立sensor on/auto时，CAMSS/CCI仍休眠，sensor有自己的TITAN_TOP引用；MCLK及VDIG/VANA正常启停、最终全部释放，无新WARN。TRY/ACTIVE四类selection与非法target通过。
- heap自动加载及权限启动复查通过；通用堆root/video0660，FastRPC专用池root0600。默认GPU因CMA不足失败；强制system后全黑并触发GPU unmap WARN。CPU默认配置已安装，显式CPU对照首帧黑/后两帧非全黑；图像和日志均私下保留。

## 源码、产物与回退依据

- 内核/home/cy122/pmos-samurai-kernel136/kernel，211只改IMX471源码、板级DTS、sensor binding三文件；其余33份已保存改动保持，25 tracked/11 untracked未暂存。配置fbde3690…、16798符号/order772、Image183及旧canonical DTB22c1…保持。旧canonical不能刷作当前树。[源码验收](reference/kernel211/source-final-validation.json)。
- 私人211保存source-before、原模块/14元数据及完整190文件原生归档；当前boot-partition-k211-sensor-domain.img。回退私人210/boot-partition-k210-front.img，哈希89242ade…；正常回退需新身份核对，不能复用旧marker。
- 211旧boot清理两次MCLK WARN及恢复证据单独保留；其后新boot独立PM已实测修复。新的GPU unmap告警是不同问题，不能混为已修复。完整相机/kernel APK、新rootfs尚未重建。
- 207 TFTP回绕已修，原厂MCFG173文件8,807,671B自动RAM复制/mdtime可读，mcfg.tmp仍0B；PDC1平台/25软件活动无pending为207证据，没有PDC选择/激活和NV写入。radio/Mesa打包债保持。

## 续作与已知风险

212先进行当前211告警记录核对、正常停用和无刷写重启；验证CPU默认配置在干净启动取流、首帧/预热/增益及资源释放。五摄分别验收：前摄完整16MP/曝光色彩方向未完成，后置主摄/长焦/超广角/人像四路未接入，未知四路PLDO输入与冷启/长稳保持开放。

GNSS真实fix/正CNR仍未解决。用户确认手机室内窗边，无无遮挡户外验收；209较小UTC误差输入未改善约6秒报告周期，候选未部署。208 ADC变化不证明RF正常，不重复同一UTC/CNR实验。NTP延迟、GeoClue晚到Signals、原厂初始化/RF/LNA、精度冷启/SSR开放。[相关机型方案](reference/kernel205/GNSS-RELATED-DEVICES.md)。

完整目标继续：蜂窝真实SIM注册/数据/通话/SMS，传感器精度/FastRPC共享池与SSR/SSC首次204退出，BT phase5，Wi-Fi/USB PM，充电闭环与其它外设，radio/Mesa可复现APK和新rootfs均未完成。[全硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
archive=repo/'archive/NEXT-SESSION-through211-2026-10-15.md';assert not archive.exists();archive.write_text(checkpoint)
current=checkpoint.replace('2026-10-15，阶段211有限修复已验，完整外设goal active。','2026-10-15，阶段212重启验证进行中，完整外设goal active。')
current=current.replace('- 当前运输reference/kernel211/host.py，当前211启动guard为/var/lib/samurai/k211-runtime/boot-id-private.txt。211三个切换marker均闭环，不可重放。当前GPU诊断后taint512；日志归档可见349条__arm_lpae_unmap，未发生Oops/DSP fatal等五类其它fault，CPU对照未新增告警。','- 当前运输reference/kernel212/host.py；212已用211当前身份完成完整停用及60份原生文件归档，发送一次restart2后以新fastboot身份发送一次reboot，没有刷写。正在等待新USB/启动读回，不可重放212的reboot-request-private.json及fastboot-reboot-private.json。旧guard为/var/lib/samurai/k212-before-reboot/boot-id-private.txt；新guard尚未建立。211旧GPU诊断日志已保留，最终taint512。')
(repo/'NEXT-SESSION.md').write_text(current)
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text();start=text.index('用途：');end=text.index('\n\n',start)
text=text[:start]+'用途：当前硬件验收清单。最后核对2026-10-15，211裁剪及独立供电修复通过；CPU ISP仅有限RGB证据，默认GPU ISP有CMA不足/黑帧与IOMMU unmap告警。212正在无刷写重启验证，完整goal active。[211报告](../../reference/kernel211/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+text[end:]
text=text.replace('这个结论限定当前已复现故障和已测负载。','211新增相机GPU ISP退出时的`__arm_lpae_unmap`告警，保存日志可见349条、taint512；它不属于此前CCU像素读回验收。CPU ISP对照没有新增告警，已安装CPU配置，212跨启动验证中。这个结论限定此前已复现故障和已测负载。')
lines=text.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 210静态前摄两轮6帧1928×1088 RAW10；211修复CROP/TRY/ACTIVE及sensor独立TITAN_TOP域，独立PM/资源释放通过。heap自动加载和普通用户访问已验；显式CPU ISP三帧中后两帧非全黑、首帧黑 | 默认GPU ISP的CMA不足、黑帧与IOMMU unmap告警未修，CPU默认配置跨boot验证中；sensor helper/增益/延迟/方向/tuning、完整16MP及后置四路均未验。未知PLDO输入/冷启/长稳开放 |'
    elif line.startswith('| GPU |'):lines[i]='| GPU | 已复现GLES/Vulkan CCU故障已修复，原像素读回与渲染回归保持 | 211相机GPU ISP退出新增IOMMU unmap WARN/taint512，当前采用CPU路径验证；Mesa可复现包/rootfs、完整扩展和长稳仍待完成 |'
path.write_text('\n'.join(lines)+'\n')
path=repo/'linux-port/camera/README.md';text=path.read_text();text+='\n211新增`configuration.yaml`，安装到`/etc/libcamera/configuration.yaml`，通过libcamera官方全局配置选择CPU ISP。默认GPU路径在CMA输出分配时ENOMEM；临时system heap对照产生全黑帧及GPU IOMMU unmap WARN。显式CPU模式仅后两帧非全黑、首帧黑；系统CPU配置已经部署，212重启验证中。它是当前兼容配置，GPU修复、sensor helper/延迟/tuning及完整拍照验收仍待完成。[官方配置机制](https://docs.libcamera.org/master/internal-api/classlibcamera_1_1GlobalConfiguration.html)、[211实测](../../reference/kernel211/README.md)。\n';path.write_text(text)
print('211 evidence, source closure, five-camera scope and212 in-flight state documented. Full peripheral goal remains active.')
