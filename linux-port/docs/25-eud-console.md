

---

## 25. EUD 真 console 落地 + 固件 cmdline/DTB 更新，等待真机验证（2026-10-07 18:1x）

> 历史版本记录。当前 tty 和 console 已搭建并实测，单字符 RX 可用；下文
> “TX-only”不再代表当前状态。临时交互入口见 [EUD-TERMINAL.md](EUD-TERMINAL.md)，
> 原生多字节 RX 未决情况见顶层 RX-CONSOLE.md 与 sessions/33。

### 25.0 产物（都已离线校验）

| 文件 | 大小 | sha256 | 用途 |
|---|---|---|---|
| `E:\edk2-samurai-out\boot-samurai-eudconsole.img` | 6,682,624 | `ea4a8f4e…` | 刷 boot 分区 |
| `E:\edk2-samurai-out\Image-rmx1931-samurai` | 30,116,352 | `fb1a6d6a…` | 放进 logdump FAT 的 `\Image` |
| `E:\edk2-samurai-out\samurai.dtb` | 94,739 | `68001bab…` | 可选，`\samurai.dtb` |
| 回滚-固件 | 6,680,576 | — | `boot-samurai-linux-console.img`（16:01，带 keep_bootcon） |
| 回滚-安卓 | 100,663,296 | `dfe18875…` | `backup\boot_stock_RMX1931.img` |

### 25.1 这次改了什么

1. **新驱动** `drivers/tty/serial/eud.c`（console-only，commit `e42788eaf`）：nbcon 三件套
   （`write_atomic` 有界会丢、`write_thread` 可睡眠、`device_lock` 用 `uart_port_lock_irqsave`）、
   帧长 4（6 entries ≤ FIFO ~7）、`dropped_bytes` sysfs。配套 `SERIAL_EUD_CONSOLE` Kconfig/Makefile、
   DTS 节点 `serial@88e0000`（`qcom,sm8150-eud-com`，2/2 cells）。
2. **earlycon 修 bug**：`EUD_COM_CHUNK` `6u` → `4u`，注释改写。
   §21.3 原来建议的「每个寄存器写之前都等 TX ready」是过度设计：`INT_STATUS_1` BIT(1) 是
   `eud_tx_empty`（整条 FIFO 排空），逐寄存器等会让每字节都等一次完整排空、慢 6 倍；
   真正的修法是**帧长 ≤ 深度**且**只在空闲时开始一帧、绝不中途停**。
3. **固件 cmdline**（`PlatformBm.c:62`）：加 `console=eud`（**放最后** = preferred → `CON_CONSDEV` →
   自动不重复回放 `CON_PRINTBUFFER`、自动注销 earlycon）、删掉 `keep_bootcon`。
4. **固件 FV 换新 DTB**：`FdtBlob/samurai/sm8150-realme-samurai.dtb` = 带 eud 节点的新版。

### 25.2 离线校验（在未压缩的 FVMAIN.Fv 上，不是 .fd）

```
cmdline: earlycon=eud,mmio,0x88e0000 console=tty0 console=eud loglevel=7 ignore_loglevel
         panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused
keep_bootcon 出现 0 次；console=eud 1 次；DTB 里 sm8150-eud-com 1 次
```

**坑（§19.2/§5 已记，这次又踩）**：`SM8150_UEFI.fd` 是 FVMAIN_COMPACT 压缩的，且 LoadOptions 是
**UTF-16**，所以对 .fd 直接 `grep console=eud`、`grep keep_bootcon` **一律假阴性（0）**。
要在 `workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.Fv` 上用 `strings -el`（UTF-16LE）查。

### 25.3 刷机顺序（有坑，别搞反）

§20.3 的固件是**注册完立刻启动** FAT 上的 `\Image`，所以：

1. fastboot 刷 **stock boot** → 进安卓；
2. 安卓 root 下 `mount /dev/block/by-name/logdump`，把新 `Image`/`samurai.dtb` 拷进去；
3. fastboot 刷 `boot-samurai-eudconsole.img`；
4. PC 侧 `eudtool com-up` + `comlog2 COM14 600 <log>`。

反了（先刷新固件）会启动**旧内核**，白刷一轮。EUD 开着时 USB 被占、fastboot 消失 → 长按电源 15 s 彻底断电。

### 25.4 验收判据（很明确）

1. 日志出现 `console [eud0] enabled` → 真 console 注册成功；
2. 日志**延续到内核后期**（不再 ~1.2 s 处断掉）→ 真 console 接管（这次特意删了 `keep_bootcon`，
   没注册成功就会早期截断，一眼可辨）；
3. `.raw` 里「数据字节数少于 LEN 的帧」= 0 → 帧边界不再错乱。

### 25.5 未落地：`/dev/ttyEUD0`（下一步）

tty/uart 版代码已经写好但**没落盘**：`uart_driver`(`dev_name="ttyEUD"`) + `uart_ops`
+ `start_tx` 只 `schedule_work()`（无 TX 中断，持 port spinlock 排空会关中断几百 ms 并卡住 printk）
+ `PORT_EUD 124` + `.device = uart_console_device` / `.data = &eud_uart_driver`。

原因：本环境的 shell 对大段文本不稳（here-string 与数组两种写法、2.4–7 KB 共 5 次，都在同一处被截断）。
下次用「分片 ≤1 KB 追加」写入，再编译 → 出 `0004` patch。
注意：EUD COM 是 **TX-only**，`/dev/ttyEUD0` 写得通、读永远没数据，这不是 bug。
