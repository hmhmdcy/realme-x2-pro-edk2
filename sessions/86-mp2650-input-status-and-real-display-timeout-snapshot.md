# Session86：MP2650 输入状态接入与真实显示超时快照

2026-10-10。用户允许实机测试，并要求充电安全。本轮比较固定的 Android R/cyborg
来源，读取输入 ADC，编译并部署只提供观测的 #86 内核。实机发现 ADC 一致性检查
导致供电事件为空，修正版 #87 已编译但未部署。随后显示监测捕获真实超时，优先保留
故障证据。全硬件目标仍 active，充电控制和显示稳定性均未验收。

当前手机 boot ID 为32bf2d8f-8dde-47dc-9b88-e87db9e95198，运行 #86。末次515.97秒
taint0、显示 frame_done_cnt=2、underrun=0；display 实例已停止，snapshot:count=0。
首次触发快照已保存，后续没有清空、重新武装或开关屏。MP2650 软件客户端已释放，
没有持久设备树节点。不能把候选 #87 或曾经成功读取的属性描述成当前完整可用接口。

## Android16 的方案与 Linux 参考范围

固定参考仍为[cyborg 内核](https://github.com/cyborgdc2000/kernel_realme_sm8150/tree/1f67e5dc641cf6477cfde07f0d35ddfbe0e5d1e1)
与[官方 Android R 内核](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/tree/23172a1571bd91156032cc9fef16284a82b63d2c)。
版本、设备树及差异见[session83](83-androidr-and-cyborg-charging-source-comparison.md)。
Android16 用户空间沿用 Android11 底包与厂商4.14充电栈。尚未确定用户当时安装包的
精确提交，因此当前分支是参考来源，不能等同于已安装固件。

| 层次 | 厂商方案 | Linux 可参考内容 |
|---|---|---|
| 电量计 | oplus_bq27541 的器件分支、读数与温补 | 身份守卫、寄存器和单位；保留已接入的 bq27xxx 标准读数 |
| 充电芯片 | oplus_mp2650 | 地址、单字节协议、输入 ADC；核对手册后逐项接入 |
| 充电策略 | oplus_charger | 温度区间、限流/电压/终止与错误路径；须结合实际输入预算和保护验证 |
| 快充 | VOOC/快充 MCU 协调 | 协议与失联处理；当前不刷 MCU、不切换快充路径 |

[MP2650 厂商驱动](https://github.com/cyborgdc2000/kernel_realme_sm8150/blob/1f67e5dc641cf6477cfde07f0d35ddfbe0e5d1e1/drivers/power/oppo/charger_ic/oplus_mp2650.c)
执行复位并关闭安全计时器，不能直接绑定其 probe。
[OPLUS 策略](https://github.com/cyborgdc2000/kernel_realme_sm8150/blob/1f67e5dc641cf6477cfde07f0d35ddfbe0e5d1e1/drivers/power/oppo/oplus_charger.c)
可作实现参考，但旧内核接口、参数继承和缺器件容错不能替代本机安全验收。
短路 IC、2719 保护映射和热敏校准仍见[session85](85-oem-chemistry-and-short-ic-observations.md)。

## 输入状态、ADC 与原厂宏的差异

[MPS 手册](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/)
REG13 的 ACOK 位1为高有效，CHG_STAT[3:2]=3表示充电终止。固定 cyborg 头文件
却定义 VIN_POWER_GOOD_YES=0、NO=BIT(1)，与手册相反。本轮纠正新驱动的解释，
没有证明这些宏在 Android 实际路径中造成错误。0x0f表示有效输入和充电终止；
不能再把它解释成“没有输入”。REG13 在较晚采样中曾为0x1f，最后回到0x0f，状态位
允许变化；其余11个配置观测值保持相同，不能把状态变化误判为配置被写入。

本轮核对的是厂商页面索引返回的表格文字。PDF 请求返回 HTML，原始响应与回执
留在私人目录；未完成 PDF 下载和页面视觉核验。没有把 HTML 当 PDF 或绕过验证。

固定输入工具仅读0b/13/1c/1d/1e/1f/13/0b，每次8个读事务，错误适配器在 I2C 前拒绝。
两次输入读数按 OEM 单位换算为4.525V、281.25/250mA，状态和0b前后相同。
它们不是外部校准值，分字节/分通道读也不保证同时采样。0b=0涉及电池供电模式 ADC
开关，不能据此断言有输入时 ADC 全部关闭。本轮没有启用 ADC。

USB 已配置为 high-speed；configfs MaxPower=100mA、bmAttributes=0x80，Type-C 和
usb_role 类无实例。描述符不是已核实的电源预算；输入 ADC 高于声明值需要后续协调
预算，不能直接提高 MaxPower 或充电限流。近99%电量、包电压约8.636V、约31.5°C、
平均电池电流接近0mA，不能据此证明充电慢。

## Linux 驱动的实机结果和修正版

本轮新增 mp2650_charger.c、Kconfig/Makefile 条目，CONFIG_CHARGER_MP2650=y。
仅提供 power_supply 的 ONLINE/STATUS/VOLTAGE_NOW/CURRENT_NOW；不设置属性、
配置、故障寄存器或硬件初始化。单字节高/低/高读取检查高字节一致，不使用 FORCE。
其一致性检查不能证明硬件锁存或消除所有采样跨越，读数仍需独立校准。

#86 经 logdump 单分区部署，保留 boot、FAT DTB、全部旧修复、initramfs 字节和身份。
通过软件 new_device 绑定 QUP1 地址5c，ONLINE=1与STATUS=Full分别连续5次成功；
电压4次有效4.500/4.525V、1次 EAGAIN，电流1次有效362.5mA、4次 EAGAIN。
三份 uevent 为空，完整接口测试失败。绑定期间旧工具正确拒绝 busy 地址；暂时释放
客户端后固定配置读数相同，再绑定，没有硬件配置写入。

本地 power_supply_sysfs.c 在遇到 EAGAIN 时终止整个事件。新修正版最多做3次高/低/高
尝试，I2C 错误立即返回；持续不一致或输入状态改变返回 ENODATA，让事件保留其它
有效属性。初次构建还修复了新版 power_supply_config 的 fwnode 接口差异，失败日志
和源码已保留。#87 编译无警告，配置、CPIO、DTB 和其它驱动保持，尚无实机验证。

| 产物 | SHA256 |
|---|---|
| 已部署 #86 Image | 7b1db95bb07be1a64b6c778d9369fffba26e0ac90d828a997507c4c13ab650f2 |
| 当前 logdump 全部64MiB | cf11644e32a138ff1319fe9e44529f1ef7b2a1907c1f8876c597f970a526d286 |
| 原 #85 回退 logdump | 60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b |
| 未部署 #87 Image | 97611f95a26866b54ba1330e370cb387fdbeff954ec1f56b4b8d13d1e6c4c4ee |
| 未部署 #87 logdump | da6a23adbc663bc6526ac6f77a6e789b0a096c91ddbdedcc96265084aee7b7f7 |
| boot 前缀6682624字节，未改 | 08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405 |

## 首次真正触发的显示快照

重新武装前已保存并审计 #85 尾部和 #86 启动跟踪。运行时2051KiB/CPU、nop/mono，
snapshot:count=1。后续空闲的 fbcon 更新出现超时，快照触发，末次计数2、下溢0。
monotonic 跟踪中的最后 kickoff 为378.330844，done callback为378.420888，
进入空闲/关中断开始378.484053，timeout事件为378.497165。完成到错误约76.277ms，
进入空闲到错误约13.112ms，值得核对 timer/帧忙标志与中断/空闲并发，不能据此确认根因。
pp_tx_done 的 new_count=1来自 atomic_add_unless 的布尔返回值，不能当剩余帧数。

首次快照15366545字节，SHA256=550d76908bd09bb280f57a5937fce7ec0101e4c167fed850b42834085e53f2f2。
后续捕获与它逐字节一致，主环形跟踪无 dropped/commit overrun；快照历史有环形覆盖，
不能称为整个空闲阶段的完整记录。没有新的光学确认，不能断言再次花屏。

部署前审计因超时失败。PowerShell 未自动以原生命令退出码停止后续序列；人工中断
发生在第二次 F1 的 OUT 提交之前，记录只有 claimed、原始接收0字节，没有 F1 回执
和第二次刷写。随后显式 detach，SSH 确认 boot ID 未变。最终部署脚本已加入停止保护，
不能复用旧守卫部署 #87。后续需要在新一轮先审阅真实故障，再制定部署步骤。

## 保存、边界与后续

input与5组启动/实机/故障捕获共6个归档、76个原始成员、70个设备生成哈希已校验。
完整配置、镜像、二进制、完整厂商源码/头文件、无效 PDF 响应保留私人目录。
公开大日志/跟踪为确定性 gzip，解压还原原字节；摘要和审计的 PASS 指证据完整性，
不是硬件可用验收。读事务包含寄存器选择写帧；无充电配置、解封/NVM/OTP/FET/OTG、
GPIO/快充路径或 MCU 写入。EUD com-up 只恢复既有 COM/VBUS 通道。

下一步先审阅显示故障前后的 timer、busy mask、IRQ 和 idle 状态，保留现有快照。
再验证 #87 的 ADC/事件处理和持久 DT 绑定；充电控制仍须输入预算、热敏校准、精确
2719保护/短路通信和主控失联安全实现。Wi-Fi/MPSS、音频、蜂窝、相机等14组硬件
尚未完成；继续全硬件目标，不能把状态观测当充电或快充验收。
