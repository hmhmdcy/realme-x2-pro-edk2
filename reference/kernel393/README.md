# 393：隔离 IPE 提交前错误，正式更新核心／适配层

已修复[392](../kernel392/README.md)发现的局部输入错误连带中断peer问题。SoC核心显式报告可安全局部拒绝的结果，adapter只让坏队列报错；另一上下文可连续工作，坏文件保持打开并可单独STREAMOFF修复，全程无需重启后端。两个匹配模块已正式安装，四摄默认r30 GStreamer另48帧和并发取消通过。完整多摄／ISP校准目标仍active。

## 分层和安全边界

沿用既有仓库／方案调查及原厂ELF/HAL的MAP/FRAME/UNMAP协议证据；本轮没有改HFI协议、IQ表、FW、传感器、板级DT或用户空间。[上游m2m](https://docs.kernel.org/driver-api/media/v4l2-mem2mem.html)与[DMA-BUF生命周期](https://docs.kernel.org/driver-api/dma-buf.html)作为标准框架依据，实际错误边界由既有核心状态和本轮代码／实测证明。

[补丁](local-job-errors.patch)只改三个源文件：camss-icp-a5-boot.c、camss-icp-a5-ipe.h、camss-icp-a5-m2m.c。新增camss_a5_ipe_run_status，返回独立结果分类，保留原camss_a5_ipe_run符号及旧调用方式。

- RESET_REQUIRED为默认。失效session、未启IRQ、协议错误、未回收临时 backing，以及任何已尝试作业transfer MAP之后的负返回，仍进入原全局停机路径。
- REJECTED只在配置／引擎状态可信、尚未尝试本作业transfer MAP、释放清理成功且作业临时映射／DMA-BUF引用全归还时产生；不按EINVAL或ETIMEDOUT等errno猜测安全性。
- adapter仅对显式REJECTED跳过全局fatal／停机，原队列仍获得ERROR/EIO并需STREAMOFF修复；未知MAP/FRAME/UNMAP、resetACK、缓冲保留及共同owner机制未放松。

“提交前”指图像作业transfer MAP之前；建立／配置session本身仍正常使用固件命令，不表示从未通信。精确DMA-pending瞬间和真实硬件故障并发没有因本轮而变成已验证。

维护源source354 branch samurai-ipe-errors393，commit 64aaf4f78c05f0912e658780294fbded531d87ce，干净。[源状态](source-state.json)区分Image363、原CAMSS复合模块389与本轮核心／adapter393。源码/build仍先284/storage.py::mounted_build，不重建32GiB backing。

## 构建和模型验证

[核心18例](transfer-validation.json)运行实际核心传输／释放及DMA导入函数，覆盖同EINVAL在提交前与提交后的不同分类、提交前fence等待超时、IRQ未启、协议错误、释放失败以及未知MAP/FRAME/UNMAP引用保留。[适配层10例](adapter-validation.json)运行实际device_work，核对局部／全局错误、启动失败、前后取消、DMA-BUF put和job_finish。均通过ASan/UBSan；提供者模拟固件／MMIO，不冒充硬件故障并发。

[ARM64构建](intree-build-validation.json)W=1/-Werror通过，诊断0。首次仅指定两个目标导致modpost缺标准媒体符号；补入所需标准依赖目标后通过。标准SG和m2m helper与已装版本摘要完全相同，只部署变动的两个模块。模型提供者曾因变量名与puts冲突编译失败，改名后通过；没有因此改核心行为。

|正式替换模块|字节|SHA256|
|---|---:|---|
|qcom-camss-icp-a5-core|352776|e22253916088e58a221c1948f025c44c939c819310c7d3f67106053dd39502f6|
|camss-icp-a5-m2m|119368|ff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1|

新旧核心／adapter必须成对使用。原qcom-camss复合模块、SG/helper、Image363、boot389/logdump365、DT389、原厂FW及r30/r25包保持；无重启／刷写。正式根文件系统只替换两文件，depmod后按正常模块依赖加载。

## 实机与失败审计

[r4完整成功窗口](runtime-r4-validation.json)、[汇总](hardware-validation.json)：

|场景|实测|
|---|---|
|同一导出DMA-BUF作输入／输出|局部-EINVAL，failed只增加1，fatal=false；peer没有-EIO|
|坏文件仍打开|peer连续两帧不同模式与时间戳／有效Y正确|
|只修坏队列|STREAMOFF后原fd换成不重叠DMA-BUF重新出帧；peer session持续存活，starts1/stops0|
|并发取消回归|CONFIG_IO后发取消，cancelled1，peer及原fd重启帧正确|
|默认四摄640×480 NV12|imx471/imx319/s5k3m5/s5kgw1各12，IPE共48，bus错误0，无私有库／配置覆盖|

完整窗口55作业=53completed/direct＋1cancelled＋1预期局部失败，硬件完成日志54（含上层取消的一帧）。first_error=-22保留作累计诊断。最后FW单session12帧/43消息/44IRQ、INIT/PC完成、watchdog/protocol0。

[失败审计](attempts-validation.json)保留三个未通过窗口，未改写为成功：

1. r1卸载原模块后，脚本错误要求静态平台设备节点消失，清理又对未绑定设备等待runtime suspend。旧文件尚未替换；实际三个模块均已卸载、设备节点无driver。通过[独立恢复](r1-recovery-validation.json)加载原平台及桌面，probe未启动FW。
2. r2探测后要求owner_refs立即为0，遇到临时引用而失败，自动恢复原两文件／旧模块和服务。r3明确记录初始owner_refs1，复用有界等待后归0，未把它冒充泄漏或放宽卸载所有权要求。
3. r3已实测局部拒绝和peer两帧，随后客户端复用旧offset16辅助，却未像原386一样额外分配行，QBUF按长度检查返回EINVAL；整体失败并自动回退。修正客户端使用offset0后r4完整通过，核心源／模块在这些尝试间未变化。

r3两帧仅作为失败窗口的部分证据，未算进r4的53正常完成；本轮全部尝试硬件完成日志共56。392旧累计132在首次正常卸载前已保存，不能与r4新模块计数55相加后冒充同一counter epoch。r2/r3自动回退已实测，r4保持新版，未通过清零计数掩盖仍在活动的故障。

[最终状态](current-state-validation.json)：新两模块磁盘摘要与加载note相符，原两模块备份相符，CAMSS复合模块note未变，四份私有配置与七包版本保持。CPU/IRQ/PM/backing、映射与导入引用回收，四相机设备suspended、17相关时钟0、九路电源disabled/users0。PW12387/WP12390各一、uid10000；m2m users0/fatalfalse，owner_refs53为正常桌面CAMSS句柄。所有四窗口worker/client/collector终态，未捕获dump、未超时、新fault0、taint0。

## 接续和回退

旧核心／adapter精确备份在设备/var/lib/samurai/k393-deployment-r4/backup，旧原件仍在private389；manifest.json记录两文件新旧摘要／加载note。回退须先停止相机消费者、确认DMA回收及owner0，再卸载正常CAMSS、adapter、core，成对恢复原文件、depmod并modprobe正常CAMSS后恢复服务。r2/r3这条回退路径已执行成功，不能重跑已有部署worker。用户空间r29/r24回退仍391，整个平台回退仍390/boot366；本轮不动那些备份。

下一步补真实硬件错误／未知完成的并发恢复证据，并推进原厂Gamma/LTM/CCM完整IQ及[363全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)：第五2MP、多模式、动态帧长／防频闪、几何／多摄同步、连续AF和光学画质。仍1:1 NV12/NV21 IQ旁路，异步implicit-fence发布和完整校准未证明。低照度黑噪点按用户关灯条件解释。

同一390启动，host393→392→391→390及guard=/var/lib/samurai/k390-active/boot-id-private.txt，旧378guard不可用。FW/HAL/ASM/CDM/全日志/图像/个体配置只private393及前序；公共镜像仅本地提交、不push/PR。完整目标active。
