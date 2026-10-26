# DEVICE start 错误进入同步恢复：未部署局部候选

本叶补齐已冻结 `dwc-device-sync-recovery-candidate` 的一个实际漏口：`dwc3_gadget_soft_connect()` 忽略 `__dwc3_gadget_start()` 返回值，端点 config、EP0 OUT/IN 初始化失败后仍写 RUN_STOP，错误没有进入已有同步恢复。新代码保存原 errno，在原 `dwc->lock` 下调用已有 `__dwc3_gadget_stop()`，清 DEVTEN 和两个 EP0 enable，然后返回错误，跳过本次 RUN_STOP。原 `connect_mutex` 中的 DEVICE 同步恢复因而可以处理这类启动失败。

只改变该函数；`start-cleanup.patch` 是相对已冻结同步候选的增量，`against-502.patch` 是相对实际 #502 原 DWC 的完整 gadget/header 候选。共享、#502、原同步候选、旧 propagate/cleanup 文件均未改。没有 Image、模块链接、设备/SSH/USB/PM/桌面操作或部署。此处不宣称实际 NCM 重枚举、历史 r5 原因或整机恢复通过。

## 清理的准确边界

实际 `__dwc3_gadget_start()` 的三处失败均发生在它调用 `dwc3_ep0_out_start()`、使能设备中断之前。控制 EP 的实际 `__dwc3_gadget_ep_enable()` 在 set_config/set_xfer_resource 失败时先返回；EP0 IN 失败时旧 start 已先 disable EP0 OUT。新增 stop 仍清两个 EP0 与 DEVTEN，使其不依赖尚未置位的 `pullups_connected`；否则 `soft_disconnect()` 会直接 early-return。重复 disable EP0 OUT 由实际 disable 函数清相同 enable bit、保留原 resource/TXFIFO flags，属于现有同一局部状态的清理，不释放 host DMA/event buffer。

事件缓冲、core/PHY 和 IRQ 资源继续有效，供已经运行的 IRQ 使用；此分支不 free IRQ、不 disable/enable Linux IRQ，不 core_exit、不释放 PHY/clock，也不修改 pending_events 的引用。原同步 helper 在再次 soft reset/event setup 前仍执行原 synchronize_irq。局部 MMIO 清 enable 不等于已证物理 HALT；底层 endpoint stop 自身也没有一个可传播的硬件完成 errno，本叶不编造 cleanup_success。

首次错误及新增恢复结果继续分别记录；首次 errno 即使后续局部恢复成功也保留。原恢复 count/MAX3、旧 UNRECOVERABLE、新 IRQ generation 与 worker 合并规则逐字复用。没有新循环、永久 terminal 字段、IRQ parking 或清旧 fault。新 generic soft_connect 检查也使 OTG 的原单次调用正确返回 start errno；OTG 没有新增重试，HOST 未改。

## PM 未闭合项保留

**core PM 仍忽略 gadget primary errno。即使本地恢复失败，DEVICE common 仍返回原 0，并保持初始化后的 core/PHY 供电，执行原 SUSPHY 和 runtime pending-event put/clear/enable 尾。不能把 PM 返回 0 当成恢复成功。** 本叶未实施“仅恢复成功才 PM 成功”，也没有把 gadget 负值直接传播至 PM。

真实旧 caller 反例仍适用：直接传播 gadget 负值会让 RPM 将设备置 SUSPENDED、system resume 将 runtime 状态置 suspended，而 core/PHY 仍 initialized；runtime 还会跳过已拥有的 pending_events 引用/IRQ 尾。旧 `propagate-errors.patch` 和 `apsd-dwc-resume-error-candidate` 因此仍是 changes-required。被拒 `dwc-resume-device-cleanup-candidate` 的永久 flags、跨 request/free_irq 停车及无证 core_exit 没有复制。

soft-reset timeout 在 start 前返回，本轮不追加 stop、不称已清理；RUN_STOP 启动超时仍按原规则返回，软件 pullup 不足以证明硬件状态。恢复的 HALT timeout 仍保留独立错误、停止本次重连且不强行 core_exit；原 stop/disconnect 函数和该超时行为逐字未改。原 core_init_for_resume 自身失败的 clock/reset unwind 保持原样。真正向上层传播恢复失败，需要另外证明 IRQ/work 与供电生命周期终态；不能从本局部修复推出该方案已完成。

具体调用链及旧拒绝依据见 `caller-evidence.json`，复用原 Image 关联源码、旧 126 断言、独立 caller 反例及同步候选收据，本轮均未重跑。

## 本次验证与真实终态

`test-result.json`：从候选/原 core 直接抽取 14 个实际函数，6 组 20 个定向病例，ASan/UBSan/Werror 通过。包含旧实际 soft_connect 吞三种 start 错误的反例、实际 start/stop/EP disable 清理及正常路径、三类 start 首次失败→同步恢复、两次不同 errno、旧 UNRECOVERABLE、软 reset 和 RUN/HALT 失败、实际 runtime pending 尾及 system SUSPHY、原 init failure unwind。MMIO、endpoint 命令返回和 PM/回调边界为 fake；不模拟 DMA、真实 Linux IRQ 或主机枚举。旧 11 组和 126 断言未重跑。

`build-result.json`：仅私有 `gadget.o`，从冻结 #502 的实际 `.gadget.o.cmd` 派生原 W=1 命令，加 Werror，路径转到新私有 source/header/output；复制原生成 include，无 make/modules_prepare/Image/ko。GCC PID **786** 同一 child wait **rc0**，**3.186 s**，零 warning/error；对象 **466888 B**，SHA `0718bc5e1c917eb9e494c74333c18a68e28532e42bd35fb4b941394d925c9b20`。

原 #502 的 DWC C/header/core、saved command、config、obj、Image/vmlinux，与共享相关源/config/obj/构建输入及 parent mountinfo 在列明范围前后不变。#502 的 DWC 确为 Image363 的同一原字节，CONFIG `23e088a9…0ed`。原 284 Ubuntu/root guard 仅建立原卷身份；没有改绑定/全局配置、SDK/Git 或新 anchor，构建窗口已明确交回。

最终交付以 `delivery.json` 的 source/test/build/raw pins 为准。当前是可审阅的局部内核候选；完整同步候选已增加 struct 字段，未来采用仍需一致内核构建与独立审查，不能向旧 Image 单独注入此对象。
