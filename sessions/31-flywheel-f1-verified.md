# 31. 飞轮 F1：Linux 自己重启进 fastboot（2026-10-08 晚，真机验证）

> 来源：2026-10-08 晚四轮真机实验（A / B / C / F1）。用途：记录 EUD 命令通道
> 打通到"免按键回 fastboot"的全过程与证据。
> 关联：`FLYWHEEL.md`（使用手册）、`RX-CONSOLE.md`（RX 协议）、
> `linux-port/docs/28-flywheel.md`（原始设计）、`HANDOVER-NEXT.md` §1/§7。

## 31.1 结论

1. **免按键回 fastboot 打通**：主机发 `[90][02]`，驱动打印
   `eud: reboot2 bootloader requested`，写 `CSR_EUD_EN=0` 交还 USB，
   `kernel_restart("bootloader")` → PON magic → ABL → fastboot。
   实测 `fastboot devices` 出现设备，**全程无按键**。
2. **命令编码进长度字段**：`id` 恒为 `0x90`；`len=2` = 回 fastboot。payload 未解也
   不影响命令通道。
3. **payload 仍未解**：读 `0x14` 的第一个字节永远是 `0x90`（id 本身），且
   `EUD_INT_RX` 门控在这一次读之后就被清掉。主假设：这台机器 `0x14` 装的是整帧
   `[id][len][payload…]`，payload 在偏移 2。探针（`len>=3`）已实现、未跑。

## 31.2 四轮实验与证据

| 轮次 | 镜像 | 主机帧 id | 结果 |
|---|---|---|---|
| A | `logdump-intrx2.img` | 0x81 / 0x82 / 0x83 | 22 帧**全部没被设备暂存**（闩锁没变）；只有最后那帧 `[90][03]"ABC"` 进了闩锁。未 wedge。 |
| B | `logdump-intrx3.img` | 全 0x90 | id 0x90 被接受 ✓；重复帧也能识别 ✓；但读回的字节是 `0x90` |
| C | 同上，主机间隔拉到 2.5 s | 0x90 | 15 帧只 7 帧被暂存（**投递率 ~1/3**）；仍读回 `0x90`；设备把读到的字节回显成一帧 `90 01 3F`（`?`） |
| F1 | `logdump-f1c.img` | 0x90 | **`[90][02]` → 自己回 fastboot ✓** |

关键原文（手机控制台，经 `parse-eud.ps1` 重组）：

    [  83.577829] eud: rx id=90 len=01 s1=07070707
    [  83.618584] eud: byte[1/1]=90 s1_after=06060606 poll=2117
    ...
    [ 274.181644] eud: rx id=90 len=03 s1=07070707        （A 轮，唯一被暂存的帧）
    ...
    [  70.662708] eud: rx id=90 len=02 s1=07070707         （F1 轮）
    [  70.702349] eud: reboot2 bootloader requested
    主机：COM 口立刻断开 "The port is closed"
    PC：  fastboot devices -> 62bc28a1 fastboot

第一版 F1（`logdump-f1.img`）失败，因为驱动等 payload 收齐才分发：`len=02` 的帧
读完第 1 个字节后门控清零 → 整条消息被放弃 → 命令永远到不了。改成**读到头部即执行**
（`EUD_F1_EARLY`）后一次通过。

## 31.3 F1 的实现（两处改动）

1. `arch/arm64/boot/dts/qcom/sm8150-samurai.dts`：

       &pon {
               mode-bootloader = <0x02>;
               mode-recovery   = <0x01>;
       };

   （vendor DTB 本来就有这两个 magic；mainline `qcom-pon.c` + reboot-mode 按
   `mode-` 前缀匹配。`POWER_RESET_QCOM_PON=y`、`REBOOT_MODE=y` 已开。）

2. `drivers/tty/serial/eud.c`：新增 `eud_reboot_cmd()`，在**读到头部**时判定
   `id==0x90 && len==2` → 先 `writel(0, CSR_EUD_EN)` 再
   `kernel_restart("bootloader")`。

**不需要 `reboot2` 小工具**（28.1 设想的 userspace helper）：驱动内建，
`kernel_restart()` 直接调用，PON notifier 负责写 magic。

## 31.4 DTB 与打包的两条路径

* 固件 DTB（权威）：`Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb`
  ← 由内核树 DTB 拷贝而来；改完重编固件（`./build.sh -d samurai --toolchain GCC5`）
  并 `fastboot flash boot`。
* logdump FAT 里的 `\samurai.dtb`（副本，一并换）：offset **30208000**，94739 B，
  原地替换（尺寸未变）。
* logdump FAT 里的 `\Image`：offset **90112**，恒 30116352 B，原地替换。
* 产物：`boot-samurai-f1.img`（sha256 `8c9dea12…`，6,678,528 B）、
  `logdump-f1c.img`、`logdump-probe.img`（Image sha256 `f147d4d5…`）。

## 31.5 上游参考（payload 部分）

* `kernel/msm` tty 驱动：`#define UART_ID 0x90`、`MAX_FIFO_SIZE 14`；
  RX 是**中断门控 + burst 读 len 次**，帧内不再查状态位。
* QUIC 官方主机库 `com_api.cpp`：*"byte 0 is Exec Env ID. byte 1 is how many bytes
  data. remaining bytes are data."*，门控只到"有没有数据"。
* 结论：**逐字节门控是本项目的偏离**，为绕开"burst 读会卡死 COM 块"而引入。
* COM 口是命令帧 + 数据帧共用（`com_eud.h`）：`0`=NOP、`1`=TX_TMOUT、`2`=RX_TMOUT、
  `3`=PORT_RESET，形态 `{opcode,0xFF,0xFF,0x00,0x00}`；数据帧首字节 `0x90`。

## 31.6 事故：主机 COM 口卡死（F2 的硬约束）

一次被中断的抓包脚本让 Windows 的 qcser 驱动把 COM14 钉在 "resource in use"。
试过且**全部无效**：`com-off`/`com-up`（3 次）、`detach`/`com-up`、
`eudtool rst`（CTL 0x09 PERIPH_RST）、杀掉所有旧 pwsh 会话、从子进程打开、
把手机彻底重启（USB 设备消失又出现）。只有**换 USB 口（换设备节点）**或
**重启主机**能解。

→ 飞轮守护进程必须：`try/finally` 关端口、一次只允许一个进程持有、每轮用新进程。
附带教训：`fastboot devices` 在常驻会话里可能挂死（放 `Start-Job` 里正常）；
PS 5.1 下 switch 参数不能 `[bool]` 强转（会恒为 true）。

## 31.7 下一步

1. **跑 payload 探针**：发 `[90][03]"ABC"`，看 `0x14` 连续读出 `41 42`（payload 在
   FIFO）还是 `90 03`（整帧在 FIFO → payload 偏移 2）。
2. 按结果修正读法 → `[90][01]` 打字可用 → 再把 recovery / EDL 加进命令表。
3. F2 守护进程（`FLYWHEEL.md` §7）。
4. pstore 路径未必可用（用户 2026-10-08 备注），28.1 的 panic→fastboot 兜底要另想办法。