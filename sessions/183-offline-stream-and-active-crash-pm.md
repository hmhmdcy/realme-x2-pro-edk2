# 183：修复离线 WCD 流清理并验证活跃播放恢复和两次 s2idle

2026-10-15。kernel181活跃播放/录音中的一次合成crash产生WCD STOP −ENOTCONN和三条ASoC错误。新增非睡眠传输状态查询与slim_stream_abort，仅离线时释放本地ports，不发总线消息；ASLEEP保持在线，普通在线清理和已报告的真实错误保持。六文件修改、12 tracked源；69实际函数场景/六负对照、W=1/全编译/FAT及770模块兼容通过，183已只刷logdump部署。

183首轮驱动错误0，但脚本把单侧DAPM断电误当成必须逻辑muted=1，保留失败。按真实GLOBAL/AMP使能位修正，独立v2再注入一次：原paplay/parecord自动重接，2旧FD EIO、18项故障0；原流左右amp-off匹配对照检出，相关0.9119/0.9312、开关差20.48/40.37dB，mixer及volume恢复。旧181参考下左未达标收据保持，没有修改门槛。

当前183的空闲45秒、活跃90秒s2idle实际45.330/87.039秒，每例success+1/fail+0、RTC IRQ+1，2392/2210个PM callback end错误全0。醒后原生/桌面左右检出，无削顶。仅s2idle和恢复验证，录音样本时间不代替墙钟或无损休眠音频证明。

最终1472.87秒同boottaint0、ADSP running，单card/HiFi，PCM关闭、功放左23/23右22/22关闭静音、16控件恢复、五consumer各1、两map/一MCLK、main cache-only=N、NGD suspended。所列20项全boot0，预期两次crash日志/首轮脚本失败及历史178/180/181真实失败保留。NV/分区/770模块核验。

当前Image bfa72dd9…/logdump e73754c7…、boot/DTB172、software/modules132、UCM173、Mesa149；私人原件已取回，SCP半件也保留。完整goal active，耳机/耳麦/按钮、真实watchdog、跨启动/长稳和音质/瞬态/保护开放。详见[本轮完整证据](../reference/kernel183/README.md)及[当前检查点](../NEXT-SESSION.md)。
