# 当前 IRQ／USB PM 候选：设备启动门和单 logdump 工具

该增量沿用已经使用过的正常硬件收拢与 RESTART2 流程。当前源为 #502、bootedd／logdumpace2、驻留 USB7cb／charger97c／保护7848；冷 stage 后仅磁盘 USBd046／manifest34ead 改变。目标为现成 #504／logdump4453，bootedd 保持只读。不是原先的501→502或旧R8→IRQ事务，不能复用已结束的运行目录。

`eud-quiesce.py`、`eud-restart.py` 的硬件后半段逐字复用原 stage-aware 版本，仅工作标签改变。既有 charging flock 持有到进程退出，stage 已完成同步停充，故不重复调用会重入该锁的服务 stop。既有 once claim、freeze、一次 RESTART2、返回时 thaw／close 保持；没有 EUD MMIO、热卸／加载模块、AUTO 或保护捕获动作。默认入口在 Linux／DBus 导入和设备访问前退出。

新增门使用真实当前 stage 的九字段请求、五字段进程记录、两个原始备份、Full／INHIBIT 前后样本和两个原进程 wait0。共17份设备原件，明确区分旧驻留 note 与新磁盘文件；失败、部分写入、临时文件残留、实例变化、PID复用或未知原进程均不能进入启动。真实 Full 停充后保留 logical Full／cause／session0，holding／hold_requested 则应清零，不能伪装成仍在 Full holding。后续真实断源或正常冷启动仍按原内核易失状态语义处理。

`stage-proof.py` 复用原已验证 fetch 字节审核和进程链函数，重审当前 stage-host 的原 IRQ adoption＋完成的97c热更新绑定，不能用旧pointer5fca冒作当前18e8。R2只导出设备请求副本，不单独导出 root launch-claim；主机不补造这个文件。设备 `read_stage()` 会独立重读原 claim 并核其 boot／request／count／argv；二者职责在代码中分开。新guard还会两次核对同一已消费MAC缓存及kernfs实例，持有只读fd，未触发新查询。

`fastboot-operator.py` 只写 logdump，正向4453、载体回退ace2；写入与 reboot 为两个独立一次动作。原 exact serial／msmnile／两分区尺寸检查和19个 once／Popen／wait／未知状态函数逐字保持。写前重新核实际载体字节，未知写入结果不重发。boot尺寸查询不会被冒称为boot内容hash，bootedd由设备前后完整只读核对。

新上下文必须为 `samurai-irq-native-usb-pm-fastboot-context-v1`，带本事务七份原收拢／派发文件，以及当前 stage／fetch／source_review_inputs。源版本精确502，目标504；operator必须再次通过实际 stage 审核，不能只接受guard标签。事务为新的 `irq-native-usb-pm-activate-[a-z0-9-]{8,48}`。

现有 Image504 FAT 完成原件、三个真实制作命令终态和当前cohort绑定已复用。材料化时分块核对两个64MiB FAT及当前96MiB boot；旧FAT作者的97811描述只代表其制作时的旧boot，当前bootedd由当前cohort证明。有效离线材料在私有 `irq-native-usb-pm-materialized-002`，包含同字节worker、合同和activation-pins；不含运行guard、lease或未来boot身份。默认operator本地检查已通过，没有USB或手机操作。

首轮八项集成检查通过；补充实际context检查发现生成器事务正则少一个`}`，当时有效请求被提前拒绝，没有进入设备动作。错误源码、八项原收据与001材料保留，不采用001。修正后仅复测受影响的context四项，原八项按未变函数／源码复用；新002材料化与operator默认入口各真实wait0。17个公共函数、19个operator函数和两个原fetch审核函数保持；没有重跑旧矩阵。设备和进程边界为明确模型，部分只读报告使用真实缓存原件。

**剩余接线仍未完成：** 当前叶没有主机 prepare／quiesce／restart 调度器、新boot postboot／adoption，或 #504→旧USB/manifest 的完整冷回退worker。`rollback-original`只还原载体，不等于完整PM回退；完整回退须USB7cb＋manifest18e8＋logdumpace2并正常重启。所有这些准备完成后才安排串行实机窗口。本叶不证明待机、枚举、500mA恢复或图标延迟已验收。
