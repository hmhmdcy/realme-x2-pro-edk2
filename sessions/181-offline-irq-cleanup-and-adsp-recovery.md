# 181：离线 IRQ 清理及受控 ADSP 恢复通过

2026-10-14。保留180 PDR修复，已DOWN时在同步停parent IRQ后将main现有MAPLE map设为软件缓存清理模式，清理后销毁，不重放。UP移除仍进行真实I/O、interface缓存策略不变；实际regmap/MFD函数证明离线无硬件访问、缓存外读EBUSY、非法操作仍失败，新UP map恢复正常。

内核181构建并仅刷logdump，boot/DTB172、模块132/UCM173/Mesa149保持。初启动及一次真实offline→running通过，资源释放/两旧句柄EIO/自动HiFi和录音恢复，所列PDR/IRQ/config/mask/ASoC等全0。恢复后原生及桌面左右编码检出、无削顶、volume/mute与16保存控件恢复。892.99秒taint0、功放13/13静音、PCM关闭、main cache-only=N，ring含0秒至当前且所列20项故障全0，NV/persist/部署/模块核验。

仅该受控恢复通过；180的72/6和178全部失败保留，耳机/耳麦/按钮、自动crash、更长PM/跨启动、音质/保护仍开放，goal active。详细[181](../reference/kernel181/README.md)。
