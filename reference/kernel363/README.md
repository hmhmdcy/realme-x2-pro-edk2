# 363：统一内核已部署、四颗传感器回归和原厂 HFI 入口核对

独立k363已完成构建、刷写、启动和相机验证。固定提交`ba61a62293e0f6bc5838c06f2e85e033e3d702a8`包含348 Gamma和357公共OF/IOMMU节点生命周期修正，778模块同release、depmod无未解析符号；实验ICP模块默认不启用。没有在相机驱动里补偿框架引用计数。用户空间保持362的r29/r24和私有完整Preview默认。

原initramfs293保留，新initramfs363只替换三个匹配release的蓝牙模块，实际Image内CPIO字节已核对。42个CAMSS组件W=1/-Werror无诊断；全内核另有62条既有W=1诊断，不能称全树零警告。构建中一次有意从3并行改为8并行的终止和续作均保留。[完整构建](boot-candidate-build-validation.json)、[封装](boot-package-validation.json)、[实际启动](postboot-validation.json)。

运行时已验证IMX471、IMX319、S5K3M5、S5KGW1各12帧GStreamer硬件采集，主摄隔离IPA另27帧／5控制阶段和Gamma回执；无新相关故障，九路电源关闭，CAMSS/双CCI休眠，服务恢复，taint0。[回归](camera-runtime-validation.json)。首轮复用的313 fixture硬编码k298，媒体操作前退出3；只更新为k363身份检查并重新编译，未删除guard，首份失败保留。

继续优先反编译已提取的原厂`CAMERA_ICP.elf`，没有重复下载或读校准分区。离线执行原始Thumb `fwEntryFunction` 的全部本体，12场景覆盖成功、共享/堆地址缺失、映射失败、ISR/信号/互斥量/线程创建失败。成功路径写HFI响应1，失败路径写2，早期idle线程失败保持0；测试路径没有写3。[结果](firmware-init-validation.json)。

分配、OS线程/信号/互斥量、IRQ注册和MMU映射由明确的桩提供，没有运行调度器或A5硬件；这些结果不能证明实际固件启动，不能推断所有其它函数都不会写3。它们说明356把响应3放行为SYS_INIT尝试并不构成成功证明；后续应等待明确初始化成功再交命令，并保留超时及清理。

另执行原始`ICPDomainCmdHandler`的SYS_INIT及三种64位cookie的PING路径：分别生成56字节0x20001和16字节0x20006回复；初始化error字段和PING cookie均从偏移8开始，符合当前解析器关键字段。[回执证据](firmware-messages-validation.json)。消息投递/日志为桩，芯片与MMIO值是合成数据，没有模拟调度器或实际硬件IRQ。

本次仅刷logdump，boot276保持；旧k298模块树和logdump可离线回退。实际Linux DT来自EDK2固件卷而非FAT中的同名DT文件，后续365/366已单独核对这条加载链。没有NV/OTP/校准分区写入。ICP完整SYS_INIT/PING/PC_ACK、IPE会话及绝对光学校准仍未完成。还存在未确认的第五颗2MP人像相机，不能将四颗已测传感器称为本机全部相机：[剩余范围](REMAINING-CAMERA-SCOPE.md)。
