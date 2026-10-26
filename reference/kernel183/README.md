# 183：离线流清理修复、活跃播放恢复及当前内核两次 s2idle

2026-10-15。内核183已部署。181在活跃播放和录音中的合成ADSP故障报告测试出现WCD STOP −ENOTCONN及三条ASoC错误；本轮新增传输状态检查与明确的软件流清理，修复后完整复测通过。当前内核两次s2idle和醒后原生/桌面左右声学验证通过，完整音频goal仍active。

## 真实失败与修复语义

[修复前实机](playback-crash-before-fix-validation.json)使用kernel181：一次合成remoteproc MMU故障报告发生时，原paplay/parecord均运行。两客户端自动恢复，但旧WCD TX1 STOP返回−107，产生三条ASoC错误。右编码音通过旧参考；左相关性虽高，未超过旧原生amp-off参考门槛，保留失败结果。随后同boot的新原生四例左右通过，1373个mixer值与181原生前快照相同；未凭幅度差假定具体硬件增益故障。

NGD先关闭QMI，再报告设备离线。旧WCD设备在间隙内仍可能显示UP，而寄存器和流消息已无法传输。[补丁](offline-stream-abort.patch)为controller新增非睡眠的is_online回调，核心检查设备状态、地址有效性及传输可用性；NGD检查DOWN、registered和QMI handle。正常ASLEEP仍在线，可以走runtime resume。

新增slim_stream_abort仅在已离线时释放本地ports并清零num_ports，不发总线消息、不表示硬件接受了STOP；在线拒绝EBUSY。WCD STOP在已离线或清理途中确认ENOTCONN且离线时使用该路径；在线清理和已有错误处理保持，独立的首个真实错误不被覆盖。START/RESUME/PAUSE_RELEASE离线时返回ENOTCONN。查询是状态快照，不是事务或寿命锁，调用者仍串行化prepare/trigger。

六个文件改动、12个tracked源。现有函数签名保持，增加两个导出函数与内部controller回调。PDR180、MFD181、MBHC172、machine175及寄存器缓存策略保持，IF没有改成缓存。没有扩大既有disable/unprepare逐port错误处理范围，不把本轮测试说成全部传输异常已修复。

## host、构建及部署

[实际函数测试](host-tests-validation.json)：九个实际核心/NGD/stream/codec函数，69场景与六负对照，ASan/UBSan通过。包括设备UP但QMI消失、地址失效、ASLEEP仍在线、离线无总线操作且释放资源、在线abort拒绝、真实NACK/其它首错误保持、检查后掉线与重新上线。传输/regmap/allocator/start-enable为薄host适配，实机验证独立保留。

[构建审计](build-package-validation.json)：四个改变对象W=1无警告，全编译仅既有eud_earlycon未用函数提示，FAT精确回读与fsck通过。770模块相同，仅两个既有模块build-id差异，保留runtime模块132；15显示源163、DTB/boot172、UCM173、Mesa149保持。首次checkpatch因本地未签名补丁缺Signed-off-by失败，原日志保留；使用no-signoff做本地风格检查后0错/0警告，不伪造签名。

重新取181身份，取回完整私人证据后停机/冻结，单次已验证Linux RESTART2进入bootloader，按新查身份/产品/分区几何只刷logdump183。一次SCP连接中断导致尾部不完整：确认仍181、quiesce未开始后保留半件，再取回并核验完整SHA；没有因此重复启动切换。[新启动](runtime-validation.json)78.44秒#183、taint0，card/桌面自动恢复、所列16项错误0，boot/logdump/persist/NV核验。boot172和回退logdump181原件保留。

## 恢复后的原客户端与匹配功放对照

183首轮注入已消除ASoC错误，但测试在单侧amp-off处误要求逻辑muted=1而失败。原记录保留。MAX37 DAPM关闭时实际GLOBAL=0、AMP使能bit0=0、powered=0；共享DAI仍运行时逻辑muted可以为0。这是测试假设错误，未修改功放驱动或硬件参数。

确认首轮结束且现场正常后，修正判据并在独立v2目录复测一次。[完整v2](playback-crash-fixed-validation.json)：注入时两PCM RUNNING；声卡/两map重建、两旧name FD EIO，原source-output和sink-input自动连接到新Mic/Speaker，无新客户端替换或手工重绑。原paplay最终0、原parecord按计划SIGINT130；18项测试窗口故障0，crash report/handler/recovery各1。注入到观察到两PCM再运行约3.690秒，包含状态查询开销。

同一恢复后的原录音/播放流完成左右阳性及对应功放关闭对照，实际寄存器使能位前后均检查；沿用181完全相同检测函数与0.75/6dB/8dB门槛。左右相关0.9119/0.9312，功放开关频段差20.48/40.37dB，两声道检出、无削顶。旧参考未被调门槛或重写；新对照匹配本次流状态。source/sink volume/mute及16个保存控件恢复。

## 当前183的两次 s2idle 与醒后回归

5秒RTC预检IRQ增加1；之后按RTC窗口保持USB/SSH安静。空闲45秒用例实际休眠45.330秒，活跃播放/录音90秒用例实际休眠87.039秒。每例success+1/fail+0、RTC IRQ+1、taint0、同boot、无手工重绑。2392/2210个device_pm_callback_end记录全部err0；两组所列音频故障增量0。[空闲](suspend-idle-validation.json)、[活跃](suspend-active-validation.json)

活跃原客户端正常结束、控件/音量恢复、PCM关闭/功放关闭。录音110.24秒样本序列不等于独立墙钟连续记录；[连续性记录](active-capture-continuity.json)保留零样本统计，不宣称休眠期间音频无损，也不将s2idle说成deep STR。

醒后[原生四例](dmic0-ucm183-low24-analysis.json)左右相关0.9809/0.9979、功放关闭差22.02/41.86dB；[用户会话桌面两例](desktop-acoustic-validation.json)0.9744/0.9967、相对同boot醒后原生amp-off参考20.72/40.84dB。均检出、无削顶、mixer/volume/mute恢复。桌面后回归不是独立桌面amp-off实验；前述crash v2才有原流匹配对照。

## 最终现场及仍开放的范围

[1472.87秒最终](final-validation.json)：#183同boottaint0、ADSP running、单card/alsa-card和HiFi(Mic,Speaker)，PCM关闭；左23/23、右22/22且failed0，功放关闭静音，16控件恢复。五consumer各1、两map/一MCLK、main cache-only=N、NGD suspended。所列20项全boot故障0，日志从0秒且保留#183 banner；本boot两次预期合成crash日志和原首轮脚本失败保留。NV/persist/boot/logdump/770模块132核验。

Image bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469；logdump e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358。私人镜像/录音/身份/日志在E:/edk2-samurai-out/kernel183及手机/var/lib/samurai/k183*，不公开原音频。历史178/180失败及本轮181三条ASoC失败保留。

当前有可用的扬声器出声、拾音和桌面闭环，171用户两组滴声确认有效。耳机/耳麦/按钮仍待实物；真实固件watchdog、更多跨启动/较长可靠性、音乐/人声、瞬态与保护尚未验收，不把本轮合成报告、两次PM和编码音扩大成完整音频完成。用户暂无耳机，不重复问。其它系统Wi-Fi/USB/蓝牙等历史问题按硬件清单保留。
