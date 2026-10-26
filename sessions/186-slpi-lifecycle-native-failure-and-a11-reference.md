# 186：SLPI停启故障、失败FastRPC原型与本机A.11参考

2026-10-15。DSP-first stop后原SLPI第二rproc start成功，但后续FastRPC共享池再probe−22；新回收原型主机337场景/4负例通过，实机第一轮采样通过但reclaim−22，总试验失败，原文件/源码恢复并热重启确认。A.11所选modem.img ZIP CRC通过，SLPI2.1-00068离线提取，未部署或刷写。

完整范围、失败和回退见[186](../reference/kernel186/README.md)，[当前检查点](../NEXT-SESSION.md)、[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。完整外设goal继续active。
