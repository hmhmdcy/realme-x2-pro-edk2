# 充电适配磁盘与构建残留只读盘点

审计时间：2026-10-28（Asia/Shanghai）  
范围：`E:\RealmeX2Pro edk2`、`E:\edk2-samurai-out`（WSL 中为 `/mnt/e/edk2-samurai-out`）、`C:`、WSL `/home/cy122` 与 `/var/cache`。  
性质：**只读盘点**。本文没有删除、移动、改名或刷写任何文件，也没有进入 R15 boot/logdump 保护目录做写操作。

## 0. 结论先行

当前空间主要不是被“当前充电源码”占用，而是被历史构建、旧 boot/logdump 载体、整卷构建镜像和重复 EDK2 克隆占用。

- E: 当前约 **126 GiB 可用 / 477 GiB**；最大可回收来源是 `E:\edk2-samurai-out` 的历史 `kernel*`、`rx*`、`cleanup*`。
- `kernel*` 共约 **107.0 GiB**（424 个目录）；`rx*` 共约 **19.2 GiB**（33 个目录）；旧 `cleanup*` 共约 **32.1 GiB**。
- 单目录最大项是 `kernel282/full-kernel-build282.ext4`（32.0 GiB）、`cleanup145/volumes`（约 27.2 GiB 压缩构建卷）、`kernel248`（19.8 GiB，含整盘 userdata 备份）和 `rx61/EWDK ISO`（18.6 GiB）。
- `E:\edk2-samurai-out` 根目录旧调试镜像合计约 **4.9 GiB**，包括约 **3.48 GiB** `logdump*.img`、约 **0.83 GiB** `Image-*`、约 **0.14 GiB** UEFI `.fd` 和约 **0.24 GiB** `boot-*.img`。它们是 2026-10-06/08 前后的旧 RX/EUD 尝试，不在 R15 证据树内。
- WSL 当前约 **838 GiB 可用 / 1007 GiB**；真正的大头是 `edk2-samurai`（8.1 GiB）和两个同 HEAD 的审计克隆，`charging-management-20261023` 本身约 4.1 GiB。
- C: 当前约 **59 GiB 可用 / 465 GiB**。最大单项是 WSL 的 `ext4.vhdx`，文件约 **216 GiB**，但 WSL 内实际只用了约 **119 GiB**；先清 WSL 内部垃圾，再离线压缩虚拟盘，不能直接删 `ext4.vhdx`。

### 优先清理顺序（建议，不代表已执行）

| 优先级 | 目标 | 预计回收 | 保留/前置条件 |
|---|---|---:|---|
| P0 | `E:\edk2-samurai-out` 根目录旧 `Image-*`、`logdump-*.img`、旧 `.fd`、旧 `boot-*.img` | 约 **4.9 GiB** | 先把根目录文本日志、JSON、已知哈希归档；R15 目录内文件不在其中 |
| P0 | WSL APT 缓存与 C: 临时目录中的明确旧诊断输出 | 约 **0.7-0.9 GiB** | 不删 `.codex` 会话、`Downloads\platform-tools` 或正在使用的临时文件 |
| P1 | `E:\edk2-samurai-out\cleanup145\volumes` 与 `cleanup20261019` 的旧 `.ext4.zst` 构建卷 | 约 **32.1 GiB** | 保留 cleanup ledger/JSON；逐卷确认无当前恢复引用后删卷文件 |
| P1 | `E:\edk2-samurai-out\kernel282\full-kernel-build282.ext4` | **32.0 GiB** | 保留同目录构建结果/状态/log；确认该卷只含可重建构建环境 |
| P1 | `E:\edk2-samurai-out\rx61\EWDK_*.iso` | **18.6 GiB** | 可重新下载；保留 `session-61.md`、下载/校验 JSON |
| P1 | WSL `edk2-samurai/clean-audit-*` 中重复的审计克隆 | 约 **4-5 GiB** | 两个目录同一个 Git HEAD `c22a47a3`；先导出未跟踪文件/差异清单，保留一个规范工作树 |
| P1 | `charging-integration-20261026-01/build-r7`、`build-r8` | 约 **179 MiB** | 旧 Image 构建快照；确认 `.config`、Image、日志已在主 `build` 或证据中 |
| P2 | `charging-integration-r22/r23` 两个旧中间轮次 | 约 **520 MiB** | 保留 manifest/结果 JSON；没有对应上机成功记录 |
| P2 | `charging-management-20261023` 内 20261026 旧 boot/FAT 载体 | 约 **1.3 GiB** | 属 boot/logdump 类，不能与 R15 保护文件混淆；必须先核对 manifest，不能盲删 |
| P2 | WSL 根下历史 `*-objects-*`、`*-tests-*`、`*candidate*` 目录 | 合计约 **122 MiB** | 数量多（64 个）但对容量贡献很小，按检索价值而非体积处理 |
| P3 | `reference` 下 426 个 `kernel*`、31 个 `rx*` 快照目录 | 合计约 **106 MiB** | 体积不大；建议归并代表性快照后清理，主要用于减少检索噪声 |
| 禁止清理 | R15 证据/回滚依赖、r20 基线、原厂 backup、OEM 原始提取、当前源码与 KO | — | 见第 2 节 |

## 1. 磁盘与测量口径

| 位置 | 容量快照 | 备注 |
|---|---:|---|
| C: | 约 465 GiB，已用约 407 GiB，可用约 **59 GiB** | WSL 虚拟盘位于此盘 |
| E: | 约 477 GiB，已用约 352 GiB，可用约 **126 GiB** | 构建、证据和历史输出盘 |
| WSL `/dev/sdd` | 1007 GiB，已用约 119 GiB，可用约 **838 GiB** | `/` 与 `/home` 同一 ext4 |

本文 E: 大目录体积来自 Windows 原生递归枚举的**逻辑文件字节数**；`du -sh` 使用块分配口径，二者可能略有差异。`du` 与 `dir /s` 不应逐字节对比。C: `ext4.vhdx` 的 216 GiB 是虚拟盘文件口径，不等于 WSL 内实际有效数据。

`/mnt/e` 上的全盘 `du` 会非常慢，因此没有为完成本报告而对整个 E: 做无界扫描；大组采用 Windows 原生枚举，局部候选再用 WSL `du` 复核。

## 2. 硬保护边界

以下路径不属于清理候选，任何后续清理都应先做前缀排除：

### 2.1 R15 证据与回滚

- `E:\edk2-samurai-out\charging-management-20261023\r15-evidence-20261027\` 整棵目录，约 **162 MiB**。
  - 包含 `r15-evidence-20261027.tar` 约 **169 MB**。
  - `trial-517-r15-fixed5v1500\old\boot.img` 约 **96 MiB**。
  - `trial-517-r15-fixed5v1500\old\logdump.img` 约 **64 MiB**。
  - `r15-mincap-install-20261027-055713\samurai-mp2650.ko` 是设备回退依赖，SHA-256 为 `dbe445cfef6e095f8d028034f0fbba9231484b6510ab6f60354c6ff55e9c23d1`。
- `E:\edk2-samurai-out\charging-management-20261023\charging-integration-trial-20261027-r9-status-precharge-15\`，约 **2.4 MiB**。
- `E:\edk2-samurai-out\charging-management-20261023\r15-final-16-acceptance-before-reboot\`，约 **32 KiB**。
- `E:\edk2-samurai-out\charging-management-20261023\restore-r15-20261028.sh` 及其 manifest/哈希回执。

`restore-r15-20261028.sh` 明确引用：

```text
trial-517-r15-fixed5v1500/original/samurai-mp2650.ko
trial-517-r15-fixed5v1500/original/modules/samurai-usb-input.ko
r15-mincap-install-20261027-055713/samurai-charging
```

因此 `r15-evidence-20261027` 不是“旧构建”，而是**硬回滚依赖**。其中的 boot/logdump 文件全部保留，不做重复文件去重。

### 2.2 r20 / 当前基线

- `charging-integration-trial-20261027-r20-apsd-rearm-01\` 整棵目录及 `device-evidence-r20`。
- r20 boot 载体 `charging-integration-20261027-boot-private-15\`。
- r20 logdump 载体 `charging-integration-20261027-fat-private-11\`。
- 回退 boot `charging-integration-20261027-boot-private-01\`。
- 回退 logdump `charging-integration-20261027-fat-private-10\`。
- r21 `charging-integration-r21-board-convergence-01\provenance\device-before-r21.tgz`。

这些路径与 R15 是不同轮次，但承担当前可确认回退链，不能为了腾空间删除；旧报告已给出 boot/logdump SHA-256 回执。

### 2.3 原厂、个体与 OEM 资料

- `E:\edk2-samurai-out\backup\`，约 **257 MiB**：原厂 boot、logdump、分区表/NV/个体备份。
- `E:\edk2-samurai-out\charging-oem-audit-20261023\`，约 **14 GiB**：
  - `gauge-2719-system-extract-private-01` 约 **11 GiB**。
  - `gauge-2719-vendor-extract-private-01` 约 **3.8 GiB**。
  - 这是 OEM 固件/系统提取，是参数溯源的基础，不应按“解包后过大”删除。
- 任何名称包含 `stock`、`original`、`partition`、`gpt`、`nv`、`persist`、`modem`、`vbmeta`、`efs` 的目录或文件。

### 2.4 当前源码、模块与待验证包

- WSL `charging-integration-20261026-01\source\`，约 **1.8 GiB**。
- WSL `charging-integration-20261026-01\build\`，约 **1.9 GiB**：是当前构建入口，优先清对象而不是整目录删除。
- WSL `r8-module\new-patch-build\samurai-mp2650.ko` 及当前 `new-patch-01` 头文件/补丁。
- r24 `boot-final`、`install`、`dts`、`provenance`、`package-result.json`、`SHA256SUMS`：当前待验证包，不等于旧中间 `r24\boot`。
- `charging-integration-r21-board-convergence-01\`：保留其上机证据和 `provenance`。

## 3. E: `edk2-samurai-out` 优先清单

### 3.1 根目录旧 RX/EUD 产物：约 4.9 GiB，P0

根目录下大于 1 MiB 的文件共 **142 个、约 4,992 MiB（4.88 GiB）**，主要是早期 RX/EUD 调试载体：

| 类别 | 文件数/大小 | 内容 | 建议 |
|---|---:|---|---|
| `logdump*.img` | 57 个，约 **3.48 GiB** | 2026-10-06/08 旧日志分区快照，多数为 64 MiB | 先把 `*.txt`、`*.json`、`*.log`、`SHA256SUMS` 归档；确认旧 fastboot/EUD 结果已保留后删除镜像 |
| `Image-rmx1931-samurai-*`、`Image-rx32-console` | 30 个，约 **0.83 GiB** | 早期 console/EUD/regprobe 内核 | 已有对应文本日志和后续构建；不建议长期保留全部重复 Image |
| `SM8150_UEFI-*.fd` | 17 个，约 **0.14 GiB** | 早期 UEFI 变体 | 保留最终/规范 `SM8150_UEFI-samurai*.fd`；旧 eudtest、fix3、oppoproj 等可归档 |
| 根目录 `boot-*.img` | 约 **0.24 GiB** | 早期 boot 封装 | 与 R15/r20 boot 无关；确认无当前刷机脚本引用后处理 |
| `avbtest_boot.img`、`custom_ramdisk.img`、`screen*.png` 等 | 约 **0.2 GiB** | 测试/截图 | 分析与截图可保留；avbtest 临时镜像可按需清理 |

这些文件均位于 `E:\edk2-samurai-out` **根目录**，不是 `r15-evidence-20261027` 内部文件。建议先保留所有文本证据，按“先镜像、后源码/脚本”的顺序回收。

### 3.2 历史 `kernel*`：约 107.0 GiB，P1/P2

`E:\edk2-samurai-out\kernel*` 共 **424 个目录、约 107.0 GiB**。这不是单一缓存，而是整个机型历史项目的混合体，不能整组盲删。

| 目录 | 大小 | 性质 | 建议 |
|---|---:|---|---|
| `kernel282` | **32.0 GiB** | `full-kernel-build282.ext4` 整卷；同目录还有 build result/state/log | **P1**：保留 JSON/log/source manifest，确认 ext4 只含可重建构建环境后删除整卷，单项可回收 32 GiB |
| `kernel248` | **19.8 GiB** | userdata partclone/整盘镜像与 sparse fixture，明显是灾备资料 | **不建议自动删**；至少保留一个已验证可用 userdata 备份，不与普通构建缓存混为一谈 |
| `kernel242` | **6.4 GiB** | 固件/时钟/设备检查材料，顶层有较小 JSON | **P2**：先按文件清单判断是否仍被其他项目引用；不按目录名删 |
| `kernel132` | **2.25 GiB** | rootfs `simg`、charger boot、logdump/Image | **P2/倾向保留**：含可能的历史回滚载体，且体积不大 |
| `kernel441`、`kernel442`、`kernel461` | 约 **4.0 GiB** | 相机/用户态运行材料，含多个 `.so` 与 tar.gz | **P2**：与充电无关，但可能是别的项目证据；仅在该项目结项后清理 |
| `kernel113`、`kernel126`、`kernel75` | 约 **3.3 GiB** | 旧 sensor/audio/GPU 尝试，含 boot/logdump 和 recoverable tar | **P2**：保留文本结果，镜像逐项确认 |
| 其余 `kernel66..kernel491` | 约 **39 GiB（估）** | 大量小目录，小文件、日志和旧产物 | 先清理明确可重建的对象/包，再决定目录级归档 |

#### 特别说明：`kernel248` 不是普通构建目录

其中的大文件包括：

```text
linux-userdata-partclone-r6-private.zst       约 4.59 GB
linux-userdata-clean-r6-private.pcl.zst       约 4.59 GB
linux-userdata-partclone-r5-private.zst       约 4.32 GB
ntfs-sparse-fixture-private.raw               约 134 MB
```

这些是设备 userdata/分区克隆，属于灾难恢复资料。除非已经验证 E: 之外还有等价备份，否则不应为了空间删除。

### 3.3 历史 `rx*`：约 19.2 GiB，P1

| 目录 | 大小 | 内容 | 建议 |
|---|---:|---|---|
| `rx61` | **19.09 GiB** | `EWDK_ge_release_svc_prod1_26100_250904-1728.iso` 约 **18.6 GiB**，其余为下载/校验脚本和 sample | ISO 可重新下载；保留 `session-61.md`、`download-state-*.json`、`ewdk-head.json`、校验结果后删除 ISO，优先回收 |
| `rx46`、`rx48`、`rx53`、`rx44`、`rx45` 等 | 约 **0.5 GiB 合计** | 旧 USB/console 调试记录 | 体积很小；保留以便追溯，不值得冒证据风险做激进去重 |
| `rx36-sources` 至 `rx65-sources` | 约 **0.1-0.2 GiB** | 旧源码快照 | 若已进入当前主线对照报告和 reference，可归档后清理重复副本 |

### 3.4 旧 `cleanup*`：约 32.1 GiB，P1

| 路径 | 大小 | 内容 | 建议 |
|---|---:|---|---|
| `cleanup145\volumes` | 约 **27.2 GiB** | 5 个旧 `*.ext4.zst` 构建卷，最大 `kernel126-build-volume.ext4.zst` 约 8.2 GiB | 保留 3 个 cleanup ledger JSON（合计约 60 KiB）；确认卷内没有唯一源码/证据后整卷删除 |
| `cleanup20261019\kernel118-current-build-volume.ext4.zst` | 约 **4.89 GiB** | 旧 kernel118 构建卷 | 保留 `wsl-cleanup-private.json`、`windows-cleanup-private.json` 与验证 JSON，删卷文件 |
| `cleanup20261022*` | 约 **5 MiB** | 小清理回执 | 保留，体积可忽略 |

`cleanup145` 目录名和 ledger 都表明它是一次清理审计的产物；但 `.ext4.zst` 是整卷镜像，删除前仍应至少保留各卷的 sha256、ledger 和最后修改时间。不要把 `cleanup145` 的 JSON 与 volumes 一起删。

### 3.5 `charging-management-20261023`：约 8.4 GiB

| 子目录/文件 | 大小 | 保留理由 | 建议 |
|---|---:|---|---|
| `r15-evidence-20261027` | **162 MiB** | R15 证据 + restore 脚本依赖 | **保留整棵** |
| `charging-integration-trial-20261027-r9-status-precharge-15` | **2.4 MiB** | 用户点名 R15 保护 | **保留** |
| `r15-final-16-acceptance-before-reboot` | **32 KiB** | R15 验收回执 | **保留** |
| `charging-integration-r21-board-convergence-01` | **261 MiB** | 有真实 fastboot 成功记录，`provenance` 是回退材料 | **保留** |
| `charging-integration-r22-typec-board-01` | **261 MiB** | 无对应上机成功证据，已被后续轮次覆盖 | **P2**：保留 `manifest`/结果 JSON 后删 boot 构建目录 |
| `charging-integration-r23-clean-01` | **260 MiB** | 无对应上机成功证据 | **P2**：同上 |
| `charging-integration-r24-usb-budget-01` | **518 MiB** | 当前待验证包；`boot-final` 与 `boot` 是不同状态 | **保留**；只可在后续确认后清理旧 `boot`，绝不删 `boot-final` |
| `charging-integration-20261026-boot-private-01/02/05/06` | 约 **1.04 GiB** | 旧 boot 中间载体，但属 boot 类 | **P2 需确认**：不与 R15 保护混同；先校验 manifest、是否有回收引用 |
| `charging-integration-20261026-fat-private-07/08` | 约 **246 MiB** | 旧 FAT/logdump 载体 | **P2 需确认**：同上 |
| `charging-integration-20261026-source-private-01` | **61 MiB** | 旧源码快照 | 若已有当前 `source` 与 reference，可归档后清理 |
| `charging-integration-20261026-dtb-private-01/02` | 约 **232 KiB** | 旧 DT 快照 | 体积小，保留 |
| 根目录 `*.tar.gz` 证据包 | 约 **2-3 MiB** | 历史上传包 | 保留；整体很小 |
| R7/R8/R9/R20 小 trial、physical-usb-cycle、daily soak | 多为 KiB-MiB | 状态/证据链 | 默认保留；不要为了几 MiB 做高风险去重 |

### 3.6 `charging-oem-audit-20261023`：约 14 GiB，禁止清理

| 子目录 | 大小 | 保留理由 |
|---|---:|---|
| `gauge-2719-system-extract-private-01` | **11 GiB** | OEM system 解包，是充电曲线/电流参数/驱动资料的一手来源 |
| `gauge-2719-vendor-extract-private-01` | **3.8 GiB** | OEM vendor 解包，含厂商充电策略/二进制 |
| `gauge-2719-system-files-private-01` | **26 MiB** | 已筛选的充电相关文件 |
| `usbin-init-host` | **60 MiB** | USB init/host 侧证据 |

这 14 GiB 是“用原厂资料优先”的底座，不应以“解包文件大”为由删除。若后续要压缩，只能压缩已经验证可在需要时解压的原始归档，并保留校验和。

## 4. E: `RealmeX2Pro edk2` 工作区

### 4.1 当前目录

| 路径 | 大小 | 判断 |
|---|---:|---|
| `build` | 0（空/近空） | 不是清理目标 |
| `out` | 29 MiB | 当前小型输出，保留 |
| `archive` | 6.4 MiB | 历史归档，保留 |
| `linux-port` | 32 MiB | 源码适配，保留 |
| `sessions` | 1.3 MiB | 会话记录，保留 |
| `.codex-tmp` | 28 KiB | 临时目录但极小；可随常规临时清理，收益可忽略 |

### 4.2 `reference` 历史快照

- `reference\kernel*`：**426 个目录，约 94.5 MiB，19,897 个文件**。
- `reference\rx*`：**31 个目录，约 11.3 MiB，1,313 个文件**。
- 总计约 **106 MiB**，不是空间瓶颈。
- 建议按项目里程碑保留代表性 `kernel`/`rx` 快照，删除已被 `r15`/`r20`/当前 reference 文本完全覆盖的旧快照；收益主要是减少检索噪声和 inode，而不是解决容量。

## 5. WSL `/home/cy122`

### 5.1 当前充电工作树

`/home/cy122/charging-management-20261023` 总计约 **4.1 GiB**，其中 `charging-integration-20261026-01` 约 **3.9 GiB**。

| 路径 | 大小 | 保留理由 | 建议 |
|---|---:|---|---|
| `charging-integration-20261026-01/build` | **1.9 GiB** | 当前构建入口；含 `.config`、Image/vmlinux/System.map、Module.symvers | **不整体删**。后续只清 `.o`、`.cmd`、`.tmp_vmlinux*`，保留配置、Image、vmlinux、System.map、Module.symvers、日志 |
| `charging-integration-20261026-01/source` | **1.8 GiB** | 当前主线源码 | **保留** |
| `charging-integration-20261026-01/build-r7` | **122 MiB** | 旧 Image 构建快照 | **P1**：确认主 `build` 已有需要产物后删除 |
| `charging-integration-20261026-01/build-r8` | **57 MiB** | 旧构建快照 | **P1**：同上 |
| `charging-integration-20261026-01/r8-module` | **49 MiB** | 当前模块源码/构建/回滚 KO | **保留**；其中 `rollback-r15-old` 与 `new-patch-build` 不能一起清 |
| `charging-integration-20261026-01/r15-mincap-module-01` | **788 KiB** | R15 历史 KO | 保留，体积小 |
| `charging-integration-20261026-01/r16-zero-contract-module-01` | **5.5 MiB** | 当前零契约模块 | 保留 |
| 根下 `*-objects-*`、`*-tests-*`、`*candidate*` | **约 122 MiB（64 个目录）** | 历史对象/测试工作树，部分可能被 root 拥有或仍被脚本引用 | **P2**：先导出路径/所有者/结果 JSON；不要用根目录通配删除 |
| 根下单个最大值 `pd5v-owner-feasibility`、`kbuild-integrated` 等 | 分别约 **12 MiB** | 历史实验 | 体积小，不建议优先处理 |
| `r8-tests-linux-final-20261027` | **1.8 MiB** | 最终测试回执 | 保留 |

### 5.2 `edk2-samurai` 与重复克隆

`/home/cy122/edk2-samurai` 总计约 **8.1 GiB**：

| 路径 | 大小 | 内容 | 建议 |
|---|---:|---|---|
| `repo` | **2.9 GiB** | 当前 EDK2 工作树；`workspace/Build` 约 **1.6 GiB**，还有 135 个未跟踪 reference/candidate 文件 | **保留规范工作树**；先归档未跟踪文件清单 |
| `repo/.git` | **348 MiB** | Git 元数据 | 保留 |
| `clean-audit-692aca26` | **2.4 GiB** | 与另两个仓库同 HEAD `c22a47a3` | **P1**：先 `git status`/未跟踪文件/差异导出，再与 `clean-audit-ee7aa8f6` 二选一保留 |
| `clean-audit-ee7aa8f6` | **2.9 GiB** | 同 HEAD `c22a47a3`；`workspace/Build` 约 **746 MiB** | **P1**：若不需要第二个审计快照，可回收约 2.9 GiB；不要在未导出未跟踪文件前删除 |
| `repo/workspace/Build` | **1.6 GiB** | 可重建 EDK2 构建输出 | **P2**：保留当前最终 fd/img 与 log 后，可清中间对象 |

两个 `clean-audit` 的 `Platform/samurai/samurai.dsc` 已逐字节一致，但 Git 状态扫描在 `/mnt/e` 与大量未跟踪文件上耗时较长，本报告不把它们称为“已确认完全干净”。安全做法是先保留一个规范工作树，并导出另一个的：

```text
git status --porcelain
git diff --stat
git ls-files --others --exclude-standard
```

### 5.3 PMOS 源码/镜像与系统缓存

| 路径 | 大小 | 内容 | 建议 |
|---|---:|---|---|
| `/home/cy122/pmos-samurai-rootfs01` | **4.5 GiB** | kernel 约 **2.8 GiB**，多个 rootfs raw 镜像（约 425-582 MiB） | **保留主基线**；只对多个 raw 镜像做 sha256 后再决定是否去重 |
| `/home/cy122/pmos-samurai-kernel109` | **4.0 GiB** | kernel 约 **2.5 GiB**，final/restored rootfs raw | **保留**；可能是主线/rootfs 对照基线 |
| `pmos-samurai-kernel128/129/136` | 各 4 KiB | 空壳或指针目录 | 极小，忽略 |
| `/home/cy122/linux-samurai-github` | **3.4 MiB** | 主线源码对照 | 保留 |
| `/var/cache/apt` | **126 MiB** | 包缓存 | P0（系统级）可 `apt clean`；不影响源码/证据 |
| `/var/lib/apt/lists` | **153 MiB** | APT 索引 | P0 可清理后重建；不影响源码/证据 |
| `/home/cy122/ghidra-data` | **413 MiB** | 逆向分析数据 | 非本任务垃圾，保留 |

### 5.4 WSL 内存/权限说明

部分 root-owned 的候选目录不适合普通用户统计或清理；本次没有使用 `sudo` 批量删除。后续若处理这些目录，应先按精确路径列出 `owner`、`mtime`、manifest，再决定是否保留。

## 6. C: 盘专项

### 6.1 WSL 虚拟盘：最大单项，但不能直接删

| 路径 | 文件体积 | 说明 |
|---|---:|---|
| `C:\Users\cy122\AppData\Local\wsl\{ee461976-57ad-4560-8244-f266f2040781}\ext4.vhdx` | 约 **216 GiB** | WSL 根文件系统虚拟盘；WSL 内实际已用约 **119 GiB** |

这说明虚拟盘内存在约 **97 GiB 的“已释放但尚未回收到宿主文件”的空洞**。正确顺序是：

1. 先在 WSL 内清理旧构建、缓存和无引用大文件；
2. 执行 `wsl --shutdown`，确保没有进程占用；
3. 使用 Windows 的 `Optimize-VHD` 或 `diskpart compact vdisk` 离线压缩；
4. 压缩前后重新测 C: 文件可用空间。

**不要删除 `ext4.vhdx`**：它不是普通临时文件，删除会丢失整个 WSL 用户空间和当前构建/证据。

### 6.2 C: 其他可见占用

| 路径 | 大小 | 建议 |
|---|---:|---|
| `C:\Users\cy122\AppData\Local\Temp` | **约 0.61 GiB** | P0：先关闭相关程序，人工确认后清明确旧诊断文件；不要无条件清空整个 Temp |
| `C:\Users\cy122\Downloads` | **约 34.61 GiB** | 人工清理历史安装包；`Downloads\platform-tools` 是刷机工具，保留 |
| `C:\Users\cy122\.codex` | **约 2.49 GiB** | 会话/审计记录，不是构建缓存；默认保留 |
| `C:\ProgramData\Package Cache` | **约 1.26 GiB** | 安装器缓存；未确认安装器修复需求前不删 |
| `C:\Users\cy122\.cache` | **约 2.11 GiB** | 通用缓存；不在本轮充电构建清理 P0 |
| `C:\Windows\SoftwareDistribution\Download` | 接近空 | 无需处理 |

## 7. 建议执行批次的先后关系

以下只是优先级和校验顺序，不代表本次已执行任何清理。

### 批次 A：低风险、先回收

1. 把 `E:\edk2-samurai-out` 根目录的文本证据、JSON、日志和 SHA 清单归档。
2. 清理根目录旧 `logdump*.img`、旧 `Image-*`、旧 `.fd`、旧 `boot-*.img`，预计约 **4.9 GiB**。
3. 清 WSL APT 缓存与 C: 明确临时目录，预计约 **0.7-0.9 GiB**。
4. 保留 R15、r20、backup、OEM 路径不变，不进入任何递归目标。

### 批次 B：大体积构建卷/下载缓存

1. `cleanup145\volumes` 和 `cleanup20261019` 旧 `.ext4.zst`：先保留 ledger/JSON/sha256，再处理卷，预计 **32.1 GiB**。
2. `kernel282\full-kernel-build282.ext4`：先保留 build result/state/log，预计 **32.0 GiB**。
3. `rx61\EWDK_*.iso`：可重新下载，预计 **18.6 GiB**。

三项合计理论回收约 **82.7 GiB**，是让 E: 恢复充裕的主要来源。每项都必须先做“卷内容 + 引用 + 结果文件”三步确认。

### 批次 C：WSL 重复工作树

1. 导出 `clean-audit-692aca26`、`clean-audit-ee7aa8f6` 的 Git 未跟踪文件/差异；
2. 二选一保留规范工作树；
3. 删除另一个克隆，预计 **2.4-2.9 GiB**；
4. 再处理 `build-r7`、`build-r8` 和旧对象目录，预计 **0.3 GiB**。

### 批次 D：最后再碰历史 `kernel*` 其余部分

`kernel248` 的 userdata 镜像和 `kernel132` 的 rootfs/boot/logdump 属灾备或潜在回滚材料，建议跳过。其余 `kernel66..kernel491` 只有在确认其他项目也已经结项、且已有归档索引后才处理。不要按数字区间或通配符一次删除。

## 8. 保留理由汇总

必须保留的核心不是“看起来很大”的目录，而是：

- R15：`r15-evidence-20261027`、`charging-integration-trial-20261027-r9-status-precharge-15`、`r15-final-16-acceptance-before-reboot`、`r15-mincap-install-20261027-055713` 及其 boot/logdump/KO/manifest。
- r20：trial 整目录、boot-private-15、fat-private-11、设备证据、r20 manifest/hash。
- 回退：boot-private-01、fat-private-10、`restore-r15-20261028.sh`、`backup`。
- OEM：`charging-oem-audit-20261023` 的 system/vendor 提取及索引。
- 源码：当前 `source`、`new-patch-01`、`new-patch-build`、`r16-zero-contract-module-01`、主线对照仓库。
- r21/r24：r21 provenance 与 r24 `boot-final`/`install`/DTS/package receipt，分别代表“已上机证据”和“待验证当前包”。

## 9. 残余风险与未完全覆盖项

- `/mnt/e` 上 488 个顶层项的历史归属非常混杂；本报告只对大组和充电相关组做了有界精算，没有把 `bluetooth-*` 等其他项目的全部子目录逐文件归类。
- 部分 WSL 目录存在 root 权限或正在被构建进程占用；本报告没有用 `sudo` 扩大权限，也没有杀掉任何进程。
- `cleanup145`/`kernel282` 的 ext4 卷内部未挂载检查；删除建议以“保留外部 ledger/log/JSON + 逐卷确认”为前置条件。
- C: 压缩 `ext4.vhdx` 的收益取决于 WSL 内释放情况和 VHDX 稀疏/碎片状态，不能把 97 GiB 当作必然回收量。
- 所有体积均是本次扫描时点的静态快照；执行清理前应重新测量，尤其是正在写入的 WSL `build`、`/tmp` 和 Windows Temp。

## 10. 本次审计验证摘要

| 验证项 | 结果 |
|---|---|
| 是否删除文件 | 未删除、未移动、未重命名任何文件 |
| 是否触碰 R15 boot/logdump | 未写入；保护树仅为只读枚举 |
| R15 回滚依赖 | 已从 `restore-r15-20261028.sh` 确认 KO/runtime/manifest 路径 |
| E: 大头 | `kernel*` 约 107.0 GiB、`rx*` 约 19.2 GiB、`cleanup*` 约 32.1 GiB |
| 根目录旧镜像 | 142 个大于 1 MiB 文件，约 4.88 GiB |
| WSL 当前工作树 | 约 4.1 GiB，其中 build/source 各约 1.9/1.8 GiB |
| WSL EDK2 克隆 | `clean-audit-*` 同 HEAD `c22a47a3`，存在重复回收空间 |
| C: 虚拟盘 | `ext4.vhdx` 约 216 GiB 文件体积，WSL 内实际使用约 119 GiB，适合先清后压缩 |

本文是清理决策依据，不是删除授权。任何后续删除都应继续满足：**R15 证据完整、r20 回退链完整、原厂/OEM 资料完整、当前源码/KO完整**。
