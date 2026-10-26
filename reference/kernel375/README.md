# 375：原厂A5固件完整HFI生命周期实机通过

**SYS_INIT、SYS_PING、SYS_PC_PREP、WFI、DMA退映射、电源释放和模块卸载首次完整通过，手机保持原启动，新增相关故障0、taint0。** 维护提交`94a92da1da7d6e5418e284b4a0c858100fa74fd9`，父374 `8bbd1f3d...`。这是原厂固件传输与生命周期通过；尚未创建IPE图像会话或输出处理图像。[实机结果](boot-runtime-r1-validation.json)、[有序日志核对](lifecycle-runtime-validation.json)。

## 修改与依据

374已证明普通platform绑定完成后仍能复现停机重启，三项固件应答俱全，最后日志位于全局块复位之后、DMA退映射之前。对照已保存的Realme GPL原厂`cam_hfi_disable_cpu`及资源停机路径，正常停机没有额外CAMCC ICP_BCR。此轮仅修改SoC A5核心：PC_PREP成功、WFI确认且CONTROL使能/唤醒位清除后，沿原厂本地CSR停机流程退映射并释放时钟/电源；正常runtime_suspend也不再断言全局ICP/AHB复位。失败或未初始化的固件仍使用强制块复位；复位失败保留CPU、内存与PM所有权。IRQ已停的失败重试不再发送依赖IRQ的PC命令。[补丁](cooperative-stop.patch)。

一次实际针对性实验确认这项修改使正常停机完整返回，不能进一步宣称已测得先前具体的总线错误、看门狗来源或复位内部机制。没有以放宽固件响应校验、忽略错误或提前释放运行中DMA来取得通过。

板级DT/保留内存、主线OF/IOMMU与设备链接框架、传感器驱动、libcamera/IPA及个体校准均未修改。保留373的reset→wake→HFI参数写入/读回→INIT_REQUEST启动修正。临时owner、overlay和固件与374相同，test模块SHA也完全相同；候选未永久安装。[源码](source-state.json)、[构建](intree-build-validation.json)。

## 验证与当前设备

实际生产quiesce/stop/runtime_suspend函数体的13条模型路径通过ASAN/UBSAN，包含PC/WFI/CONTROL失败强制复位、复位失败重试、退映射失败保留PM、释放顺序及幂等性；旧代码正常停机反例被拒绝。MMIO、DMA、IRQ、reset与PM提供者是桩，不替代实机结果。worker分发和清理模型通过；实际k363两模块in-tree W=1/-Werror构建无诊断。[模型](stop-validation.json)。

实机就绪响应1约5.270ms、firmware 0x01000100；3条消息、4次IRQ、debug包1，watchdog/protocol错误0。三个队列读写索引均收敛；CPU/IRQ关闭，固件/共享/堆映射归零，时钟组与电源域引用归零。模块正常退出、overlay remove返回0、17个ICP/BPS/IPE时钟恢复0、CAMSS休眠、临时固件删除，worker/collector均结束。无主机复位、无刷写、无NV/OTP/校准写入。

随后四颗传感器各12帧GStreamer采集及主摄独立IPA进程27帧/5阶段/Gamma ACK通过；既有模块、r29/r24及362私有Preview默认保持。桌面/音频/SSC和adsp/slpi/modem正常，CAMSS/双CCI休眠、9相机电源disabled/users0。[采集](camera-runtime-validation.json)、[终态](final-state-validation.json)。

**当前guard仍为k374-recovered，使用host375会沿用它；375没有重启，也没有k375-recovered启动。** Image363、boot366/DT365保持。完整原厂ELF、事务副本、日志和校准仅私存。旧373/374失败终态原样保留，不用本轮成功改写历史。

## 后续范围

下一步从已保存原厂HFI session ABI、ICP管理器和可复用上游原型入手，实现严格应答匹配的IPE会话创建/销毁，再接IO/IQ、帧完成与libcamera m2m，将已提取的Gamma/LTM/CCM映射到真实后级处理。不能用“固件启动通过”代表完整Spectra图像管线。

第五颗2MP身份、共享前摄PHY/MCLK/reset选择、更多模式、动态帧时长/自动防频闪、光学/几何/同步及连续AF仍在[剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。整体目标继续active。
