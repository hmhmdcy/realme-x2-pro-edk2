# 370：拆分 A5 停止与 DMA/PM 释放，准备受约束的故障窗口

本轮仅离线工作，没有新硬件启动、刷写、模块加载或个体校准更改。设备采用369恢复后的既有基线：Image363、boot366／DT365、libcamera r29／config r24，当前身份仍由host369的严格原密钥与369恢复guard保护。四颗相机与桌面健康验证复用369，未重复采集。完整多摄／ISP目标仍active。

## 原厂指令证据

在352保存的同一原厂ELF上执行`vmm_preinit`和`program_section_entries`的原始Thumb指令，只对L1清零提供memset桩。检查到代码、异常字段、页表和CSR所用地址均为恒等映射；07400000共享区、0741c000 SFR和10a00000堆在该静态表中未映射，仍依赖后续动态VMM。这不是硬件SMMU、CP15或完整RTOS验证。完整页表、原始静态表和反汇编只私存。[映射结果](firmware-mapping-validation.json)。

实际初始化请求等待块的4个用例证明：请求为0／2时先等待，变为1后才写固件版本0x01000100。原厂主机代码也先唤醒CPU后提交初始化请求。结合369实际版本值，可推断那次已经通过该请求等待点；不能再把响应3解释为请求尚未置位，也没有证据靠交换这两次写操作解决故障。版本写入后还有堆、线程、IRQ和SFR映射，具体失败位置仍未知。

另执行原始ARM data／prefetch abort入口与公共字段存储，CP15故障值为显式合成，core-save为桩。4例确认FAR、FSR、type偏移分别1099a0／1099a4／1099a8，data type3、prefetch type1，传给C异常处理器的是按入口修正过的故障PC。此模型没有恢复任何设备异常，亦未据此臆测完整core-save布局。[异常布局](exception-layout-validation.json)。

## 驱动层变化

SoC传输核心将`quiesce_locked`与`stop_locked`分开：前者停止计时器／CPU／IRQ并断言块复位，后者才撤销DMA映射、释放RAM和PM引用。启动失败尝试quiesce后保留已拥有的映射及PM，API明确要求owner在成功或失败后最终调用stop。失败dump仍在quiesce之前发布，避免丢失已有的故障通道。复位失败继续保留CPU标志、内存和PM归属；不把软件复位返回0等同于真实DMA静止证明。

临时boot-test增加默认false、加载后只读的`hold_start_failure`。仅失败、已尝试CPU启动、quiesce无错误、CPU／IRQ关闭、块复位已断言、PM引用及完整固件映射仍保留时，进入`failed-held`，跳过自动资源释放并pin模块。既有cleanup入口负责最终释放，只有全部内存、CPU、PM、时钟和电源域归属清零才可解pin。

临时设备的`firmware`二进制属性为0400，只在上述held窗口允许读取，匹配设备owner并同时持有test_lock与a5锁。读取受实际分配长度限制，拒绝负offset、越界截断，cleanup后不可读。它只读该驱动已映射的固件RAM，没有新增/dev/mem通道。该视图只属于临时诊断，不是正式相机ABI；其中内容按私有固件／异常数据处理。CPU停止后的DDR也可能未包含A5脏cache，零异常字段不能证明没有异常。

板级DT、reserved-memory位置、主线公共OF/IOMMU框架、传感器、CAMSS/VFE、libcamera、IPA及用户配置均未更改。没有以用户空间绕过HFI错误。完整SYS_INIT/PING/PC_ACK、IPE图像会话及多摄剩余范围仍未完成。

## 验证与产物

实际生产start／quiesce／stop函数体的ASAN／UBSAN模型：13种start路径、9种stop／重试／单独quiesce路径通过，旧版2例因过早释放归属被拒绝。MMIO、复位、DMA、PM和调度为桩，不能推导watchdog修复或硬件清理成功。[生命周期](lifecycle-validation.json)。临时reader实际函数体15种归属／边界用例通过；实际held／pin判断13种用例通过。[读取](snapshot-validation.json)、[owner](owner-validation.json)。

维护源分支`samurai-a5-quiesced-failure370`，commit `e79613d477deee2a55726cc2e05c7789057395ba`。两个候选模块针对实际k363配置in-tree W=1/-Werror构建通过，无诊断，intree=Y，构建配置及既有CAMSS输出已恢复。core232976字节，test73320字节；产物私存kernel370，未安装或加载。[构建](intree-build-validation.json)、[源码](source-state.json)、[补丁](a5-quiesced-failure.patch)。

## 下一步

为held窗口准备独立收集／清理worker及夹具，必须使用369当前guard和显式`hold_start_failure=1`；不能复用369的默认自动清理launcher。先验证窗口结果与固件首个代码页仍匹配原厂ELF，再读取109000异常字段页和所需页表，原始数据只私存；页不匹配、复位失败或归属不全就停止读取，不把重启后旧DDR当故障现场。快照落盘后再分别观察DMA撤销和PM释放的终态，从而分辨369重启是否与清理阶段有关。

不能在新worker未准备好时重复CPU启动。更不能把本轮的模型、模块构建、软件状态或空SFR当作成功启动；最近真实实验仍是369的响应3／2.711ms／自动重启／无清理终态。完整目标剩余见[363范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。
