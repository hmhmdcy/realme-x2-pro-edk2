# 172：绑定 WCD934x 耳机检测，修正偏置电压和状态错误

2026-10-14。用户回家后要求重放；在171 boot/kernel168上重放左右编码音，用户确认“两组都听到，来自手机”。麦克风和对应功放关闭对照也通过。[人工听音](../kernel171/home-listening-validation.json)。随后继续原生音频目标，构建并部署kernel172、boot/logdump/DTB172，保留SD1/GPIO140与既有NGD/显示修复。耳机检测启动与未插入状态通过软件验证，插拔、耳机出声和耳麦采样仍未验收。

## 修复内容

原samurai machine没有注册jack或调用WCD934x的set_jack。新增一个卡级jack，RX与TX仍各自设置SLIM通道图，只对共享WCD组件绑定一次、设置9.6MHz MCLK和四个按键。ASoC为每个pin生成CARD控件，实际控件是`Headphone Jack`、`Mic Jack`；`Headset Jack`只是输入设备名称，不存在同名合并CARD控件。耳机插入报告控制Headphone端点及反向扬声器端点，麦克风报告控制Mic Jack和反向Handset Mic。新增AMIC2→Mic Jack/MIC BIAS2/MCLK设备树路由。[增量补丁](headset-detection.patch)

WCD旧set_jack第二次传同一个非空jack会停止MBHC；启动失败仍置started=true。修为同一jack幂等，活动期间更换jack返回EBUSY，只有成功启动才保存绑定，NULL停止一次并清状态。组件初始化失败与MBHC控件创建失败向上传播，后者释放已申请的MBHC资源。

旧parse_data在micbias设备树尚未解析时复制micb_mv，得到0；后续ADC阈值计算以它为除数。现在解析micbias后复制MIC_BIAS2电压，零阈值除数被拒绝，偏置寄存器写失败向上传播，正数“寄存器改变”返回仍算成功。公共MBHC按钮默认值改为500mV，与显式设备树微伏值除1000后的单位一致。本机现有按钮属性正常转换，未改其阈值。Class-H、过流保护、功放增益、校准与DSM配置均未改。

## 构建与软件验证

实际C函数提取后用硬件调用桩进行ASan/UBSan错误注入，覆盖失败启动、重复绑定、不同jack、停止、零偏置、解析失败、五个寄存器写失败、默认/显式阈值单位及RX/TX通道图保留。旧函数组合复现零偏置、错误started标志、重复绑定停止、默认单位四项缺陷。首个测试桩编译因宿主缺ENOTSUPP、未用桩和缩进失败，修正后通过；它不是完整内核或实物检测测试。[测试收据](host-tests-validation.json)

严格checkpatch首轮6处对齐、第二轮一处101列被拒绝，纯空白换行修正后0；三个修改音频对象W=1无告警，全内核只有原有EUD unused-function一条。首次DTB审计把本树`widgets`误写为`audio-widgets`，守卫拒绝；核对实际属性名后续跑审计，未重编或改变DTB。相对171只变`/sound/widgets`及`audio-routing`，SD1和显示源保持，.config不变。[源码](source-validation.json)、[内核](kernel-build-validation.json)

770个模块与132代码字节一致，两个重新构建模块仅build ID不同。完整UEFI构建相对171只有DTB模块变化，其余模块包括BDS字节一致；30条提示属于既有2类模板。Android header、shim、ramdisk、兼容DTB、分区尾部及FAT读回通过。[包审计](build-package-validation.json)

## 部署与新boot

重新核对仍在171 boot、kernel168，boot/logdump/persist完整哈希和NV通过。正常停机至全部DSP离线、桌面/DRM/功放关闭，prepare0→0。最后checker因上传名不匹配中断；现场已停止，补齐文件后通过，只续跑收据尾部，没有重复停机或切换。冻结F2FS、单次F1后刷boot/logdump172，F1后的USB EIO边界留存。[停止](shutdown-validation.json)、[部署](deployment-validation.json)

新boot运行`#172 SMP PREEMPT Wed Oct 14 13:42:53 CST 2026`，release仍带k132；按uname-v识别。MBHC与machine绑定各一次，micbias=2700mV，Headphone/Mic CARD控件均off。首个runtime collector误查不存在的合并Headset CARD控件失败；保留初始收据后仅修核验项，同boot重采通过，没有修改或重复启动硬件。boot/logdump/persist完整读回、NV、WCD0x411、桌面、SD1/GPIO140、taint0及关键故障0。[首启](runtime-validation.json)

## 扬声器回归与剩余工作

相同−24dBFS编码音/算法/门槛，四个原生用例DMIC0检出左/右相关性0.922/0.999，功放开关频段差18.10/40.01dB。两次桌面PulseAudio播放检出0.917/0.926，对照同boot原生amp-off高15.83/38.87dB；没有改变sink总体volume/mute或功放增益。首0.5秒后满幅削波0。桌面分析首个调用漏传archive参数，只读分析重跑后通过；播放没有重复。[声学回归](acoustic-validation.json)、[桌面](desktop-acoustic-validation.json)

最终同boot383.76秒，taint0、关键DMA/TX/queue/resume/WARN/Oops/GPU故障0；PCM关闭、双功放关闭静音、各5次启停配平，17个控件恢复、NGD suspended，模块132/NV通过。5条WCD TX underflow均紧随capture stop，仍待定位，不宣称完整日志零错误。[最终现场](final-validation.json)

本輪UCM132保持，只有Speaker与DMIC0设备，耳机端点检测出现不等于桌面耳机路由已完成。下一步按本机AIF1 RX0/1及OEM AMIC2接线补充Headphones/HeadsetMic，并实际验证插拔、左右耳机与耳麦录音。已核对[ALSA上游WCD934x配置入口](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/Qualcomm/sdm845/HiFi-MM1.conf)使用Headphone Jack；其中其他设备的AIF2 RX2/3和AMIC MUX0不能直接套到本机。音乐/人声音质、首次瞬态、断电冷启动、休眠与长稳仍开放，goal active。

回退优先配套完整boot171/logdump171：已取得用户出声确认和三DMIC/桌面证据。更早boot164/logdump168为SD0版本。全部原始录音、XML、身份、日志和镜像留私人`E:/edk2-samurai-out/kernel172/`；公开只留自写脚本、补丁和脱敏收据。
