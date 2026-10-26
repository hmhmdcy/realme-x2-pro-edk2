# 211：前摄裁剪、独立供电域与用户态取流

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
