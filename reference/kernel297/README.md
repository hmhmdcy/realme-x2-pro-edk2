# 297：图像／统计共享 SOF 帧号与断粮恢复

2026-10-19。现机 **#297 / 7.3.0-rc6-rmx1931-samurai-k297+**，维护树干净分支 `samurai-sof297`、提交 `ab709d9670f6dcaa71858fd4f3e189522f669913`。完整 Image、独立778模块及加载 build-id 已核对，boot276、DTB、原厂固件与961包／50相机载荷保持。目标继续推进；本轮落实帧关联修复并固定BLS资料，黑电平、偏色和硬件pipeline／IPA尚未完成。

## 真实缺陷与分层修复

#296 的 PIX 图像／统计分别按完成次数编号，只有图像 output[0] 获得 CAMIF SOF 标签；统计晚启动复制图像完成计数。旧记录首个晚启动统计包报18，与图像19完成仅相隔28微秒。完成时间接近不是同帧证明，但源码明确允许两路计数错位和断粮后压缩帧号。[基线与原始位置](baseline-validation.json)

本轮仅修改两个内核驱动文件，40增／18删，一个本地提交：

- SM8150 CAMIF SOF回调把同一输入帧号标记到所有正在运行的捕获输出，跳过无写主设备的参数节点；已有标签不被下一次SOF覆盖。
- PIX完成路径保留SOF标签，缺少标签的buffer以ERROR返回；其它版本保留原计数行为。
- 参数回执使用下一次输入SOF序号，避免SOF与上一帧DONE同次处理时报告已经开始的帧。
- 延用既有VB2队列、帧同步事件和typed参数／统计格式；未增加板级分支、DT属性、固件、UAPI或产品包补丁。

[候选补丁](sof-candidate.patch)、[源码收据](source-validation.json)。本地提交与模块 `intree=Y` 不代表上游接受。

## 实机验证

| 检查 | 实际结果 |
| --- | --- |
| SOF、图像和统计 | 长焦 S5K3M5 GRBG10 2104×1560 图案2，真实CSI→VFE175 FULL 320×240。126图像、111有效统计、128标准SOF事件；全部图像／有效统计找到对应SOF，110组可按共同帧号配对，无重复身份或早于SOF的完成。[定量分析](sof-association-validation.json) |
| 晚启动和断粮 | 图像重开、统计停流期间改4×2 ROI后晚启动，首包为SOF19、人口2；旧人为计数为18。耗尽三个统计buffer后图像继续，恢复排队后序号保留7帧间隔，未压缩为连续完成计数。未出现统计ERROR包。[R2原生结果](stats-r2-capture-validation.json) |
| 参数对应 | 五次可辨识ROI人口变化，首个生效统计包与参数回执10／28／37／46／55完全一致。六次可观察WB变化，包括图像重开后的绿色增益变化，首个生效图像与参数回执一致。[ROI](sof-association-validation.json)、[颜色变化](frame-association-validation.json) |
| WB像素 | 11阶段对照291独立RDI RAW参考，最大通道误差<1.235；10非法参数拒绝，8参数完成。[颜色测量](stats-pixel-validation.json) |
| 广角实景 | IMX319 RGGB10 1632×1224，传感器与CSID图案关闭，18图像／18统计均有效、人口499392。曝光500→3000→500：Y75.6113→95.6392→75.6110；统计均值bin73.0162→120.0075→73.0164。[图像](optical-pixel-validation.json)、[统计](optical-statistics-validation.json) |
| 实景复查 | 已实际查看私人预览，结构可辨、仍暗绿；黑电平／AWB／完整IQ没有校准，不能称画质修复。[复查](optical-review.json) |
| 产品四摄 | 原有libcamera RAW＋CPU ISP 18段232帧通过，主摄SIGINT28帧后重开12帧正常。[回归](four-camera-regression-validation.json) |

成功探针合计144硬件图像／129有效统计；不包含首轮失败探针。首轮实际取得1图像／1统计后，事件队列为空返回ENOENT，探针只接受EAGAIN而退出。失败记录保留，图与资源已恢复、fault0；独立R2工具修正空队列处理并通过实际drain函数ASan／UBSan，未再次刷写。[R1失败](stats-capture-validation.json)、[工具修复](event-drain-validation.json)、[过程记录](preparation-notes.json)

主机实际SOF／排队／完成函数：旧函数负对照失败，新函数ASan／UBSan通过正常／晚启动、相邻SOF先于DONE、统计断粮恢复、缺标签ERROR、参数未来帧、其它版本保护、u32回绕及1000轮重排队。[负对照](sof-parent-host-validation.json)、[修后](sof-fixed-host-validation.json)

验证限于上述传感器／模式和一次实际启动。多次未观测SOF合并、严重IRQ延迟、其它模式与长稳、多个参数排队／Request API和硬件IPA仍未验收。广角没有订阅本轮帧事件，不把图像／统计编号相同扩大为独立SOF证明。`ready_for_automatic_exposure=false` 保留。统计与图像完成时刻相差可达−32100至102微秒，不能用最近完成时刻替代帧身份。

## 原厂 BLS 资料与下一步

GitHub代码搜索找到固定版本Titan17x BLS12硬件设置与IQ计算资料，四文件固定提交 `36fc163a534963a5b3af52186af5efcc63401ad2`，完整参考仅私人保存。与296固定生成头交叉核对：BLS配置0x6b0、两个阈值寄存器0x6b4／0x6b8、lens enable bit11、offset14位、scale寄存器17位且小数位Q11、GR／GB／R／B阈值。[来源与哈希、仅协议事实](blc-protocol-validation.json)

这些资料提供硬件协议，不能提供本机模组的黑电平、增益／温度依赖、AWB／色彩矩阵和阴影校准。未套用其它手机调校、未把单场景曝光截距当标定，也未复制或执行厂商实现。本轮没有BLS内核实现和本机黑电平校准，不声称已消除暗绿。

下一步按对应位深与sensor模式落实黑电平参数及校准／色彩验证，SoC驱动负责寄存器与队列，板级DT只描述连接，算法与模组数据进入匹配IPA；随后接入libcamera硬件pipeline／IPA。主／前摄硬件路径、AF Continuous／距离映射、Shine OV02A1B、GUI录像及长稳继续开放。

## 构建、部署、资源与更新边界

完整构建138.08秒、五阶段诊断0、40个CAMSS组件严格编译通过，778模块vermagic／depmod与3嵌入BT模块一致。296六个产物已核对保存在私人kernel297/completed-boot296。配置仅LOCALVERSION／INITRAMFS_SOURCE改变。[构建](boot-candidate-build-validation.json)、[封装](boot-package-validation.json)

一次受控296→297切换，仅刷logdump，boot276与DTB保持；新启动镜像分区读回与778模块一致，pstore空。早期默认服务尚未启动时快照保留，后来SSC／桌面／SensorProxy默认成功，未重试或nodeps。[启动读回](postboot-identity-validation.json)、[服务就绪](startup-readiness-validation.json)

最终camera／lens／CCI／CAMSS均suspended，九rails及共享IO关闭，MCLK／CCI时钟0，fault0／taint0／pstore空，无CCI错误；Wi-Fi／HCI及modem／adsp／slpi正常。Phoc3673／Phosh3899／PW5303／WP5316。`checked_runtime_healthy=true`只覆盖所列检查，旧SSC偶发EPERM根因、GPU默认路径故障、旧modem watchdog和整机长稳未结案，`whole_system_healthy=false`。[最终检查](final-health-validation.json)

Image SHA `ec3e50b7d7a0c086b6a0dc40013046785d7ccad6ff990eca35b95b056043f7a9`；logdump `e6cf910b3a3499232eecccc9d47524c19b949bb59ffc619174f44a78813f44ec`；config `82c5ab39f5749693c8e94b7bec7266a9d02a255212af86093e40dfe2e9a101da`。稳定回退仍首选290镜像与独立778模块，296及此前模块树保留，未做回退往返。

当前相对7.3rc6基础为54本地提交／177改动文件；libcamera配方28补丁含发行版既有，PipeWire6项目补丁，三个ignore_unused仍存在，尚无跨新内核／完整rootfs验收与上游接受证明。[分层审计](layering-validation.json)

维护树 `/home/cy122/x2pro-linux/camera279-isp-kernel`。构建输出 `/mnt/samurai-full282/build`，先由284/storage.py核backing并挂载；input-initramfs297／modules297。当前运输本目录host.py及 `/var/lib/samurai/k297-work/boot-id-private.txt`；本次main6-0010／lens6-0072、tele8-002d、wide7-0010、front9-0010，后续仍按实体发现。所有构建／切换／采集已终态，勿盲目重放；私人像素、参考载荷、校准和密钥不公开。
