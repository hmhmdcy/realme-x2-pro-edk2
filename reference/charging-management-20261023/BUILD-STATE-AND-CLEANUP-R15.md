# R15 构建、装载状态与空间清理审计

审计时间：2026-10-28（Asia/Shanghai）  
审计方式：只读检查；本文不执行删除、构建、刷机或设备操作。  
范围：`E:\RealmeX2Pro edk2\reference\charging-management-20261023` 的 `integration-20261026`、`integration-20261027-r13`、`integration-20261027-r14`；`E:\edk2-samurai-out\charging-management-20261023` 的 `charging-integration-20261026-*`、`charging-integration-20261027-r13/r14`、`charging-integration-trial-*`、r20-r24 与旧 boot/logdump 中间物；C: 临时缓存；WSL `/home/cy122/charging-management-20261023`。

## 1. 结论先行

- 当前有设备证据、可直接回退的基线仍是 **r20 / kernel #528**。r21 有真实 fastboot 成功记录；r22、r23、r24 找到构建/打包成功记录，但未找到对应的 fastboot 上机成功记录。
- 当前源码包含 2026-10-28 的板级与 DTS 修改，**已不等于 r20 已部署的 #528 Image**。不能把 r24 的“打包通过”写成“上机通过”。
- E: 活跃充电输出目录约 **8.4 GB**（8,555 MiB），C: 临时目录约 **448.3 MiB**，WSL 工作树约 **4.1 GB**（4,015,275,894 B）。
- 保守、可重建且被取代的候选约 **3.2 GB**；扩展谨慎候选可再多回收约 **3-4 GB**。C: 缓存类约 **0.45 GB**；WSL 可重建旧构建/测试对象约 **0.7-1.3 GB**。
- 本次**不删除任何文件**。磁盘余量本身尚可，但删除前必须按本文的保留清单和命令逐项复核。

## 2. 磁盘现状（只读测量）

| 位置 | 总量 | 已用 | 可用 | 备注 |
|---|---:|---:|---:|---|
| C: | 464.62 GB | 406.21 GB | **58.40 GB** | 系统盘，优先只清临时缓存；审计期间可用量从 61.31 GB 降至 58.40 GB |
| E: | 476.94 GB | 351.01 GB | **125.93 GB** | 构建与证据盘，余量尚可 |
| WSL `/dev/sdd` | 1007 GB | 118.05 GiB | **837.56 GiB** | `/` 与 `/home` 同一文件系统；精确：1,081,101,176,832 / 126,775,717,888 / 899,333,103,616 B |

WSL 内存：7.7 GiB 总量，约 3.4 GiB free，约 6.9 GiB available；不是磁盘瓶颈。磁盘实时值会随 Windows/WSL 服务变化，执行清理时用命令重新测，不以本文静态快照为准。  
建议告警阈值：C: < 50 GB、E: < 80 GB、WSL < 200 GB 时先做只读盘点，再决定清理；不要以“看起来很大”为由删除证据或备份。

## 3. 最新实际成功构建与最近上机结果

### 3.0 点名历史目录核验

`reference\charging-management-20261023` 下的 `integration-20261026`、`integration-20261027-r13`、`integration-20261027-r14` 仍在，但只是构建/打包回执，不是设备证据。r13 有 `image-build-result.json`、`logdump-package-result.json`；r14 有 `boot-package-result.json`、`image-build-result.json`、`logdump-package-result.json`。这些目录体量很小，建议保留，避免丢失历史参数与来源链。

`E:\edk2-samurai-out\charging-management-20261023` 下未找到名为 `charging-integration-20261027-r13` / `r14` 的目录；实际 r13/r14 的产物落在 `charging-integration-20261027-boot-private-*`、`fat-private-10/11` 以及对应 trial/evidence 中。不要按不存在的轮次名批量清理，必须以实际目录名和本文表格为准。

`charging-integration-trial-*` 中，r20 是最终可确认上机基线；`r9-status-precharge-13` 至 `19` 属旧小目录；其余 `trial-private-01`、`r8-status-precharge-01`、`20261026-06..10` 等是历史尝试/证据，体积小但可能被审计链引用，默认只归档不删。

按目录名核验后的结论：

| 历史家族 | 当前位置/状态 | 处理 |
|---|---|---|
| `reference\...\integration-20261026` | 存在，构建回执 | 保留 |
| `reference\...\integration-20261026-r11/r12` | 存在，后续中间回执 | 保留；不纳入 P0 |
| `reference\...\integration-20261027-r13` | 存在，image/logdump 打包回执 | 保留 |
| `reference\...\integration-20261027-r14` | 存在，boot/image/logdump 打包回执 | 保留 |
| `E:\...\charging-integration-20261026-boot-private-01/02/05/06` | 存在，旧 boot 载体 | P0 |
| `E:\...\charging-integration-20261026-fat-private-07/08` | 存在，旧 FAT/logdump | P0 |
| `E:\...\charging-integration-20261027-boot-private-02/03` | 存在，旧 boot 载体 | P0 |
| `E:\...\charging-integration-20261027-boot-private-01` | 存在，回退 boot | 保留 |
| `E:\...\charging-integration-20261027-boot-private-04..09/12..14` | 存在，历史 boot 载体 | P1/保留哈希回执，不自动删 |
| `E:\...\charging-integration-20261027-boot-private-15` | 存在，r20 boot carrier | 保留 |
| `E:\...\charging-integration-20261027-fat-private-01..07` | 存在，旧 FAT/logdump | P0 |
| `E:\...\charging-integration-20261027-fat-private-10` | 存在，回退 logdump | 保留 |
| `E:\...\charging-integration-20261027-fat-private-11` | 存在，r20 logdump | 保留 |
| `E:\...\charging-integration-trial-*` | 存在，历史 trial/evidence | 除 r20 外默认保留或单独归档，不计入 P0 |

### 3.1 最新可确认的整机运行基线

- 轮次：**r20 / `charging-integration-trial-20261027-r20-apsd-rearm-01`**
- kernel 版本语义：**#528**
- boot_id：`67f122ca-d67e-4ca6-b8a7-9de86d702810`
- 设备接受证据：`accepted.json`、auto-acceptance、guard-check 均通过。
- 差量复核：重新计算 carrier 哈希与 r20 manifest 完全一致；boot `758694a1...`、logdump `705aacb9...`、回退 boot `13c98860...`、回退 logdump `b9127946...` 四项均匹配。
- 接受证据目录：`device-evidence-r20\final-boot-acceptance-67f122ca-d67e-4ca6-b8a7-9de86d702810`，其中 `SHA256SUMS`、`accepted.json`、`carrier-readback.json`、`guard-check.json` 均存在。
- boot SHA-256：`758694a1959656d7a97fa91104151a58925f3ab13b46ab25c4ae8553430a4acd`
- logdump SHA-256：`705aacb90b836c02be49e47c2389800bc56312e58ab43e8309a2e85bfb550fee`
- Image SHA-256：`8a4aea91b809423561ffd7cb9bf6f651dd01c1952815e0fce467ce860d944312`
- 证据目录：`E:\edk2-samurai-out\charging-management-20261023\charging-integration-trial-20261027-r20-apsd-rearm-01`

r20 `package-result.json` 的 `package_state` 原文是 `final_boot_accepted_rtc_passed_10h_soak_running_physical_wake_pending`；其 `pending_real_device_gates` 仍列出正式物理拔插、USB 插入/移除 s2idle wake、suspend 内线缆循环、满电到回充和 10 小时 soak 严格审计。因此本文结论必须区分：

- **已有证据**：最终 boot 接受、RTC suspend、固定 5V/500mA tier、模块/服务自检、10 小时 soak 启动与阶段性样本。
- **尚不能声称**：所有物理唤醒/满电回充/10 小时 soak 严格审计已全部通过。

这是当前最新可确认的整机运行基线，不应被 r22-r24 的构建产物覆盖或替代。

### 3.2 后续轮次状态

| 轮次 | 构建/打包 | 上机证据 | 结论 |
|---|---|---|---|
| r21 board convergence | 有 | 有真实 fastboot 成功记录；serial `62bc28a1`，boot SHA `81190bf60836098dbd17636a364a0741468ab9d91f6d00a7b2fa5a0558ad8983`；flash/reboot exit 0 | 保留其 `provenance/device-before-r21.tgz`，这是细粒度安装前备份 |
| r22 typec board | 有 | 未找到对应 fastboot-result | 旧中间轮次，可替换性高 |
| r23 clean | 有 | 未找到对应 fastboot-result | 旧中间轮次，可替换性高 |
| r24 usb budget | `package-result.json` 为 `passed: true`；final boot SHA `95398419a9f987f590ed056278a139905de6eff0c87af71a1490c286dc38a1c4` | 未找到对应 fastboot 成功记录；2026-10-28 有 EUD 尝试记录 `TX 1 at 3018ms: 90 02`，属于未完成尝试 | 当前“待验证包”，不是已通过上机基线 |

关键时间判断：r24 的 `samurai-mp2650.c` 修改约在 2026-10-28 00:24，DTS 修改约在 00:44/00:53，晚于 #528 Image；因此当前源码和 r20 实际运行 Image 不能混为一谈。

### 3.3 最近一次恢复尝试

- 2026-10-28 01:38 的 r15 restore 尝试记录了 `TX 1 at 3020ms: 90 02`，未显示完成。
- 2026-10-28 01:44 新建 `restore-r15-20261028.sh`；它只恢复 userspace/module，不负责恢复 boot。
- 不能把该脚本当成完整 boot 回退入口。

### 3.4 r20 soak 状态的特殊说明

`SOAK-R20-TEST-RESULTS.txt` 记录本地 Windows/Linux 各 331 项测试全通过，soak-focused 35 项通过；同时明确写了“No device access and no module loaded”。`device-evidence-r20\final-soak-10h-20261027-2010\status.json` 显示 `samples: 181`、`running: true`，`package-result.json` 记录 `samples: 601`、`state: running`。两者是不同时间点/不同口径，不能把 601 个计划样本当作全部已完成，也不能把 331 项离线测试当作物理 soak 通过。

负向回归记录：`r14 soak-samples.jsonl` 重放为 `passed=false`、`samples=250`、`boot_ids=8`、`errors=6939`。该旧证据不可用于 r20 的通过声明，反而应保留以证明审计确实拒绝了旧证据。

## 4. 当前构建、打包、刷入与回退入口

### 4.1 构建

```text
WSL source:
/home/cy122/charging-management-20261023/charging-integration-20261026-01/source

WSL build:
/home/cy122/charging-management-20261023/charging-integration-20261026-01/build

旧成功 Image 日志:
/home/cy122/charging-management-20261023/charging-integration-20261026-01/Image-build-status-precharge-r9-final.log

模块构建:
/home/cy122/charging-management-20261023/charging-integration-20261026-01/r8-module

r24 DTS:
E:\edk2-samurai-out\charging-management-20261023\charging-integration-r24-usb-budget-01\dts\sm8150-samurai.dts
E:\edk2-samurai-out\charging-management-20261023\charging-integration-r24-usb-budget-01\dts\samurai-measured-vbus.dtsi
```

`build` 约 1.9 GB，包含当前编译状态，不应整体删除。若必须回收，只清 `.o`、`.tmp_vmlinux*` 等可重建对象，并先保留 `.config`、`Image`、`vmlinux` 和关键日志。

### 4.2 r24 打包与刷入

```text
r24 final boot:
E:\edk2-samurai-out\charging-management-20261023\charging-integration-r24-usb-budget-01\boot-final\boot-r24-usb-budget-final.img

重新打包脚本:
E:\edk2-samurai-out\charging-management-20261023\charging-integration-r24-usb-budget-01\boot-final\rebuild_boot.py

安装包:
E:\edk2-samurai-out\charging-management-20261023\charging-integration-r24-usb-budget-01\r24-usb-budget-install.tar.gz

安装脚本:
E:\edk2-samurai-out\charging-management-20261023\charging-integration-r24-usb-budget-01\install\install-r24.sh

刷入脚本:
E:\edk2-samurai-out\charging-management-20261023\charging-integration-r24-usb-budget-01\boot-final\flash-r24.ps1
```

`rebuild_boot.py` 遇到既有输出会拒绝覆盖；重打包要在新的私有目录进行，或先经人工确认移走旧输出，不能直接删除证据。  
`flash-r24.ps1` 期望 serial `62bc28a1`、Image SHA `95398419...`、boot 分区大小 `0x6000000`；默认**不会重启**，必须传 `-Reboot`。该脚本只刷 boot，不等于安装 r24 userspace/module。

### 4.3 回退

r20 设备端回退（仅 userspace/module）：

```text
/root/charging-management-20261023/trial-517-r15-fixed5v1500/original
```

设备内恢复脚本（只恢复 userspace/module，不恢复 boot）：

```text
restore-r15-20261028.sh
```

boot / logdump 回退载体：

```text
boot:
E:\edk2-samurai-out\charging-management-20261023\charging-integration-20261027-boot-private-01\boot-eud-off-route-private-r7.img
SHA256 13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756

logdump:
E:\edk2-samurai-out\charging-management-20261023\charging-integration-20261027-fat-private-10\logdump-mp2650-r13-private.img
SHA256 b91279466383d04ec17fbdb75d6e08bf2bb4be16d38d383083ee52f8e1dd67b1
```

回退时用 fastboot 分别刷 boot 和 logdump，刷前确认唯一设备为 `62bc28a1`，刷后先不要清空 r20 证据和原厂备份。

## 5. 必须保留清单（优先级 S）

### 5.1 设备证据与 r20

- `E:\edk2-samurai-out\charging-management-20261023\charging-integration-trial-20261027-r20-apsd-rearm-01\` 整个目录。
- 其 `device-evidence-r20`、`source`、`source-snapshot`、`modules`、`service`、`tests`、`manifest.json`、`package-result.json`、`SHA256SUMS`。
- r20 boot carrier：`charging-integration-20261027-boot-private-15\boot-5v1500-private-r17.img`。
- r20 logdump carrier：`charging-integration-20261027-fat-private-11\logdump-5v1500-r14-private.img`。

### 5.2 回退与原厂/个体备份

- `E:\edk2-samurai-out\backup\` 全部（原厂 boot/logdump/GPT/vbmeta/iomem）。
- `boot_stock_RMX1931.img`，SHA-256 `dfe18875...`。
- `logdump_stock.bin`，SHA-256 `a1688d6...`。
- boot 回退：`charging-integration-20261027-boot-private-01\boot-eud-off-route-private-r7.img`。
- logdump 回退：`charging-integration-20261027-fat-private-10\logdump-mp2650-r13-private.img`。
- `boot-samurai-canonical-stockhdr.img`。
- 分区表、NV、modem、persist、vbmeta、原厂资料与任何个体备份（不论目录大小）一律不进入删除候选。
- WSL 设备端原始备份：`/root/charging-management-20261023/trial-517-r15-fixed5v1500/original`；本次未访问设备，不能删。

### 5.3 证据与最新板级产物

- `r15-evidence-20261027` 及其 `.tar`（约 162 MB，属证据，不是缓存）。
- `charging-integration-r21-board-convergence-01`，尤其 `provenance/device-before-r21.tgz`。
- r24 的 `boot-final`、`install`、`package-result.json`、`SHA256SUMS`、`dts/`、`provenance/`；这是当前待验证包，不是旧中间产物。
- `reference/charging-oem-audit-20261023`，以及 `reference/charging-management-20261023` 下源码、脚本、证据。
- `C:\Users\cy122\Downloads\platform-tools`（fastboot 工具，不删）。

### 5.4 源码与构建入口

- WSL `/home/cy122/charging-management-20261023/charging-integration-20261026-01/source`。
- WSL `/home/cy122/charging-management-20261023/charging-integration-20261026-01/build`。
- WSL `charging-integration-20261026-01/r16-zero-contract-module-01` 及 r20 的 source/snapshot/module。
- `/home/cy122/charging-management-20261023/charging-integration-20261026-01/source-r7-backup` 仅在确认源码回退不再需要时才可考虑，默认保留。

## 6. 删除候选与安全等级

以下路径均为候选，不代表本次已删除。等级定义：

- **P0 安全可重建**：已有证据/哈希或明确 `OBSOLETE.md`，删除只损失可重建中间物；仍需逐项核对命令。
- **P1 需确认**：旧轮次或旧 boot/logdump，可能被某些历史记录引用；先保留 manifest/哈希回执，再决定。
- **P2 不自动删**：会话、原厂/个体备份、设备证据、分区/NV、当前回退、最终安装包。

### 6.1 E: P0（保守确认可回收约 3.2 GB）

以下路径以 `E:\edk2-samurai-out\charging-management-20261023\` 为根：

体积复核：r22 约 272,948,031 B（260.3 MiB），r23 约 271,761,923 B（259.2 MiB），r24 `boot` 约 270,543,214 B（258.0 MiB），r21 约 272,829,996 B（260.2 MiB）；r24 `boot-final` 约 270,542,044 B（258.0 MiB）。P0 的 boot/FAT 条目均按目录逐项核验，下面保留一位小数 MiB。

| 候选目录 | 估算 | 理由/风险 |
|---|---:|---|
| `charging-integration-r22-typec-board-01` | 260.3 MiB | 无上机成功记录，已被 r23/r24 后续取代 |
| `charging-integration-r23-clean-01` | 259.2 MiB | 无上机成功记录，旧中间轮次 |
| `charging-integration-r24-usb-budget-01\boot` | 258.0 MiB | 目录有 `OBSOLETE.md`，connector 恢复前旧中间载体；不要删同级 `boot-final` |
| `charging-integration-20261027-boot-private-02` | 258.0 MiB | 旧 boot 中间载体 |
| `charging-integration-20261027-boot-private-03` | 258.1 MiB | 旧 boot 中间载体 |
| `charging-integration-20261026-boot-private-01` | 258.0 MiB | 旧 boot 中间载体 |
| `charging-integration-20261026-boot-private-02` | 258.0 MiB | 旧 boot 中间载体 |
| `charging-integration-20261026-boot-private-05` | 258.0 MiB | 旧 boot 中间载体 |
| `charging-integration-20261026-boot-private-06` | 258.3 MiB | 旧 boot 中间载体 |
| `charging-integration-20261027-fat-private-01` 至 `07` | 56.6 MiB/个，合计 396.2 MiB | 旧 FAT/logdump 中间物；保留 r20 的 `fat-private-11` 和回退 `fat-private-10` |
| `charging-integration-20261026-fat-private-07` | 124.8 MiB | 旧 FAT 中间物 |
| `charging-integration-20261026-fat-private-08` | 121.1 MiB | 旧 FAT 中间物 |
| `old-image503-build-retained-20261024` | 247.8 MiB | 明确标为 retained 的旧 Image 构建 |
| `old-repro-build-retained-20261024` | 247.8 MiB | 明确标为 retained 的旧复现构建 |
| 旧 r9 trial 13-19 小目录 | 约 11 MB | 历史小目录，删除前保留 manifest |

估算：boot 中间目录约 1.51 GiB，FAT 约 0.64 GiB，r22/r23 约 0.51 GiB，r24 `boot` 约 0.25 GiB，old retained 约 0.49 GiB，小目录约 0.01 GiB，合计约 **3.2 GiB**。  
注意：`fat-private-11`、`boot-private-15`、`boot-private-01`、`fat-private-10` **不在 P0**。

### 6.2 E: P1（需确认，扩展约 3-4 GB）

| 候选 | 估算 | 风险 |
|---|---:|---|
| `usb-boot` | 198 MB | 旧启动载体，先确认无回退引用 |
| `eud-boot-pack-baseline-private-01` | 155 MB | EUD baseline，保留其哈希回执后再决定 |
| `gauge-image501-boot-private-01` | 258 MB | 旧 gauge Image boot，已被后续取代 |
| `usb-input-irq-boot-private-01` | 258 MB | 旧 IRQ boot，已被后续取代 |
| `tcpm-sink507-boot-private-01` | 258 MB | 旧 TCPM boot |
| `tcpm-usb-budget508-boot-private-01` | 258 MB | 旧 USB budget boot |
| `eud-boot-two-ffs-candidate-private-01` | 258 MB | 旧候选 boot |
| 其他旧 logdump 目录 | 约 64-121 MB/个 | 只保留 r20/r21/r24 必要回执，逐目录确认 |

该组建议不自动批删；可先保留 `SHA256SUMS`、manifest、结果 JSON，再按引用关系清理。

### 6.3 E: P2（不自动删）

- `E:\edk2-samurai-out\backup\`。
- r20 证据目录、r20 carriers、r15 evidence、r21 provenance。
- r24 `boot-final`、`install`、`dts`、`provenance`、安装包与 SHA 回执。
- `reference\charging-oem-audit-20261023`、`reference\charging-management-20261023` 源码/脚本。
- 任何名为 `partition`、`gpt`、`nv`、`persist`、`modem`、`vbmeta`、`stock`、`original` 的资料，默认不删。

### 6.4 C: 候选

| 路径 | 估算 | 安全性 | 风险 |
|---|---:|---|---|
| `C:\Users\cy122\AppData\Local\Temp` | 448.3 MB | 低-中 | 先关应用再清；临时文件可能被当前程序占用 |
| `C:\Users\cy122\AppData\Local\Temp\DiagOutputDir` | 314 MB | 低-中 | 2026-10-26 旧诊断输出；确认不再需要该次诊断后删 |
| `C:\Users\cy122\AppData\Local\Temp\charging-trial-516-...` | 约 0 MB（空/近空） | 低 | 空 trial 临时目录 |

不建议删除：

- `C:\Users\cy122\.codex\sessions`（约 1.0 GB）：对话/审计记录，不是构建缓存。
- `C:\Users\cy122\.codex\archived_sessions`（约 124 MB）：不是构建缓存。
- `C:\Users\cy122\Downloads\platform-tools`（约 16.7 MB）：刷机工具。

C: 本轮可回收估算约 **0.45 GB**，但不要把 Codex 会话计入“可安全删除”。

### 6.5 WSL 候选

| 路径 | 估算 | 安全性 | 风险 |
|---|---:|---|---|
| `/home/cy122/charging-management-20261023/charging-integration-20261026-01/build-r7` | 122 MB | 中 | 旧 Image 构建快照；先确认 `.config`/Image 已在 `build` 或证据归档 |
| `/home/cy122/charging-management-20261023/charging-integration-20261026-01/build-r8` | 57 MB | 中 | 旧 Image 构建快照 |
| 根下旧候选/测试对象目录（`apsd-*`、`dwc-*`、`tcpm-*`、`usb-input-*`、`gauge-*`、`protection-*`、`charge-timer-*`、`charger-reattach-*` 等） | 约 246 MB | 中 | 多为历史对象/测试工作树；可能有 root-owned 子目录 |

WSL 保守可重建候选约 **0.4-0.7 GB**；把上述旧对象目录全部纳入后约 **0.7-1.3 GB**。不建议整体删除：

- `charging-integration-20261026-01/source`（约 1.8 GB，源码）。
- `charging-integration-20261026-01/build`（约 1.9 GB，当前构建入口）。
- r20 source/snapshot、`r16-zero-contract-module-01`、设备端备份。

部分 root-owned 目录（如 `protection-observed-2719-profile-tests-01`、`charge-timer-hold-tests-*`、若干 `*-objects-*/*-work/work`）当前普通用户 `du` 报 `Permission denied`，本审计无法精确统计；不要用 sudo 批量删除，先单独列出并确认归属。

## 7. 精确清理命令（仅示例，本次不执行）

> 执行前先关闭 WSL 编译、设备脚本、PowerShell 刷机脚本和 IDE；先做 dry-run 或列出目标；命令中的路径均来自本审计，不允许改成通配符根目录。

### 7.1 E: P0 清理（PowerShell，先预估）

本文的 E: 候选里，`charging-integration-20261027-fat-private-01` 至 `07` 与 boot 目录是同级目录，不能用一个 `-Recurse` 删除父级根目录；下表把每个实际目录逐条列出。先执行完整 dry-run，核对输出中的 `Path` 与本文第 6 节完全一致。

```powershell
$root = 'E:\edk2-samurai-out\charging-management-20261023'
$targets = @(
  'charging-integration-r22-typec-board-01',
  'charging-integration-r23-clean-01',
  'charging-integration-r24-usb-budget-01\boot',
  'charging-integration-20261027-boot-private-02',
  'charging-integration-20261027-boot-private-03',
  'charging-integration-20261026-boot-private-01',
  'charging-integration-20261026-boot-private-02',
  'charging-integration-20261026-boot-private-05',
  'charging-integration-20261026-boot-private-06',
  'charging-integration-20261027-fat-private-01',
  'charging-integration-20261027-fat-private-02',
  'charging-integration-20261027-fat-private-03',
  'charging-integration-20261027-fat-private-04',
  'charging-integration-20261027-fat-private-05',
  'charging-integration-20261027-fat-private-06',
  'charging-integration-20261027-fat-private-07',
  'charging-integration-20261026-fat-private-07',
  'charging-integration-20261026-fat-private-08',
  'old-image503-build-retained-20261024',
  'old-repro-build-retained-20261024'
)
$rows = foreach ($relative in $targets) {
  $path = Join-Path $root $relative
  if (-not (Test-Path -LiteralPath $path -PathType Container)) {
    [pscustomobject]@{ Path = $path; MB = $null; Status = 'MISSING' }
    continue
  }
  $bytes = (Get-ChildItem -LiteralPath $path -Recurse -File -Force -ErrorAction Stop |
    Measure-Object Length -Sum).Sum
  [pscustomobject]@{ Path = $path; MB = [math]::Round($bytes / 1MB, 1); Status = 'OK' }
}
$rows | Format-Table -AutoSize
'TOTAL_MB=' + [math]::Round(($rows | Measure-Object MB -Sum).Sum, 1)
```

确认没有 `MISSING`、且路径和本文第 6 节一致后，才可在人工复核下逐条调用 `Remove-Item -LiteralPath $path -Recurse`。不要用 `$root\*`、`-Filter` 或通配符批量删除；`boot-private-01`、`boot-private-15`、`fat-private-10`、`fat-private-11` 必须始终不在 `$targets` 中。

注意：r9 trial 13-19 小目录不计入上面 `$targets`，建议保留；如经确认要清，必须单独列出六个精确路径。

### 7.2 C: 临时缓存（先查看）

只允许精确到 `DiagOutputDir` 或明确的空 trial 目录，不允许清空整个 `Temp`。

```powershell
$temp = Join-Path $env:LOCALAPPDATA 'Temp'
$candidate = Join-Path $temp 'DiagOutputDir'
if (Test-Path -LiteralPath $candidate -PathType Container) {
  $bytes = (Get-ChildItem -LiteralPath $candidate -Recurse -File -Force -ErrorAction Stop |
    Measure-Object Length -Sum).Sum
  [pscustomobject]@{
    Path = $candidate
    MB = [math]::Round($bytes / 1MB, 1)
    LastWriteTime = (Get-Item -LiteralPath $candidate).LastWriteTime
  } | Format-List
}
Get-ChildItem -LiteralPath $temp -Force |
  Sort-Object Length -Descending |
  Select-Object -First 30 Name, Length, LastWriteTime
```

人工确认 `DiagOutputDir` 不再需要后，才可在单独命令中移除；不要清空整个 `Temp`，也不要触碰 `.codex\sessions`。C: 只以 0.45 GB 的临时缓存为上限估算，不把会话目录算进回收量。

### 7.3 WSL（先查看，不要 sudo rm -rf）

下面命令只测量和列出，不删除。旧对象目录需要先看 `stat` 所有者；若为 root 且属于设备/模块证据，保留。

```bash
cd /home/cy122/charging-management-20261023
du -sh charging-integration-20261026-01/build-r7 \
       charging-integration-20261026-01/build-r8 2>/dev/null

find . -maxdepth 1 -type d \
  \( -name 'apsd-*' -o -name 'dwc-*' -o -name 'tcpm-*' \
     -o -name 'usb-input-*' -o -name 'gauge-*' -o -name 'protection-*' \
     -o -name 'charge-timer-*' -o -name 'charger-reattach-*' \) \
  -printf '%f\n' | while IFS= read -r p; do
    du -sm "$p" 2>/dev/null
  done | sort -nr | head -70
```

确认目录不属于当前构建、且无 root-owned 设备备份后，再逐项处理。不要对 `/home/cy122/charging-management-20261023` 或 `/root/...` 使用递归通配删除。若必须清理 root-owned 目录，先用 `sudo find <exact-path> -maxdepth 2 -printf '%u %p\n'` 核对归属，再逐条删除；不能直接 `sudo rm -rf /home/cy122/charging-management-20261023/*`。

### 7.4 构建缓存的安全替代

若必须释放 WSL `build` 空间，优先清理可重建对象：

```bash
cd /home/cy122/charging-management-20261023/charging-integration-20261026-01/build
find . -type f \( -name '*.o' -o -name '*.tmp_vmlinux*' -o -name '*.cmd' \) -print | head -100
```

先保留 `.config`、`Image`、`vmlinux`、`System.map`、关键 `*.log`，再决定是否清理；不要整体删除 `build`。

## 8. 容量估算与执行顺序

| 范围 | 保守可回收 | 扩展/谨慎 | 备注 |
|---|---:|---:|---|
| E: | **约 3.2 GB** | 再加约 3-4 GB | P0 优先；P1 需逐项确认引用 |
| C: | **约 0.45 GB** | 不含会话 | 仅临时缓存；`sessions`/`archived_sessions` 不属于构建缓存 |
| WSL | **约 0.7-1.3 GB** | 可再加上 build 内 `.o` | `source`、`build`、r20 证据不整体删 |

建议顺序：

1. 先备份/记录 P0 目标目录的 `SHA256SUMS`、manifest、`package-result.json` 与关键日志。
2. 清理 E: 的 P0；每删一组后重新测 E: 余量。
3. 清理 C: `Temp\DiagOutputDir` 与明确空目录；不要触碰 Codex 会话、下载工具。
4. 清理 WSL `build-r7`、`build-r8` 和已确认旧对象；保留 `source`、`build`、模块与设备备份。
5. P1 旧 boot/logdump 仅在确认无回退引用、且哈希/回执已归档后处理。

风险提示：

- r24 `boot-final` 与 r24 `boot` 名称相近，**只允许处理 `boot` 旧中间目录，不得误删 `boot-final`**。
- `fat-private-10` 是回退载体，`fat-private-11` 是 r20 logdump；二者不在清理表。
- `boot-private-01` 是回退载体，`boot-private-15` 是 r20 carrier；二者不在清理表。
- `r15-evidence-20261027`、r20 设备证据、r21 `provenance`、原厂 `backup` 是最终证据/回退链，不进入任何清理批次。
- `flash-r24.ps1` 默认不重启；需要重启时显式 `-Reboot`，且先确认唯一设备 serial 为 `62bc28a1`。
- 当前源码晚于 #528 Image；重新构建后必须重新生成哈希并重新上机验证，不能沿用 r20 的接受结论。

## 9. 复核清单

- [ ] E: `backup` 仍在，原厂 boot/logdump/GPT/vbmeta 哈希可读。
- [ ] r20 evidence、r20 boot-private-15、fat-private-11 仍在。
- [ ] boot-private-01、fat-private-10 回退载体仍在。
- [ ] r15 evidence `.tar` 与目录仍在。
- [ ] r21 `provenance/device-before-r21.tgz` 仍在。
- [ ] r24 `boot-final`、`install`、`package-result.json`、`SHA256SUMS` 仍在。
- [ ] WSL `source`、`build`、r20 module/snapshot 仍在。
- [ ] C: 只清临时缓存，Codex sessions 与 platform-tools 未动。

## 10. 本次审计验证摘要

| 验证项 | 证据 |
|---|---|
| 磁盘用量（收尾复测） | C: 464.62 GB / 已用 406.21 / 可用 58.40；E: 476.94 / 351.01 / 125.93；WSL 1007 GB / 118.05 GiB / 837.56 GiB |
| r20 最新成功运行 | `package-result.json` 记录 kernel `#528 SMP PREEMPT Tue Oct 27 08:49:26 CST 2026`，boot_id `67f122ca...` |
| r20 Image | `8a4aea91b809423561ffd7cb9bf6f651dd01c1952815e0fce467ce860d944312` |
| r20 carriers | 重新计算 SHA256：boot `758694a1...`、logdump `705aacb9...`，与 manifest 一致 |
| 回退 carriers | 重新计算 SHA256：boot `13c98860...`、logdump `b9127946...`，与 manifest 一致 |
| r21 上机 | `fastboot-result.json`：serial `62bc28a1`，`flash_exit=0`、`reboot_exit=0`，时间 2026-10-27T23:36:13+08:00 |
| r24 打包 | `package-result.json`：`passed=true`，boot SHA `95398419...`，仅包/构建通过 |
| r24 上机 | 在 `charging-management-20261023` 下只找到 r21 的 `fastboot-result.json`；r24 没有上机成功回执 |
| P0 体积 | r22 260.3 MiB、r23 259.2 MiB、r24 `boot` 258.0 MiB，均已用 `dir /s /-c` 复测 |
| FAT 体积 | `20261027-fat-private-01..07` 每个约 56.6 MiB，`20261026-fat-private-07/08` 约 124.8/121.1 MiB |
| 保留证据体积 | `r15-evidence-20261027` 约 169,195,024 B（161.4 MiB）；`backup` 约 268,783,436 B（256.4 MiB） |
| 文档完整性 | UTF-8 可读，正文包含 r20 结论、磁盘表、目录核验、P0/P1/P2、精确命令、保留清单与验证摘要 |

本文是审计记录，不是删除授权。R15 结束时应保持原厂/个体证据、r20 接受证据与四个回退 carrier 完整。
