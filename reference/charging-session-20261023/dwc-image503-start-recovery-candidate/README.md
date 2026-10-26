# Image503：DWC start 同步恢复的一致私有构建

这是独立、未部署的候选，不是当前 #502 事务、IRQ cohort 或启动载体。来源是已通过的实际 #502 三树；只换已独审 DWC `gadget.c` / `core.h`，构建身份 #503，原 reproducible timestamp 与 config/release/BQ/initramfs 不变。实际 UTC 单独记载。

本次唯一原执行为 `run-503.py --execute-503`，native exec session **74911**、父 worker **854**，已沿同 handle 最终 **exit0/passed**。namespace child **1463**、8对象 make **1473**（11.61s）及 Image make **2032**（56.01s）均真实终态rc0。父最后完成 #502 三树、原363、共享及挂载保持门后才报告整体通过。不能重放已有私有目录 `/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01`。

最终 Image **59243008 B** / SHA `969b01585e2fd8895a73715fdb6d48ed16bdb0c3886b6695eb9111bb5b613500`；vmlinux SHA `7f5d8ed47694c85ea69ce428bc97e9749e3d55df099693044fc35e87f6ede4ee`。路径在该私有目录 `build/arch/arm64/boot/Image` 与 `build/vmlinux`。真实 source/metadata/ABI/终态绑定见 `build-result.json`、`execution-receipt.json`、`abi-reuse-result.json` 和 `delivery.json`。没有后续载体或设备动作。

`prepare-runner.py` 从冻结 `gauge-image502-notify-candidate/run-502.py` 派生，`runner-delta.patch` 保留完整差异；原 284 Ubuntu/root guard、私有三树无 hardlink 复制、child recursive-private namespace 四 canonical bind、原 PID wait/finally、父基线/共享/mount 终核均沿用。没有共享源码或原 #502 写回。默认/check-local 只验证本地来源，不使用 guard/WSL/build。

原 #502 的实际9242个 cmdfiles中只有8个对象依赖私有 core.h：core/trace/gadget/ep0/debugfs/dwc3-qcom/dwc3-qcom-legacy/dwc3-generic-plat。它们全部 built-in；of-simple 无依赖，不重编；本目录没有模块目标。显式8目标后仅 `Image`，保存各真实 compile 命令与原日志。根批准的 archive 变化集合只有8件加 `init/version.o`，另3238叶/32stub逐字保持；8件某些最终字节相同不构成错误，但必须实编全部。archive外版本timestamp、kallsyms、vmlinux等仅走原链接产生。

版本两ELF须只把 #502 字符串换为 #503、其余字节/可执行 section不变；原 ramfs三件、CONFIG/UTS_RELEASE/public headers、BQ默认false、15097个内置导出实际ELF及symvers全行须保持。新私有DWC core.h是明确的内部布局差异，不能由CRC0冒认type ABI。既有778模块/481+CCI导入证据仅在新导出/其它源与对象门通过后复用，不重新扫描旧模块、重跑20/126或旧函数矩阵。

本候选只使实际 `__dwc3_gadget_start()` 的错误先清局部EP0/设备IRQ并跳过本次RUN_STOP，进入已独审同步恢复。core PM仍忽略gadget primary、保持原 initialized/powered-success与pending尾；HALT/soft-reset失败及负返PM安全unwind没有闭合。即使构建全部通过，也不等于实体待机/NCM重枚举或整机恢复通过。

没有 modules/dtbs/SDK/Git、boot/FD/FAT封装、设备/SSH/USB/PM、安装或部署操作。实际输入集合和计划来自 `dwc-start-recovery-image-integration-plan/`；局部源码/实际函数与单对象验证来自 `dwc-device-start-recovery-candidate/`，独立薄审 a6ce6a39…ae70b8b 保持原件。
