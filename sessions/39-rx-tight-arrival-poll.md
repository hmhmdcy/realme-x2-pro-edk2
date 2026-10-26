# 39. 接收窗口假设：UEFI 紧轮询仍重复首字节（2026-10-09）

承接 session 38，继续寻找有效原生多字节 RX。**本轮仍未修复。**
只改变接收帧到达前的轮询间隔：从 UEFI 的 1 ms 延迟改为无延迟循环。
帧内仍连读 DAT、完整缓存后输出，高 TPL 排除已知固件 TX 定时器；没有设置 PHY/时钟/中断寄存器。
没有改 Linux、boot 固件、DTB 或主机 payload。

## 39.1 为什么不是重跑旧的字节间延时

厂商 eud.c 在 RX 中断中读帧，现有 Linux 用 20 ms 轮询；session 38 UEFI 对照每轮检查间隔 1 ms。
此前调整的是首字节之后的读间隔，并未量化到达检测间隔。
本轮检验“轮询太迟，错过接收窗口”的候选解释。公开 RX_TIMEOUT 示例没有单位/默认值规格，
因此不声称存在特定时限，也不把它当已知硬件要求。

回看 session 31，0x81/82/83 的 22 帧已未改变设备闩锁；TestEUD 的 0x81 示例不是新发现的成功实现。
没有据此又重跑同样的 EE ID 实验，也没有把 COM_TX_ID 猜作 EE enable bitmask。

## 39.2 构建与读法

独立应用仍预载原 `\Kernel`，继承原 LoadOptions/DTB，在两次最多 25 秒的阶段结束后接续启动。
当前 `linux-port/uefi-rx-probe/` 为 RX39 版本；RX38 的原应用源码固定在 fork 提交 703469c。
新应用无 1 ms delay，记录接收前两次循环入口计数之差 `gap_ns`。
它不是 USB 到达至首次 DAT 的端到端延迟，也没有与主机时钟同步。
反汇编核对：空闲循环无 delay 调用；DAT 循环没有 TX、计时或状态读取，计时换算只在整帧缓存后进行。

打包时原内核、DTB、应用均逐字节比对；只刷诊断 logdump，再恢复基线。

| 产物 | SHA-256 |
|---|---|
| logdump-rx39-uefi.img | d72b6b20d51ad6a661a291b2a607b69abd01bcfd381fbcdf851368ba570a8185 |
| RxProbe.efi | 901fc75a3e3ddbd6962cdae3b80a88f8a804ccd7ccd936b6d371731b466acbec |
| 恢复目标 rx33-console | d5a36aa2152dd77735f1ea8861f05ad35cb7f714605d5c3cd9db106b6c5f8953 |

## 39.3 新受理结果

```text
63ms OUT ABC attempt=1 hex=90-03-41-42-43
RX39-UEFI RESULT ABC gap_ns=625 status=07070707 id=90909090 len=03030303
  words=41414141 41414141 41414141
174ms OUT DEFG attempt=1 hex=90-04-44-45-46-47
3186ms OUT DEFG attempt=2 hex=90-04-44-45-46-47
RX39-UEFI RESULT DEFG gap_ns=572 status=07070707 id=90909090 len=04040404
  words=44444444 44444444 44444444 44444444
RX39-UEFI CHAINLOAD original Kernel
```

结果依旧 AAA/DDDD，不是连续 payload。“检测间隔为毫秒”的候选解释在这个路径没有得到支持，
不再以缩短轮询/加 RX IRQ 为由重复硬件循环；这不等于证明全部 IRQ 硬件语义均无关。
Linux 接续启动日志已捕获，仍为原 #44 内核；最终恢复状态与精选证据见 reference/rx39。
接续日志另有早期 `generic_ioremap_prot` WARNING，调用栈为 eud_setup，session 38 同样存在。
本地 mm/ioremap.c:23 检查 slab_is_available，现有 eud_earlycon.c 早期调用 ioremap 映射 CSR_EN；
它发生在上述 UEFI RX 结果之后，不解释 pre-Linux AAA/DDDD。本轮记录此已有问题，未改早期 console。

## 39.4 恢复过程与最终设备状态

UEFI 抓包共 13,927 帧，0 stray/pending，脚本 finally 关闭并 Dispose COM14。
之后 Windows F1 三次 OUT 没有回执，一次 com-off/up 后的 Ctrl-U 也没有回执。
实验与恢复之间约有两小时墙钟间隔；这些空抓包不能证明 F1 受理、Linux 崩溃，
也不能单独归因为紧轮询。

改用 libusb/WSL 并先发送 PORT_RESET 后，首个 Ctrl-U 获得新回执（uptime 7462.528660）。
同时改变主机路径和 reset，恢复原因没有被隔离。随后 libusb F1 有新回执
`[7481.852656] eud: reboot2 bootloader requested`；读端返回 EIO（errno 5），工具退出 1，
finally 仍释放接口。另行枚举确认 62bc28a1 fastboot 与 18d1:d00d，才恢复基线。
不能把 EIO 本身或工具退出码当成功依据，也没有泛化忽略所有 I/O 错误。

只刷回 `logdump-rx33-console.img`，reboot 前先起被动抓包：10,179 帧、0 stray/pending、0 OUT，
原 #44 Linux、ttyEUD0、initramfs shell 仍启动。结束关闭后，另开一次 Windows 单步串口，
第一个 `[90 01 15]` 得到新 `eud: tty byte=15` 回执，停止重发并 finally 关闭/Dispose。
最新状态（03:20 UTC）：9501/9505 均 OK，COM14 已关闭，6-5 Shared、未 Attached。
基线镜像、Linux Image 和 eud.c 的 SHA-256 与 session 33 一致；本轮未改内核、DTB、boot。
原有内核工作区修改及 .bak 文件全部保留。

## 39.5 本轮搜索的新来源与限制

再次搜索 COM_RX_DAT/EUD_COM_RX、SM8150/AHB2PHY、公开 boot 硬件定义和 U-Boot 实现。
厂商树仍是 ID/LEN/DAT 连读，未找到已验证的同 SoC 多字节成功对照。

* [SM7150 U-Boot 补丁](https://github.com/djStolen/u-boot_sm7150-mainline_withEUD/blob/0ee5e4cec1993b520d9a7bf82b1b2b6fa0a63b54/uboot-patch-enable-eud-fastboot.patch)
  只提前返回、跳过 fastboot USB cleanup；无 COM RX 实现，不能当串口修复。
* [SDM670Pkg/HalusbHWIO.h](https://github.com/Rivko/android-firmware-qti-sdm670/blob/20bb8ae36c93fc16bbadda0e0a83f930c0c8a271/boot_images/QcomPkg/SDM670Pkg/Include/HalusbHWIO.h)
  文件头实际写的是 SDM845 Napali v2。其 AHB2PHY SWMAN 基址相对 offset 为 0xe000，
  TOP_CFG 在该资源 +0x10，分别有 read/write wait states；不是 EUD mode manager +0x10。
  这不建立 SM8150 地址或当前配置，不能据此写 0x88e1010 或跨 SoC 地址。
* [SM8250/HalusbHWIO.h](https://github.com/SwedMlite/BOOT.XF.3.3/blob/55ff7c1920ccf084951b2770d46ffcbe8917864f/QcomPkg/SocPkg/8250/Include/HalusbHWIO.h)
  文件头明确列出生成过滤：EUD 只包含 enable/attach/tuning 等字段，排除了 COM RX。
  未出现 COM_RX 不能证明硬件没有别的推进字段；跨 SoC base 布局也不能直接移植。

两份头文件全文保存在外部 `E:\edk2-samurai-out\rx39-sources\`，均与 GitHub blob SHA 校验一致；
固定链接、全文哈希和最小审查索引见 reference/rx39。没有运行下载的源码或加入猜测寄存器写入。

外部完整文件在 `E:\edk2-samurai-out\rx39\`。下一步仍需要 SM8150 COM 专属读副作用/完成握手
或已验证的同 SoC 对照；不能从本轮失败直接推导熔丝限制。成功标准仍是稳定 ABC/DEFG 全 payload。
