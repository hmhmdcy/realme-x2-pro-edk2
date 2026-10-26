# 170：麦克风检测扬声器编码测试音，未检出可信信号

2026-10-14。用户询问是否可以利用麦克风验证音频，随后确认手机普通桌面放置、未插耳机；对听到的声音表示“有可能是电脑风扇……拿不准”。该反馈不计为手机发声通过。当前仍是169第二次独立启动的kernel168，boot164/logdump168、modules/software132、Mesa149保持。本阶段没有修改内核、固件、功放增益或保护配置。

## 方法与结果

[采集脚本](capture-acoustic.py)通过原生ALSA同时播放和录音，暂挂桌面音频后保存/恢复mixer。左声道997Hz、右声道1511Hz，各4秒刺激包含0.5秒静音、15个0.2秒编码槽及末尾静音。每组分别测左开、左关对照、右开、右关对照：目标功放关闭时仍向相同PCM声道送相同测试音，另一颗功放收到零样本。实时核对播放/录音RUNNING、目标功放global及powered，录音每次6秒/288000帧。耳机路由在测量时关闭，之后恢复。

[分析器](analyze-acoustic.py)用20ms Hann窗提取载频能量，按编码包络搜索PCM启动延迟，比较编码开/关槽以及目标功放开/关。预先门槛为相关性≥0.75、槽间功率差≥6dB、功放开/关功率差≥8dB。[合成验证](detector-validation.json)覆盖已知信号不同延迟及噪声/连续载波负对照；这只验证分析算法，不校准实体麦克风。

20个完整用例的播放/录音返回0、PCM运行、功放开关验证通过；去掉首0.5秒后满幅削波0。但五组的左右扬声器均未满足声学检测门槛：[汇总](acoustic-validation.json)。

| 输入与PCM峰值 | 左/右编码相关性 | 左/右功放开关目标频段差 | 判定 |
| --- | --- | --- | --- |
| DMIC0，−48dBFS | 0.197 / 0.164 | +1.26 / −1.34dB | 未检出 |
| DMIC0，−36dBFS | 0.174 / 0.163 | −0.23 / −0.29dB | 未检出 |
| DMIC2，−36dBFS | 0.098 / 0.146 | +0.90 / −2.02dB | 未检出 |
| DMIC1，−36dBFS | 0.110 / 0.144 | −1.60 / −1.42dB | 未检出 |
| DMIC0，−24dBFS | 0.208 / 0.205 | −0.15 / +1.78dB | 未检出 |

各组详细数据：[DMIC0 −48](dmic0-low48-r1-analysis.json)、[DMIC0 −36](dmic0-low36-analysis.json)、[DMIC2](dmic2-low36-analysis.json)、[DMIC1](dmic1-low36-pins-analysis.json)、[DMIC0 −24](dmic0-low24-pins-analysis.json)。dBFS是送入PCM的数字幅度，不代表声压级；本轮未做校准测量。

## 路由检查与实际限度

[运行时pinmux](live-i2s-pinmux-validation.json)确认GPIO137/138/139均为qua_mi2s，空闲时GPIO功能不能作为播放时错误的证据。另做一次4秒−36dBFS双声道播放，[现场路由](active-route-validation.json)显示MultiMedia1实际后台为Quaternary MI2S，48kHz/S16_LE/双声道，两个快照间hw_ptr前进43680帧；Q6ASM、QUAT mixer、AFE及两颗功放DAPM均On。MAX98937输入格式、时钟/采样率、左右接收/monomix、global/amp寄存器读回符合当前驱动及固定OEM来源配置，原始状态无报告故障。没有据此修改引脚或功放表。

这些是软件及寄存器证据，不能证明物理I2S时钟/数据波形、麦克风拾音或扬声器实际发声。检测失败也不能独立区分扬声器不发声、录音侧未正确拾音、声学耦合/灵敏度不足。下一步先用独立的已知声源验证麦克风，再用相同编码音与功放关闭对照定位输出；实体耳机插拔仍需现场配合。

## 失败、恢复与收尾

首次DMIC0 −48脚本把布尔值传给amixer，现场功放状态断言拒绝了该次结果；修正为整数0/1后用新目录重测。中断原件留私人目录，不算完整通过用例。−24组SCP中断留下不完整文件，保留后重新核对手机仍同一boot，再取完整档案；完整SHA256与手机一致。没有重复发送重启或刷写。

[最终现场](final-validation.json)：仍同169第二次boot，桌面存在、taint0；DMA prepare、TX timeout、queue full、resume failure、WARNING、Oops、GPU fault计数0；PCM关闭、双功放关闭静音、17次启停配平、无测试PCM进程，原先本轮mixer控件恢复，NGD suspended。另有22条WCD TX underflow日志，均紧随capture stop；单独保留为停止链待分析项，不把它们写成已修复或全部日志无错误。

原始录音、包络、日志、启动身份和传输不完整文件留`E:/edk2-samurai-out/kernel170/`及手机root专用目录；公开只保留自编脚本、补丁、统计与验证摘要。上一轮修复/回退/两次启动见[168](../kernel168/README.md)、[169](../kernel169/README.md)。
