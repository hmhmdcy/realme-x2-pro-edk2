# Bounded pre-Linux EUD RX comparisons

**Session 41 found a working native FIFO method:** verified SM8150 SOUTH
AHB2PHY TOP_CFG at `0x088ee010`, set it to `0x11`, read the entire payload
before TX. `EudWaitProbe` produced ABC/DEFG correctly across two reboots and
restored the original zero before Linux. See [session 41](../../sessions/41-rx-ahb2phy-wait-state-fix.md)
and [raw evidence](../../reference/rx41/README.md). This does not establish
lossless OUT delivery; a missing device receipt remains inconclusive.

The build now emits three separate applications:

* `RxProbe.efi`: retained RX39 tight-poll failure control; no configuration write.
* `EudSnapshot.efi`: reads TOP_CFG twice, replays the cached pair five times,
  then starts the preloaded original Kernel. No configuration write or RX read.
* `EudWaitProbe.efi`: writes `0x11` only if the original configuration is zero,
  requires two matching readbacks, runs the original RX39 payload loop,
  restores zero and prints the restoration readback before starting Kernel.

`package.sh [new-output.img] [application.efi]` accepts explicit paths; without
arguments it retains the RX39 defaults. It checks the rx33 baseline hash,
rejects an existing output and compares the retained Kernel and DTB byte for byte.
All apps preserve LoadOptions and the DTB. The snapshot/wait trial does not
reset the PHY or change clocks, interrupts or the boot partition.

For the wait trial, start `wait-capture.ps1 -Out <fresh-prefix> -Marker RX41-WAIT`
before reboot. Omit `-StartAbc`: host writes require the fresh READY marker.
Each pattern is bounded to three attempts. For the read-only snapshot, use
the default marker without StartAbc; it sends no RX pattern. Always wait for
the capture's `Closed/disposed` result before any new serial owner.

The following RX38/39 workflow is retained as history, not a trial to repeat.

SM8150 samurai 的诊断应用。sessions 38/39 均实测 ABC→AAA、DEFG→DDDD，**不是原生 RX 修复**。
当前为 RX39 紧轮询版本，受理前检测间隔约 625/572 ns 仍失败。RX38 的 1 ms 版本见提交 703469c。
该间隔是相邻循环入口计数之差，不是 USB 到达至首次 DAT 的端到端延迟。
不链接 SerialPortLib，在高 TPL 屏蔽已知固件 TX 定时器，整帧缓存后才输出；每阶段等候最多 25 秒，
然后启动预先加载的原 `\Kernel`。保留 BDS LoadOptions 和现有 DTB 配置表，不改 PHY/时钟/中断寄存器。

在既有 WSL 仓库镜像本目录，运行 `bash .../uefi-rx-probe/build.sh`。
`package.sh` 针对本机路径：检查基线哈希，只创建新的 logdump-rx39-uefi.img，
把原 Image 重命名为 Kernel，再添加应用为 Image；内核、DTB、应用均逐字节校验。
输出文件已存在时拒绝覆盖。构建不触碰 boot 固件或 Linux/initramfs。

手动 F1 → 确认 fastboot → 只刷诊断 logdump；先起 `wait-capture.ps1 -Out <新前缀> -StartAbc`，
再单步 reboot。脚本等 CTL、com-up、找 COM，打开后先发 ABC，收到 DEFG ready 再发 DEFG，
各最多 3 次、间隔 3 秒；100 秒后 finally 关闭。第一次 ready 可在打开端口前丢失。
省略 StartAbc 时只响应实际收到的 UEFI ready，普通 Linux 下可作被动抓包。

结束后单独 F1、核实 fastboot，刷回原 logdump-rx33-console.img，再启动并核实 console。
记录、限制和哈希见 [session 38](../../sessions/38-rx-pre-linux-and-usb-boundaries.md) 和
[session 39](../../sessions/39-rx-tight-arrival-poll.md)。不再原样重复这两项失败对照。
