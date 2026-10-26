# 171：扬声器从SD0改为板上SD1，三麦克风及桌面检出编码音

2026-10-14。继续音频goal，用户询问是否搜索一加/Realme相关机型。本轮补查实际OnePlus 7T Pro主线音频补丁，并从固定Realme原厂提交核对本机19781 overlay、MI2S掩码解释和引脚。原厂quaternary RX=2→SD1/GPIO140，原生此前选<0>/GPIO139→SD0。OnePlus实际补丁独立选SD1，但功放TFA9874不同；保留本机MAX98937配置。[来源、修复与全部证据](../reference/kernel171/README.md)

只改samurai DTS的sd-lines及两处active/sleep pins，重建DTB/固件，主Image仍168。三个生命周期源文件、.config、15个显示源文件保持，DTB树只三处音频属性变化。固件代码逐字节保持，三模块仅版本标记更新，BDS164交接逻辑保留。第一次严格模块守卫拒绝元数据差异，核对后按精确版本字符串替换审计通过；36条固件提示仍为4类既有模板。首份补丁头检查失败后修正，最终checkpatch0。

使用170同boot新preflash身份正常停机，DMA prepare0→0、taint0、全部DSP离线、GUI/DRM/功放关闭。冻结F2FS，单次F1后仅刷boot/logdump171。F1 receipt后的USB EIO边界保留，没有重复切换。新boot运行SD1/GPIO140，boot/logdump/persist真实读回、NV、声卡/WCD0x411和桌面通过，仍kernel168。

用170相同编码音、固定检测门槛及目标功放关闭对照共20个原生完整用例：DMIC0 −48/−36检出右；−24检出左右，相关性0.952/0.993，关闭功放对照差19.51/40.33dB。DMIC1/2 −24也均检出左右，非零噪声已不再作为拾音依据。原SD0相同−24条件左右均失败，修正后通过支持线路错误解释。功放增益/保护未变，首0.5秒后满幅削波0。

再从正常PulseAudio Speaker sink经用户paplay播放，DMIC0检出左/右相关性0.894/0.943，引用同boot原生amp-off对照差18.30/39.32dB。sink总体volume/mute保持，私有WAV通过stdin供给，没有开放文件权限。[闭环汇总](../reference/kernel171/acoustic-validation.json)、[桌面闭环](../reference/kernel171/desktop-acoustic-validation.json)

最终同新boot、taint0、关键DMA/TX/queue/resume/WARN/Oops/GPU计数0，模块132/NV通过，PCM关闭、功放关闭静音、13次启停配平、17个mixer控件恢复、NGD suspended，无测试PCM进程。14条WCD underflow均紧随capture stop，仍待分析。[最终现场](../reference/kernel171/final-validation.json)

用户170旧SD0时期可能听到电脑风扇，不能改写成人工成功；本轮听音问题尚待答。当前双声道编码音及三路拾音已取得闭环证据，音乐/人声质量、首次瞬态、耳机、声学保护、断电冷启动、休眠、长期可靠性仍开放，goal active。完整回退优先保留boot164/logdump168配套原件。


后续同boot回家重放：用户确认“两组都听到，来自手机”。左右编码相关性0.964/0.955，功放开关对照差18.02/40.80dB，新增关键故障0、mixer恢复、功放关闭。首次取得双组测试音的人工来源确认；音乐/人声质量和耳机仍未验。[人工确认](../reference/kernel171/home-listening-validation.json)。听音时172新耳机源码尚未部署；SD1可用回退优先完整boot171/logdump171。
