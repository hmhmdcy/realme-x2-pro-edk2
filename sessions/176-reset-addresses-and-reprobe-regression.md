# 176：复位地址刷新与10次声卡恢复回归

2026-10-14。kernel176/logdump176已部署，boot/DTB172、UCM173保持。扬声器和麦克风通路已可用，171用户“两组都听到，来自手机”的证据仍有效。本轮继续修175父设备复位NACK：失效main/sidev旧logical address，查询放到WCD私有锁外，ready门控阻止早期IO；status和电源devm cleanup覆盖SLIM bus wrapper晚期失败，重复absent不重复释放IDA。

71函数级场景、六个负对照、ASan/UBSan、W=1及完整构建、模块兼容和FAT回读通过。两个codec、八个父设备重绑全部自动恢复声卡；18个旧debugfs句柄EIO，MCLK/map和五路consumer回收/恢复配平，无machine手工重绑及NACK/超时。175历史失败不改。

八次录音启停、三次真实pause恢复、原生四例及桌面paplay+parecord左右声学检测通过，目标功放关闭参考可区别环境噪声。最终955.71秒taint0，所列故障计数0，PCM关闭、功放68/68配平，NV/persist/模块132/UCM173保持。实物耳机、系统休眠/SSR、冷启动/长稳和正常音质仍待验，完整goal active。

本轮继续读取上游MFD/SLIM core源码，哈希和API限流情况均有记录。具体来源、实现范围和所有脱敏报告见[176证据](../reference/kernel176/README.md)，当前部署/回退统一见[检查点](../NEXT-SESSION.md)。
