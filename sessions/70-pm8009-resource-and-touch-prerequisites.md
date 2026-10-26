# 70. PM8009 资源缺失影响范围与触摸前提（2026-10-10）

**新证据把 PM8009 警告下调为 P3；下一项应补齐原生硬件的探测前提。**
设备保存的 85404 字节 dmesg、5427 字节 command DB 和两份状态副本均通过设备
SHA256、gzip CRC 和长度核对。没有 panic/Oops，仍为 #60、同 boot_id、taint=0。
本轮没有修改内核/设备树、刷机、配置 gadget 或改变 EUD；证据见
[reference/kernel70](../reference/kernel70/README.md)。

## 70.1 当前模式、连接与日志完整性

打开 COM 前核实：9501/9500/9505 三节点均 OK，6-5/COM14 位于 Windows，
usbipd 为 Shared、未 Attached；已知 owner 扫描为空。实际 Git HEAD 为
218812bca7dacd7aaec7cd1aae74bec449433df4，工作区干净。
既有 Windows 原生终端取得新 K70F 回执，确认 Linux 7.3.0-rc6、boot_id
afbbf870-b998-43d8-ab3d-42b3c68c0122、taint=0；不是用 USB PID 推断系统模式。

每份副本先保存在手机 /tmp，再压缩和导出；完整起止标记、设备 SHA、gzip CRC
及手机 wc 字节数逐项通过。没有填补实时输出的残缺前缀。

| 文件 | 原始字节 | gzip 字节 | 校验结果 |
|---|---:|---:|---|
| /tmp/K70C：command DB | 5427 | 1089 | 通过 |
| /tmp/K70S：挂载、SPMI、调压器/I²C 状态 | 907 | 344 | 通过 |
| /tmp/K70L：完整当前 dmesg | 85404 | 17963 | 通过 |
| /tmp/K70P：PM8009 父设备/绑定、gadget/UDC | 333 | 196 | 通过 |

K70L gzip SHA256：`748fba37a71da75bd71868158b256ac9c12f149492666f7fc845f0dd705fa9f2`；
原文 SHA256：`d928e6a53e5f44ef7fe619bca20ed3d5e7bf481ac3c5ac7d8e04568145cc568a`。
它从0秒启动记录开始，有6个 Attached SCSI disk；未见 panic/Oops、旧 ioremap WARN
或 CPU7 2956800 的 Voltage update failed。它是当前 ring 的完整快照，不保证此前
没有被覆盖的更早记录。CPU7 高频负载仍未验收。

只用原有 eud-terminal.ps1，无 Reconnect、reset、com-up/off、掩码或节奏调整。
长文件沿用 session69 的 TailSeconds15 观察窗口，不改变发送/ACK 参数。
九个有界 owner 均 finally Close/Dispose、退出0；四次仅 startup Ctrl-U 重试一次，
数据帧均只发一次，保留 LEN2/F1。raw 解帧逐字节等于 text，stray/buffer 均0；
这些指标不证明 EUD 长期无损。关闭行来自工具 stdout/stderr，事件文件本身不含关闭行。

## 70.2 PM8009：资源缺失，但未找到供电消费者

当前 dmesg 仍有 `ldo2: could not find RPMh address for resource ldof2`。
实际 qcom-rpmh-regulator.c 在资源地址为0时返回 -ENODEV；probe 随即退出，后面的
ldo5/ldo6 不会继续注册。K70P 确认父设备存在而 driver 链接不存在，符合这个路径。

内建 cmd-db 驱动已有只读 debugfs 导出。临时挂载 debugfs 后读取 /cmd-db，
在同一 shell 子进程的 EXIT trap 中卸载；K70S 独立确认最终无 debugfs 挂载。
没有直接访问或写入 MMIO/SPMI 寄存器、调压器使能或电压。
dump 与查找函数使用相同的 slave 终止规则，导出包含139条记录、135个唯一 ID，
没有 ldof*/smpf*。不是简单给资源改名或换 PM8009-1 compatible 就能补上的地址。

实际使用的94803字节固件 DTB SHA 为
4641207124f1276f00749132d118ba73c3fdeaef24aeac8b2b1df017ef5dea9a，与 session68 一致。
对整个 DTB 的 phandle 和所有 -supply 属性解析后，PM8009 子节点没有供电消费者。
该组来自继承的 sm8150-mtp.dts，pmic-id=f，包含 ldo2/5/6。

[Realme 官方源码](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-regulator.dtsi)
和2026-10-05保存的本机 Android live DT 同样保留 smpf2/ldof2/5/6；旧 live DT 的
这些节点也是 available，但没有 -supply 引用。旧 Android dmesg 从457秒开始，
不能以其中没有启动报错证明它曾成功探测。资源表也不能证明物理 PM8009 不存在。

结论是：当前这组未注册的调压器没有已发现的 DT 供电依赖，尚无证据说明它导致
触摸、面板或其他硬件掉电。下调为 P3，保留配置和原始警告，不删除节点静音。
这只是 DT 供电引用审查，不代替原理图或所有固件消费者审查。

## 70.3 触摸：尚未进入正常探测

当前 CONFIG_I2C=y、I2C_CHARDEV=y，但 I2C_QCOM_GENI=m，RMI4_CORE 未启用；
实际 initramfs 没有加载 GENI 模块，K70S 没有 /sys/class/i2c-adapter。
实际 DTB 的 i2c17@c80000 为 disabled，也没有原生 RMI4 触摸节点。
因此不能把当前没有触摸设备理解成已经发生的 RMI4 probe 失败。

本机旧 live DT 和原厂19781树一致指向 S3706、I²C17/0xc80000、地址0x20、
TLMM IRQ122/reset54、PM8150 L17 供电，以及 PM8150L GPIO5 的1.8V使能。
`vdd_2v8_volt` 实际值是3000000，名称中的2v8不是可直接使用的电压约束；
各 GPIO 原始 flags 也须按原厂驱动的使用方式解释，不能机械翻译。
上游 RMI4 binding/Kconfig 已存证，尚未验证 S3706 的 RMI 查询、供电时序或输入事件。

下一步先审查 GENI/GPI DMA、QUP wrapper、GPIO/供电和 RMI4 查询依赖，再决定
最小配置/本机 DTS 增量；不移植另一机型的引脚、电压或固件。任何 DTS 变动仍须
更新实际固件 DTB，FAT-only 不会生效。既有 F1、回退和 boot/logdump 范围继续适用。

## 70.4 处理优先级与 rootfs

| 优先级 | 当前证据 | 下一步 |
|---|---|---|
| P1 | 普通 USB gadget 仍为空，UDC not attached；触摸的驱动/总线/DT 前提未启用 | 审查普通 USB 功能路径和本机触摸依赖，逐项小步实现与验收 |
| P2 | RPMh 不支持读回 -95 共120条；QMP data-lanes 和 aux_bridge -ENODEV | 区分固件读回限制、继承的 USB3/DP 图与本机原生面板接线 |
| P3 | PM8009 F 资源缺失且当前没有 DT supply 消费者 | 保留影响边界，暂不以删除节点消除警告 |
| P3 | PSCI PC mode=-3、无 KASLR seed、init tail EINVAL | 保留既有证据；后续用户态成功，不是 panic 证据 |

电池/充电、触摸、原生面板、GPU、Wi-Fi及USB实际流量仍未证明可用，目标保持进行中。

只读检查原有 logdump-k67-usb.img：64 MiB FAT 中 Image=30185984字节，
DTB=94803字节，空闲36737024字节（约35.04 MiB），镜像 SHA 未变。
这是保留镜像的容量证据，不是重新读取手机文件系统或GPT。
它只支持继续评估极小只读 rootfs 文件，不保证完整 pmOS、图形栈或持久更新空间。
保留 Android/全部数据时仍没有已确认的大空闲分区；boot 是引导用途，userdata/cache/
system/vendor/odm 等不在写入授权内。详见 ROOTFS-PRESERVE-ANDROID.md。

## 70.5 纠错、保留与交接

原厂19781目录实际是 arch/arm64/boot/dts/19781，最初误加 qcom 前缀的检索无匹配，
不能当成 PMIC 节点缺失。离线属性解码曾把部分全零前缀整数误判为字符串，已修正
为按原始 cells 解码并重生成报告；原始 tar、DTB和抓取未改。

最终三节点 OK、COM14 Windows/Shared/未Attached、无已知 Windows/WSL owner，
原驱动/终端/eudtool/回退和实际 Image/config/init/EUD/earlycon 哈希不变。
TOP_CFG0x11、整帧 payload、RX53 console/IRQ、F1、两种终端、RX48回退保留。
本轮 F1 未触发，无内核修复部署、刷机或 Android/data/GPT 写入；只推 fork/master。
下一轮从本机原生硬件前提继续，不重复 EUD passing、reset、延时或驱动实验。
