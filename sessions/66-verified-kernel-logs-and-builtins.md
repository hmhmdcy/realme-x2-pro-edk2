# Session 66 — 校验 Linux 日志，逐项修复内建依赖与 early mapping

2026-10-10（Asia/Shanghai）。先阅读 HANDOVER-NEXT、RX-CONSOLE、FLYWHEEL 和 sessions 41/42/65，保留 session 43 对旧解码误判的更正。本轮从既有工具采集日志，不增加 EUD 实验。用户允许缺字时推断线索，但修复依据区分完整校验证据、校验摘要和残缺抓取。

## 当前结果

三项小改动依次仅刷 logdump：OSM L3 内建使 CPU policy0/4/7 出现；ADC5/VADC_COMMON 内建使三路 PMIC 温度与三个 IIO 设备出现；earlycon CSR 改为 early_ioremap/early_iounmap 后早期 mm/ioremap.c 警告消失、taint=0。最后确认运行 #59、boot_id `87a7b341-6139-4afd-9ca2-3c0b20493e68`。CPU7 高档 OPP 和 USB deferred 仍在，未宣布硬件全部可用或 EUD 无损。

实际内核 `/home/cy122/x2pro-linux/linux`，实际 initramfs `/home/cy122/x2pro-linux/initramfs`。没有运行旧 build-image.sh。CPU/ADC 改动只改配置，未改 DTS 或 init。映射修复只改 `drivers/tty/serial/eud_earlycon.c` 的一次性 enable 映射，readl 完成写入后释放临时映射。

## 连接、采集与完整性

初始核对手机为 Linux，Windows 9500/9501/9505 OK、COM14、oem102.inf/2.1.3.5；usbipd 6-5 Shared/unattached，无串口或 libusb owner、无临时驱动日志/ETW。采集前先在设备 `/tmp/K66` 保存 dmesg 等文件，再压缩/base64 导出，保留设备长度/SHA256，不补字节。

| 证据 | 结果 |
|---|---|
| 初始完整 dmesg | 设备 59841 字节，直接收到 59474，少 367；SHA 不同，仅 `dmesg.partial.txt`，不能称完整日志。 |
| 初始完整 tar.gz | 设备 14558，收到 14516，gzip/哈希失败，保留失败副本。另一次 /dev/kmsg 归档仅 251 字节，源端记录长度/重定向限制也可能参与。 |
| 初始 facts / issues / config | 分别 676/1880/58 字节导出，SHA 通过；两个 gzip CRC 也通过。实际缺少 CPU provider 和 ADC5 模块可据此确认。 |
| CPU 修复完整 dmesg | 55416 字节，SHA `99064aed87571faebaa694e38dc7eca8e4f095e166ef129e48042a33cd0dbebb`；gzip 13085 字节，SHA `28c63e48f0fa1ea92dac04b7dfe91ef700701af1d5e0ce1942f6426dc39e6ed0`，CRC/长度/设备哈希全部通过。 |
| CPU / ADC 运行摘要 | 导出 762/603 字节，分别 SHA `ad63aa9e04d12945987d90297a1aadd363c9626a027269692a9d69053b861920` / `b64ea050d58f6c314a0ecbba0470c3a8e68994f58b62a8309ad58bc19feeea41`，CRC 通过。 |
| 映射修复运行摘要 | gzip 377 字节、解压 656 字节，SHA `16b92a35dd769ee8f2f58bf843288625cc5c8580d304aae736da76bc0e5ddc85`，CRC 通过。#59、taint=0、三个 policy 和 PMIC 温度仍在，保存的启动日志没有 WARNING 匹配。 |
| 映射修复完整 dmesg | 53866 字节，SHA `e29ff2301abbfef7de16bf78c81ab0216187a99dde4666e8ecf04be76755ed7d` 与设备副本一致；gzip 12510 字节，SHA `60f17e8a50125b8883fffe6479e542558f2565167f733bf308a55f3fed23fca9`，CRC 通过。六个 UFS LUN，未见 early ioremap 堆栈或 Kernel panic。 |

原始抓取、设备 export hash、CRC 核验和完整性边界统一在 [reference/kernel66](../reference/kernel66/README.md)。CPU/ADC/module 差异及 build/hashes 保留。raw/event/usbmon 确认宿主接到的正长度 IN 与 raw 一致，不能因此证明设备 TX 从不丢帧。

### 本轮操作错误和纠正

读取 GPT 时选择了前 34 个 4096 字节扇区，但本机 GPT first usable LBA=6，会越过表进入分区数据；随后在大段 base64 完成前过早发下一命令，使输出交错。该大抓取只本地保留、不入库、不作为当前 GPT 证据。仓库只保存 ADC 的有效摘要前缀和外部文件哈希/关闭状态。PTY Ctrl-C 终止的是主机 helper；finally 已释放。随后一次已回执的设备 Ctrl-C 未足以证明大输出被中断，不作该结论。

ADC 的保存 dmesg 是 54226 字节，SHA `edc816150500d9c789ceb8cade318d3c27628e9352cb3d45444e12ad38a05751`。重新接管后 #58/boot_id 未变、shell 正常；其完整 gzip 导出又未过 SHA（收到 12709，设备导出 SHA `ff4dd808fabd13b1f678e458a07226736c400843eed0b40a7ea9ca9a8bfba9fe`）。保留失败记录，ADC 修复依据为独立通过的运行摘要。

Windows 两次各单一 F1 均无新回执，一次独立 fastboot 查询超时；一次 WSL 初始 find 找到 0 个设备，未发 OUT。后来发现 WSL 会话已停止；保持普通 WSL shell 会话运行，再 attach 并独立 lsusb 核对 05c6:9505 后读取成功。用户同时确认手机屏幕仍是 Linux。这些无回执不判手机内核故障。

在同一已枚举的 WSL 会话中先关闭日志 owner，再用已有 eud-usb-step 发送一次 F1：新回执收到，随后重启断开报 EIO、finally dispose/监视线程退出。Windows 独立枚举 serial 62bc28a1、product msmnile 后才刷映射候选。没有参数调优、reset/setup/ZLP 或换驱动。

## 已刷镜像和构建边界

| 顺序 | logdump 镜像 SHA256 | 运行验证 |
|---|---|---|
| CPU #57 | `43b1c0799acac5878cb1541bfceb4237249db3a2ed5181b39c917e27344eb154` | 三策略、频率表；完整 dmesg 通过。 |
| ADC #58 | `38c35f641d48579b58c4aa9833efe0feafa7cabb0c32d99709e7fa731485c815` | 27 thermal zones，其中三 PMIC；三个 IIO，CPU 策略保留。 |
| map #59 | `c2658235953cbdb8820cfabe6bee9ab0526b8fceb6b69f71f029174690b16e4d` | 校验摘要确认 taint=0、早期警告消失。 |

均为 64 MiB，独立 fastboot 产品核对后 `flash logdump`/reboot 成功，未刷 boot。CPU/ADC 增量编译无警告；map 重编译报既有 `eud_wait_tx` 未使用警告，严格 gate 起初拒绝，随后明确确认仅这一已存在且函数内容未改的警告，保存诊断后打包。没有把编译成功说成零警告。

Windows earlycon 镜像源码原来落后于实际 #56 内核，缺少既有 paced TX 实现；本轮把实际源码同步回来。因此仓库 diff 除映射外显示历史 pacing 变化，但真实设备早期 TX 延时和函数路径没有新调整。映射增量与两份 before 源码在 reference/kernel66，可独立核对。TOP_CFG=0x11、整帧、RX53 console/IRQ、F1、原生/兼容终端和 RX48 回退保留；eud.c、DTB、init 和 Windows 驱动/实装终端不变。

## 余下异常和处理顺序

1. CPU7 的 2956800 kHz LUT 项没有对应主线 OPP，Voltage update/OPP 失败；初始频率是 invalid 表项 0xffffffff。已有三策略不代表全频率验证。先核对 SM8150AC/LUT/interconnect 带宽，暂不填猜测电压或带宽。
2. a600000.usb/dwc3 持续 deferred，QMP combo orientation/mode 和 aux bridge graph 提示；查板级 Type-C/提供者/DP 图，不干预 EUD PHY 或套用其他 SoC PHY。
3. MTP 继承 PM8009 regulators-2 ID=f/ldof2 在 cmd-db 缺资源。不是 PM8150L；需本机拓扑证据后再处理。
4. 电量、触摸、原生屏幕/GPU等尚未可用或验证。主线已有 ti,bq27541，先核对本板型号、总线地址；充电不按跨机型快充参数改。下游参考来自 realme 官方 19781 板号固定源码。
5. UFS 全部 LUN 已出现，启动早期 supplier defer 后可恢复；simpledrm/fb0 已用，不能因 simple-framebuffer 资源提示判黑屏。初始 console 打开失败后 initramfs shell 可用。RPMh -95 是已有不支持读取路径，不能混作旧 -110。PSCI PC mode -3、KASLR seed 和用户态 tail/devkmsg EINVAL 单独保留，优先低于持续未工作设备。

具体源码、权威仓库与下一步见 [source-audit](../reference/kernel66/source-audit.md)。当前校验日志没有证明 panic；pstore 空仅代表该次检查，不能证明所有历史启动都没 panic。

## rootfs 与发布

用户明确保留 Android 和全部数据。既有 GPT 备份 CRC 通过，但没有发现安全的大空闲 rootfs 分区；cache 未证明可重用，userdata 不覆盖或缩容。仅评估 logdump 内极小压缩 rootfs / 未来 USB 外置 / 经加密兼容性核实后的文件方案。详见 [ROOTFS-PRESERVE-ANDROID](../linux-port/docs/ROOTFS-PRESERVE-ANDROID.md)。本轮未实施这些方案。

变更仅提交并推 fork/master；证据包不含完整 ADC 大抓取、GPT 过读分区内容、Image 或镜像二进制。串口/USB owner 均在 finally 释放，USBIP 交还 Windows；最终设备和哈希状态另存 finish-state.json。早期 final-state.json 明确只是首次刷机前采集结束状态，不能当成本轮未刷机。
