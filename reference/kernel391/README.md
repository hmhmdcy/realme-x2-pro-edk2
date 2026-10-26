# 391：正式安装 IPE 用户空间，默认四摄与 PipeWire 通过

五个 libcamera 运行包已升级至 99990.7.2-r30，config/stack 至 0.1.0-r25。IPE 管线从387私有候选进入正常已签名软件包，默认应用不再需要私有库路径。四摄、RAW与隔离IPA完成82个IPE作业，普通用户PipeWire另12帧，本轮共94个direct作业，failed/cancel均0。完整多摄／ISP校准目标继续active。

## 改动与分层

沿用既有仓库／方案调查、原厂固件/HAL反编译及[390正式内核／板级平台](../kernel390/README.md)。本轮只落实用户空间包；SoC核心、板级DT、内核、五模块和原厂固件均未变，无重启、刷写或模块重载。原厂四份个体Preview配置摘要保持，未打入公共包。IPE目前为1:1 NV12/NV21、IQ旁路，不能据此宣布完整Gamma/LTM/CCM或光学校准完成。

[源核对](package-source-validation.json)证明0040补丁零fuzz复现已验证387的四个管线文件；IPA算法、接口及事件分发器未变。维护源为/mnt/samurai-full282/libcamera391-ipe-r30-built/src/libcamera-v0.7.2。访问现有ext4构建卷仍先调用284/storage.py::mounted_build，不能重建backing。

[构建](package-build-validation.json)生成13包，保留原有GStreamer、v4l2、tools、Python、qcam、dev及其他IPA功能；实装7包。[签名与产物](package-artifact-validation.json)验证所有APK、正向与回退仓库签名；六个IPA签名由新包内核心实际验证，六个IPA二进制与r29逐字节相同，故复用362算法测试。新核心SHA256 b948765ea94423d628a1d455a7de8f737a84b45b3bee969a949b6886a4dee6b8。构建前一条错误的空目录断言曾在绑定或编译前退出；删除断言后保留SDK底层原工作目录，构建正常完成、绑定已卸载。

## 实机与失败审计

[r1](install-r1-validation.json)实际安装新包并完成全部七组管线测试，随后脚本把libcamera映射归于PipeWire服务器而断言失败，自动离线恢复r29/r24及原仓库／world。真实加载相机SPA和核心的是WirePlumber，已通过实际进程映射确认；此失败没有导致内核／板级变更。

[r2](install-r2-validation.json)只修正进程映射检查，再安装完全相同产物。核对既有r1测试摘要后复用已成功的82作业，不重跑或重复累计。补齐普通用户PipeWire路径，实际WirePlumber映射为已安装新核心，四个节点可枚举，imx319完成12帧且IPE计数增加12。最终仓库指向r2本地签名索引。

|实测路径|结果|
|---|---|
|默认GStreamer四摄|imx471/imx319/s5k3m5/s5kgw1各12帧NV12，IPE各12|
|主摄RAW＋NV12|6请求／6对RAW，原始IFE时间戳及SOF保留|
|RAW-only|6请求，IPE新增0|
|强制隔离IPA主摄|28帧、5控制阶段、Gamma ACK1、统计进程隔离|
|普通用户PipeWire|四节点、12输出帧／12IPE、errors0，核心由WirePlumber加载|

[实机汇总](hardware-validation.json)总94个新增direct作业；390重载后原有12，本轮末累计106，不把旧12再次计入。最后FW单session create/destroy/peak1，12帧，43消息／43中断，INIT/PC完成，watchdog/protocol0。Gamma ACK属于既有IFE IPA控制证据，非完整IPE IQ。

两窗口collector均终态，无新dump、无超时；worker/client均终态。[最终状态](current-state-validation.json)：五包r30、配置栈r25，八项部署文件摘要与加载CAMSS note相符；个体配置未变，taint0、新fault0。CPU/IRQ/PM/backing、映射和导入引用释放，四个相机设备suspended、17相关时钟0、九路电源disabled/users0；PW/WP各一，uid10000。owner_refs53是正常桌面CAMSS句柄，m2m users0，并非缓冲数量。

## 回退与接续

设备/var/lib/samurai/k391-install-r2/repository/rollback保存签名r29/r24七包，backup有原world及相机仓库配置；r1回退已实际通过，r2回退未执行。用户空间回退先停相机消费者并回收DMA，用rollback.list离线安装七个精确旧版本，再恢复world／仓库与服务。它不涉及内核回退。内核回退仍见390：原两模块、原缺失三模块和FW记录及boot366保持。

同一390启动，继续host391→host390及/var/lib/samurai/k390-active/boot-id-private.txt；旧378guard不可用。驱动维护源仍a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07，Image363／boot389／logdump365保持。源锁区分实际Image与后续模块，未声称完整Image重新构建。

下一步补显式在途取消／硬件错误并发，再推进原厂Gamma/LTM/CCM完整IQ；保留[363全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)的第五2MP、更多模式、动态帧长／防频闪、几何／多摄同步、连续AF和光学校准。当前关灯黑场／噪点不单独判链路故障，依赖照明的验证后做。FW/HAL/反汇编/CDM/完整日志/图像/个体配置只private；公共镜像仅本地提交，无push/PR。
