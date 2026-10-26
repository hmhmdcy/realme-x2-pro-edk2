# session102：WCD934x接入与真实双MAX98937识别

2026-10-11，Linux #101已通过F1飞轮刷入boot/logdump。WCD934x实际ID major0x108/minor0x1，SLIM SAT收到master capability、控制器注册、codec绑定与原生AFE API7/ASM API2回复通过。ALSA仍无卡，播放/录音未验收。

本机实际左右功放是MAX98937，不是名称暗示的MAX98927：0x39和0x3a在0x01ff均返回0x00，在0x0600均返回0x43。最初原生MAX98927组件仅绑定，尚无声卡触发其component初始化；错误组件已正常解绑，两条复位线最终物理低。没有功放寄存器数据写入、没有PCM/声音输出；下一步先修正型号/驱动，再接机器声卡与DAI。

本次首次MPSS自动启动成功（up44.627426秒），Wi-Fi worker result0/WIFI_READY；checkpoint uptime 673.35秒，MPSS连续运行628.722574秒，未手动恢复。5GHz通过认证、DHCP、路由、DNS及577字节HTTP，网关3/3回复。仅一次暖启动；initramfs/无线代码不变，不能把这次成功归因于某个音频节点或宣布首轮fatal已修复。历史99–101失败、2.4GHz reason7/删除等待、冷启动/休眠/长期稳定保持待办；热点配置仍为私人临时测试配置，未内嵌自动连接。

蓝牙自动地址查询完成并保持未配对，用户关闭后控制器从/sys/class/bluetooth移除；本轮两次phase2/115200/chunk1/partial0/first00错误保留。振动ID97/standby/error0/starts0；用户无人测试，机械确认暂缓，没有待答问题或新增播放。

125文件checkpoint SHA `92fd414040265009df106e9a27236be6a7642ecc955f23f6211135cec13b51d8`。3个完整原包逐字节绑定、首个不完整collector保留、所有nested manifests纳入外层SHA清单；boot/logdump完整读回、运行FDT、原模块/服务、6个NV源及persist不变通过。两个DSP running、taint0，SMMU fault0，显示超时2：

```
[  376.480431] [drm:dpu_encoder_frame_done_timeout:2772] [dpu error]enc35 frame done timeout
[  570.079820] [drm:dpu_encoder_frame_done_timeout:2772] [dpu error]enc35 frame done timeout
```

显示故障独立保留，不能用本轮早期205秒timeout0覆盖当前两次或历史快照；本轮未打开单播删除跟踪，不能报“删除问题修复”。

原厂契约：只读原sde17 DTBO24MiB，源/副本/之后哈希相等；vendor以ro,noload/nosuid/nodev/noexec挂载并卸载，33私有文件归档通过。两份overlay中MTP board-id8匹配本机19781，SDX50M条目不采用。Tavil的元素地址、IRQ123、MCLK9.6MHz、reset143与五路S4 1.8V已核对；micbias2为2.7V，其它1.8V。原生MFD逻辑0→1与物理SYS_RST_N低→高对应ACTIVE_HIGH，原生MAX复位逻辑1→0对应ACTIVE_LOW。

QUP4 I2C实际寄存器0x890000、IRQ605、GPIO51/52；原厂SPI覆盖GPIO53/54不是I2C映射，GPIO54保持触屏复位。新增总线使adapter编号变化，当前功放1、振动2、触摸4；helper按唯一驱动+完整DT路径识别振动，不依赖旧1-005a。当前源DTS仍有MAX98927兼容候选，**实机已解绑，后续必须修正；不能直接重绑定后启用声卡/扬声器**。

SLIM资源由同机19781基树与固定SM8150公开参考互证：NGD0x171c0000/IRQ163、BAM0x17184000/IRQ164、SID0x1b46；采用原生BAM/NGD/PDR及严格SMMU映射，不扩大mask或旁路。仅新增9个DT节点、i2c4 status/100kHz与10个音频配置变化，initramfs/模块逐字节一致，其它已修改源码保持。真正EDK2重建只替换DTB FFS/压缩容器，compat/shim/ramdisk/执行代码/EUD/F1源保持。

参考源码为[Realme官方自定义功放实现](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/audio-kernel/asoc/codecs/max989xx/max98937.c)：虽然L/R compatible写max98927，presence会检查两个型号的只读版本地址，reset为低1ms→高→20ms。源码GPL2，头文件由该实现使用；不移植其全量配置/DSM或共享static生命周期逻辑。ID工具只在ALSA无卡、两native组件解绑、精确QUP4/TLMM身份后运行；普通I2C_SLAVE拒绝绑定地址，未用FORCE；仅两种版本寄存器的地址指针+读字节，GPIO只访问已核实的148/37，完成后复位低。

同SoC公开参考：[固定403b56 SM8150资源](https://github.com/ClearStaff/linux-sm8150-mainline-hotdog/blob/403b56c33e2ccdda25d90378970a5e5b928dee19/arch/arm64/boot/dts/qcom/sm8150.dtsi)及[WCD9340](https://github.com/ClearStaff/linux-sm8150-mainline-hotdog/blob/403b56c33e2ccdda25d90378970a5e5b928dee19/arch/arm64/boot/dts/qcom/sm8150-wcd9340.dtsi)。仅参考互证资源，未套用其它机型功放/card。

失败与边界：首个pin查询用了不存在的3400000路径；fresh guard后转正确3100000并另存。准备guard遗漏51/52时在修改前停止；补完整现场后继续。分块脚本旧#99 guard在任何分块前失败，改#100后新前缀完成。首次runtime collector的i2c-adapter class路径不存在，完整partial保留，重采新retry1包。首次网络流程已完成所有网络项，但关闭并移除BT后旧mgmt info超时；completion只归档并验证原网络结果与空HCI，无重启BT、无重测覆盖。GitHub API403，固定commit filtered Git取源码；无GPL头的build recipes触发guard后停止，限定C/H恢复并保留错误记录。初次FDT audit未列UEFI五个运行期chosen字段而失败，补字段值/descriptor版本与对齐校验，未放宽任何硬件节点差异。

80个2MiB备份块/8192Kbit/s全部SHA通过；并发只读SSH一次连接超时后成功重读，SCP未重放失败块。F1 receipt后EUD EIO/设备退出保留；独立fastboot身份/产品/96MiB boot/64MiB logdump验证后刷入。本次postflash EUD读取7.578秒后EIO，保存原raw/events/usbmon；完整内核证据来自NCM设备归档，不把截断EUD当完整日志。

Image `2672a9cdb0a90eb17be0e4b28f18a7fabf98ddaccb4f3b0043b166faa095a65e`；DTB `8255f6309eeb5e1885e1fd83b5fa46e857648798fd857f7a01c985412d87786a`；CPIO `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`；boot `94fcd45f23179c3ce1bae258e40b2d0fc8e072d8a257aa78a31c59d4e83cc4ff`；logdump `6c96d1de3a12c64e321450b686d0ed62fb75e34b203e2bded5e972246f40f75d`；完整boot读回 `4b3e76ae4c1ea5da894f219c20e5ca680785afd880dc2dd9fce09a3f914566ea`。

下一项：[MAX98937、声卡及全硬件交接](../reference/kernel102/next-session.md)。固件/OEM XML/库/原DTBO/原日志/身份/密码/镜像/二进制只在私人目录，无commit/push；Android/GPT/userdata/原NV/persist/SSH/显示快照/rootfs01保持，全硬件goal active。

最终9文件只读现场在uptime 949.51秒确认同一次#101启动：5GHz COMPLETED、MPSS/ADSP running、fatal0、taint0，WCD组件仍绑定，错功放组件解绑/两reset低，BT控制器移除、振动standby/starts0、NV/persist不变；显示超时2/BT phase2错误2，无新增fatal。原包SHA `b48f30cb3c22efed6339597b658d22e14c5a813750f2023c3d29d666a3621728`，私人final-status-validation.json；全硬件goal保持active。
