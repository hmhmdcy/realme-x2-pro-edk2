# EUD RX：组帧与Linux控制台调查

用途：RX技术历史与故障证据。整理日期：2026-10-14；部署及操作边界见[检查点](NEXT-SESSION.md)和[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)。下文按2026-10-08至09的实验阶段解释，后来结论由所链接会话补充。

## 后续证据入口

- [41完整payload修复](sessions/41-rx-ahb2phy-wait-state-fix.md)、[43旧缺输出更正](sessions/43-native-terminal-evidence-audit.md)
- [53 console边界RX](sessions/53-console-boundary-rx-service.md)、[65持续WSL TX缺口](sessions/65-wsl-full-packet-console-overlap-and-tx-gap.md)
- [测试飞轮](FLYWHEEL.md)、[当前功能清单](linux-port/docs/HARDWARE-STATUS.md)、[会话索引](sessions/INDEX.md)

原先累积在本文开头的阶段交接已保存在[逐字快照](archive/docs-before-maintenance-2026-10-14/RX-CONSOLE.md)。

## RX side: registers, framing and the console driver (2026-10-08)

> **session 38 新对照：** 独立 UEFI 程序在 Linux 运行之前、屏蔽已知固件 TX 定时器、整帧缓存后输出，
> 新受理 ABC/DEFG 仍为 AAA/DDDD。合法 LEN=14 满 16 字节 OUT，及另附 ZLP，均仍为首字节后全 90。
> PORT_RESET 后 ABC 也未改善；timeout 无回执不能算有效失败。已只刷 logdump 恢复 rx33-console，
> Linux/COM14 Ctrl-U 新回执正常、端口关闭。实际 HS PHY 匹配 SNPS femto-v2，修正此前 QUSB2 参考归属。
> 详见 [session 38](sessions/38-rx-pre-linux-and-usb-boundaries.md) 和 reference/rx38；原生多字节仍未修复。

> **session 39 新对照：** UEFI 去掉 1 ms 等待、紧轮询的相邻循环入口差为 625/572 ns，
> 新受理 ABC/DEFG 仍为 AAA/DDDD；这个数值不是 USB 到达延迟。不要原样重跑更快轮询。
> libusb 加 PORT_RESET 恢复单字节/F1 回执后，另证实 fastboot，已只刷回 rx33-console；
> 原 Linux/tty/shell 启动、Windows Ctrl-U 首次受理，COM14 关闭。新搜到的 boot HWIO 定义
> 属于其他 SoC 或经过过滤，没有给出 SM8150 COM advance 修法。完整证据和限制见
> [session 39](sessions/39-rx-tight-arrival-poll.md)、reference/rx39。

> **session 40 源码审查：** 完整旧一代 DSP 寄存器表列出 EUD_ACORE/flags，仍没有 DAT 读副作用规格；
> 原厂 RMX1931 SM8150 UsbConfigDxe 检查 EUD enable 并避开 PHY reset，没有提供 COM RX 推进代码。
> 未刷机、未重跑多字节，基线 Windows Ctrl-U 第 2 次 OUT 有新回执并 finally 关闭。
> 原生 RX 仍未修复；固定来源、证据边界见 [session 40](sessions/40-rx-register-map-and-stock-firmware-audit.md)。

本节至「命令通道打通」是同日较早阶段的历史记录；当前实测结论见文首及末节。
其中「每读一次必定弹出后续 payload」和 offset-2 都不能当作本机已验证事实。

Earlier sections describe the transmit direction.  This one is the receive
direction, measured on this unit.

Registers inside the 0x2000 window (every readback replicates the low byte into
the four lanes, so mask with 0xff):

| offset | meaning |
|---|---|
| 0x0c | RX_ID - latch holding the id of the last message the host wrote |
| 0x10 | RX_LEN - latch holding that message's length |
| 0x14 | RX_DAT - downstream treats this as a FIFO read port; advancing after the first payload byte is unverified on this unit |
| 0x40 | INT_STATUS_0 - 0x00 idle, 0x02 while RX data is pending |
| 0x44 | INT_STATUS_1 - 0x06 idle, 0x07 while RX data is pending (BIT(0)) |
| 0x20 | INT0_EN_MASK - reads 0; writing 0xff reads back 0x1f (five bits) |
| 0x60 | reads 0x0b0b0b0b, undocumented |

Protocol: the host writes [id][len][payload...] as one transfer; the device
reads id from 0x0c, len from 0x10 and then reads 0x14 `len` times for the
payload.  Unframed writes are dropped by the device entirely.  The status bits
are not reliable enough to gate on (they can read idle while data is pending),
so new data is detected by watching the 0x0c/0x10 latch pair change.

Ids used by this port: 0x82 = tty input (the payload goes to /dev/ttyEUD0),
0x81 = command channel (payload[0] is the command code: 0x01 ping, 0x02 register
dump, 0x03 status).  0x90 is the id the device uses when it transmits.

The kernel driver is drivers/tty/serial/eud.c: a uart driver ("ttyEUD") with a
workqueue transmit path paced at 200 us per register write and 2 ms per frame, a
20 ms RX poll, and a console that registers only when the command line contains
"console=eud" - otherwise the early console is a second writer on the same seven
entry FIFO and the two interleave byte by byte.

Caveat: reading 0x14 too eagerly wedges the EUD COM block.  The console goes
silent (the 9501 control device and the COM port stay up) until a full power
cycle.  Only read it once a complete payload is certain.


## Payload read attempts (2026-10-08 evening): what works, what does not

Three kernel builds were tried after the register map above was established.

1. `logdump-payload.img` - read 0x14 up to `len` times whenever the header
   changed or INT_STATUS_1 BIT(0) looked set.  The device went silent, console
   included, right after the first host frames; a full power cycle cleared it.
   Hammering 0x14 is what wedges the block.

2. `logdump-safe.img` (direction A) - trigger only on the 0x0c/0x10 latch
   changing, read at most ONE 0x14 byte per 20 ms poll, validate `len` 1..16,
   and let the host alternate ids 0x82/0x83 so that two identical characters in
   a row still change the latch.  Result: the device did not wedge immediately -
   the shell echoed all 18 characters of "echo SHELL-LL-TEST" - but most payload
   bytes came back as 0x3F ('?') and only a few were the characters actually
   sent.  0x3F looks like the value an empty 0x14 read returns, i.e. the payload
   is not in the FIFO yet when it is read immediately after the header latch
   changes.  After about two minutes of host traffic the device went silent
   again.

3. `logdump-payloaddiag.img` - prints "eud: msg id=.. len=.. s0=.. s1=.." and
   then "eud: payload[n/m] = xx s0=.. s1=.. polls=.." for every byte read, so a
   known host frame ([0x90][0x03]"ABC") shows exactly what comes back and when.
   On its boot the console produced almost no output at all, so those
   diagnostics have not been collected yet.

Open questions, in the order they should be answered next session:

* Is the silence a device-side wedge or a host-side stall of the qcser/USB read
  path?  `eudtool com-off` followed by `com-up` once delivered six leftover bytes
  ("[  1") and then nothing, which points at the host side at least once.  Test
  by attaching the host capture BEFORE the kernel boots and draining
  continuously so the FIFO never overflows, and by re-enumerating the COM
  function while the device is known to be logging.
* When exactly does a payload byte become readable in 0x14 after the host's
  write?  Candidates: one poll (20 ms) later; only while INT_STATUS_0 has BIT(1)
  or INT_STATUS_1 has BIT(0); or only after the header latches have been read.
  The diagnostic build answers this once it runs with a continuous capture.
* Until then the verified-stable RX is the header-only protocol in
  logdump-tty6.img: [0x81][cmd] commands (reliable) and [0x82][char] typing
  (works, characters can be lost).

Hardware note that cost several cycles: a silent EUD does not always mean a
crashed kernel.  The EUD block keeps state across warm reboots, and a full power
cycle (hold Power about 15 s) is the only reliable way to clear a stuck COM
block.  Always try that before concluding the image is broken.


## External reference found (2026-10-08): EUD_INT_RX lives in INT_STATUS_1

A web search turned up the downstream Qualcomm driver `drivers/soc/qcom/eud.c`
(AOSP kernel/msm; the same driver ships in realme sdm710 and motorola sm6375
trees).  Its RX interrupt plumbing is:

    static void eud_stop_rx(struct uart_port *port)
    {
            /* Disable Rx interrupt */
            writel_relaxed(~EUD_INT_RX, port->membase + EUD_REG_INT_STATUS_1);
            /* Ensure Register Writes Complete */
            wmb();
    }

so `EUD_INT_RX` is a bit in `EUD_REG_INT_STATUS_1` (0x44).  On this unit that
register reads 0x06060606 when idle and 0x07070707 while payload bytes are
pending, which pins `EUD_INT_RX = BIT(0)`.  The same driver's uart_ops has
`eud_tx_empty`, `eud_stop_tx`, `eud_start_tx`, `eud_stop_rx`, `eud_startup` and
`eud_shutdown`, i.e. it is a tty driver of exactly the shape ours has.

Consequence for our driver: gate every read of 0x14 on `INT_STATUS_1 BIT(0)`
and read only one payload byte per poll.  `logdump-intrx.img` implements that
and is the current candidate.


## The downstream RX function itself (found 2026-10-08 by searching)

The receive side of the Qualcomm driver was finally extracted from AOSP
kernel/msm (`drivers/soc/qcom/eud.c`).  The search that worked was a
quoted-string probe of the googlesource page through Exa.

    static void eud_uart_rx(struct eud_chip *chip)
    {
            struct uart_port *port = &chip->port;
            u32 reg;
            unsigned int len;
            unsigned char ch, flag;
            int i;

            reg = readl_relaxed(chip->eud_reg_base + EUD_REG_COM_RX_ID);
            if (reg != UART_ID)
                    ...                 /* not our message: drop the whole thing */

and the status bits are

    #define EUD_INT_RX          BIT(0)
    #define EUD_INT_TX          BIT(1)
    #define EUD_INT_VBUS        BIT(2)
    #define EUD_INT_CHGR        BIT(3)
    #define EUD_INT_SAFE_MODE   BIT(4)
    #define EUD_INT_ALL         (EUD_INT_RX | EUD_INT_TX | EUD_INT_VBUS | \
                                 EUD_INT_CHGR | EUD_INT_SAFE_MODE)

with

    static void eud_stop_rx(struct uart_port *port)
    {
            /* Disable Rx interrupt */
            writel_relaxed(~EUD_INT_RX, port->membase + EUD_REG_INT_STATUS_1);
            wmb();
    }

So the reference sequence is exactly: read the id latch (0x0c), filter on
`UART_ID`, read the length (0x10), then read `len` payload bytes from the FIFO
port (0x14), with `EUD_INT_RX` (BIT(0) of INT_STATUS_1) as the data-available
gate.  On this unit INT_STATUS_1 reads 0x06 when idle and 0x07 while payload
bytes are pending - BIT(0) = RX, BIT(1) = TX - which confirms the mapping.

What is still unknown: the value of `UART_ID`.  The device itself transmits with
id 0x90, while the QUIC host library writes [exec-env id][len][payload] with the
id in 0x80..0x88 (0x81 = APPS).  The candidates are therefore 0x90 and 0x81, and
picking the right one is the first thing to settle next session.

How our driver compares:

| step | downstream reference | our driver (logdump-intrx2.img) |
|---|---|---|
| detect a message | RX interrupt, then read the id latch | read the id latch every 20 ms |
| filter | `if (reg != UART_ID) drop` | none yet |
| length | RX_LEN latch | RX_LEN latch, validated 1..16 |
| payload | read `len` bytes from 0x14 inside the ISR | ONE byte per 20 ms poll |
| gate | EUD_INT_RX in INT_STATUS_1 | EUD_INT_RX in INT_STATUS_1 |

The one-byte-per-poll deviation is deliberate: a burst of 0x14 reads while the
FIFO is empty wedges the COM block on this unit (the console dies until a full
power cycle), while one read per poll is the pattern that survived a 175 s
hardware probe.

---

## 命令通道打通，payload 仍未解（2026-10-08 晚，真机验证）

结论：**`0x14` 的 payload 读取仍未解**，但**命令通道已经能用**，手机能从 Linux
自己重启进 fastboot（使用手册 `FLYWHEEL.md`，实验记录 `sessions/31-flywheel-f1-verified.md`）。

1. **id `0x90` 是唯一被受理的**：A 轮用 `0x81`/`0x82`/`0x83` 发的 22 帧，闩锁完全没有
   变化；只有 `[90][03]"ABC"` 进了闩锁。`0x90` = 上游 `UART_ID`（两处 kernel/msm 镜像确认）。
2. **命令编码进长度字段**：`0x0c`/`0x10` 两个闩锁精确可靠 → `len=1` = tty 字符、
   `len=2` = reboot bootloader、`len>=3` = payload 探针。实测 `[90][02]` →
   `eud: reboot2 bootloader requested` → 写 `CSR_EUD_EN=0` → `kernel_restart("bootloader")`
   → fastboot，**全程无按键**。
3. **门控语义（实测）**：收到头部时 `0x44` 读 `0x07`（BIT(0) 置位）；读一次 `0x14`
   之后读 `0x06` —— **门控在第一次读之后就被清掉**。
4. **读回的字节永远是 `0x90`（id 本身）**：`len=1` → `byte[1/1]=90`，`len=3` →
   `byte[1/3]=90`。读到的字节确实进了 tty（设备回显了一帧 `90 01 3F`，即 `?`）。
5. **上游全是"消息级门控 + 帧内 burst"**：`kernel/msm` 用 RX 中断门控后一次读 `len` 次；
   QUIC 官方主机库规范："byte 0 is Exec Env ID, byte 1 is how many bytes data, remaining
   bytes are data"。**逐字节门控是本项目的偏离**（为绕开"burst 读会卡死 COM 块"）。
6. **主假设（未证）**：这台机器的 `0x14` 装的是整帧 `[id][len][payload…]`，payload 在
   偏移 2。探针 `[90][len>=3]`（读 `len-1` 字节、逐个打印、门控清零也不放弃）就是为
   判定它而写的，尚未跑。
7. **COM 口的命令帧**（`com_eud.h`）：`0`=NOP、`1`=TX_TMOUT、`2`=RX_TMOUT、
   `3`=PORT_RESET，形态 `{opcode,0xFF,0xFF,0x00,0x00}`；数据帧首字节才是 `0x90`。
   设备侧按首字节分派。
8. **主机投递率约 1/3**：实测 15 帧只有 7 帧被设备暂存。→ 每条命令发 3–5 次。
9. **主机 COM 口会卡死**：被中断的脚本能让 qcser 把端口钉在 "resource in use"，
   `com-off`/`com-up`/`detach`/`rst(0x09 PERIPH_RST)`/杀进程/重启手机都无效，
   只有换 USB 口（换设备节点）或重启主机能解。飞轮脚本必须 `try/finally` 关端口。

## 单字符 RX 修正与多字节探针的新结果（2026-10-08，session 32）

`drivers/tty/serial/eud.c` 现在先读 RX_DAT、存入内存，再打印诊断或向 tty 推送。
RX_DAT 不跳过头部。长度 1 的字符真实进入 tty，并更新 RX 计数；长度 2 在头部
立即请求 bootloader；长度 3..14 只按声明长度采样，读完才打印缓存，不因门控位
中途清零而提前终止，不分发 recovery，不向 tty 注入探针结果。
tty TX、console 与单次 RX 数据操作使用同一 port lock。

已经排除「只要忽略逐字节门控，直接多读两字节就行」这个修法。无前置打印的
连续 readl 得到 `41 41 41`；200 μs 读间延时和 readb 也未改善；20 ms 间隔并
推迟所有打印得到 `41 90 90`。首字节成功与整帧成功必须分开报告。
前置 printk 改变读回值有真机证据，具体硬件机制仍未证明。

复测用 `linux-port/scripts/eud-step.ps1`，每次只操作一帧，独立进程、持续排空、
Write 后 Flush、最多 5 次重发、finally 关闭并 Dispose。对于 tty 输入用
`-Ack 'tty byte=69'` 这类已受理诊断停止重发，再排空 2 s，避免一个字符被
重复键入；不能对整条 shell 字符串不看回显就盲发 5 遍。

当前源码的可复现副本是 `linux-port/eud.c`；镜像、原始抓包、哈希和后续未决
问题统一记录在 [session 32](sessions/32-rx-printk-interference.md)。

最终单字符版真机按 `i`、`d`、回车逐个发送并等受理诊断，shell 返回完整
`uid=0 gid=0` 和 `~ #` 提示符。对应 `rx32-final-i/d/enter.raw` 帧重组均为
0 stray bytes；同版 `ABC` 探针三次受理均为 `41 90 90`。

## 访问路径与量产权限复查（2026-10-09，session 33）

帧内完全禁止 TX，200 μs/2 ms 连读仍重复首字节；20 ms 仍可出现 `41 90 90`。
数据先于 ID/LEN 读取、实际验证为 Device-nGnRnE 的映射，以及临时改变 IRQ mask
均未取得连续 payload。SCM 读取返回 -22，不能作为有效数据或具体熔丝状态的证明。
RX 位也不是每次首次读后立即清零：短间隔读完可能仍为 07，较长间隔可能变 06。
因此，前置 printk 是已证实的干扰因素，不能独自解释后续字节失败。

核对同 SM8150 厂商树和当前上游后，未找到适用的 FIFO advance 修复；源码中未发现
第二个 RX 消费者。QUIC 主机库有一个覆盖 opcode 的 WriteCommand 重载错误，
但本项目的原始帧发送不经过它，不能归为本次根因。已安装 qcusbser 与公开 WDF
驱动版本不同，尚缺 USB OUT 抓包，主机这一层仍未完全排除。

量产调试权限可受熔丝和 OEM 签名策略限制，但未找到 COM 限为单字节的公开证据；
此前 SWD/DAP 受限也不能直接证明 COM FIFO 同样受限。详细来源、有效/无效样本、
哈希与下一步见 [session 33](sessions/33-rx-access-and-production-policy.md)。
最终版再次以单字符输入执行 id，返回 `uid=0 gid=0`，F1 再次进入 fastboot；
同版 ABC 仍为 `41 90 90`。只保留头部/首次 DAT 持锁与 mapbase 修正。
