# 362：隔离 IPA 的提交所有权与公共请求顺序

当前已部署r29/config-r24、348 Gamma模块和360完整私有Preview默认。安装后四摄五模式共137帧隔离请求通过，GStreamer/PipeWire各12帧通过；四硬件相机/四桌面节点、taint0、资源全部休眠。[安装结果](install-r1-validation.json)、[最终设备](final-state-validation.json)。离线r27/r22及原338模块/344配置回退位于手机`/var/lib/samurai/k362-install-r1`。以下先描述开发验证过程。

2026-10-20。沿用361已定位的失败，修复 CAMSS 控制队列及公共 PipelineHandler 的同步 IPC 重入。目标继续进行；当前通过的是本轮明确列出的模式与请求链，不能等同完整 ISP 和绝对光学校准。

CAMSS `submitStatistics()` 原来持有 deque 首项引用，跨越同步 `applyIspControls()`；内层事件再次消费同一项。现由外层串行提交，调用前移出首项，EAGAIN按原顺序退回，epoch改变或停流后不提交旧返回值。保护覆盖参数准备与统计提交，没有删除断言或禁用隔离。[补丁](camss-submit-reentrancy.patch)。

第一次实机 r1 越过旧空队列崩溃，但请求7先于请求6进入硬件，回交时图像时间戳逆序，8帧后失败。同步 `convertControls()` 可递归进入公共 `doQueueRequests()`；原实现虽然先弹出请求，却未保证前一次 `queueRequestDevice()` 完成后才提交下一次。公共修复按camera约束同线程重入，由外层继续排空；其它camera仍可推进，类布局未改。[补丁](pipeline-request-order.patch)。r1失败与设备恢复记录保留，未改称成功。

直接编译生产函数体、注入递归IPC的主机ASan/UBSan回归中，旧版三种控制队列场景及公共请求顺序均复现失败。新版8种控制/统计/停止/重启/重试场景，以及公共同摄顺序、其它camera推进、准备/容量恢复检查通过。[控制回归](submit-regression-validation.json)、[公共顺序回归](ordering-regression-validation.json)。提供者为桩，另有真实ARM64核心构建和设备验证。

修复后 r2：隔离GW1模式2、线程IMX319 Preview及正常广角实景，共84帧、15段请求通过。r3：隔离IMX471、S5K3M5、IMX319和GW1模式4，共111帧、20段请求通过。合计五物理模式隔离138帧，加线程/实景57帧；每组五段EV/手动频闪/WB控制，Gamma仅启动上传一次，真实AE更新存在。通过实际库映射与应用/IPA不同PID核实隔离；没有用线程执行冒充IPC。[运行结果](runtime-validation.json)。

每次临时实验已恢复原CAMSS338、r27/r22及桌面服务；无新增相关内核故障，taint0，双CCI/CAMSS休眠，九路电源disabled/users0。真实场景只测取流、亮度与请求元数据，没有做绝对色彩/遮光/畸变标定，也没有验证消除光源频闪。五模式未覆盖全部高分辨率或用途组合。

候选源码 `/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2`，包含361公共分发器修复。完整r29/config-r24配方由360 r28/r23递增，0039组合补丁在基线上零fuzz应用后与三个实际源文件一致。原厂曝光/Gamma及其它算法原样复用；公共配置未加入私有原厂或个体表。[配方检查](package-source-validation.json)。软件包构建/签名及后续安装状态以各结果文件和当前检查点为准。

分层：本轮是通用libcamera框架与CAMSS pipeline生命周期修正，没有改SoC MMIO、板级DT或传感器模式。原厂HAL/EEPROM提供的调校继续作为IPA数据；VFE175后端继续通过标准参数节点执行。ICP/A5/IPE仍缺完整固件握手和图像会话，不能将VFE采集成功记为整个Spectra完成。

复查了[主线CAMSS文档](https://docs.kernel.org/admin-guide/media/qcom_camss.html)及公开仓库搜索；该文档的详细硬件说明明确限定旧平台，不能套为SM8150的完整能力声明。没有找到可直接回移的本次队列修复。沿用[352固定上游原型与原厂固件来源](../kernel352/README.md)，不重复下载已保留固件。完整目标仍有ICP/HFI/IPE、后级Gamma/LTM/CCM、动态帧长、自动频率检测、更多模式、光学/几何、多摄同步及连续AF。
