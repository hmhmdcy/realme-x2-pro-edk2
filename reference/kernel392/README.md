# 392：在途取消、双上下文与输入错误恢复实机验证

在正式390内核／板级平台和391签名r30/r25用户空间上，实测四种取消场景：输出队列先停、捕获队列先停、直接关闭活动文件、另一个上下文排队时取消。四次均进入真实取消计数；同文件重启和另一个上下文的有效Y像素保持。重叠DMA-BUF被拒绝、排队上下文报错、全部关闭后重新打开恢复也通过。随后默认r30 GStreamer广角完成12帧。完整目标仍active，真实硬件错误并发及完整IPE IQ未完成。

## 依据与改动范围

沿用既有仓库调查、原厂ELF/HAL反编译和[391正式部署](../kernel391/README.md)，只新增实际V4L2客户端、运行辅助和证据，没有内核／DT／模块／FW／软件包／个体配置改动，无重启、刷写或模块重载。维护驱动源仍a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07，干净；用户空间r30/r25保持。现有硬件模块和算法测试复用，不重复构建。

[上游m2m文档](https://docs.kernel.org/driver-api/media/v4l2-mem2mem.html)要求驱动安全终止活动事务后归还调度器。实际adapter通过job_abort置aborting，工作线程完成有界核心调用后标记取消，STREAMOFF/close等待调度器及work结束。没有取消工作队列而丢失job_finish，也没有在DMA可能活动时直接释放缓冲。

客户端复用386实际V4L2分配、格式、模式和出队辅助。先从/dev/kmsg新尾部等待本次CONFIG_IO确认，再发取消；四次均有硬件帧完成日志且上层作业记cancelled，表明已配置硬件工作中的取消、等待和回收确实执行。该日志标记不是DMA-pending采样，不能证明在某个精确DMA指令周期发出abort，也没有测试未知完成／硬件超时／IRQ错误恢复。

## 实机及失败保留

[r1](runtime-r1-validation.json)前3场景通过。第4场景首次在CONFIG_IO后才填充并计算另一帧CRC，耗时约10毫秒，活动作业已正常完成，故cancelled未增加，客户端断言退出。三个已完成正常帧仍计入真实总数，但该并发取消用例未算通过；资源释放、collector结束和服务恢复正常，没有内核故障。

[r2](runtime-r2-validation.json)把另一帧准备移至启动前，只补第4取消与输入错误恢复，前3成功用例未重跑。并发取消时另一上下文完成正确Y像素，原文件随后可重启。两种队列顺序和直接close的证据来自r1，来源分开保留。

输入错误使用同一个真实导出DMA-BUF作为输入和输出，经过正常DMABUF导入、session配置及核心物理别名检查，DMA提交前返回-EINVAL。adapter当前把所有核心负返回视为全设备错误，停后端并置fatal，另一排队上下文得到-EIO；两个队列通过ERROR缓冲或EIO通知，没有静默成功。全部消费者关闭后fatal清除，新上下文的Y像素与模式相符。此处是输入校验错误，不是人为损坏原厂固件、IOMMU硬件错误或未知DMA完成的替代证据。

[r3](runtime-r3-validation.json)仅补正式默认应用恢复：无私有库／配置覆盖的r30 GStreamer广角640×480 NV12完成12帧，bus错误0、IPE增加12、fixture恢复。累计failed仍2、first_error仍-22是历史诊断，未清零或卸载模块掩盖；当前fatal/running均false。

|本轮计量|结果|
|---|---|
|V4L2作业增量|26 = 20 completed + 4 cancelled + 2预期失败|
|硬件帧完成日志|24 = 20正常完成 + 4上层取消；别名／受影响peer未提交图像帧|
|合并五组场景|r1前三＋r2后两，均有实际成功证据|
|正常结果像素|7个合成正常输出核对有效Y；第4用例r1首次正常完成的原活动帧未做像素验收|
|默认应用回归|r3另12帧真实广角，不以关灯黑噪点判失败|

[汇总](hardware-validation.json)包含r1时序失败窗口的真实工作量，不重复累计用例；旧391末jobs106/completed106，本轮末jobs132/completed126/direct126/cancel4/failed2，starts/stops20。first_error=-22累计保留。最后FW单会话12帧/43消息/43IRQ、INIT/PC完成，watchdog/protocol0。

三窗口collector、worker、client均终态，无新dump、无超时、新内核fault0、taint0。[最终状态](current-state-validation.json)：CPU/IRQ/PM/backing、map/import均释放，ICP/CAMSS/双CCI suspended，17相关时钟0、九路相机电源disabled/users0。PW10271/WP10274各一，uid10000。owner_refs53来自普通桌面CAMSS句柄，m2m users0；客户端close后短暂owner_refs2属于延迟DMA-BUF fput，外层等待最终归0再恢复桌面。

## 下一步

本轮暴露的优化点是**已知未提交图像DMA的输入错误仍影响其它上下文**。后续优先在SoC核心给出明确的安全拒绝／已提交／未知完成边界，让adapter只隔离可证明局部的作业；不能仅凭errno猜测，也不能放松未知MAP/FRAME/UNMAP后的DMA保留和resetACK要求。真实硬件错误并发仍独立保留，不把本轮输入错误测试写成完成。

继续原厂Gamma/LTM/CCM完整IQ及[全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)：第五2MP身份/mux、多模式、动态帧长／防频闪、几何／多摄同步、连续AF和光学画质。仍是1:1 NV12/NV21 IQ旁路，异步implicit-fence发布未证明。照明相关校准等合适光照，底层和离线工作继续。

同一390启动，host392→host391→host390，guard=/var/lib/samurai/k390-active/boot-id-private.txt；旧378guard不可用。回退仍391签名r29/r24七包和390原两模块／boot366，未执行新的回退。原FW/HAL/汇编/CDM/全日志/图像/个体配置只private392及前序；公共镜像仅本地提交、不push/PR。
