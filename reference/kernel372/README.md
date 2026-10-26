# 372：取得复位前原厂异常现场，定位初始化失败的错误清理路径

本轮以371为基础，增加可选owner `failure_snapshot`回调；它在start失败且CPU已尝试启动时，于标准dump和CPU／块复位之前执行。临时诊断模块通过原厂ELF对应LOAD段比对固件首4KiB代码页，匹配后才按只读参数打印4段、76个word；参数限制为最多4范围、每范围96word，必须对齐、完整映射并处于实际加载／分配范围。SoC核心没有加入原厂符号地址，诊断参数和解析器负责固件版本约束。没有修改板级DT、主线框架、正常相机驱动／用户空间或个体校准。[补丁](pre-reset-observer.patch)。

先执行原厂完整ARM异常入口及`rex_jettison_core`，仅CP15故障值合成，没有再桩掉context-save。两类异常确认：异常保存通过`arch_coredump_ptr`指向coredump内的寄存器区，**不是A5ContextRegisters**；ABT SP字段在该区+0x58，原厂冷启动ABT栈顶也已核对。早期按A5ContextRegisters/+0x64读取的模型失败，纠正后才生成本次profile。[指令证据](firmware-context-validation.json)。

临时observer／配置检查的19个ASAN/UBSAN用例覆盖代码页不符、归属不足、越界／溢出／对齐／数量错误及坏ELF；实际start函数体13路径确认回调先于dump及quiesce，仅失败且CPU已释放才触发。printk、DMA屏障及平台为桩，非实机证明。[observer](observer-validation.json)、[生命周期](lifecycle-validation.json)。两个k363 in-tree W=1/-Werror候选模块构建通过、无诊断，维护提交`71ca6b6361edfba4a144295656e6737d2c18e8c2`。[构建](intree-build-validation.json)。

实机一次事务`k372-boot-r1`仍响应3／2.712ms并自动重启，旧worker未返回。**ramoops完整保留了复位前begin、代码页匹配、76个word和end**，从而取得真实data abort。原始寄存器、栈和日志只私存。[实际结果](boot-runtime-r1-validation.json)、[解析摘要](pre-reset-runtime-validation.json)。没有读取重启后的旧DDR来猜测异常。

实际C异常处理器已把旧PC栈槽覆盖为自己的返回地址，不能沿用“保存ABT SP+32就是故障PC”的入口瞬间假设。改为只接受受界原厂异常文字中、同时与直接保存的FAR／FSR／type一致的PC；不一致、缺行、重复或越界记录拒绝。模型增加原槽被覆盖、文字FSR不符等反例。[解码](decoder-validation.json)。实机指向`DALSYS_DestroyObject`中的对象读取，调用者为mutex销毁错误路径。

继续执行原厂`fwEntryFunction → ICPHostInterface_destroy → vSYS_DestroyMutex → DALSYS_DestroyObject`实际指令；共享区地址或大小缺失时，两种输入都复现实机相同的对象地址和故障PC，并且在写初始化失败2之前异常。OS分配、线程、信号析构、MMU及日志仍有桩；它证明该故障路径可达，**不直接证明实机CSR为0或CPU复位会清空寄存器**。[重现](shared-failure-validation.json)。

随后373针对主机初始化顺序进行功能修正；372恢复身份／临时固件清理已完成，当前最终设备状态以[373记录](../kernel373/README.md)为准。原始固件、异常字、文字、完整ramoops和认证数据不进公共Git。完整多摄／ISP目标保持active。
