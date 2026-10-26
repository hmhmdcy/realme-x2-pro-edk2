# 本次 EUD boot-only host launcher：纯离线候选，未执行

默认 `python3 -B controller.py` / `check-local` 只核本地固定输入和语法/测试摘要，不导入transport，不创建目录，不访问USB/手机。五个显式动作是 `prepare`、`quiesce`、`fetch`、`inspect-restart`、`restart`；均需新 `--transaction eud-boot-<唯一nonce>`、`--execute --window-confirmed`。此flag由root在实际交接后给出，不代替真实独占。没有fastboot/flash/rollback/cleanup/新boot adoption功能；这些由独立host operator与只读采集器处理。

`input-pins.json` 绑定14份已存在输入：精确4126候选/a30回退及实际passed封装收据、R8已采用清单、481正式wrapper/归还proof、原key/R7 IPv6 transport及其base argv、旧adoption guard、同boot USBIN003实际SoC/compatible摘要来源、冻结guard/contract。私有个体摘要不写本README。prepare只通过已验证的 `python3 -` stdin传源码，逐字复用r7 transport的固定SSH key/known-host/IPv6/HostKeyAlias参数；不拼Windows长命令。

唯一host目录为 `E:/edk2-samurai-out/charging-management-20261023/eud-boot-activation/<transaction>/`。host parent的active-owner原件及远端 `/run/samurai-eud-boot-activation-owner-private.json` 都一次创建，换新transaction也不能绕开旧未知状态；没有自动释放/删除owner。远端prepare fresh读取当前boot/旧guard/SoC/uname/rootfs，和481归还/R8采用/已有SoC原件核对，只上传两冻结worker、481 wrapper与新guard，然后运行同guard完整只读验证。partial prepare/文件/owner失败全部保留，不能自动重做或推进。

每次mutation先持久化本地intent；restart另存与UI相同schema的原host claim。每次SSH由独立host supervisor持真实Popen句柄，记录实际PID/startticks/argv，等待同一child真实终态。controller有界等待35秒后只返回pending，不kill、不重新dispatch；metadata失败也继续join原child，缺原身份的终态不能变成合格context。stdout/stderr/输入源码/job/进程/终态和错误全部留原件。

fetch只读取/回收同事务原件与原进程，绝不cleanup。原pending prepare/quiesce只有在**同原job、哈希一致的原stdin CONFIG、原SSH真实terminal rc0、精确tx/token/boot/action回包**满足时才只读晋升known。prepare guard只从这次原stdout取字节并核hash；quiesce known仍只表示原launch ack，必须再fetch到原PID/startticks/argv已absent/zombie及匹配终态state/summary/bootid后才能inspect。只观察到进程消失或另一PID不能晋升。错/未知回包留存，仍不能派新mutation。

restart同一原SSH终态（包括255）只保留真实rc和remote_outcome_unproved，不把最后 `filesystem_frozen_restart2_armed` 当syscall成功；超时后fetch可从同job终态收敛，不能重发。inspect可重复作只读新鲜检查；commit前须在30秒内重新inspect。远端实际执行保持冻结311e quiesce / 0fb restart，未知native provider不卸载/热替换，未新增普通reboot路径。

`host-context-private.json` 与UI冻结b8f043 operator共用 `samurai-eud-fastboot-context-v1`：七份同目录basename+sha原件为guard、quiesce state/summary/bootid/process、restart原host claim与dispatch。dispatch的host_process是原SSH进程真实终态，`restart_claim_intent='claimed_by_pinned_worker'` 仅说明固定worker负责claim的设计意图；未实际fetch phase时claim_observed=false，syscall_success_proven始终false。后续每次host USB动作仍需fresh唯一精确fastboot serial/msmnile/96MiB及独立claim，不由本context代替。

初版9f1b controller、原6682497d收据和11个实际边界测试源码原hash保留；它们没有重跑。最终240f controller只补Popen metadata失败join与pending只读收敛，运行 `test-revision.py` 的3个受影响实际函数组：包括本函数生成七raw并被UI实际冻结validate_context接受。全部fake进程/文件边界，零网络/设备/native child；默认check-local实际通过。两worker及旧17/8套件不变且未重跑。仍未执行本launcher的任何传输或现场动作。
