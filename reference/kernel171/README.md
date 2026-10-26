# 171：参考 OnePlus/Realme 原厂链路，修正扬声器 SD1 并检出编码音

2026-10-14。用户要求继续原生Linux音频修复，并询问是否参考一加/Realme相关机型。本轮补查了OnePlus 7/7T系列的主线适配资料，取得OnePlus 7T Pro实际音频补丁；同时从固定Realme GPL提交读取本机19781设备树和原厂MI2S驱动。修正并部署后，左右扬声器编码音均被三路DMIC检出，桌面PulseAudio两路播放也检出。用户随后回家重听并确认两组滴声来自手机；耳机与完整音质/可靠性仍未验收。

## 找到的配置错误与来源

本机[原厂音频overlay](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi)的quaternary RX掩码为2。原厂[MI2S头文件](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/audio-kernel/asoc/msm-dai-q6-v2.h)定义SD1为1<<1，驱动直接保存掩码并选AFE SD1；[原厂pinctrl](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-pinctrl.dtsi)把SD1配置在GPIO140。

原生qcom,sd-lines属性使用线号数组，驱动转换为BIT(index)。此前`<0>`和GPIO139选择SD0，所以“播放中137/138/139均为qua_mi2s”仍不足以证明选了板上连接的输出线。171改为`<1>`，active/sleep引脚由137/138/139改为137/138/140。[小补丁](speaker-sd1.patch)、[来源与语义核对](contract-validation.json)

独立对照的[OnePlus 7T Pro扬声器补丁](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0039-asoc-hotdog-enable-bounded-tfa9874-speaker-output.patch)同样选Quaternary RX SD1/GPIO140。该机使用TFA9874，本机是MAX98937；只参考线路选择，没有套用TFA寄存器、增益或其AMIC路由。源码固定提交、文件哈希见[OnePlus来源](hotdog-contract-provenance.json)、[Realme来源](oem-contract-provenance.json)，外部脚本没有执行。本轮检索没有找到可核验的另一套完整Realme X2 Pro原生音频修复。

麦克风方面另核对了原厂DMIC clock drive编码：值0代表原厂默认2mA，当前设置符合该值，没有凭常量名把它改为更强驱动。录音路由与本机私有mixer来源保持，不因一加AMIC4路径改变本机DMIC0/1/2。

## 构建、部署与守卫记录

仅重建DTB与固件，主Image和三个168生命周期源文件、.config、15个显示相关源文件均保持。DTB全树节点不变，只有三处音频属性变化：sd-lines及active/sleep pins。DTB编译无警告、补丁checkpatch0。[源码](source-current-validation.json)、[DTB](dtb-build-validation.json)

固件完整重建通过，审计验证shim、ramdisk、兼容DTB、Android header及分区尾部保持。第一版“只允许DTB模块变化”的守卫拒绝三处版本字符串变化；逐字节核对证明PlatformSmbiosDxe/BdsDxe/UiApp各仅7个UTF16字符由旧构建标记f23a9f8变为当前5c80582，其余代码/数据逐字节一致，BDS164面板交接逻辑保留。原件与首次拒绝脚本留私人目录。36条固件编译提示属于已知的4类模板，新增重链接模块也报告既有RWX/LTO提示，不称零提示构建。首次导出补丁头格式检查失败后补上描述和分隔符，最终checkpatch通过。[启动包审计](build-package-validation.json)

按当前170 boot新身份正常停止桌面/无线/全部remoteproc，DMA prepare从0保持0、taint0、DRM CRTC关闭、双功放关闭。F2FS冻结、单次F1后核对bootloader，刷boot171和logdump171；logdump只更新DTB，Image仍168。F1后USB读EIO/endpoint消失作为已收到receipt的重启边界保存，没有重复切换。[停止](shutdown-validation.json)、[部署读回](deployment-validation.json)

新boot与preflash不同，运行时SD1及137/138/140属性正确，boot/logdump/persist完整读回匹配、NV通过，声卡/WCD0x411与桌面正常、taint0、DMA/TX/queue/resume/WARN/Oops/GPU计数0。[首启](runtime-validation.json)

## 与原SD0的编码音对照

保持170相同载频、15槽编码、录音时长、功放关闭对照和检测门槛；分析函数AST逐字等同170已验证函数，没有调整判定门槛。原生ALSA五组/20个完整用例。功放增益、DSM/校准/保护配置不变。

| 输入/PCM峰值 | 左/右相关性 | 左/右功放开关频段差 | 检出 |
| --- | --- | --- | --- |
| 原SD0 DMIC0 −24dBFS，170 | 0.208 / 0.205 | −0.15 / +1.78dB | 均未检出 |
| SD1 DMIC0 −48dBFS | 0.214 / 0.948 | +0.74 / +15.32dB | 右 |
| SD1 DMIC0 −36dBFS | 0.718 / 0.934 | +8.82 / +28.27dB | 右；左未达相关性门槛 |
| SD1 DMIC0 −24dBFS | 0.952 / 0.993 | +19.51 / +40.33dB | 左右 |
| SD1 DMIC1 −24dBFS | 0.962 / 0.999 | +18.91 / +39.98dB | 左右 |
| SD1 DMIC2 −24dBFS | 0.927 / 0.929 | +32.39 / +16.77dB | 左右 |

−24dBFS下三路麦克风都录到左右编码音，并与目标功放关闭对照区分；去掉首0.5秒后满幅削波0。原SD0相同−24幅度两路均失败，修正后通过，支持本轮数据线错误与无测试音之间的因果解释。[汇总](acoustic-validation.json)、[170负对照](../kernel170/dmic0-low24-pins-analysis.json)

在正常用户会话的既有Speaker sink中用paplay分别送左右编码音；根用户仅通过标准输入供给生成样本，没有放宽私有文件权限。DMIC0录得桌面左/右相关性0.894/0.943，相对同boot原生目标功放关闭对照高18.30/39.32dB。sink总体volume/mute前后相同；单次stream unity，源PCM峰值−24dBFS。该对照引用此前原生amp-off样本，未称独立桌面amp-off实验。[桌面闭环](desktop-acoustic-validation.json)

数字幅度不代表校准声压，单频检出不证明音乐/人声质量、完整频响、声学保护或左右声压平衡。用户早前“可能是电脑风扇”属于170旧SD0测量；后续回家重放获得用户明确确认，见下段；旧反馈仍属于原SD0时期。

## 最终现场与待办

[最终现场](final-validation.json)：同本轮新boot，taint0、桌面存在；模块132及NV验证通过、关键DMA/TX/queue/resume/WARN/Oops/GPU计数0。PCM关闭、双功放关闭静音且13次启停配平、17个原mixer控件恢复、NGD suspended、无测试PCM进程。当前14条WCD TX underflow均紧随capture stop，继续作为停止链待分析，未隐藏或宣称修复。

当前组合为kernel168、boot171/logdump171、DTB171、software/modules132加Mesa149。原boot164与logdump168完整字节仍保留，恢复时必须配套；163只作更早历史回退。原始录音、日志、身份、镜像、原厂XML与外部源码留私人`E:/edk2-samurai-out/kernel171/`，公开保留自写代码/补丁及验证摘要。

后续推进现场听音/已知人声、首次瞬态、耳机插拔与麦克风、桌面录音、冷启动、休眠和长稳。保持全音频目标，不把本轮双扬声器编码音与三路采样通过等同完整音频修复。

## 用户回家后重放与人工确认

用户要求“我现在回到家了，请你再试一遍。”在同一171 boot/kernel168下重放−24dBFS、997/1511Hz两组编码音，各含对应功放关闭对照。左右相关性0.964/0.955，开关功放频段差18.02/40.80dB，关闭功放时相关性0.179/0.200；无新增WARN、DMA prepare、TX timeout或resume错误，mixer恢复、双功放关闭。用户回复：“两组都听到，来自手机。”由此新增有限的人工出声确认；不把它扩大成音乐/人声音质、耳机或完整可靠性验收。[人工收据](home-listening-validation.json)、[重放分析](dmic0-sd1-home24-analysis.json)

听音时172耳机检测源码仍在构建，手机没有部署该候选。171旧最终收据的13次启停与14条TX停止underflow属于重放前快照，不用于代表重放后的计数。当前可用SD1回退应优先保留完整boot171/logdump171配套原件；boot164/logdump168是更早SD0版本。
