# 35. 下一会话交接：继续原生多字节 RX 排查（2026-10-09）

> 历史交接，保留原文。session 41 已验证真实整帧 payload 的推进修复；当前剩余终端
> 问题与可直接粘贴的新提示词见 [session 42](42-native-terminal-next-session-handoff.md)。
> 下文“原生 RX 未修复”和 §35.5 的旧提示词不再代表当前状态。

用户要求：临时终端先支撑 Linux 驱动移植，下一会话仍要继续搞清楚原生 RX。
本节只整理交接，不操作手机、不重刷内核。

## 35.1 先读与工作位置

先读 `HANDOVER-NEXT.md`、`FLYWHEEL.md`、`RX-CONSOLE.md`；详细实验为
`sessions/33-rx-access-and-production-policy.md`，临时终端为
`sessions/34-temporary-eud-terminal.md`。需要追溯原探针/飞轮时再读 sessions 32/31。

* Windows 工作区：`E:\RealmeX2Pro edk2\`。
* WSL 内核：`/home/cy122/x2pro-linux/linux`；目标 `drivers/tty/serial/eud.c`。
* 可复现源码副本：工作区 `linux-port/eud.c`。
* 工具：`E:\eud-host\`；镜像与完整实验文件：`E:\edk2-samurai-out\`。
* 发布仓库：WSL `/home/cy122/edk2-samurai/repo`，只推 fork/master。
* 当前已验证镜像：`logdump-rx33-console.img`，源码/Image/镜像哈希在 session 33。
  session 34 只加主机工具，未改内核、未刷分区。

上次验证后手机在该版 Linux，COM14 已由 finally 关闭。用户期间曾手动进入
fastboot；下一会话先检查实际枚举和是否已有终端占口，不把旧状态当实时事实。

## 35.2 必须保留的事实与边界

| 项目 | 已验证结果 |
|---|---|
| 手机 TX → PC | 限速、每帧最多 4 payload 字节可组成完整长输出；直接 tty 与 console 均已实测 |
| PC → 手机 RX | 长度 1 的真实 payload 字符进入 tty；长度 3 的 ABC 仍为重复首字节或 41 90 90 |
| 原始 offset-2 假设 | 原探针 90 90；去掉前置 printk 后首字节为 A，不支持跳过两字节 |
| 门控 | RX_PENDING 并非每次首次读后立即清零；短间隔读完也可仍为 07 |
| 飞轮 | `[90][02]` 头部命令 → 先关 EUD → 无按键进 fastboot，设备 62bc28a1 |
| 临时终端 | `E:\eud-host\eud-terminal.cmd -Reconnect`，逐字符受理重试，Ctrl-] 关闭 |

原生 RX 的成功标准是按发送顺序读出全部 payload，例如 ABC → 41 42 43、
DEFG → 44 45 46 47，并能复测；只读对首字节、临时输入整条命令或 0 stray 都不算。
长度 3..14 目前是有界诊断，不是 recovery，不把未验证内容注入 tty。

临时终端已有键盘/命令模式，默认 500 ms 加扰动、最多 10 次发送；原单步探针和
F1 仍是秒级重发。回执没有序号/去重，ACK 丢失可能重复字符，不能承诺 exactly-once。
发探针/F1 前先退出终端；一次只让一个进程开串口，始终 try/finally Close/Dispose。
com-off/com-up 可恢复部分零日志状态，不能解除 qcser resource-in-use 钉死。

## 35.3 已做过，别原样再跑

完整配置和有效/无效抓包在 session 33，短证据在 `reference/rx33/`；临时终端
成功记录在 `reference/rx34/`。

* 帧内禁止 TX/printk、共用 port lock：burst 仍 AAA；20 ms 仍可 A90…。
* readb、readl/DSB、200 μs、2 ms、20 ms、重读 LEN：没有连续 payload。
* 实际页表核实为 Device-nGnRnE 的映射：仍失败，最终恢复普通 ioremap。
* DAT 先于 ID/LEN；临时 IRQ mask 变化、每次 DAT 后写 RX 位：未解决。
* SCM DAT 访问返回 -22，不能当 FIFO 零数据或具体熔丝状态证明。
* 主机补零到 16 字节、去掉 Flush：未解决。逐字节 Write/timeout 配置部分没有
  受理证据，不能算确认应用后的有效反例。
* Linux/EDK2 源码未找到第二个 RX 消费者；这不证明所有不可见固件均已排除。
* 多个厂商树采用相同 ID/LEN/连读 DAT 代码，不等于这些机型实测过多字节 COM。
* QUIC 库存在覆盖 opcode 的 WriteCommand 拷贝错误，但我们的原始帧发送不调用
  该重载，不能当本机根因。主线近期 PHY/角色补丁也不是 COM RX 修复。
* 熔丝/OEM debug policy 可限制 EUD，但没有证据建立“量产 COM 仅一字节”限制。
  SWD/DAP 受限不能直接类推到 COM。

## 35.4 下一轮应取得的新证据

1. 优先检查 USB OUT 抓包条件，确认旧 qcusbser 真正送出的字节、USB 包边界和
   受理时序。当前只有主机 Write 记录与手机 TX 抓包，尚无线上 OUT 证据。
   已安装 qcusbser.sys 2.1.3.5 与公开 WDF 源码版本不同，不能靠后者排除前者。
2. 或做可控的另一条主机传输路径对照，记录驱动/初始化/包边界差异，保留现有
   终端和飞轮的可恢复路径。先确认本机现有工具，不把旧的“未安装”当实时库存。
3. 搜索并审查 SM8150 的 RX 读副作用、完成握手、初始化和时钟资料；跨机型只能
   作为线索，不猜寄存器地址写入。量产权限假设需要 COM 专属配置或同 SoC 对照。
4. 每轮只改一个可解释变量，先写预期与判据；区分有效失败、未确认受理、真正改善。
   手动小步操作，不做无人值守大循环。

只有需要测试新内核时才构建/打包，确认 fastboot 设备和打包完成后**只刷 logdump**。
保留 `[90][02]`、现有 tty/console；不要顺手刷 boot/DTB/其他分区。
结论、原始证据和限制写入 RX-CONSOLE.md 与 sessions，再运行
`linux-port/scripts/sync-docs-to-repo.sh` 同步推 fork。改动 linux-port 时仍需先镜像
对应文件；该同步脚本只处理顶层文档与 sessions/reference。

## 35.5 可直接粘贴的短提示词

```text
继续 E:\RealmeX2Pro edk2 的 EUD 多字节 RX 排查。先读 HANDOVER-NEXT.md、RX-CONSOLE.md、FLYWHEEL.md 和 sessions/35 的交接。临时终端可用，原生 RX 未修复；优先查 USB OUT、qcusbser 与 SM8150 握手，搜索并审上下游源码，别重复无效实验。先核实设备状态，手动小步、串口 finally 关闭；只刷 logdump，保留 F1/console，记录并推送结论。
```
