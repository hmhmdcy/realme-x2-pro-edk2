# 177：kernel176 的系统 s2idle 与恢复后音频验证

2026-10-14。177是软件验收轮次，仍运行kernel176/logdump176、boot/DTB172、UCM173，没有构建或刷写kernel177。[源码核验](source-validation.json)确认10个tracked文件与176一致。扬声器/麦克风主通路继续可用，本轮补上两次真实系统s2idle及恢复后的音频回归；完整音频goal继续active。

## 休眠路径与测试方法

当前`/sys/power/state`为freeze/mem/disk，`mem_sleep`只有`[s2idle]`，没有deep。按[Linux休眠文档](https://docs.kernel.org/admin-guide/pm/sleep-states.html)，这里写mem选择的是s2idle，不能把结果称为深度suspend-to-RAM。内核CONFIG_PM_DEBUG关闭，没有pm_test文件。本轮没有改配置、内核或RTC系统时间。

源码中NGD的system PM通过`pm_runtime_force_suspend/resume`进入runtime路径；Qualcomm common会给DPCM链设置ignore_suspend，ASoC核心会跳过对应PCM suspend。依据[设备PM文档](https://docs.kernel.org/driver-api/pm/types.html)核对回调阶段，使用独立trace instance `k177-pm`记录power suspend_resume、device_pm_callback_start/end和wake source事件。已有display/radio实例保持，本轮实例结束后删除。这里记录的是PM core调用完成，不能把外层callback成功当作每个内部runtime分支都执行的函数轨迹。

RTC日历与墙钟不同，直接读取RTC since_epoch后加秒数设置wakealarm，不设置日期/时间；先确认没有已有alarm，不覆盖其它闹钟。[五秒清醒闹钟测试](rtc-validation.json)实际5.576秒、IRQ新增1、alarm到期，wakeup已启用且保持。随后每例只发一次mem，15秒RTC闹钟负责自动唤醒。phase和当前boot身份先写入私人目录并fsync，后台worker独立于USB SSH，连接临时丢失时只观察原worker，没有重发休眠命令。

## 两个实机场景

| 场景 | 结果 |
| --- | --- |
| [空闲](suspend-idle-validation.json) | PCM关闭、功放关闭后进入；CLOCK_BOOTTIME与MONOTONIC差14.760秒，RTC IRQ+1，success+1/fail+0，mem写返回0，同boot、taint0、声卡仍在 |
| [桌面播放/录音运行](suspend-active-validation.json) | 普通用户paplay+parecord，前置确认两个PCM RUNNING、两个功放开启；实际休眠14.411秒，RTC IRQ+1，success+1/fail+0；播放/录音返回0、无feed错误，结束后PCM/功放关闭，mixer及sink/source volume/mute保持 |

活跃场景播放-36dBFS、12秒编码合成音。录音1702079帧、35.460秒；该样本长度不能单独证明休眠中连续拾音。[样本连续性分析](active-capture-continuity.json)最长精确零段19.69ms，没有十几秒全零段，也不能据此认定无丢样。[编码分析](active-code-analysis.json)在采样时间线16.5秒处检出完整12秒右声道序列，相关0.8799，支持原应用播放流恢复后的实际发声；没有独立墙钟对齐或校准声源来证明休眠中不停播、无丢样或无瞬态。

[最终回调收据](final-validation.json)每例捕获2392个callback_end，返回均0；card、WCD codec/MFD及NGD都有suspend/resume阶段记录。没有重启、重新probe或手工绑定来恢复声卡，MBHC/jack仍11次，属于176首启与此前10次有意重绑。

## 恢复后回归与当前状态

[启停/暂停](capture-stop-validation.json)在两次系统休眠之后再通过8次FE16/32/48kHz录音和3次真实PAUSED/RUNNING，trigger全0，underflow/overflow/Port Closed新增0。

[原生四例](dmic0-ucm177-low24-analysis.json)重新使用-24dBFS的997/1511Hz编码音与目标功放关闭参考，左右相关0.9106/0.9388，功放关闭对照差19.37/43.24dB；[用户paplay+parecord](desktop-acoustic-validation.json)左右相关0.9621/0.9738、对关闭参考差17.80/42.19dB。左右均检出、采样无削顶，音量/mute和路由控件保持。

[最终收据](final-validation.json)2811.49秒、taint0、系统success2/fail0；所列WARN/Oops/ASoC/NGD中断/读超时/bring-up和WCD端口错误均0。单Pulse CARD/alsa-card与HiFi(Mic,Speaker)，PCM关闭，功放72/72配平静音，17控件恢复，五路consumer各1、两个regmap与一个MCLK，NGD suspended；boot/logdump/persist、NV、770模块132、UCM173核验。报告中的codec2/MFD8/18旧句柄字段明确属于先前176，177没有重跑这些绑定。

非音频告警没有隐去：从本次kernel176启动累计USB HS-PHY not in L2为2、Wi-Fi invalid-frequency为71、authentication denied为2；最后wlan operstate up，USB SSH/SCP已恢复。这不是全系统日志零错误或完整USB/Wi-Fi休眠验收。本轮限于音频相关故障及短时系统返回；独立告警留给对应驱动继续核对。

## 证据与续作

[汇总](checkpoint-validation.json)、补充脚本及脱敏报告在本目录；完整身份、原始PM trace、日志和录音在`E:/edk2-samurai-out/kernel177/k177-all-private.tar.gz`与两个声学包，以及手机`/var/lib/samurai/k177*`。初次只读查询遇到pm_test缺失、PowerShell参数引号和BusyBox ps -p不支持，均不是休眠/驱动失败；实际两例各执行一次，阶段与计数持久保存。RTC alarm已清除，临时trace instance删除。

两次约15秒s2idle是新增实机证据，不代表重复长时PM、SSR、冷启动、音质/瞬态或扬声器保护已经完成。用户暂无耳机，不重复问；实物3/4段插拔、自动profile、声道/耳麦/按钮仍待验。接着核对实际ADSP服务重启/SSR路径和跨启动恢复，再扩大PM时长/负载与正常听音范围。无需为已通过场景修改ignore_suspend或强制让busy资源停机；若新测试暴露故障，按实际结果修复。

部署/回退仍见[176](../kernel176/README.md)及[当前检查点](../../NEXT-SESSION.md)，操作边界见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。171人工双组滴声证据继续有效，本轮声学检测不是新的人工音质验收。
