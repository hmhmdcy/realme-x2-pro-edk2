# DWC DEVICE start 错误清理候选：独立薄审

对正式冻结的 `dwc-device-start-recovery-candidate` delivery `1f3aa44fa29c8f901c39a378ff4a7d546c447c40072e3e5283226857cfcb1349`，在本次局部增量范围未发现新增阻断。仅读作者源码、patch、14个实际函数提取及20例/对象构建收据；没有执行作者生成器、入口、测试、构建、存储 guard 或设备操作，没有改作者文件。

原同步候选已经审查的事件序号、恢复上限、worker 合并、NCM 回调和 PM 行为不重新作为本轮验证结果。独立整文件比较确认相对该候选只有 `dwc3_gadget_soft_connect()` 变化，`core.h` 逐字相同；16个旧函数逐字保持。14个 fixture 函数与候选/原 core 的实际函数体一致。作者20例和私有 `gadget.o` W1/Werror 的同 child 终态收据均与当前冻结源绑定，本轮未重跑。

局部清理的具体依据：

- `gadget.c:2817` 保存 `__dwc3_gadget_start()` 的 errno。失败分支在既有 `dwc->lock` 下执行原 `__dwc3_gadget_stop()`，返回原 errno，不进入 `:2832` 的本次 RUN_STOP。没有新增 Linux IRQ enable/disable、PM 引用、core/PHY teardown 或 event-buffer 释放。
- 实际 start 的 start_config、EP0 OUT、EP0 IN 三处返回失败在 `:3016..3035`；均早于 `:3043` 的 EP0 OUT setup 和 `:3045` 的 DEVTEN enable。控制 EP 的 set_config/resource 失败早于其 DALEPENA enable；IN 失败的原 err1 已 disable OUT。再次 stop 重复清 OUT enable，清理 IN 与 DEVTEN，沿原 disable 的 resource/TXFIFO/可能 delayed-stop flags 规则处理；EP0 descriptors 不因 number>1 的分支而被清空。
- `:3084` 的原 stop 只屏蔽 DEVTEN 并 disable 两个 EP0。`dwc3_remove_requests` 的已有 giveback/停止传输行为保留；新分支没有释放 IRQ handler 会引用的 event/cache/EP/TRB 分配。线程 IRQ 在同一 dwc 锁下处理事件。清 DEVTEN 并不 join 已在途 IRQ，也不证明 pending 事件已消费或硬件 HALT；本叶没有从这个清理点推导 DMA/主机枚举成功。
- 新失败清理后，已有恢复主体在其再次 reset/event setup 前执行原 synchronize_irq；序号发布及新错误补排逻辑逐字未变。新分支没有清 recovery count 或绕过旧 UNRECOVERABLE。若 reset 自身失败，仍在 start 前直接返回；RUN/HALT timeout 的旧状态/错误也未被包装成清理成功。
- soft_connect 是共享函数，因此 OTG 的原单次调用也会获得正确的 start errno；只有 DEVICE resume 接入原已冻结的同步重连。HOST 行为和正常 start 路径保持。

未闭合的边界不是本轮通过项：原 core PM common 仍忽略 gadget primary errno，DEVICE common 保持供电成功返回并走原 SUSPHY/runtime pending-event 引用与 IRQ 尾。恢复失败不等于 PM 负返回或 core/PHY 已安全断电；直接传播负值的旧错配/遗漏尾处理反例继续成立。start 的 endpoint-command timeout 及 stop 内部 void/无传播清理结果也不是物理 HALT 证明。README/caller-evidence 对这些限制已准确保留。

审阅结论只适用于这份未部署的内核候选增量，不证明历史 r5 失联原因、实际 NCM 重枚举、整机待机恢复或负错误安全 unwind；不允许将对象直接注入旧 Image。完整候选增加了 core struct 字段，未来采用需要一致内核构建及相应集成验证。
