<!-- split out of DIAG-CAPTURE.md on 2026-10-08 (document 2 of 2), verbatim -->

# EUD 试水结果 + 会话交接（2026-10-06 16:5x）

## ✅ EUD 在本机可用（实测）

| 步骤 | 结果 |
|---|---|
| Android root 下 `echo 1 > /sys/module/eud/parameters/enable` | PC 立刻出现 `Qualcomm EUD Control Device 9501`（`VID_05C6&PID_9501`）+ `VID_05C6&PID_9500` 集线器 |
| 之前（未开启） | PC 上**没有**任何 VID_05C6 设备 |
| 代价 | adb/fastboot/USB 被接管；**必须长按电源 15s 彻底断电**才能恢复（热重启可能保持 EUD 开启 → fastboot 找不到） |

**结论：这台量产机的 EUD 没有被熔丝禁用。**

## 寄存器（内核 `enable_eud()` 同款）

```c
base = 0x088E0000            // DTB: qcom,msm-eud@88e0000
writel(BIT(0),             base + 0x1014);   // CSR_EUD_EN
writel(BIT2|BIT3|BIT4,     base + 0x0024);   // INT1_EN_MASK = 0x1C (VBUS|CHGR|SAFE_MODE)
```
本机 DTB 无 `qcom,secure-eud-en` → 不需要 SCM，普通 MMIO 即可（所以 EDK2 也能做）。

## EDK2 侧：已实现 + 已构建，**尚未刷机验证**

- `samurai.dsc` 加 `-DSAMURAI_ENABLE_EUD`
- `PlatformBm.c`（BDS 阶段）在 `#ifdef SAMURAI_ENABLE_EUD` 里写上述两个寄存器各 10 次（间隔 200ms），并用 `Print()` 上屏标记
- 确认 `[SAMURAI-EUD]` 字符串已编入 FV

| 镜像 | sha256 | 状态 |
|---|---|---|
| `boot-samurai-eudtest.img` | `a2819fbafe2e2eb4774fcdd22c4cb7ac2c1d718b463e30c8638835575e8b1ce8` | **未刷，待验证** |
| `boot-samurai-release3.img` | `c9feb0cab6abb66b4f3722f041449034d908c15bbf9a95b7903e394026360cde` | 正式版（三键可用，未真机验证此版本） |
| `backup\boot_stock_RMX1931.img` | `dfe18875…` | 回安卓 |

**验证方法**：长按电源 15s 彻底断电 → 音量下+电源进 fastboot → 刷 eudtest → 期望屏幕出现
`[SAMURAI-EUD] CSR_EUD_EN=0x00000001 INT1_EN_MASK=0x0000001c`，PC 出现 VID_05C6 设备。
失败则说明 BDS 时 USB PHY 未就绪 → 把写入挪到更晚的时机或加更长的重试。

## GitHub

- 仓库 `hmhmdcy/edk2-realme-x2-pro`，`master` = **`4b50685`**（EUD + 交接文档），上一个 `696bf82`（按键修复）
- 新增文档：`Platform/Realme/sm8150/EUD.md`、`HANDOVER.md`（完整交接，见 `E:\RealmeX2Pro edk2\HANDOVER-NEXT.md`）

## 下一个会话的起点

1. 刷 `boot-samurai-eudtest.img` 验证 EDK2 能否自己开 EUD
2. 配 PC 侧 OpenOCD（`usbipd-win` + WSL 编译 `linux-msm/openocd`，或原生 Linux）
3. 可选：`startup.nsh`、samurai DSDT、`USE_DISPLAYDXE`、固件内 RAM 日志环形缓冲（这样 OpenOCD/pstore 就能读到完整日志，不用拍照）

**安全**：只刷 boot 分区；U 盘模式勿让 PC 格式化；EUD 开启后务必彻底断电恢复。
