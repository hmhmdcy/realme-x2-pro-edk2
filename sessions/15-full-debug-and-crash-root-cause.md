---
<!-- from HANDOVER-NEXT.md, section 15 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 15. 全量 DEBUG 打通 + 崩溃真因修正（2026-10-07 03:20）

**镜像** `E:\edk2-samurai-out\boot-samurai-eudlog5.img`
sha256 `5a0aab582df3f1382b6b7cae6fd58568930a50b2a80dd5ab3013c265d8837d82`，真机验证通过。

### 崩溃真因（推翻了交接文档的判断）

`ArmCpuDxe + 0x34B8` 反汇编后是 **`ldp x19, x20, [sp, #16]`** —— 即
**ArmMmuLib 的 `ReplaceTableEntry()` 收尾弹栈**，是**栈访问 fault**，**不是**串口/EUD 写。

- 那条 "splitting block entry with MMU disabled" 是同一分支打印的，
  所以它的文本才会留在栈上 —— **症状而非原因**；
- 旧版写 EUD MMIO、新版写 RAM 环形缓冲，都崩在**同一条指令**（所以偏移完全一致）；
- 真正的问题是：更新"活动块映射"时（关 MMU 做 break-before-make），
  **栈所在页会变得不可访问**，紧接着的弹栈就 fault；
- 全量 DEBUG 才触发，是因为它改变了内存属性更新的数量/时机，某次更新覆盖了栈区
  （`SP=0x9FFCF5E0`，落在 "UEFI Stack" 0x9FFB0000–0x9FFD0000）。

**修复**：删掉该分支里的 `DEBUG()`（原则：绝不在"即将关 MMU"的路径上做日志输出），
见 `Common/edk2/ArmPkg/Library/ArmMmuLib/AArch64/ArmMmuLibCore.c`。
改后全量 DEBUG（`PcdDebugPrintErrorLevel=0x800B05C7`，加在 `samurai.dsc`）**4 秒进 BDS**。

### 验收数据

- `comlog COM14 90` → **138501 字节 / 2099 行 / 12 遍**
- 每遍 `10214 byte(s) in 8510 ms` → **约 1.2 KB/s**
- **无 overflow**：整份启动日志仅约 10KB，80KB 环绰绰有余
- 日志覆盖：DXE 启动 → BDS → 启动项转储 → SimpleInit → 变量驱动 → CPU 频率驱动

### 附带收获：两个以前看不见的真 bug

1. `SetCPUFreqDxeMain: CPU 1 Now running at -1875767296 Hz`（CPU 2 同样）—— **负值/垃圾频率**
2. `Failed to get the maximum performance level for CPU 4, Status: Protocol Error` +
   `This CPU may not exist on current platform` —— 8 核平台只配置了 CPU 0–3

### 之前那个 BdsDxe 错误，被这份日志直接证实了

启动项转储显示自动枚举出 **8 个不可引导项**：
`UEFI Misc Device 1–6`（六个 UFS LUN）+ `UEFI Non-Block Boot Device 1–2`。
BDS 逐个尝试加载失败 → 正是
`EFI_SW_DXE_BS_EC_BOOT_OPTION_LOAD_ERROR (V03051002)` 约 7 次 +
`BOOT_OPTION_FAILED (V03051003)` 1 次。**属良性噪音，但确实是每次开机报 9 次错误的来源。**

### 待提交（仓库当前未提交改动）

- `Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c`（循环回放 + 每遍标记/统计 + 时间预算）
- `Platform/Realme/sm8150/samurai.dsc`（全量 DEBUG PCD）
- `Common/edk2/ArmPkg/Library/ArmMmuLib/AArch64/ArmMmuLibCore.c`（移除危险 DEBUG）
- 以及 EUD 环形缓冲相关的全部文件（EudSerialPortLib 重写、EudLog.h、内存表改名）
---
