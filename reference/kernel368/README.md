# 368：确认原厂响应 3 为 SFR 故障路径，修复错误诊断与 DMA 回收顺序

上一阶段367恢复了四颗已确认传感器及正常桌面。366的HFI响应3／modem watchdog失败没有改写。本轮只做固件分析、单次定点DDR只读取证和未部署的内核候选；没有再次释放A5 CPU、重启或写分区，手机仍为367基线。

原厂`CAMERA_ICP.elf`中的`SendSfrMessage`从0x1b8a5进入，完整348字节函数体先使用SFR缓冲，再在0x1b9f2向CSR 0xe001004c写3。保留符号和反汇编显示调用者包括异常处理、栈保护失败和assert错误路径。实际Unicorn执行11个路径，包括BPS/IPE状态、provider失败、短SFR与缺SFR：全部写3；有效SFR的格式化调用先于发布3。[实际固件指令证据](firmware-sfr-validation.json)。日志、cache维护、格式化和电源提供者明确作桩，不能把这些结果当真实缓存／电源／完整RTOS验证，也未恢复出366真正的故障文本。

因此3不能再作为“等一会也许变成1”继续等待，也不能发送SYS_INIT。新候选直接把它视为终态失败，在清理前通过标准`dev_coredumpv`发布568字节LE诊断：固定版本、HFI响应、版本寄存器、六个队列索引、三个计数及最多511字节SFR／结尾NUL。该记录不包含图像或调校缓冲。SFR拷贝同时受固件声明大小与实际分配大小限制；发布后的独立快照不会随共享RAM回收丢失。[补丁](a5-terminal-sfr.patch)、[私有记录解码器](decode-start-dump.py)。

同时把DMA别名和backing回收移到runtime-PM释放之前；unmap失败保留PM引用和剩余内存供重试。此前顺序在设备断电后才开始撤销映射。本轮不声称这就是modem watchdog原因，也没有改变CPU复位／WFI或GDSC策略来绕过故障。

实际生产`camss_a5_start`函数体13组ASan/UBSan检查通过，包括3后又出现1仍拒绝、未知值／超时、命令失败、启动前错误和清理失败保留资源；旧版两个反例保留。[启动](start-regression-validation.json)。实际stop函数体7组检查确认先退DMA后断电、reset/unmap失败保留所有权及PM引用不重复丢弃；旧版两个反例保留。[停机](stop-regression-validation.json)。这些平台／MMIO／DMA／PM提供者为模型，不证明真实SMMU静默或异常恢复。

实际诊断helper与原队列结构在ASan/UBSan下检查了空指针、错误table、短分配、损坏SFR长度、NUL、分配失败和快照独立性；从C实际生成的记录由Python解码，错误长度／magic／版本均拒绝。[快照和解码](diagnostic-regression-validation.json)。

源码已应用至维护树`/mnt/samurai-full282/source354`、`samurai-a5-terminal-sfr368`、`9c60745372258f2f37374862a06c9fd09eeaf240`，只改SoC A5启动后端一个C文件。按已安装k363 release实际in-tree构建core模块，W=1/-Werror无诊断，232352字节，CONFIG_DEV_COREDUMP=y；共享相机输出和配置已恢复。[实际构建](intree-build-validation.json)。没有换现机模块、DT、IPA、包或私有校准默认。

另尝试只读现有专用固件DDR的4KiB代码页以判断能否恢复异常寄存器；代码页与已知ELF不匹配，遂停止，没有读取计划中的异常页或扩大扫描，不能对残留状态作来源判断。[有限只读结果](retained-firmware-validation.json)。原始字节、反汇编、固件与SFR内容只私存。

下一步是在新的、具备预先收集devcoredump能力的针对性实验中取得实际SFR原因并验证回收次序，不能重放366旧事务。完整ICP握手／IPE会话、未知2MP人像传感器、更多模式和完整光学／几何／同步／连续AF仍未完成；全部目标保持active。
