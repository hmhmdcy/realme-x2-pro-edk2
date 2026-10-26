---
<!-- from HANDOVER-NEXT.md, section 16 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 16. 提交、噪音消除、bug 定位（2026-10-07 03:30）

### 已提交（master，5+1 个提交，尚未 push 到 fork）

```
04da4b4 samurai: EUD COM log ring + cyclic replay drainer
1da715f samurai: do not auto-enumerate every device as a boot option
2d26a5a SetCPUFreqDxe: print UINT32 frequencies unsigned and keep going
a3b70b8 samurai: ship the ArmMmuLib full-DEBUG fix as a patch
18e965b docs: EUD log ring verification, ArmMmuLib root cause, boot option noise
(+ 后续一个 docs 补丁说明提交)
```

**重要约束**：`Common/edk2` 子模块只有 `origin = tianocore/edk2`，**没有 fork**。
若在其中 commit，父仓库记录的指针在上游不存在 → `clone --recursive` 不可复现
（与交接文档里"二进制传不上 GitHub"是同一个坑）。因此 ArmMmuLib 修复以补丁形式随父仓库发布：

```
git -C Common/edk2 apply Platform/Realme/sm8150/patches/armmmulib-no-debug-in-mmu-off-path.patch
```

工作区里该子模块改动保持未提交（本地构建需要它）；如需真正入库，需要先 fork edk2 并加 remote。

### 启动项噪音：已消除

`PlatformBm.c` 里的 `EfiBootManagerRefreshAllBootOption()` 已注释掉（附完整说明与恢复方法）。
它曾为 6 个 UFS LUN + 2 个 FS-only 设备自动建启动项，BDS 逐个尝试加载失败 →
每次开机 9 条 `BOOT_OPTION_LOAD_ERROR/FAILED`。菜单项改为只显示显式注册的
（UiApp / SimpleInit / UEFI Shell / UAS Storage），其他可从 Shell 启动。

### bug 定位与修复：SetCPUFreqDxe（源码就在本仓库）

`Platform/RenegadePkg/Drivers/SetCPUFreqDxe/SetCPUFreqDxe.c`

1. **显示 bug**：`perfLevel`/`frequencyHz` 声明为 `UINT32` 却用 `%d` 打印 →
   2419200000 Hz（2.4192GHz，Silver）显示成 `-1875767296`，
   2956800000 Hz（2.9568GHz，Gold+）显示成 `-1338167296`。**频率本身是对的。** 已改 `%u`。
2. **真 bug**：循环 `for (i = 0; i < 9; i++)`（假设 4+4 CPU + L3），
   而 `GetMaxPerfLevel` 失败时**直接 `return`** → 本机 index 4 返回 Protocol Error 后
   整个循环中止，**Gold/Gold+ 核（4–7）从未被设置频率**。已改为 `continue` + 跳过记录。

### 记忆

- **Mnemon 后端在本机不可用**（`spawn mnemon ENOENT`，未安装 CLI）→ 记忆空间创建失败，
  无法写入 Mnemon 空间。若要启用：安装 Mnemon Windows 版并把 `mnemon.exe` 加入 PATH。
- 已改用 **host 的运行时 MEMORY.md**：新增一条 2026-10-07 摘要（3 条，6850/10240 字节），
  记录 EUD 环、三条硬教训、崩溃真因、噪音来源、SetCPUFreqDxe 缺陷、Linux 侧 earlycon 现状。

### 新镜像（待真机验证）

```
E:\edk2-samurai-out\boot-samurai-eudlog6.img
sha256 060efe010b5a1b6a54d52927fbafcd4980bd16a51a623426d749f26fb51dbe25
```

包含：EUD 环全量 DEBUG + 启动项噪音消除 + SetCPUFreqDxe 修复 + ArmMmuLib 补丁（已应用）。
验证要点：① 启动更快、日志里不再有那 9 条 BOOT_OPTION 错误、启动项只剩 4 个；
② `SetCPUFreqDxeMain` 频率为正数，且 CPU 4–8 不再因 index 4 失败而中断。
---
