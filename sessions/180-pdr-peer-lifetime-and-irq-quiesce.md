# 180：PDR 世代/寿命修复及父中断退出

2026-10-14。实现并部署PDR锁外事务/回调、端点与通知世代、旧注册取消及回调/worker停止后释放对象，WCD先同步停止parent IRQ再清理children。118函数场景/15负对照、W=1/checkpatch、全编译/FAT和模块兼容通过。

初启动所列故障0；一次ADSP停启自动恢复card/录音与资源，但config72/mask6导致测试失败，PDR/IRQ读/ASoC均0。随后左右原生声学检出，错误版本标签经boot-id与runtime验证，仅更正派生metadata，原始包保留。F1无RX回执，确认Linux仍在原boot并解冻后诊断；串口重绑未恢复，使用同内核重启路径的标准RESTART2完成bootloader切换，以实际fastboot状态确认。

180已被181替代，完整原件和失败保留。详细源码、测试和数据见[180](../reference/kernel180/README.md)。完整音频goal active。
