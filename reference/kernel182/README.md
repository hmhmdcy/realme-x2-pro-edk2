# 182：活跃桌面录音中的单次 ADSP 自动恢复

2026-10-14。继续使用已部署的kernel181/logdump181，本轮没有内核、UCM或固件改动。一次活跃桌面录音中的合成remoteproc崩溃报告触发自动恢复，原parecord客户端重新连接到重建的Mic source，并检出恢复后的右声道编码音。完整音频目标仍active。

## 实机证据与边界

[测试代码](test-active-crash.py)在确认#181、同boot、taint0、ADSP running、recovery enabled、coredump默认disabled后，仅向debugfs crash写入一次0。此入口调用rproc_report_crash，模拟MMU故障报告；不是令DSP固件产生真实watchdog故障。没有手动stop/start或重绑补救。

注入时Mic PCM RUNNING。监视器观察到card和两regmap移除、重建，两个旧debugfs name FD均EIO；五个电源consumer恢复。PulseAudio自动恢复HiFi(Mic,Speaker)，同一个source-output从旧Mic连接到新Mic，原parecord仍存活。17项测试窗口故障计数0，预期crash report/handler/recovery各1；worker没有Traceback，监视器没有异常。

[分析](active-crash-validation.json)沿用181完全相同的检测函数和门槛：原录音中的1511Hz编码相关性0.96958，编码开关频段差40.71dB，相对同boot181原生目标功放关闭参考高20.40dB，无削顶。source volume/mute相同。这是一次恢复后桌面播放到原录音客户端的声学验证，未另做桌面amp-off对照，也不证明故障期间连续无损录音或音乐质量。

时间线名义25ms采样：观察到的card/map资源缺口0.3615秒，资源重现后2.2069秒首次观察到capture RUNNING。原始report的recovery_latency_seconds=7.9271实际计时截止于测试音播放和尾部等待之后，字段误名；原件未改，派生摘要更名为crash_to_after_playback_and_wait_elapsed_seconds。不能把7.9271当作纯恢复延迟；原录音样本位置也不是连续墙钟时间。

## 最终状态

[最终收据](final-validation.json)：2514.86秒同boot、taint0、ADSP running、单card/alsa-card与HiFi。两PCM关闭、双功放18/18配平且failed0、关闭静音；16个保存的mixer控件恢复，五consumer各1、两regmap/一MCLK、main cache-only=N，NGD suspended。NV/persist/boot/logdump/770模块132核验。当前日志仍从0秒起且含#181 banner，所列20项故障全boot0；预期合成崩溃日志及既有可选SoundWire child未找到of_node信息保留，不宣称整机所有错误清零。

私人日志/录音/身份在E:/edk2-samurai-out/kernel182与手机/var/lib/samurai/k182*；原始crash包SHA256 f12d2003913ec7c407355d14da493e03099a2f1467d9e77b74556be779440bd0。181原生amp-off参考同boot已逐字比较，原178/180失败继续保留。

下一步补活跃播放中的恢复、当前181的较长重复PM和跨启动，再推进音乐/人声、瞬态和保护。耳机/耳麦/按钮待有实物，用户暂无耳机，不重复询问。真实DSP watchdog故障和所有SSR路径尚未验收。

## 相关机型研究如何用于本机

本轮重新搜索并读取[OnePlus 7T Pro扬声器移植实测记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-05-mainline616-internal-speakers.md)：从原厂格式/时钟/通道约定出发，建立功放生命周期、UCM2桌面路由，并用麦克风独立测量分声道输出。该机功放TFA9874，本机MAX98937，寄存器与增益不能照搬。

此前[171研究](../kernel171/README.md)已固定并校验一加原始补丁与Realme19781原厂设备树，依据本机SD1掩码及GPIO140纠正原SD0/GPIO139错误，随后左右声学检出并获得用户双组滴声确认。研究不是仅列出机型名称，已经形成实机修复。没有找到另一套已核验的完整X2 Pro原生音频补丁可直接替换当前实现。
