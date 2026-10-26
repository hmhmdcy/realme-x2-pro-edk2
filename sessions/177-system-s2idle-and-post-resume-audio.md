# 177：系统s2idle与恢复后左右声道验证

2026-10-14。本轮177是软件验收，内核和部署仍为176，boot/DTB172、UCM173保持，没有新构建/刷写。RTC五秒清醒闹钟中断先通过，再各执行一次空闲和普通用户播放/录音运行中的mem→s2idle。

实际休眠14.760/14.411秒，由15秒RTC闹钟唤醒，success2/fail0，同boot、taint0；每例2392个PM callback_end返回0，音频相关card/codec/MFD/NGD有suspend/resume收据。应用流正常结束，声卡无需重启或重新绑定恢复，控件和音量保持。活跃录音检出恢复后的完整12秒编码序列；没有据此宣称休眠中连续/无丢样。

两次休眠后8次录音启停、3次真实暂停，以及原生四例、用户桌面左右编码闭环通过。最终2811.49秒、音频故障计数0，功放72/72配平静音、PCM关闭，NV/persist/模块132/UCM173核验；RTC alarm和临时trace清理。USB PHY和Wi-Fi独立告警保留，不称全系统日志无错误。

完整方法、scope和报告见[177证据](../reference/kernel177/README.md)，当前部署见[检查点](../NEXT-SESSION.md)。SSR、重复长时PM、冷启动/长期、实物耳机与音质/瞬态/保护仍待验，完整goal active。
