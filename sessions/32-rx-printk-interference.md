# 32. RX 探针：前置 printk 改变读回，多字节推进仍待验证

> 来源：2026-10-08（Asia/Shanghai）真机逐步实验及跨机型源码对照。
> 用途：记录第三种探针结果，防止把未证的「payload 偏移 2」写进驱动。
> 关联：`RX-CONSOLE.md`、`FLYWHEEL.md`、`sessions/31-flywheel-f1-verified.md`。

## 32.1 已确认的事实

开始时 USB 枚举及 `fastboot devices` 都显示 `62bc28a1 fastboot`，因此先只执行
`fastboot reboot` 启动原有探针，没有先刷机。后续所有成功的 flash 都只有
`fastboot -s 62bc28a1 flash logdump ...`，没有刷 boot 或任何其他分区。
本轮没有修改 DTS / DTB / 固件。

1. 原探针发 `90 03 41 42 43`，得到 **90 90**，既不是 `41 42`，也不是 `90 03`：

       [   35.642246] eud: rx id=90 len=03 s1=07070707
       [   35.681849] eud: byte[1/2]=90 s1_after=06060606 poll=120
       [   35.754248] eud: byte[2/2]=90 s1_after=06060606 poll=121
       [   35.803438] eud: PROBE len=3: 90 90

   同一抓包又复现一次；帧重组 2666 帧，0 stray bytes。

2. 保留头部 printk、随后一次连续读 5 次 `0x14`（无中途状态查询/打印），全部
   `90909090`，读后状态 `06060606`。连续读取本身在这次实验没有让飞轮失效。

3. 去掉头部 printk，在读取结束后才打印缓存：

   - `90 04 44 45 46 47` → 连续 6 次读回全部 `44444444`；两次受理均如此。
   - 再发 `90 03 41 42 43` → 连续 5 次读回全部 `41414141`。
   - 这时读后状态仍是 `07070707`，与前置 printk 版不同。

   **首个数据字节确实是 payload 的首字节，证据不支持跳过两个头字节。**
   「前置 printk 干扰 RX」有改动前后的实测支持；具体硬件机制还没有证明，不能
   断言是共享 FIFO、总线回读锁存或某个时钟问题。

4. 无前置 printk、只读 `len` 次、读间 `udelay(200)`：`ABC` 仍得到 **41 41 41**，
   3 次受理均如此。短延时没有解决 FIFO 后续字节推进，不把它当已完成的修复。

## 32.2 主机与飞轮约束

每次实验独立执行短小的 `E:\edk2-samurai-out\eud-step.ps1`：先排空、每 3 s
重发同一帧、最多 5 次；串口从 Open 到实验结束都在 `try/finally` 中，最终
`Close()` 和 `Dispose()`。原始字节保存在 `.raw`，用 `decode-rx32.py` 连续重组
`90 len payload`，不能直接 grep 原始抓包。

发送时补上 `BaseStream.Flush()` 后，连续读取版出现可分析的 RX 结果。前面不带
Flush 的几组没有 RX 诊断，不能据此宣称手机 wedge，也不能单独证明 Flush 的因果性。

`90 02` 在各版均能自行回 fastboot；COM 的预期断开会让后续 Write 报
`The port is closed`，finally 仍正常运行。本轮没有发生 resource-in-use。

一次打包命令尚在运行就调用了 flash，fastboot 报镜像文件不存在，**没有刷写**。
随后 reboot 仍启动上一版；已利用这一启动复测 Flush。之后先等打包完成并核对
64 MiB 文件存在，再继续 flash。

## 32.3 同代与后续平台的源码对照（2026-10-08 检索）

以下是源码证据，**不代表在这些机型上做过 EUD 真机验证**。

| 来源 | RX 行为 | 对本项目的约束 |
|---|---|---|
| [OnePlus SM8150，Android P](https://raw.githubusercontent.com/OnePlusOSS/android_kernel_oneplus_sm8150/oneplus/SM8150_P_9.0/drivers/soc/qcom/eud.c) | UART_ID 0x90；RX_ID → RX_LEN → 在锁内 readl_relaxed(RX_DAT) len 次；不跳过头部 | 不应凭 0x90 首字节加入 offset 2 |
| [小米 9 cepheus-p-oss](https://raw.githubusercontent.com/MiCode/Xiaomi_Kernel_OpenSource/cepheus-p-oss/drivers/soc/qcom/eud.c) | 相同寄存器、UART_ID、14 字节上限和连续读取 | 不是已发现的机型特有原始帧格式 |
| [OnePlus SM8250，Android Q](https://raw.githubusercontent.com/OnePlusOSS/android_kernel_oneplus_sm8250/oneplus/SM8250_Q_10.0/drivers/soc/qcom/eud.c) | 同样读 len 次 0x14；计数后推送 tty flip buffer | 后续平台也未采用逐字节中断门控 |
| [当前主线 qcom_eud.c](https://raw.githubusercontent.com/torvalds/linux/master/drivers/usb/misc/qcom_eud.c) | EUD 启停、SCM、VBUS/safe-mode 与 USB role switch；没有 uart/tty RX 实现 | 不能拿它替换本项目的 console 驱动来解决 payload |
| [QUIC 主机 com_api.cpp](https://github.com/quic/eud/blob/main/src/com_api.cpp) | USB 帧格式 id、payload 长度、payload；芯片侧读 RX_DAT len 次 | USB 头部与 MMIO 数据寄存器的内容要分开判断 |

[OnePlus SM8150 DTS](https://raw.githubusercontent.com/OnePlusOSS/android_kernel_oneplus_sm8150/oneplus/SM8150_P_9.0/arch/arm64/boot/dts/qcom/sm8150.dtsi)
及 [MiCode SM8150 DTS](https://raw.githubusercontent.com/MiCode/Xiaomi_Kernel_OpenSource/cepheus-p-oss/arch/arm64/boot/dts/qcom/sm8150.dtsi)
均在 `0x88e0000` 描述 0x2000 窗口、SPI 492，所查节点没有 clock-vote 属性。
其他平台源码确实支持可选 `qcom,eud-clock-vote-req` / `eud_ahb2phy_clk`，但这不等于
本机缺少该 vote；当前还带 `clk_ignore_unused`，没有证据时不追加 DTS 时钟。

## 32.4 可复核产物（Windows 本地）

所有下列文件位于 `E:\edk2-samurai-out\`，镜像不纳入文档仓库：

| 文件 | 内容 |
|---|---|
| eud-before-rx32.c | 本轮修改前的 WSL eud.c 完整备份 |
| rx32-probe.raw / .txt | 用户指定的原探针，90 90 |
| rx32-burst-flush.raw / .txt | 前置 printk + 连续读取，5 个 90 |
| rx32-nolog-len4.raw / .txt | 无前置 printk，6 个 44 |
| rx32-nolog-ABC2.raw / .txt | 无前置 printk，5 个 41 |
| rx32-paced.raw / .txt | 200 μs 读间延时，3 个 41 |
| rx32-readb.raw / .txt | readb + 200 μs，仍为 41 41 41 |
| rx32-buffered.raw / .txt | 每 poll 一个字节、打印推迟到最后，41 90 90 |
| rx32-final-i/d/enter.raw / .txt | 最终单字符实现输入 id 并取得完整 shell 响应 |
| rx32-final-ABC.raw / .txt | 最终实现三次受理均为 41 90 90 |
| rx32-final-F1.raw | 最终实现自行返回 fastboot，COM 预期断开 |
| rx32-startup-ABC2.raw / .txt | vendor startup + 锁内 relaxed burst，仍为 41 41 41 |
| logdump-rx32-burst.img | Image SHA256 74e33dec83ba892e91f7a78a62242289d6b1940ef02da92627d5c08d10778aa6 |
| logdump-rx32-nolog.img | Image SHA256 fc0a1afe9f22a0eba99e2453a206117f76ea92640f831b8f6fdf7415fb18344a |
| logdump-rx32-paced.img | Image SHA256 3d0f4c512a4c209eef404df12ec781fbf7832cf140e7edc4ffee24f518b6f2e8 |

## 32.5 后续验证与最终实现

补充实验没有解决多字节推进：

| 改动 / 镜像 | ABC 的实际读回 | 处理 |
|---|---|---|
| readb + 200 μs 读间延时，logdump-rx32-readb.img | 41 41 41 | 撤回，保留 readl |
| 每 20 ms poll 一个字节、先缓存再打印，logdump-rx32-buffered.img | 41 90 90 | 保留为有界诊断，不送 tty |
| SM8150 vendor startup 写 INT_STATUS_1 = BIT(0)、wmb，锁内 readl_relaxed burst，logdump-rx32-startup.img | 41 41 41，读后 07070707 | 撤回，恢复已验证版本 |

最后一项来自 OnePlus SM8150 `eud_startup()` 的实际代码差异，不是盲加寄存器。
下游 RX ISR 没有发现额外的逐字节清中断 / advance 写操作；因本次组合实验未成功，
也不能声称已经单独证明该 startup 写无任何作用。
第一次 startup 抓包仍在启动日志阶段，没有有效 RX 诊断；上表来自随后已到 shell
的 `rx32-startup-ABC2.raw`，不是把「没有日志」算成失败。

最终恢复的源码（SHA256 `13e107b2be2928f929ac713dbbf90b07736aea073cc1aec5524a9489b29951bd`）
是 WSL `drivers/tty/serial/eud.c`，仓库副本 `linux-port/eud.c` 与之逐字节相同。
实现只交付已经实测的部分：

- 读 RX_DAT 前不 printk，不跳过两个头字节；len 1 的真实字符进入 tty 并更新 icount。
- len 2 在读完头部后立即关闭 EUD、重启 bootloader，保留飞轮。
- len 3..14 最多按声明长度读取，门控中途清零也不提前放弃；结果缓存到最后才打印，
  不注入 tty；移除原潜在 len 3 recovery 分支。
- tty TX、console 与单次 RX 数据操作使用同一个 uart port lock。

增量 `make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image` 通过，
`git diff --check -- drivers/tty/serial/eud.c` 通过。新增诊断撤回后也已重新编译通过。
本轮没有替换 DTB，没有改动本来存在的其他内核修改。

### 最终单字符版的 shell 与飞轮证据

主机逐个发送 `90 01 69`、`90 01 64`、`90 01 0a`，分别等 `tty byte=..` 受理诊断
后停止重发，再继续排空 2 s。前两个字符的诊断分别是 `69`、`64`；回车抓包为：

```text
[  465.682980] eud: tty byte=0a

uid=0 gid=0
~ #
```

`rx32-final-enter.raw` 为 85 bytes / 15 frames / 0 stray bytes；这是实际 shell
执行 `id` 的完整响应，不是驱动在 printk 里模拟 shell。随后同版 ABC 三次受理均为：

```text
[  492.966971] eud: BUFFERED len=3 s1_after=06060606
[  493.012347] eud: byte[1/3]=41
[  493.041711] eud: byte[2/3]=90
[  493.071038] eud: byte[3/3]=90
```

该版发 `90 02` 后 COM 自行断开，`fastboot devices` 返回 `62bc28a1 fastboot`。
startup 诊断版也通过相同飞轮返回，再仅刷 `logdump` 恢复最终单字符版。
本轮各次串口操作均经 finally 关闭，未出现 resource-in-use、换 USB 口或重启主机。
恢复后再次启动 Linux，`rx32-restored-clear.raw` 收到
`[120.985694] eud: tty byte=15`（Ctrl-U）；8 frames / 0 stray bytes。
结束时手机停在该 Linux 内核，COM14 已 Close / Dispose，没有停留在 fastboot。

手机最终使用 `E:\edk2-samurai-out\logdump-rx32-console.img`：

| 对象 | SHA256 |
|---|---|
| FAT 内 Image，30,116,352 bytes | d478871c6d12ee018823c8716d82c3fd445791df6c36a76ae4bc2a3b37e0ce40 |
| logdump-rx32-console.img，67,108,864 bytes | 4d0cc65e037294d63176151092dc954a0cc9f57b5bd0e7ab9629f3bd68f14c2f |
| 撤回的 logdump-rx32-startup.img | 06b69880caa93f2a97755050e22c69b4715c1afc88b89a8a699412b99d2292e9 |

主机复测工具已保存为 `linux-port/scripts/eud-step.ps1` 与
`linux-port/scripts/decode-eud-capture.py`。每次只运行一步，不自动构建/刷机/循环。

## 32.6 剩余问题

**多字节 payload 尚未打通，本轮只修正了单字符真实输入。** offset-2 不符合
当前证据；前置 TX/printk 为什么改变 RX 回读、后续数据如何推进，仍需硬件说明或
新的有效实现证据。不要把重复首字节 / stale 0x90 当成正确 payload 送入 shell。

下一步查 RX 完成握手、MMIO 读副作用及 TX 访问影响；对照真实寄存器访问轨迹，
区分时钟/字节通道/互连假设，避免原样重做已失败的 burst、readb、200 μs、20 ms
及 startup 组合实验。当前源码主线不提供 tty RX，其他机型源码也不能替代真机验证。

另纠正旧文档的 COM 控制帧长度：[QUIC com_eud.h](https://github.com/quic/eud/blob/main/inc/com_eud.h)
定义 TX_TMOUT / RX_TMOUT 为 5 bytes，**PORT_RESET 为 1 byte**；不是所有 opcode
都使用 `{opcode,ff,ff,00,00}`。本轮试过两个 timeout 帧而没有取得推进改善；没有
尝试 PORT_RESET，也没有盲加 DTS clock vote。
