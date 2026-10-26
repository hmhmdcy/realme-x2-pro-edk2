# 71. 本机S3706触摸接入（2026-10-10）

**本轮实际实现、构建并只刷boot/logdump，把原生触摸带进主线驱动。**
完整54413字节设备保存dmesg通过SHA256/gzip CRC和长度校验；新内核#61、
boot_id=a31c1158-fbca-4515-83ac-1a3b40ee808e、taint=0。识别到Synaptics
S3706A、fw id3078696，F01/F12绑定，/dev/input/event2注册；真实事件采样另列。
证据入口reference/kernel71；功能清单linux-port/docs/HARDWARE-STATUS.md。

## 71.1 接线、代码和构建

使用Realme官方9668fcdc6ec15be7a10d66f7b93c347829e0fdb6的19781 DTS、S3706
驱动/common power/header，与此前保存的本机Android live DT对照。I²C17@c80000、
地址0x20、TLMM IRQ122/reset54；PM8150 L17实际要求3.0V，PM8150L GPIO5
由原厂驱动raw HIGH开启1.8V。因此不能机械使用vendor GPIO flag1作为低有效使能。
IRQ的0x2008由vendor传给request_threaded_irq：LEVEL_LOW与ONESHOT；主线DTS
使用IRQ_TYPE_LEVEL_LOW。GPIO驱动强度、偏置和PMIC power-source按本机证据。

原生配置内建GENI I²C、GPI DMA、RMI4 CORE/I²C/F12，F34重刷支持关闭。启用
QUP2、GPI DMA2、I²C17，不改原来的DMA掩码、不启其它SE/SPI。新增fixed VIO、
触摸节点及三组引脚状态；L17约束为3.0V。采用generic syna,rmi4-i2c，设备实际
报告S3706A，未复制OnePlus S3706B的引脚、电压或quirk。

[Roman Vivchar提出的复位GPIO补丁](https://lists.openwall.net/linux-kernel/2026/09/12/719)
用于补齐当前rmi_i2c对reset-gpios的缺失；本地增加devres失败清理时assert reset、
硬件reset后invalidate page cache和GPIO错误输出。只在存在reset GPIO时使用
10–20ms上电等待，然后释放reset，再按本机原厂80ms等待；F01软件reset也等待80ms。
这是触摸芯片的原厂上电时序，与EUD reset/延时试验无关。休眠/恢复逻辑已实现，
尚未做硬件休眠恢复验收，不能以编译通过代替。

补丁0007/0008、kernel71-builtins.config及实际DTS同步到linux-port。反向dry-run
通过；make Image/DTB无新增warning/error，Image30317056字节。实际initramfs、
eud.c/earlycon及UEFI EUD/F1核心源码哈希未变，没有运行旧build-image.sh。

DTB校验解析phandle为目标路径，排除仅编号重排：新增6个触摸/供电/引脚节点；
既有节点仅3个status与L17的min/max改变，其他属性全相同。固件实际嵌入该DTB；
101个模块集合不变，除DTB和三个版本字符串外可执行字节不变，兼容DTB/BootShim
及bootargs保留。FAT中Image/DTB提取后逐字节匹配源码构建产物。

## 71.2 手动飞轮、失败记录和回退

开始前COM14位于Windows，三节点OK、Shared/未Attached，无已知owner；新回执
确认旧#60/boot_id/taint0。只读sde11的PARTNAME=boot，前6682624字节手机保存、
压缩导出校验，与session68 boot-k68-opp.img哈希相同，作为即刻boot回退。
logdump-k67-usb.img与RX48/RX53回退未动。

Windows既有step一次F1无回执，独立fastboot枚举为空，未刷机。随后使用既有
WSL step一次F1，无setup/reset/ZLP/参数改动；有新F1回执，接着USB EIO，helper
finally dispose，launcher finally尝试detach（设备已离开），持久WSL shell退出。
独立fastboot枚举62bc28a1、product=msmnile，boot=96MiB/logdump=64MiB确认后，
仅写这两项，Writing均OKAY，再reboot。Android、userdata、GPT均未写。

| 产物 | 长度 | SHA256 |
|---|---:|---|
| boot-k71-touch.img | 6680576 | a4f4b75a52ec13a9b0b5cd4ebd678daa9a9dafd36548ce82ce4602a1fbcc15db |
| logdump-k71-touch.img | 67108864 | f6837573c908eddad7a2d8d0ab494c259ff99a9a5b85878e3b6747d40b2d3fb8 |
| Image #61 | 30317056 | 9d1639ee02d6844225feed1969e90b0a87aec2559b855085e94ca5862efbef66 |
| firmware DTB | 95933 | 5f184f24c3fe23723b01639f7462c6be9ed7238505b50102794de064bd6f4849 |

重启后一次正常com-up恢复COM枚举，未com-off/reset/换Windows驱动。首个原生
终端处于earlycon启动期，Ctrl-U没有回执，10次有界同步后退出1，**数据命令未发**；
完整原始抓取保留。一个不发输入的30秒既有reader随后接收启动尾行。用户态就绪后
新原生owner成功保存/导出完整日志，不把前述残缺实时数据当故障。

## 71.3 校验日志与实际结果

手机/tmp/K71L/dmesg先保存，原文54413字节，gzip12775字节，设备SHA256
f9b67d52ee3e65e7d24954c7c8228ccf24d837c14eb9f7d8a858d3dc53920444。
导出严格base64、gzip CRC、SHA和手机wc长度全通过。没有填字，手机副本重启前保留。

在30.712s transport注册；30.892s F01识别S3706A/fw3078696；31.204s输入设备注册。
独立1855字节facts gzip545字节校验通过，F01/F12/physical/I²C四个driver链接存在，
event2是touch，INPUT_PROP_DIRECT；GPIO122 Level IRQ及F12子中断都有真实计数。
并保留六个UFS盘、用户态、EUD与taint0，无panic/Oops/新WARN或触摸probe失败。

既有PM8009/RPMh读回-95/QMP/aux_bridge/PSCI/KASLR/init tail警告按前两轮边界
保留；本轮没有删除节点静音。原生面板、GPU、USB真实功能及其它硬件不随触摸注册
而自动宣称可用。普通USB仍没有gadget函数配置，用户Android EUD/ADB互斥观测保留。

## 71.4 输入事件验收、收尾与后续

在手机上用现有timeout/cat只读event2，120秒有界采样保存到/tmp/K71T/events，
用户已确认完成点按、滑动、双指操作。采样已自然结束，ps未发现capture进程；event-errors为空。
306744字节/12781个24字节ARM64 input_event记录，gzip43740字节，手机与主机
SHA256/gzip CRC/长度全通过，原文SHA为
13930452eea095ae66fb47b278c513bceafa7d2583a09be94fafc00f11d9bfcf。

970个SYN_REPORT，241个tracking contact均有release，末尾active=0；223个contact
发生移动，BTN_TOUCH按下/抬起各69次。记录中最多同时5个contact，553帧有两个及
以上触点；x146–1047/y572–2224，均在1080×2400配置内，活动跨度30.239秒。
因此基本输入通路（点按/移动/释放/多点）已验证，不只是input设备注册。用户确认
操作不是严格的触点数量/边缘标定：不能把最多5个记录触点自动称为五指精度验收，
也尚未做长时间/休眠恢复/方向及边缘校准。数字是实际事件记录，不是补出的EUD文字。

所有串口/USB使用原有工具，finally Close/Dispose/detach，fastboot进程也finally
Dispose；每步只一个连接owner。结束设备状态、校验报告及fork/master提交见本轮
证据。没有新EUD实验、Windows驱动/掩码/发送节奏变化；TOP_CFG0x11、整帧、RX53
console/IRQ、F1和两种终端保留。rootfs仍只有保留logdump镜像内少量空间，未安装
postmarketOS、未写userdata。下一项按实际输入结果推进普通USB传输/SSH和原生显示。

操作后的第二份完整dmesg为66932字节（gzip14630字节），设备SHA
b8b0c8cda262f07c06ad4a18124f62da5f97f23e70c98b7a26f533afca662d50，
导出校验全通过；没有新panic/Oops/WARN回溯或触摸I²C错误。后续956字节facts
也通过校验，仍#61/相同boot_id/taint0，三个policy最高频率1785600/2419200/2956800、
27个温度读数、六个UFS盘和a600000.usb UDC保留。initial-console warning与#60
同样存在，不能因首次看到就称为新故障。最终COM14 Windows/Shared/未Attached，
三节点OK、无已知owner，原Windows驱动/工具和回退哈希不变。

直接交接见[NEXT-SESSION](../NEXT-SESSION.md)，短提示词见
[NEXT-SESSION-PROMPT](../NEXT-SESSION-PROMPT.md)。
