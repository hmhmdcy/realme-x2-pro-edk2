# 38. 原生 RX：UEFI 对照与 USB 包边界（2026-10-09）

承接 sessions 35–37，用户要求持续寻找有效的原生多字节 RX 方法。
**仍未修复。新增关键证据：Linux 尚未运行时，同样的失败已在最小 UEFI 程序中复现。**
本轮只刷 logdump，两次分别为诊断入口和恢复基线；没有刷 boot、DTB 或其他分区，没有改内核。
当前已恢复 `logdump-rx33-console.img`，Linux 存活、Windows COM14 新 Ctrl-U 回执正常。

## 38.1 先核实设备与受理条件

开始检查 9501/9505 Status OK、COM14、CTL ID。临时终端尝试 `cat /proc/cmdline`，
只完整受理到 `cat /pro`，下一字符重试失败，未发送换行；**该命令没有执行**。
新 tty 回执证明 Linux 存活。后续 Ctrl-U 受理清除了残留半行。
本轮串口进程均 finally Close/Dispose，PyUSB 均 dispose_resources、usbmon 线程停止。
WSL 临时 shell 最后已退出；9505 已 detach 回 Windows，6-5 保留 Shared。

## 38.2 有新受理证据的主机设置对照

源码依据为 QUIC `693741a3b0448690402539ed0e6af067510e386f` 的 COM opcode 表和
com_api.cpp 中的 timeout 示例。`eud-usb-step.py` 新增一次性 setup 与 16 字节 IN 读长选项；
没有 set_configuration、USB reset 或自动卸载内核驱动。

| 序列 | 新证据 | 判定 |
|---|---|---|
| 基线 ABC，OUT `90 03 41 42 43` | 完整 5 字节 OUT 完成；新 BUFFERED 回执 `41 90 90` | 有效失败 |
| PORT_RESET `03`，随后 ABC | reset 的 1 字节和 ABC 的 5 字节均完整 OUT；新回执 `41 90 90` | 该序列未改善；无 reset 配置读回 |
| RX_TIMEOUT `02 ff ff 00 00`，随后 DEFG | setup 和 3 次完整 DEFG OUT 完成，0 IN、无回执 | 未确认受理，不能归为有效 payload 失败或证明 timeout 已应用 |
| PORT_RESET，随后 Ctrl-U | 新 `tty byte=15` | 恢复活性并清行 |

COM 设置命令没有协议响应；USB 完成不等于设备配置读回。timeout 的单位/端序没有额外规格验证，
这里仅复制公开示例，不扩展其语义。`--setup tx-timeout` 已提供工具选项，本轮没有执行。
两次准备失败也不能算硬件实验：usbmon 未加载导致监视器打不开；WSL 未运行导致 attach 拒绝。
各次重试均在修复前置条件后进行，不把零设备/零输出当 RX 结果。

## 38.3 Linux 之前的最小 UEFI 对照

独立应用源码见 `linux-port/uefi-rx-probe/`，不是固件组件。
在基线 FAT 中把原 `Image` 重命名为 `Kernel`，新增 16 KiB 应用为 `Image`。
打包时分别逐字节比较原内核、DTB 和应用，确认原内容未变。BDS 已安装的 DTB 表和原 LoadOptions
交给预先 LoadImage 成功的 `Kernel`；应用实验结束后 StartImage 接续启动。

实验在 TPL_HIGH_LEVEL 内进行，以阻止已知 EudLogDxe 定时 TX writer；无 Boot Services 调用、
分配或 PHY/时钟配置。按 STATUS1 pending、ID=90、预期 LEN=3/4 识别帧；连读指定次数 DAT，
完整存入本地数组后才写日志。反汇编核对 DAT 循环中只有 MmioRead32 和缓存写，没有 TX 或额外状态读取。
每阶段最多等待 25 秒；无数据也会继续启动原内核。这不排除不可见的安全固件或硬件内部行为。

抓包 `uefi-1` 的新 OUT/受理结果：

```text
63ms OUT ABC attempt=1 hex=90-03-41-42-43
RX38-UEFI RESULT ABC status=07070707 id=90909090 len=03030303
  words=41414141 41414141 41414141
165ms OUT DEFG attempt=1 hex=90-04-44-45-46-47
3172ms OUT DEFG attempt=2 hex=90-04-44-45-46-47
RX38-UEFI RESULT DEFG status=07070707 id=90909090 len=04040404
  words=44444444 44444444 44444444 44444444
RX38-UEFI CHAINLOAD original Kernel
```

首次 ready 标记在打开 COM 之前丢失，结果行完整捕获；主机先发 ABC，见 DEFG ready 后再发 DEFG。
源码工具后来把“打开即发 ABC”改为显式 `-StartAbc`，重跑此对照需传该开关。
全程重组 13,917 帧、0 stray、0 pending；这不证明每一完整 TX 帧都未丢失。
后续捕获 Linux #44、ttyEUD0、shell 启动；F1 新回执后确认 `62bc28a1 fastboot`。

结论：重复首字节在 Linux 接管前已存在，不能只归因于 Linux 调度、串口层或接管时关钟。
它没有证明 PHY 初始化、共同 MMIO/COM 硬件路径、host 路径或权限配置中的哪一个是根因。
session 36 已另证绕过 qcusbser 仍失败；这里没有物理 USB 分析仪，不能声称排除了所有 USB 层。

## 38.4 恢复基线后，合法满包与 ZLP 对照

再次只刷原 `logdump-rx33-console.img`。被动启动抓包 100 秒、0 OUT，
10,515 帧、0 stray、0 pending，确认原 Linux 回来；随后才执行两个独立 libusb 步骤：

| 完整 OUT | 完成与受理 | DAT 低字节 |
|---|---|---|
| `90 0e 41 42 … 4e`，16 字节，不附 ZLP | 两次 16 字节 OUT；第二次后新 len=14 回执 | `41` 后 13 个 `90` |
| `90 0e 61 62 … 6e`，16 字节，另一次 0 字节 OUT | 每次 16/0 字节完成；第二次后新 len=14 回执 | `61` 后 13 个 `90` |

这次 LEN=14 且完整 payload，区别于 session 33 的 LEN=5 后补零到 16 字节。
两项均未改善，不再原样重复。usbmon 记录虚拟 HCD 的 URB 提交/完成，**不是物理包或总线 ACK 证明**。
两个进程均 140 个重组帧、0 stray/pending、监视器线程关闭。
detach 后 Windows 单字符 Ctrl-U 首次受理，COM14 finally 关闭；没有额外 com-off/up。

## 38.5 新源码审查与更正

实际 SM8150 HS PHY 是 `qcom,sm8150-usb-hs-phy` → `phy-qcom-snps-femto-v2.c`。
session 37 参考的 qusb2_phy_init **不是本机匹配的驱动**，已在参考说明中更正。
实际 SNPS init 同样开启 regulator/clock、assert/deassert reset，并改 POR/UTMI override；
因此直接 phy_init 依然可能断开当前 EUD，需要先审接管和恢复，不能据此直接应用。
SM8150 DTS 只有 `ref` 时钟；驱动中的 cfg_ahb 是 optional，不能声称这个节点提供了 cfg_ahb 资源。

本轮完整启动日志确认实际 cmdline 含 clk_ignore_unused / pd_ignore_unused / regulator_ignore_unused。
约 25 秒仍有 QMP 等待 ldo5、DWC3 初始化延迟、HS PHY sync_state pending；随后 UFS 等继续 probe。
不能把早期延迟当永久失败，也不能用 QMP 供应者错误代替 HS PHY 的绑定状态。

继续搜索 AHB2PHY 的 wait-cycle 配置：Realme 原厂 dwc3-msm.c 有有条件的 TOP_CFG=0x11，
但同树 SM8150 USB DTS 未提供 ahb2phy_base/cfg_ahb，GCC 未暴露对应 cfg clock，仅有 reset ID。
所以没有把其他 SoC 的地址或该配置猜写到本机。公开 TestEUD 的 port_test.cpp 也只是沿用 QUIC 注释和
主机 0x81 数据发送，未提供设备侧推进实现或多字节成功证明。固定链接、哈希和源码范围见 reference/rx38。

## 38.6 产物、发布与下一步

| 产物 | SHA-256 |
|---|---|
| 基线 logdump-rx33-console.img（已恢复） | d5a36aa2152dd77735f1ea8861f05ad35cb7f714605d5c3cd9db106b6c5f8953 |
| logdump-rx38-uefi.img（仅诊断，不是修复） | f557ffc4526a7563bad4a0a8e66ddb03b46ec67b74ceeb6c6b56302c265c4322 |
| RxProbe.efi | e127b250c59afc0cf311d03e79c2cbeed0930e35ea50f23910241d0aa94d1177 |

外部完整证据在 `E:\edk2-samurai-out\rx38\`；发布的精选原始证据、manifest、源码审查说明见
`reference/rx38/`。应用可复现源码和主机工具已镜像进 EDK2 fork；内核源码及 Image 保持基线。

下一步需要 SM8150 COM 读指针/读副作用的专属证据或同 SoC 的成功对照。沿实际 SNPS PHY 和
同机型启动初始化继续审查，明确安全接管再试；不要重跑本轮 UEFI burst、合法满包/ZLP、reset 序列。
成功标准仍是新受理的 ABC=41 42 43、DEFG=44 45 46 47 且复测稳定；当前目标保持未完成。
