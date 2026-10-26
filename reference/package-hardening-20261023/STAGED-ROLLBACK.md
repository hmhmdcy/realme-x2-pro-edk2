# 当前k363、r0/r2的隔离事务与回退

`staged-bluetooth-transaction.py` 是本次唯一推荐的隔离安装/恢复入口。默认纯dry-run；仅允许带本轮验证器登记标记的明确绝对隔离root，拒绝`/`、活系统根别名、路径穿越、相关祖先/文件符号链接和目标硬链接。所有变更只作用于该root。工具不连接手机，不启停服务、不卸模块，不修改原签名APK或直接编辑包数据库。

当前工具中的机型、release、daemon和module状态是明确的隔离I/O fixture，不是手机状态证明。root由`validate-staged-rollback.py`从既有r0验证目录复制、登记；不得为了绕过限制给手机根文件系统手工加此标记。现场部署需要主线用真实状态采集替换这一I/O边界，并协调停用/刷入窗口。

流程只针对这两份冻结签名文件：r0 SHA85fa43b6…bb6、r2 SHA f4a7d4eb…71b5。输入包完整hash、真实签名、现有三个模块hash/AArch64/vermagic、唯一APK owner、包版本、错误标志与静止状态都须匹配。r0原件来自已有363归档，逐模块核对到已验签r0相同字节。旧k132或未知载荷拒绝。拒绝发生在任何APK调用之前，真实计数器已核对目标bytes/DB不变。

1. `--action upgrade`：必须clean r0包/字节、已静止。外部检查通过并验签后执行真实APK r2升级，再核对模块字节、owner、版本和f/s/x错误标志。
2. `--action restore-bytes`：仅接受r2 metadata及已知r2或已恢复r0字节。用目录fd、O_NOFOLLOW和原子rename恢复hci_uart到r0，btbcm/btqca保持。此时报告明确为“r0字节已恢复、r2 metadata仍在，数据库降级待办”，不得叫完成。
3. `--action rollback`：接受上述r2 metadata状态，必要时先恢复r0字节，再把原r0 APK显式交给原生APK降级。无需allow-downgrade，也没有任意覆盖参数。只有最后owner/version/hash都吻合且无f/s/x才完成。

例如在验证器已经登记的`/absolute/isolated-root`中，命令须提供`--root`、`--r0-apk`、`--r2-apk`、`--module-archive`、`--apk`、`--verification-keys`。不加`--apply`只列计划、不调用APK。加入`--apply`才执行对应阶段。实际可复跑的完整命令参数见`validate-staged-rollback.py`的CLI和本轮私有日志。

真实原生APK失败实验另有独立root：直接r2→r0触发r0 pre-upgrade校验失败，APK exit1，但文件/metadata已经r0且f:sS。官方v3.0.8源码对应关系见主线`reference/bluetooth-20261023/apk-hook-semantics.json`：小写f/s/x是broken_files/broken_script/broken_xattr，大写S是正常sha256_160。不能要求f字段为空，也不能把f:sS看作成功。

针对这一已知坏状态，`--action repair-r0`是显式的隔离恢复：确认r0字节与仅script错误后，实际升到r2以移除旧s标志，恢复r0字节，再实际降到r0。两个APK无服务副作用，全程保持模块未加载；最后再次核对错误标志已回到S。该路径已用真实APK通过，没有改DB标志，也不自动重试未知失败。它只处理本轮确切状态，不是通用包修复器。

APK3给脚本运行提供自己的/proc，WSL中没有手机device-tree。因此本轮仅在隔离测试root的/bin/sh I/O适配器中，将原签名hook的`/proc/device-tree/compatible`读路径换到固定fixture；每份原始hook逐字留存并核对SHA。其余原始检查和真实APK脚本/DB提交路径照常执行。该适配器不在正式恢复器中、不随APK发布，不能冒认设备验收。

本轮[集成报告](staged-rollback-validation.json)包含四类真实拒绝、dry-run、原生正向/回退、advisory失败后的实际提交与显式恢复。现场仍缺：当前设备owner/canonical path/release/载荷的readback、真实daemon/模块静止、外部入口接真实状态I/O、设备上的加载/扫描/连接/PM及回退验收。签名旧包内guard措辞为历史描述，以本说明为准。
