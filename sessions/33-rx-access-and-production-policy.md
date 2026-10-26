# 33. EUD RX：访问路径、上下游与量产权限排查（2026-10-08 至 09）

用途：承接 session 32，记录多字节 RX 的进一步真机实验，以及量产权限假设的证据边界。
关联：`RX-CONSOLE.md`、`FLYWHEEL.md`、`linux-port/eud.c`。

## 33.1 当前结论

**原生多字节 RX 仍未解决，不能把本轮记为成功修复。** 已确认首字节是真正 payload，
不能跳过两个字节。`[90][01][char]` 可逐字符操作 shell；`[90][02]` 可无按键回
fastboot。长度 3..14 继续只作有界探针，不把重复或陈旧数据注入 tty。

连续读、禁止帧内 TX、数据先于头部读取、改变 MMIO 属性和部分中断配置，都没有读出
`41 42 43`。正常帧头读取顺序下 burst 通常为 `41 41 41`；20 ms 间隔通常为
`41 90 90`。**即使整帧禁止 TX，20 ms 实验仍能出现后续 90**，所以前置 printk
确实影响首字节，但不能独自解释多字节失败。

本轮最终仅保留两项小修正：RX 的状态、头部和首次 DAT 读取共用 TX 的 port lock；
从实际资源填写 `port->mapbase`。没有保留 SCM、特殊映射、长时间关中断或 armed 探针。
无效头部也不再盲读一次 DAT，避免对无效消息做无依据的数据读取。
这些是访问路径修正，**不是已经解决 FIFO 推进的证据**。

## 33.2 手动实验与有效结果

每次单独运行发送/抓包进程；串口均在 finally 中 Close/Dispose。最多重发 5 次，
用受理日志停止重发。所有镜像只替换 **logdump**，未刷 boot、DTB 或其他分区。
各诊断镜像之间均通过 F1 返回 fastboot。

下表 DAT 取低 8 位；32 位 MMIO 常把低字节复制到四条 lane，例如 41 → 41414141。
原始 `.raw` 和解码 `.txt` 在 `E:\edk2-samurai-out\`，部分有效记录另存于
`reference/rx33/`。0 stray 仅说明帧重组无需丢弃字节，不证明日志绝无丢失。

| 镜像/实验 | 有效结果 | 抓包文件名（省略 .raw） |
|---|---|---|
| rx33-access，整帧持锁、4 次 SCM DAT | 每次返回 -22，数据无效 | rx33-access-DEFG |
| rx33-access，每次 DAT 前重读 LEN | ABCDE → 41 41 41 41 41；LEN 一直 05 | rx33-access-LEN |
| rx33-access，先正常 MMIO，再 SCM | 首字节 41；后两次 SCM 返回 -22 | rx33-access-ABC3 |
| rx33-mmio，readl + DSB SY + 200 μs | ABC → 41 41 41，3 帧受理 | rx33-mmio-ABC2 |
| rx33-mmio，readb 读 0x14..0x17 四条 lane | DEFG → 44 44 44 44 | rx33-mmio-lanes |
| rx33-wait，整帧禁止 TX、2 ms | ABC → 41 41 41；读后 s1 仍 07 | rx33-wait2 |
| rx33-wait，整帧禁止 TX、20 ms | ABCDE → 41 90 90 90 90 | rx33-wait20-2 |
| rx33-wait，临时开启 INT0/INT1 RX mask、2 ms | 长度 6：前五个 41，最后 90 | rx33-mask-2 |
| rx33-wait，每次读后向 STATUS1 写 RX 位、2 ms | 长度 7：41 后六个 90 | rx33-ack |
| rx33-order，mode 12，先 3 次 DAT，再 ID/LEN，200 μs | ABC → 41 41 41；s1=07 | rx33-order12-reenum |
| rx33-order，mode 13，先 3 次 readb DAT，再头部，2 ms | ABC → 41 41 41；s1=06 | rx33-order13-reenum |
| rx33-order，mode 14，两组 IRQ mask 归零、DAT 在头部之前，2 ms | ABC → 41 41 90；s1=06 | rx33-order14 |
| 恢复版 rx33-console，常规 20 ms 探针 | ABC → 41 90 90 | rx33-final-ABC |

**门控解释需修正：** RX 位不是每次都在第一次 DAT 读取后立刻清零。短间隔整帧读取后
仍可为 07，长间隔可能中途变 06；还有同一配置出现 AAA 与 AA90 的情况。
因此，不能把早期一次“读后为 06”推广为确定的逐字节 ACK 语义。

特殊 MMIO 映射通过实际页表核对：PTE `00680000088e0f0f`，
MAIR `000000040044ffff`，AttrIndx=3，对应 MAIR byte 3=00，即 Device-nGnRnE；
物理页为 088e0000。此配置仍失败。这不等于普通 ioremap 原先配置错误，最终已恢复
普通 devm ioremap。读宽度和屏障实验只排除各自测试路径，不能代替芯片寄存器手册。

SCM `qcom_scm_io_readl` 的 -22 仅说明该访问请求被拒绝；不能据此推导具体熔丝状态，
也没有把失败读返回的零当作 FIFO 内容。

## 33.3 主机侧实验及无效样本

* 数据帧填充到 16 字节：长度 5 的 ABCDE 仍重复 41，见 `rx33-pad16.raw`。
* 去掉 BaseStream.Flush：20 ms 仍是 41 后四个 90，见 `rx33-noflush.raw`。
* 每字节单独 Write、间隔 10 ms：没有捕获到受理日志，不能下定论。
* TX/RX timeout 和 PORT_RESET 命令做过发送，但没有设备 ACK/readback；随后的零捕获
  不能证明这些配置已生效，更不能当作它们损坏或修复了 FIFO 的证据。
* 部分零捕获在 `com-off`/`com-up` 后恢复。未出现 resource-in-use 锁死，
  不应把这次重新枚举的效果推广为能修复 qcser 端口钉死。
* 最初 mode 12 的 ABC 只发一次，没有确认受理；随后发 arm13，错误地让 pending
  mode 12 消费了长度 13 的头部。该零数据结果作废，已重新 arm12，并取得上表有效
  `rx33-order12-reenum.raw`。armed 实验必须确认 arm 和数据各自的 ACK。

## 33.4 上下游与其他机型源码

同 SM8150 的 [OnePlus 厂商驱动](https://raw.githubusercontent.com/OnePlusOSS/android_kernel_oneplus_sm8150/oneplus/SM8150_P_9.0/drivers/soc/qcom/eud.c)、
[realme 发布树](https://raw.githubusercontent.com/realme-kernel-opensource/realme_6pro_7pro_8pro_X2-AndroidR-kernel-source/master/drivers/soc/qcom/eud.c)，
以及之前核对的 MiCode cepheus、SM8250 和本轮 Sony/Nothing 树，均采用
ID → LEN → 连读 LEN 次 DAT 的基本路径，没有找到明确的另一个 FIFO advance 寄存器。
这些树存在相同代码，**不证明各量产机实际验证过 COM 多字节接收**。
厂商代码直接比较完整 32 位 ID，本机读回 90909090，仍需低 8 位处理，不能原样照抄。

当前主线 `drivers/usb/misc/qcom_eud.c` 管 USB 角色，不读取 COM_RX_DAT；本机自定义
compatible 由 tty 驱动独占匹配。`eud_earlycon.c` 只 TX，bootconsole 会退役。
EDK2 的 EudSerialPortLib 用 RAM 日志环，Read 返回 0；EudLogDxe 为启动服务期间的
TX 定时器。本轮审查的 Linux/EDK2 源码未找到第二个 RX 消费者。

截至核对的 [2026-10-07 v9 系列反馈](https://lkml.iu.edu/2610.0/12408.html)，
近期上游工作涉及 PHY 路由、端口和角色切换，Glymur-CRD 测试不等于 COM RX 测试。
没有找到可直接套用的多字节 FIFO 修复。

其他 SoC 有 ahb2phy clock vote 或 secure mode-manager 配置，不应把其寄存器地址
直接写进 SM8150。同 SoC 厂商 EUD 节点未提供相同显式 clock 资源，本轮未猜地址写入。
[2025 年 MODE_MANAGER2 权限补丁](https://lists.openwall.net/linux-kernel/2025/07/22/710)
解决的是 secure enable 控制，不能当作本机 DAT 的修复。

主机安装的是 qcusbser.sys 2.1.3.5（2018，oem102.inf）。公开 WDF serial 源码
`E:\eud-host\qcom-usb-kernel-drivers\src\windows\wdfserial\QCWT.c` 将写缓冲直接
交给 USB pipe，但版本不同，不能据此证明已安装旧二进制的线上行为相同。
本轮未取得 USB 线上的 OUT 数据包，Windows 驱动这一层仍未完全排除。

另外发现 QUIC 库 `src/eud.cpp` 的三参数 8 位 opcode/data/response WriteCommand 重载有具体错误：
先设置 opcode，随后 `memcpy(data_out_p, data, payload_sz - 1)` 又从首字节覆盖它；
目标应从 data_out_p+1 起。**session 37 更正：COM timeout API 实际调用正确的两参数
版本（memcpy 从 data_out_p+1 开始），没有调用上述错误重载。** COM 实现仍有原型代码。
**我们的 PowerShell 原始帧和 comtool 不调用这个重载**，所以它不能解释本轮现象。
未修改这份外部库，也没有把它记为已应用修复。
[QUIC COM issue #6](https://github.com/quic/eud/issues/6) 也未提供可用的接收实现答复。

## 33.5 是否是量产机限制

有这种可能，但**没有证据证明本机 COM 被限制为一个字节**。
[Linaro 的亲测文章](https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/)
说明 EUD 权限会受熔丝和 OEM 签名 debug policy 影响，同时记录了量产 OnePlus 6
可使用 EUD 的例子；文章当时未探索 COM。它支持“存在权限限制”，不支持“多字节
接收必被禁用”。

本机此前 SWD/AP DAP 的限制是相关线索，但不能直接迁移为 COM FIFO 的根因。
已经实现真实单字符输入、完整帧头和 F1，只证明相应功能可用，不排除细分限制。
本轮搜索没有找到 COM 单字节上限、RX read-pointer 熔丝或对应错误码的公开说明。
当前应同时保留主机传输、初始化/时钟、访问握手和权限配置等候选原因，不能定性为
硬件坏了、熔丝锁了，或简单归咎于主线缺代码。

## 33.6 最终版本与复测

源码副本：`linux-port/eud.c`，与 WSL `drivers/tty/serial/eud.c` 相同。

| 产物 | SHA-256 |
|---|---|
| eud.c | 311e5508fccb8d6f0623ba21e7f5891e4fda45984ba9dd6c3a76168037c6d411 |
| Image | 8acd3b00a713aa4c0203cc57d32ab9b6e5914fed7b7e0acbfddb849c179cc044 |
| logdump-rx33-console.img | d5a36aa2152dd77735f1ea8861f05ad35cb7f714605d5c3cd9db106b6c5f8953 |

产物均在 `E:\edk2-samurai-out\`。`make -j12 ARCH=arm64
CROSS_COMPILE=aarch64-linux-gnu- Image` 成功，无本轮编译警告；打包成功后才刷入。

最终真机逐个发送 i/d/回车并等待受理，返回 `uid=0 gid=0` 与 shell 提示符。
抓包 `rx33-final-i.raw`、`rx33-final-d2.raw`、`rx33-final-enter.raw`；d 第一轮未见
ACK，不计成功。ABC 仍失败如上表。`rx33-final-F1.raw` 包含
`eud: reboot2 bootloader requested`，主机确认 `62bc28a1 fastboot`。
随后再次 reboot 回同版 Linux，端口按 finally 关闭。
重新枚举 COM 后 `rx33-final-return-ABC.raw` 再次收到内核探针输出，确认已回到 Linux；
仍为 `41 90 90`。先前仅抓取 25 s 的零捕获不能作为启动失败证据。

诊断源码留档：`E:\edk2-samurai-out\eud-rx33-wait.c`、`eud-rx33-order.c`；
本轮之前的单字符基线是 `eud-before-rx33.c`。诊断镜像 SHA-256：

| logdump 镜像 | SHA-256 |
|---|---|
| rx33-access | f44af1ceccf72d867f2971111a2b38d7609cf1a06749b61b157690632e0389a5 |
| rx33-mmio | 61fb35a9642ad5f0553b4b2063cd2abbe06918433ee2f11e3f303d789c56bc7d |
| rx33-wait | a4f9583afa1c7e55e181b2e4ee17d524f437fc5d468fc3bd368434d56a26b495 |
| rx33-order | 41a33dcef094a63d6a701a581913497a0e488bc9cbb1b5f3997817e9234a026b |

## 33.7 后续需要的新证据

优先获取 USB OUT 抓包，确认旧 qcusbser 实际发出的完整帧、包边界和受理时序；或用
受控的另一条主机传输路径对照。其次需要 SM8150 COM RX 的硬件握手/时钟说明，
以及同 SoC 工程机/其他量产机的实测对照，才能验证权限假设。
不要原样重复已失败的 readb、200 μs、2/20 ms、nGnRnE、头部顺序实验。
在获得新证据前，逐字符长度 1 帧是已经验证的输入路径，不能包装成原生多字节修复。
