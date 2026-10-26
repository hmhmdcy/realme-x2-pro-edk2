# 173：部署耳机 UCM 路由，验证桌面播放与录音

2026-10-14。延续音频goal，上一轮已部署WCD耳机检测kernel172并取得171测试音人工确认。本轮保持kernel/boot/logdump/DTB172、modules/software132及Mesa149，新增UCM173与路由助手。用户回复“暂时没有耳机”，本轮只做软件和扬声器/内置麦克风验证，未模拟CARD插入状态。

## 路由与持久源码

[UCM](../../linux-port/ucm2/conf.d/Realme_X2_Pro/HiFi.conf)定义Speaker、Headphones、Mic、Headset。耳机使用本机AIF1 PB→SLIM RX0/1→RX INT1/2→HPHL/R；耳麦按原厂AMIC2/ADC2，经AMIC MUX1、ADC MUX1 AMIC、DEC1/TX1复用现有单声道AIF1捕获FE。没有套用其他SDM845设备的AIF2 RX2/3、AMIC MUX0或INT0耳听筒路径。

[路由助手](../../linux-port/scripts/samurai-audio-route.py)在HiFi初始化时读取真实Headphone/Mic CARD控件，先选择一个播放BE与一个单声道TX槽，满足Pulse先打开FE、后启用UCM设备的顺序。设备启用更新DPCM mixer；设备停用暂留路由供下一次FE打开，verb关闭才清后端，PCM关闭仍会关闭功放。助手不写jack端点、模拟音量或Class-H模式；用control节点flock串行操作、预校验枚举、错误后恢复旧路由，重复选中不重启流。

JackControl分别关联Headphone Jack和Mic Jack，JackHWMute对应kernel172已实现的反向Speaker/Handset端点。实际插入后的硬件静音、分类和Pulse配置切换仍待实测。当前有by-path input链接，但没有可核验的by-id JackDev，未编造该值。[ALSA字段语义](https://www.alsa-project.org/alsa-doc/alsa-lib/group__ucm.html)、[UCM命令及设备配置](https://www.alsa-project.org/alsa-doc/alsa-lib/group__ucm__conf.html)

源码可用[安装器](../../linux-port/scripts/install-audio-ucm.py)装入明确的live/staged rootfs，只更改两个板级UCM文件与/usr/libexec/samurai-audio-route。Linux临时根中实际核对三个文件哈希、755/644权限和目录通行权限；kernel172六文件源码、Image与DTB哈希保持。[当前源码及暂存安装](current-source-validation.json)、[清单](source-validation.json)

## 已验证的软件范围

实际助手导入后8种路由/初始化状态、63个写入后失败注入及错误枚举检查通过；回退恢复原路由，播放BE最多一个、CAP启用时TX槽恰一个；pin/音量/Class-H不被写。[宿主事务测试](host-tests-validation.json)

临时UCM经普通用户执行，Speaker+Mic、Headphones+Mic、Headphones+Headset的枚举与寄存器读回通过，重复启用、四设备依次选择、inactive清后端及恢复原控件通过；全程PCM关闭，功放状态无变化，关键故障增量0。[UCM实接口测试](ucm-test-validation.json)

新配置已部署。PulseAudio仍生成四种设备对组合profile；去掉显式ConflictingDevice并没有把它合为一个profile，不能沿用先前的设想。当前只有一个CARD/alsa-card模块、一个Speaker sink与Mic source，激活HiFi (Mic, Speaker)，Headphones/Headset在CARD上均not available。桌面和Pulse PID保持，重建声卡时恢复了用户软件volume/mute。[部署](deployment-validation.json)

另用全零立体声发送至Headphones路由，与Headset路由录音同时运行，48k/S16/单声道144000帧成功，双PCM RUNNING、扬声器功放关闭且状态不变。CARD保持未插入、端点未强开；这里只证明数字PCM流程，不证明HPHL/R实际出声或AMIC2拾音。[静音PCM](silent-headset-pcm-validation.json)

## 扬声器与真正的桌面双向回归

四个新原生编码音/对应功放关闭对照：左/右相关性0.921/0.999，功放开关频段差20.00/41.22dB，门槛/分析函数沿用既有测试，功放增益不变。[原生](dmic0-ucm173-low24-analysis.json)

本轮桌面捕获使用普通用户parecord Mic source，与用户paplay Speaker sink同时工作，未用root arecord替代桌面录音，也未强制mixer端点。左/右录得286079/288000帧，相关性0.901/0.936，相对同boot本轮原生amp-off参考高18.66/40.17dB；sink/source软件volume/mute前后相同。录音以计划6秒INT停止，首0.5秒后满幅削波0。该数字幅度与单频检测不等于声压、音乐/人声音质或校准频响。[桌面双向](desktop-acoustic-validation.json)、[汇总](acoustic-validation.json)

## 失败、回退和策略记录

首个控件采集误假定Mic Jack Switch存在而失败；实际只有其CARD检测与DAPM端点，改用真实控件继续，只读阶段未改硬件。初版alsaucm -b -在本机没有执行输入命令，空输出和路由读回守卫揭出，改为真实命令文件。V1库以ENOENT拒绝冲突设备，首次检查误要求错误文本包含conflict，修核验后该阶段通过；V2已移除显式冲突列表，验证最终单BE/单TX选择。

首次音频发现模块重载漏卸载它留下的alsa-card子模块，导致重复CARD，数量守卫拒收。文件先恢复UCM132，但两次重载累计三个子模块，不能称完整回退；专门检查并移除三子模块后恢复唯一声卡、原用户音量，再部署V2。[单声卡恢复](single-card-recovery-validation.json)。最终重载工具同时核对子模块并卸载，Phosh/Pulse进程未重启。所有失败快照保留私人档案。

现场开始时module-switch-on-port-available未加载，系统default.pa已含其启动命令。补载当前策略模块并确认仍是Speaker+Mic；系统文件未修改。它的重启加载和真实插入事件行为尚未证明，仍需后续验证。最终工具记录策略存在，未把成功load-module当成实际插拔通过。

## 最终现场与下一步

同kernel172 boot，最终4583.58秒，UCM/助手哈希通过，单声卡、策略模块存在、未插入状态正确；taint0，DMA/TX/queue/resume/WARN/Oops/GPU计数0。PCM关闭、双功放关闭静音、各22次启停配平，17个原控件恢复、NGD suspended，模块132/NV通过。8条WCD TX underflow均紧随capture stop，未修复或隐藏。[最终](final-validation.json)

下一步定位停止underflow、首次瞬态，验证正常人声/音乐、重启后UCM与策略、休眠/冷启动和长稳。有耳机后完成3/4段识别、插拔/自动配置切换、左右听音、耳麦采样及按钮。用户已说明暂缺耳机，不重复追问。全音频goal保持active。

内核回退仍优先配套boot171/logdump171；软件UCM132原件在手机/var/lib/samurai/k173-source和私人k173-all-private.tar.gz。软件回退要恢复两个UCM文件并重载唯一音频子模块/发现模块，不把只恢复文件叫完整运行时回退。原始录音、身份、日志、镜像等只保存在私人E:/edk2-samurai-out/kernel173/。
