# USB 同线 host-resume：标准分层实现（2026-11-10）

> **2026-11-11 禁用**：板级 keep-connect opt-in 已关闭。没有可信的
> VBUS/attach 源时，它会通过 `dp_hs_phy_irq` 伪唤醒 suspend，并曾在
> 插线 resume 后触发 Windows Code 43。本文仅保留为历史记录；当前结论见
> [USB-REMOTE-WAKE-20261111](USB-REMOTE-WAKE-20261111.md)。

## 状态

内核、Qcom glue、板级 DTB 和部署载体已完成，并在 RMX1931 上启动到最终
release `7.3.1-rmx1931-samurai-v731-usbwake`。部署仍是安全的 U3-only
版本：Windows NCM 驱动保持 U0 时，系统 suspend 返回 `-EBUSY`，手机保持
唤醒，SSH/NCM 不会因休眠丢失。

调试飞轮另装了 debug-only 的 `usbwake-debug`：它通过上游
`sleep-inhibitor` 在“外部电源在线或 NCM carrier up”时持有睡眠锁，因此
调试时不会因为手机单独熄屏/空闲而切断 SSH。它没有修改官方
`/etc/sleep-inhibitor.conf`，也没有进入正式 `samurai-platform`。

仍未取得一次“USB host resume 唤醒手机”的成功样本；`host_resume_verified`
和 `u0_usb_wake_verified` 都保持 `false`。成功的是“不睡眠所以 NCM/SSH
不断线”，不是 U0 唤醒。

这不是把 soft-disconnect 改掉就结束的 DTB 改动。实现保持三层边界：

| 层 | 内容 | 位置 |
| --- | --- | --- |
| L1 通用 DWC3 core | `snps,gadget-keep-connect-sys-sleep` 语义，链路活跃时拒绝系统睡眠 | `0006-usb-dwc3-gadget-keep-connect-sys-sleep.patch` |
| L2 Qcom glue | peripheral role 布防已有的 DP/DM/SS PDC wake IRQ；keep-connect 时保留 clocks/interconnect | `0007-usb-dwc3-qcom-peripheral-wake.patch` |
| L3 板级 DT | 只打开 `wakeup-source` 和 keep-connect 策略 | `0008-arm64-dts-samurai-usb-host-resume.patch` |
| L4 用户空间 | 不新增常驻服务；NCM/configfs 生命周期不变 | 现有 `samurai-usb` |

## 上游依据

通用 core 语义来自尚未合并的 RFC：

- [RFC PATCH 0/2](https://lkml.iu.edu/hypermail/linux/kernel/2303.2/04359.html)
- [RFC PATCH 2/2](https://lkml.iu.edu/hypermail/linux/kernel/2303.2/04358.html)

Qcom binding 已经把 `dp_hs_phy_irq` / `dm_hs_phy_irq` / `ss_phy_irq`
描述为 wakeup IRQ，SM8150 DTS 也已把它们接到 PDC；缺的是 driver 在
peripheral role 去 `enable_irq_wake()`。本实现没有新增板级 USB 驱动，
也没有在 DWC3 里硬编码 GPIO 或 PMIC。

### 多源检索结论

Qualcomm 平台的 USB 系统唤醒不是“任意 USB 包都能从 U0 唤醒”：

- 2021 年 `dwc3-qcom` host wake 讨论明确要求用 **PDC** 代替 GIC，
  因为 XO shutdown 时 GIC 唤醒路径不可用；
- 2023 年 DP/DM wake IRQ 修复把 HS/FS 的 DP 边沿改为 **falling**，
  用于同时检测 disconnect 和 remote wakeup；PDC 仍是父控制器；
- DWC3 gadget keep-connect RFC 只允许 link 已经进入 **U3/L2** 的系统
  睡眠；活动链路 U0 不在其语义内；
- binding 中的 `hs_phy_irq` 是“默认不触发、与 DP/DM/QUSB2 互斥”的
  PHY 事件线；mainline `dwc3-qcom` 没有把它实现成 U0 通用唤醒源；
- Linux 公共接口是 host 侧 `power/control=auto` +
  `autosuspend_delay_ms`，不是 DWC3 里的私有 GPIO。

因此，标准可用的链路是：

```text
host autosuspend -> USB link U3 -> DP/DM PDC wake IRQ -> phone resume
```

而 U0 下依赖 DWC3 GIC IRQ 唤醒 s2idle 没有 mainline 公共路径。

参考：

- [Qualcomm PDC USB wake series](https://lore.kernel.org/linux-usb/20210331040824.28772-1-wcheng@codeaurora.org/)
- [PDC wakeup support](https://lore.kernel.org/linux-usb/20210406122321.15393-1-wcheng@codeaurora.org/)
- [DWC3 gadget keep-connect RFC](https://lkml.kernel.org/r/20230320093447.32105-1-rogerq@kernel.org)
- [Qcom DWC3 binding: DP/DM/SS wake IRQs](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/devicetree/bindings/usb/qcom,snps-dwc3.yaml)

## 行为

- 只有显式带 `snps,gadget-keep-connect-sys-sleep` 的 DT 才启用。
- gadget 已连接但 USB link 仍是 `On/U0` 时，系统 suspend 返回
  `-EBUSY`，避免在无法处理 USB 事务时睡下去。
- link 进入 `Suspend/U3` 后，core 不 soft-disconnect、不 `dwc3_core_exit`；
  Qcom glue 保留 clocks/interconnect，并 arm DP/DM PDC wake IRQ。
- resume 时只重新使能 gadget IRQ、处理 pending event；不重新初始化
  controller/PHY。
- NCM 的 configfs 生命周期不变；如果主机重新枚举，现有
  `samurai-usb`/network 恢复路径仍负责 carrier 和地址。

## 产物

Release：

```text
7.3.1-rmx1931-samurai-v731-usbwake
```

| 产物 | SHA-256 |
| --- | --- |
| `Image` | `fe9e623a1276a25fe03fa73c55f7cbe345c03b4150f28da730ded29304772ecf` |
| `sm8150-samurai.dtb` | `9648ca7f8dbba077c7474b2687ccdbf54b6f9c26fd196e50acf007f7d7e9cb52` |
| boot carrier | `b9e9e53129d7d82401385a6f096af8a260a3b3d9e63d5940f7516424f4e6a438` |
| logdump FAT | `2d91d2eae5a65e0f38509d02e2fcdb89954063fcdbe372e10424f0a54041db94` |
| modules tar | `32ac83ef4b082eb99c7efc9167a0dd01b695053a53707cf00a7133ce90a16aaf` |

boot carrier 相对源 boot `62dee7b9…` 只改变 DTB FFS
`25462cda-221f-47df-ac1d-259cfaa4e326`；其余 100 个 main FFS、BDS、
compat DTB 和 ramdisk 保持不变。

最终产物目录：

```text
E:\edk2-samurai-out\standard-arm64-v731\usbwake-final-20261110\
```

其中包含 `Image`、`sm8150-samurai.dtb`、`boot-eud-production-off.img`、
`logdump-usbwake.img`、773 模块归档和 `manifest.json`。`usbwake1` 的
Image `15851c6e…`、logdump `70fde22d…` 和 boot_id
`9b3f38f2…` 只作为历史证据保留，不再是当前部署。

实验性 U0 构建（`usbwake2`，**未部署**）保留在
`E:\edk2-samurai-out\standard-arm64-v731\usb-active-link-20261110\`：

| 实验产物 | SHA-256 |
| --- | --- |
| Image | `6354e8dd271764109903c8f46c25c22bb81565774c74bc9b646dcd08543da238` |
| DTB | `964799445c221488dd87241cc3a666d966bf2e3ff66c5f9b98b49a8a371ce675` |
| modules tar | `3ac692fa3d513419cf648a14977337af10f0b8d89f53287377c8f9006890e277` |
| boot carrier | `74b3fa08ac7a57871807b6fdc18982477b3d83ce1c9535ca632b9fecd9e33b51` |
| in-place FAT | `3ef713e2789a1ff9c75e7282fdf3b484af8c03efc8e878396a055c470ed4f0d3` |

## 已真机验证

最终 `usbwake` 部署的运行时证据：

```text
uname -r = 7.3.1-rmx1931-samurai-v731-usbwake
boot_id before = 9b3f38f2-8233-4425-a20a-d921edc8381b
boot_id after  = b0964a6b-84e5-458a-a944-0c2538e6bc3a
/proc/device-tree/.../usb@a600000/wakeup-source 存在
/proc/device-tree/.../usb@a600000/snps,gadget-keep-connect-sys-sleep 存在
/sys/bus/platform/devices/a600000.usb/power/wakeup = enabled
UDC state = configured
UDC current_speed = high-speed
usb0 = 169.254.42.1/16 + 10.42.0.1/24, carrier=1
wlan0 = 192.168.0.114/24, connected
Wi-Fi SSH to 192.168.0.114 = ok (independent of NCM)
boot partition readback = b9e9e531… (matches candidate)
logdump partition readback = 2d91d2ea… (matches candidate)
module_count = 773
module load/unload probe = nbd ok
usbwake-debug service = started
USBwake sleep inhibitor count = 1
usbwake-guard power/ncm/either rc = 254 / 254 / 254
official /etc/sleep-inhibitor.conf = 9c6ca8ec… (unchanged)
taint = 512 (also 512 before deployment; pre-existing clk warnings)
```

活跃链路下的受控 suspend 尝试：

```text
PM: suspend entry (s2idle)
dwc3-qcom a600000.usb: PM: dpm_run_callback():
  dwc3_qcom_pm_suspend returns -16
PM: Some devices failed to suspend
PM: suspend exit
```

`boot_id` 不变，`suspend_stats` 为 `success: 0; fail: 1`。这证明
keep-connect 的 U3 门禁生效，没有把活跃 USB 事务带进睡眠。

## 未完成的验收

当前 Windows 主机即使启用 USB selective suspend，`UsbNcm` 端口仍长期
保持 `On/U0`；因此 `dwc3_gadget_suspend()` 按设计返回 `-EBUSY`，无法
进入 L2 qcom wake IRQ 布防和 host resume 测试。

### 不要用主机 S3 作为常规测试

为了确认主板睡眠时是否保留 VBUS，曾临时让 Windows 进入 S3。这是
诊断手段，不是本功能的运行方式，也不应作为默认验收流程：目标始终是
手机进入 `s2idle` 后由 USB resume 唤醒手机，而不是让电脑睡眠。

那次诊断证明了两点：

- Windows S3 期间手机侧确实进入 `Suspend/U3`，不是 `Disconnected`；
- Windows 的 `UsbNcm` 没有 WDF 空闲电源策略，不能代替 selective
  suspend 做日常触发。

### U0 active-link 实验结论：不可部署

另外做了一次 U0 active-link 实验：保留 DWC3/clocks/interconnect，不
soft-disconnect，并在 `dwc3_gadget_suspend()` 里把 gadget IRQ 设为
wake-capable。手机确实进入了 `s2idle`（`success=1`，同一 boot_id，
link 仍 `On`），但 USB ping 没有唤醒 SoC；测试脚本的 RTC 安全闹钟在
约 45 秒后恢复，之后 USB ping 才得到响应。`a600000.usb` 的
`wakeup_sources` 事件仍为 0。原因与上面的检索一致：DWC3 IRQ 是 GIC
IRQ，不是 PDC wake 线，U0 下没有可用的 SoC 唤醒路径。

该实验补丁已移到
`patches/experiments/0009-usb-dwc3-gadget-keep-connect-active-link.patch`，
**不进入 v7.3.1 部署**。部署已回退到 U3-only：Windows 主机保持 U0 时
拒绝系统 suspend，手机/SSH 保持在线；Linux 主机完成 autosuspend 后才
使用 PDC wake IRQ。

随后一次“手机先 U3、再系统 suspend”的组合测试取得
`suspend_stats/success = 1`，但手机只睡了约 0.6 秒就提前唤醒，主机
仍在 S3 中约 57 秒后才恢复。因此这不是成功的 host-resume 样本。
目前还不能把提前唤醒归因于 `dp_hs_phy_irq`：该计数器在之前的 S3
诊断中已经增加过，必须用同一轮的 before/after 计数判断。测试脚本
现在会记录完整的 `wakeup_sources`、PDC/PHY/RTC/charger IRQ 和
`pm_debug_messages`，用于下一次真实验收。

要完成验收，需要满足其一：

1. Linux 主机对 NCM 设备启用 autosuspend：

   ```sh
   sh linux-port/scripts/linux-host-usb-autosuspend.sh
   # 确认手机侧 link_state 变为 Suspend/U3
   ```

   然后在手机侧运行
   `SAMURAI_ALLOW_SUSPEND=1 linux-port/scripts/test-usb-host-resume.sh 90`，
   并在 RTC 到期前向 `10.42.0.1` 发送 NCM 流量。

   这个脚本只使用 Linux USB 公共接口
   `/sys/bus/usb/devices/<bus-port>/power/control=auto` 和
   `autosuspend_delay_ms`；不依赖板级私有驱动。主机把 NCM 设备置入
   autosuspend 后，手机侧应先在 `/sys/kernel/debug/usb/a600000.usb/link_state`
   看到 `Suspend`，再启动手机侧测试。

2. Windows 管理员临时 disable/enable NCM 适配器，使 USB function
   进入 selective suspend；需要确认 disable 后手机侧是 `Suspend/U3`
   而不是断开。若 disable 直接导致 `Disconnected`，本层无法完成
   same-cable 测试，应改用 Linux 主机。

如果目标是“Windows 主机保持唤醒、手机进入睡眠、任意 NCM 包唤醒手机”，
当前 SM8150 mainline + Windows `UsbNcm` 组合没有公共接口：Windows 不会
把端口置 U3，U0 又没有 PDC wake 路由。此时应使用 Linux host autosuspend，
或者用标准 `sleep-inhibitor` 保持手机在调试 SSH 期间不进入系统睡眠。

### PinePhone 式插电不休眠

调试期新增了 `linux-port/debug/sleep-policy/usbwake-guard`，通过标准
`sleep-inhibitor` 实现 PinePhone 的“插电时不自动休眠”策略，不写用户
`powerdevilrc`，也不绑定 KDE。默认 `either` 模式在以下任一条件成立时
持有 sleep 锁：

- `/sys/class/power_supply/*` 中存在 online 的 Mains/USB/USB_PD 等外部电源；
- `samurai` NCM gadget 已绑定 UDC，`usb0` carrier 为 1。

策略代码不依赖本板名称：NCM 侧会扫描所有 configured UDC、匹配对应
ConfigFS gadget，再从 `ncm/ecm/rndis/eem` function 读取 `ifname` 并检查
carrier；电源侧扫描 `/sys/class/power_supply/*`。本机外部电源节点是
`mp2650-input`（`type=USB`，插线时 `online=1`），仅作为运行时示例。
`power` 模式可以完全复现 PinePhone 的插电策略；`ncm` 模式更窄，只保护
已工作的 NCM 链路。该守卫是 debug-only，不进入 `samurai-platform`，也不
应在验收 U3/L2 host resume 时加载，因为它会有意阻止插电状态下的 suspend。
启动、检查和使用边界见
[`linux-port/debug/sleep-policy/README.md`](../debug/sleep-policy/README.md)。

可复现调试部署使用独立的 `usbwake-debug` OpenRC 服务，经官方
`sleep-inhibitor` 执行；服务名和插件不包含板名/SoC 名，只通过
`/etc/conf.d/usbwake-debug` 选择 `either`、`power` 或 `ncm` 模式。
该服务不修改 `/etc/sleep-inhibitor.conf`，不进入 `samurai-platform`，
也不加入正式 runlevel。

### 2026-11-10 最终 `usbwake` 刷入与验收

刷入脚本默认 dry-run，先校验 boot/logdump 的固定尺寸和 SHA-256，再按
`logdump -> boot -> reboot` 顺序执行；任一步失败都不会继续：

```powershell
& E:\RealmeX2Pro edk2\linux-port\scripts\flash-v731-usbwake-final.ps1
& E:\RealmeX2Pro edk2\linux-port\scripts\flash-v731-usbwake-final.ps1 `
  -FlashPair -Reboot -WaitSeconds 120
& E:\RealmeX2Pro edk2\linux-port\scripts\verify-v731-usbwake-final.ps1
```

设备进入 bootloader 使用主线 `reboot-mode` 的 `RESTART2("bootloader")`
路径；刷写只写 `logdump` 和 `boot`，没有写 GPT、NV、persist、
calibration 或 userdata。最终 manifest 位于
`E:\edk2-samurai-out\standard-arm64-v731\usbwake-final-20261110\manifest.json`。

同一 release 上的服务启停幂等性：

```text
initial USBwake inhibitor count = 1
restart 1/2/3                 = 1 / 1 / 1
after stop                    = 0, no usbwake-run/sleep-inhibitor child
after start                   = 1, service started
```

离线插件矩阵 18 项全部通过，包括 Mains/USB 外部电源、battery 排除、
status fallback、NCM/ECM/RNDIS、carrier down、UDC/gadget 不匹配和三种
mode；插件源码中没有 `samurai`、`usb0`、`a600000`、SM8150 或 mp2650
硬编码。设备端文件与仓库源码 SHA-256 一致。

### 历史：`usbwake1` debug-only 验证

在 `7.3.1-rmx1931-samurai-v731-usbwake1`、同一 boot
`9b3f38f2-8233-4425-a20a-d921edc8381b` 上完成：

```text
UDC state = configured
link_state = On
usb0 carrier = 1
a600000.usb power/wakeup = enabled

USBWAKE_GUARD_MODE=power  -> 254
USBWAKE_GUARD_MODE=ncm    -> 254
USBWAKE_GUARD_MODE=either -> 254
模拟拔电/无 NCM           -> 0
```

临时 `sleep-inhibitor` 实例启动后，
`elogind-inhibit --list` 出现 `Plugin USBwake power/NCM guard (debug only)`
的 `block` inhibitor；停止后该条目、`sleep-inhibitor` 子进程和
`elogind-inhibit` 子进程均消失，没有留下常驻锁。初版临时验证使用设备的
`/root/usbwake-debug/`；没有写入 `/etc/sleep-inhibitor.conf`，也没有
安装进 `samurai-platform`。

随后把同一策略收敛为 `usbwake-debug` OpenRC 服务：

```text
mode = either
service = started
runlevel = default
official /etc/sleep-inhibitor.conf sha256 =
  9c6ca8ecb04ca042abab57d0f1b44ac2dbcfbc5d9f1962185a1bcfe3b51cab99
3 次 restart 后 USBwake inhibitor count = 1
stop 后 USBwake inhibitor count = 0，无 usbwake-run/sleep-inhibitor 子进程
start 后 inhibitor count = 1
```

服务由通用 `/usr/libexec/usbwake-guard`、
`/usr/libexec/usbwake-run`、`/etc/usbwake-sleep-inhibitor.conf` 和
`usbwake-debug` OpenRC 文件组成；插件自动发现 UDC、ConfigFS gadget、
`ncm/ecm/rndis/eem` function 与 ifname，不包含 `samurai`、`usb0`、
`a600000` 或 SM8150 硬编码。

不要再用主机 S3 作为常规测试；只有在明确允许、且已经确认自动唤醒
定时器和物理恢复路径都可靠时，才可把 S3 当作一次性的诊断夹具。

成功判据：

- `boot_id` 不变；
- `suspend_stats/success` 增加；
- `/sys/kernel/debug/wakeup_sources` 出现 `a600000.usb` 的 event；
- `link_state` 从 `Suspend` 恢复为 `On`；
- UDC 仍为 `configured`，`usb0` carrier 恢复为 1；
- 无新的 DWC3 WARN/Oops。

最终部署的当前状态：

```text
release = 7.3.1-rmx1931-samurai-v731-usbwake
boot_id = b0964a6b-84e5-458a-a944-0c2538e6bc3a
UDC state = configured
UDC current_speed = high-speed
usb0 carrier = 1
usbwake-debug = started
USBwake sleep inhibitor = 1
active-link experiment property/code = absent
```

本次最终验收没有重新执行 suspend 测试，因为目的就是让调试期插着 USB
时保持在线；`usbwake-debug` 会有意阻止该状态下的自动 suspend。要重做
U3/PDC host-resume 验收，必须先停掉该 debug 服务。

## 回滚

设备上保留了：

```text
/root/boot-before-usbwake.img
  SHA-256 62dee7b9a3c11a2bc549e570b57c35911fa8aa0b0220fe182dd7ec7dc4fab152
/root/logdump-before-usbwake.img
  SHA-256 82b330802fdc824ec1772b14ddbddf10dbbc2a4368a0b571c2f125dfc983a77d
/root/boot-usbwake1.img
  SHA-256 b9e9e53129d7d82401385a6f096af8a260a3b3d9e63d5940f7516424f4e6a438
/root/logdump-usbwake1.img
  SHA-256 70fde22dc1f928dd066f76a800b2551c1eef6e2cc1d54d91c1c4cb2d3130bf9a
```

旧 release 的同源模块也已补齐：

```text
/lib/modules/7.3.1-rmx1931-samurai-v731            773 modules
/lib/modules/7.3.1-rmx1931-samurai-v731-usbwake1    773 modules
/lib/modules/7.3.1-rmx1931-samurai-v731-usbwake     773 modules
```

`usbwake` 与 `usbwake1` 的 boot carrier 相同，回退到 `usbwake1` 只需用
fastboot 把 `E:\edk2-samurai-out\standard-arm64-v731\usb-host-resume-20261110\logdump-usbwake.img`
写回 `logdump`；设备侧备份 `/root/logdump-usbwake1.img` 与之逐字节相同。
回退到最初状态则写回 `logdump-before-usbwake.img` 和
`boot-before-usbwake.img`。任何回退都不需要触碰 NV/persist/calibration/
userdata。

## 边界

- 这是 debug 策略，不是量产默认功耗策略。keep-connect 会保留 USB
  clocks/interconnect，suspend 功耗高于 soft-disconnect。
- 主机不 suspend USB 时，手机不会系统睡眠；这是防止丢 USB 事务的
  正确行为，不应通过删除 U3 门禁来绕过。
- 同线 resume 不等于“主机魔法包唤醒”；仍然是 USB resume 信号 +
  PDC wake IRQ。
