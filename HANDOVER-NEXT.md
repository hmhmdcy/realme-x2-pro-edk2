# Realme X2 Pro 交接导航

相机按用户要求暂停，进展与恢复步骤见[491交接](reference/kernel491/HANDOFF.md)。续作读[当前检查点](NEXT-SESSION.md)与[适配工作流](linux-port/docs/PORTING-WORKFLOW.md)；后文提交统计和旧阶段入口用于定位历史，不作为当前部署。

用途：兼容旧交接入口、记录仓库工具与旧节号映射。文档整理：2026-10-25；部署身份、目标状态、当前待办与回退依据统一见[当前检查点](NEXT-SESSION.md)。

## 0. 从哪里继续

先读[检查点](NEXT-SESSION.md)、[充电交接](reference/charging-management-20261023/charging-adaptation-handoff-20261025.md)、[操作边界](WORKING-BOUNDARIES.md)和[适配工作流](linux-port/docs/PORTING-WORKFLOW.md)，再按功能查[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。本文件中的工具路径和仓库提交记录用于定位资料，设备状态需按检查点核对。

## 1. 下一步

按用户任务和[检查点的续作项](NEXT-SESSION.md#未闭环与操作)推进；相机按用户要求暂停，当前进展及恢复步骤见[491交接](reference/kernel491/HANDOFF.md)。标准单次AF与早期四摄回归见[278](reference/kernel278/README.md)，此前RAW统计见[277](reference/kernel277/README.md)，标准镜头/CCI见[276](reference/kernel276/README.md)。历史阶段的active和健康值不代表当前部署。音频任务读[音频提示词](AUDIO-NEXT-SESSION-PROMPT.txt)，完整导航见[DOCS-INDEX](DOCS-INDEX.md)。

## 2. 硬件与协议资料

[硬件清单](linux-port/docs/HARDWARE-STATUS.md)维护功能验收；[BINARIES](BINARIES.md)记录固件来源；[EUD](EUD.md)、[RX-CONSOLE](RX-CONSOLE.md)及[SWD-JTAG](SWD-JTAG.md)保留技术历史和证据。历史寄存器值与工具版本按对应会话解释。

## 3. 仓库记录

下方块由`linux-port/scripts/update-repo-state.py`从本地git生成，仅描述已提交历史；当前未提交源码以`git status`/`git diff`为准。

<!-- repo-state:start -->
    master = 30c1f4dc bluetooth: publish coordination and runtime index
             dc88f8d7 charging: publish current read-only investigation and handoff
             9635f869 docs: publish October maintenance and package audits
             3770dc6a bluetooth: publish host stack and transport investigations
             278ea218 platform: publish desktop and device service packages

    222 commits ahead of upstream origin/master, as of the tip named above;

    fork remote: https://github.com/hmhmdcy/edk2-realme-x2-pro

此块不证明未提交改动已构建、已部署或已推送；状态由本地git与检查点核对。

<!-- repo-state:end -->

## 4. 工具与路径

| 范围 | 交接路径 |
| --- | --- |
| EDK2仓库（WSL） | `/home/cy122/edk2-samurai/repo` |
| Windows编辑源 | `E:\RealmeX2Pro edk2` |
| 仓库文档镜像 | `Platform/Realme/sm8150` |
| 镜像与备份输出 | `E:\edk2-samurai-out`；具体包按检查点证据选择 |
| EUD主机工具 | `E:\eud-host` |
| Linux源码/产物身份 | [检查点正式基线](NEXT-SESSION.md#正式基线与新候选)、[相机交接](reference/kernel491/HANDOFF.md) |

## 5. 工具使用依据

固件压缩容器的核对、EDK2日志与SerialPortLib范围见[EUD技术历史](EUD.md)。F1命令、挂起/关流、回执和回退方法见[FLYWHEEL](FLYWHEEL.md)。历史脚本的身份、分区和参数按当前任务核对。

## 6. 当前边界

以[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)为唯一操作规则来源。旧临时禁令按历史解释，失败证据及未验收范围保留。

## 7. 未决问题与历史

功能缺口见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)，本次源码/产物风险见[检查点](NEXT-SESSION.md)。实验全过程见[会话索引](sessions/INDEX.md)及[显示修复历史](sessions/display-handoff-152-165.md)。

## 旧8—30节映射

旧引用如“HANDOVER-NEXT §19.7”通过下表定位，正文仍在原文件中。更多阶段见[会话索引](sessions/INDEX.md)。

| 旧节号 | 内容 | 原文件 |
| --- | --- | --- |
| 8 | Linux boot path and persistent variables - decision | [reference/DECISIONS.md](reference/DECISIONS.md) |
| 9 | Port checklist status | [reference/DECISIONS.md](reference/DECISIONS.md) |
| 10 | Linux porting paths; when a GPT change is really needed | [reference/DECISIONS.md](reference/DECISIONS.md) |
| 11 | EDL (9008) resources for RMX1931; the auth question | [reference/DECISIONS.md](reference/DECISIONS.md) |
| 12 | Final image verified, why boot logs were still missed, two fixes | [sessions/12-final-image-and-log-gap.md](sessions/12-final-image-and-log-gap.md) |
| 13 | EUD log ring buffer implemented | [sessions/13-eud-log-ring-implemented.md](sessions/13-eud-log-ring-implemented.md) |
| 14 | EUD log ring: verified on hardware | [sessions/14-eud-log-ring-verified.md](sessions/14-eud-log-ring-verified.md) |
| 15 | Full DEBUG works; the real cause of the +0x34B8 crash | [sessions/15-full-debug-and-crash-root-cause.md](sessions/15-full-debug-and-crash-root-cause.md) |
| 16 | Commits, boot-option noise removed, SetCPUFreqDxe bug | [sessions/16-commits-noise-and-cpufreq-bug.md](sessions/16-commits-noise-and-cpufreq-bug.md) |
| 17 | Submodule solved with plan A (fork + branch) | [sessions/17-submodule-solution-a.md](sessions/17-submodule-solution-a.md) |
| 18 | Mainline Linux: the kernel goes into the firmware volume | [sessions/18-mainline-kernel-in-firmware.md](sessions/18-mainline-kernel-in-firmware.md) |
| 19 | Kernel command line in the boot option LoadOptions | [linux-port/docs/19-loadoptions.md](linux-port/docs/19-loadoptions.md) |
| 20 | Mainline Linux boots on hardware; kernel moved to the FAT | [linux-port/docs/20-linux-boot.md](linux-port/docs/20-linux-boot.md) |
| 21 | EUD log garbling: kernel-side FIFO overflow | [linux-port/docs/21-eud-framing.md](linux-port/docs/21-eud-framing.md) |
| 22 | Kernel side into GitHub: fork from upstream | [linux-port/docs/22-kernel-upstream.md](linux-port/docs/22-kernel-upstream.md) |
| 23 | Kernel side: fetch and branches done, push blocked | [linux-port/docs/23-upstream-push.md](linux-port/docs/23-upstream-push.md) |
| 24 | samurai-bringup pushed to GitHub | [linux-port/docs/24-push-done.md](linux-port/docs/24-push-done.md) |
| 25 | EUD real console + firmware cmdline/DTB update | [linux-port/docs/25-eud-console.md](linux-port/docs/25-eud-console.md) |
| 26 | Real-hardware review: console works, two culprits, panic loop | [linux-port/docs/26-real-machine-review.md](linux-port/docs/26-real-machine-review.md) |
| 27 | Userspace reached; console to /dev/kmsg; shortcuts vs goals | [linux-port/docs/27-userspace-and-shortcuts.md](linux-port/docs/27-userspace-and-shortcuts.md) |
| 28 | Button-free fastboot and the hands-off flywheel | [linux-port/docs/28-flywheel.md](linux-port/docs/28-flywheel.md) |
| 29 | EUD COM console, tty and command channel | [sessions/29-eud-console-tty-command-channel.md](sessions/29-eud-console-tty-command-channel.md) |
| 30 | Current artifacts and how to drive the phone | [sessions/30-artifacts-and-workflow.md](sessions/30-artifacts-and-workflow.md) |

最早拆分全文见[2026-10-08归档](archive/HANDOVER-NEXT-full-2026-10-08.md)，本轮整理前入口见[2026-10-14快照](archive/docs-before-maintenance-2026-10-14/README.md)。
