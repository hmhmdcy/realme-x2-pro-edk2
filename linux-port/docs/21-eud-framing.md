
---

## 21. EUD 日志乱码的真因：内核侧 FIFO 溢出，不是主机重组（2026-10-07 16:0x）

### 21.1 现象

`keep_bootcon` 之后 EUD 能拿到整个启动过程的日志，但文字是花的，像这样：

```
[15:56:23.808]  32-bix51df8ux ver+ (cy1inux-gubuntus for .00000 lack odel: [    0e ]---ic_iorules l.00000ID: 0 tainte[    0Realme[    0[    0[    0prot+00] sp [
```

一开始怀疑是主机侧 comlog 的帧重组有问题。**查过之后：主机侧确实该修，但乱码的真因在内核侧。**

### 21.2 真因：一帧往 TX FIFO 里塞 8 个值，而 FIFO 只有约 7 个字节深

`drivers/tty/serial/eud_earlycon.c` 的 `eud_write()`：

```c
#define EUD_COM_CHUNK 6u
...
writel_relaxed(EUD_COM_UART_ID, base + EUD_REG_COM_TX_ID);   /* 值 1 */
writel_relaxed(chunk,             base + EUD_REG_COM_TX_LEN); /* 值 2 */
for (i = 0; i < 6; i++)
        writel_relaxed(s[i],      base + EUD_REG_COM_TX_DAT); /* 值 3..8 */
eud_wait_tx(base);                                            /* 只在整帧写完后才等 */
```

每个寄存器写 = 主机侧看到的 1 个字节（`0x90`, `LEN`, 数据…），所以**一帧共 8 个字节**。
而这块硬件的 TX FIFO 只有约 7 个字节深——交接文档 §2 早就记过："A whole string written in one go is
truncated by the TX FIFO after about seven payload bytes."

**后果**：每帧最后 1~2 个字节被硬件丢掉 → 下一帧的 `0x90` 被当成上一帧的数据 →
**帧边界从这一刻起永久错位**，之后所有内容都是错位拼接出来的。
**主机侧再怎么重组也救不回来**，因为边界信息已经在硬件里丢了。

（这也是为什么 EDK2 那条路径当初要用"6 字节帧 + 200 µs/字节 + 2 ms/帧"的节奏——它靠**延时**而不是流控来避免溢出。内核 earlycon 里没有校准好的定时器，不能用 `udelay`，所以必须改成**逐字节流控**。）

### 21.3 内核侧修法（下次重编内核时一起改）

两个改动：

1. **每个寄存器写之前都等 TX ready**，而不是整帧写完才等；
2. **每帧缩到 4 个数据字节**（ID + LEN + 4 = 6 个值），稳在 FIFO 深度以内。

```c
#define EUD_COM_CHUNK 4u        /* ID + LEN + 4 = 6 writes, under the FIFO depth */

static void eud_putreg(void __iomem *base, unsigned int off, unsigned int v)
{
        eud_wait_tx(base);      /* INT_STATUS_1 BIT(1), same bit as the vendor eud_tx_empty */
        writel_relaxed(v, base + off);
}

static void eud_write(struct console *con, const char *s, unsigned int n)
{
        ...
        while (n) {
                unsigned int chunk = min(n, EUD_COM_CHUNK);

                eud_putreg(base, EUD_REG_COM_TX_ID, EUD_COM_UART_ID);
                eud_putreg(base, EUD_REG_COM_TX_LEN, chunk);
                for (i = 0; i < chunk; i++)
                        eud_putreg(base, EUD_REG_COM_TX_DAT, s[i]);

                s += chunk;
                n -= chunk;
        }
}
```

`eud_wait_tx()` 里有 `EUD_TX_POLL_LIMIT` 上限，所以即使状态位读错也不会挂死启动。

### 21.4 主机侧：`comlog2`

老 `comlog.exe`（`comlog.cpp`）除了不能处理错位，本身还有几个问题，所以写了个 `comlog2.cpp`：

| 问题 | comlog2 的做法 |
|---|---|
| 启动时往串口写了 10 个字节（`WriteFile(p1/p2)`），污染流 | 只读，不写 |
| 帧边界错位后无法恢复 | `LEN == 0 \|\| LEN > 64` 即判定错位，立刻重新扫 `0x90`，并统计次数 |
| 看不到真实字节流 | **额外把原始字节流完整写成 `<log>.raw`** |
| 每 50 ms 才读一次，容易丢 | 连续读（`ReadIntervalTimeout = MAXDWORD`） |

编译（**必须在 MSYS2 环境里跑**，直接调 `g++.exe` 会因为它找不到 `cc1plus` 而**静默退出 1**）：

```sh
# 方式一
E:\msys64\msys2_shell.cmd -ucrt64 -defterm -no-start -here -c "cd /e/eud-host && g++ -O2 -o comlog2.exe comlog2.cpp"
# 方式二：开 MSYS2 UCRT64 终端
cd /e/eud-host && g++ -O2 -o comlog2.exe comlog2.cpp
```

用法与老的一样：

```
comlog2.exe COM14 600 E:\eud-host\out.log      # 同时写出 out.log.raw
```

### 21.5 怎么验证

1. 用 comlog2 抓一次，检查 `out.log.raw`：统计"数据字节数少于 LEN 的帧"有多少——这个数字就是 FIFO 溢出的频率；
2. 内核侧按 §21.3 改完再抓一次：`.raw` 里应该每帧完整、`0x90` 只出现在帧首，乱码消失。

### 21.6 后续（顺带记下）

- 把 `eud_earlycon.c` 升级成**真正的 console 驱动**（注册 `struct console`，支持 `console=eud`），
  这样日志通道不再依赖 `keep_bootcon`，也不会每次为日志参数重刷固件；下游 4.14 的
  `drivers/soc/qcom/eud.c`（`ttyEUD`）是参考实现。
- 上述内核改动应走正式的 `format-patch`，放进 `linux-port/patches/`（当前内核树在
  `~/x2pro-linux/linux`，已有两个提交：`e4858b30a` earlycon、`0450fd895` DTS）。