# 357：公共 IOMMU 引用修正与停滞现场恢复记录

2026-10-20。修正主线 OF/IOMMU 保留区查询的设备树节点引用泄漏，完成源码回归和 ARM64 对象构建；尚未安装。设备恢复尚未完成，目前停在 Qualcomm 9008，需现场强制重启后继续实机工作。完整多摄／ISP 目标保持进行。

`of_iommu_get_resv_regions()` 对 `iommu-addresses` 中每个 phandle 调用 `of_find_node_by_phandle()`，原代码没有释放返回的引用。356 R4 的真实日志在移除覆盖时报告该设备节点“期望1、实际21”。357 在公共框架内将循环局部节点改为 `__free(device_node)`，正常结束、零长度 continue 和分配失败均自动释放，不在相机驱动补偿计数。[补丁](iommu-node-lifetime.patch)。本改动只修引用生命周期，没有改写地址翻译和保留区类型算法。

对原／新实际公共解析函数体执行同组9场景：普通、coherent、四区域、零长度、分配失败、缺映射属性、物理地址解析失败、带物理区以及100次重复查询。原函数累计泄漏409次，修正后归零，区域数量／类型／访问属性保持。[回归](node-lifetime-validation.json)。OF API 由桩提供，不能替代设备上验证。

实际 ARM64 内核 `drivers/iommu/of_iommu.o` W=1／-Werror 构建通过，12.72秒，无诊断，对象27736字节。[构建](kernel-build-validation.json)。保存并恢复相关共享构建输出，没有请求 Image／模块目标，也没有向手机安装；此功能在当前内核为内置，未来需纳入统一 Image。源码分支 `samurai-iommu-node-lifetime357`，提交 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`，父356 `3a485310...`，一行变更、459字节补丁、分支干净。[源码](source-state.json)。

设备恢复过程获得了 SSH 之外的直接证据：

| 操作 | 实际观察 |
| --- | --- |
| USB 与 EUD 控制端观察 | NCM 曾仍枚举，9501 控制器可读，原 CTLOUT为1。 |
| 开启既有 EUD COM、被动接收 | 成功解码924帧。CPU5长时间 RCU stall，NMI无响应；`sshd-auth.pam` 在 `smp_call_function_many_cond → kick_all_cpus_sync → BPF JIT → seccomp` 等待。这直接解释 SSH 握手超时。没有取得 CPU5 本身的堆栈，不能断言其精确卡点。 |
| EUD Ctrl-U／换行 | 各一次请求均有新内核回执，出现真实 `/dev/ttyEUD0` 登录提示；其它核和 EUD 接收工作仍可运行。 |
| 已知控制台账户登录 | 用原有私存凭据尝试一次，未观察到 shell 或明确拒绝；没有修改认证设置。认证阶段采集含敏感输入，仅私存，后续 pstore 也需避免原样公开。 |
| Qualcomm EUD MSM reset | 按已有 `quic-eud/src/ctl_api.cpp::eud_msm_reset()` 的 bit0低／100ms／高顺序，在同一控制句柄完成一次复位。最初一次辅助脚本因 PowerShell UInt32 参数转换在打开句柄前失败，没有发出复位，修正后实际发送一次。 |
| 复位后观察 | NCM消失，主端进入05c6:9008／COM16。读到 Sahara HELLO：命令1、48字节、协议2、最低1、模式0，证明已离开旧 Linux 运行状态；没有恢复正常系统启动。 |
| Sahara RESET_REQ | 按现有开源实现发送一次8字节命令7，收到命令8／长度8的复位确认。随后仍枚举9008；确认响应不能当作 Linux 恢复成功。 |
| 退出 EUD COM／VBUS | 9505已移除、WSL USB转发已释放，9501与9008仍在。最后一次读串口无新HELLO；没有重复发出系统复位。 |

EUD reset 原函数来自已在主机保留的 Qualcomm 公开实现。Sahara 包依据 [bkerler/edl 的 cmd_reset](https://github.com/bkerler/edl/blob/master/edlclient/Library/sahara.py) 及 [协议常量](https://github.com/bkerler/edl/blob/master/edlclient/Library/sahara_defs.py)，定点下载两个文件并记录 [哈希](sahara-upstream-sources.json)；GitHub API限流，未获得提交号，实际文件私存并按哈希标识。没有上传 programmer、刷写分区、访问 NV 或更改启动镜像。[恢复状态汇总](device-recovery-validation.json)。

已请不在现场的用户方便时，按[realme 官方方法](https://www.realme.com/in/support/kw/doc/2083404)同时长按电源＋音量上超过10秒，出现启动画面后松开并保持USB。不能把当前9008状态当作正在运行的 Linux，也不能把旧R5工作报告补写成成功。其旧 Linux 进程已不可能在当前 PBL/Sahara 环境运行，但没有获得正常终态与清理报告。

356的板级物理固件区修正 `0x9ab00000`／5 MiB及命名 `memory-region` 候选仍待实机启动验证。恢复后先采集 boot ID、pstore、原R5事务及临时文件状态，再决定清理与下一次实验。完整 ICP SYS_INIT／PING／PC_PREP、IPE图像会话与原厂调校接入仍未完成；曝光表、防频闪、更多模式、光学、同步、连续AF等目标继续保留。
