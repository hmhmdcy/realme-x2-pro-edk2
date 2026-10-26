# IRQ配套 boot-only fastboot 操作者

此候选服务于独立`usb-irq-protection-activate-*`事务，复用已冻结的实际502操作者。新增范围只有stage-aware上下文、对应源码/载体绑定和仅boot写入。默认`check-local`只检查工作站现有源码、载体与工具，不访问USB、不创建未来boot身份、guard或运行请求。本轮尚未上机，也不修改当前prepared502事务。

候选boot为`eddadec3…f6e06`，原boot为`97811cc4…7f695`；两者均96MiB。logdump始终要求保留实际502载体`ace2e261…63ed1`，此工具没有logdump/rootfs/相机/NV写入命令，不能用于Image503。完整新boot、IRQ与充电状态在之后的只读postboot中核对；fastboot写成功与reboot返回0都不证明系统启动成功。

## 实际上下文

`host-context-private.json`必须来自同一个新activation事务。沿用七件原raw：guard、quiesce state/summary/boot-id/process、restart claim/dispatch，另带实际host `stage_directory`和`stage_fetch_directory`。validator重新调用独立`stage-proof.py`，重审真实502 adoption、原stage请求/上传源码/执行fetch与两个真实child终态，再把规范化stage原件、SoC/rootfs、adoption及fresh-validation原hash逐字段与guard比较。仅手填passed/hash外形或旧501/prepared502材料不能替代。

新guard必须是配套stage-aware合同；quiesce已终态、原PID/ticks/argv ended证据和restart原worker/source/once claim/真实SSH终态都须匹配。SSH rc255或“filesystem frozen”仅是原dispatch事实，不能授予已成功重启的结论。工具每次inspect、flash或reboot前仍重新查询唯一精确fastboot serial、msmnile product和boot/logdump真实几何。

后续host activation控制器负责产生这些**实际原件**；此叶不运行quiesce/restart，也不制造它们。缺材料时在创建fastboot动作目录前拒绝。常规修复授权沿用，`--window-confirmed`只表达root已经协调好的当前设备独占窗口。

## 显式单次动作

WSL中默认检查：`python3 -B fastboot-operator.py`。实际使用时只有root持当前窗口才可对实际context调用：

```sh
python3 -B fastboot-operator.py inspect --context <actual-activation/host-context-private.json> --execute --window-confirmed
python3 -B fastboot-operator.py flash-candidate --context <actual-activation/host-context-private.json> --execute --window-confirmed
python3 -B fastboot-operator.py reboot-candidate --context <actual-activation/host-context-private.json> --execute --window-confirmed
```

`rollback-original`和`reboot-original`分别为原boot的显式一次动作；不存在自动回退、自动reboot或重试。任一动作claim即永久占用，部分或未知原件保留，只能`fetch`查看同一原进程。每个fastboot命令由原detached worker持有确切Popen并wait真实终态，PID absent不制造退出码。后续reboot绑定最后一次对应成功写boot的claim/result原hash；之后若有失败或未知写入，不能拿旧成功记录继续启动。

**原boot回写不是三文件rootfs回退。** 先前stage的新USB/protection模块与manifest仍可能在磁盘，故本工具始终`rootfs_rollback_proven=false`。完整旧R8恢复仍需受控INHIBIT、精确三文件回退和后续新启动验收；此缺口未完成前，不能把boot-only工具称作完整IRQ激活/回退方案。既有prepared502不依赖此新路径。

## 离线验证范围

31项新增边界检查实际执行boot-only dispatch、last-write reboot绑定与stage-aware context比较。所有USB/进程/认证接口均明确fake，临时fixture不作为未来运行材料；独立stage-proof本身由其自己的保存材料审核测试覆盖。15个未变函数和worker/main仅action schema的变化绑定旧收据，未重跑旧22项套件。

`completion-proof.py`另提供纯读取API `review_completed_activation(context_path)`，供新postboot host复核原flash/reboot材料：每条原command的requested argv、实际Popen记录、同PID wait终态0、stdout/stderr原hash均须匹配，再通过saved-call接口复用真实run_action验证产品/几何/Writing输出。实际observed argv保留Windows互操作形态；精确发起命令由requested argv与固定Popen源码绑定。它返回context/guard、源boot、两个动作的request/result/命令材料摘要，并始终声明新boot/硬件读回及完整rootfs回退尚未通过。新增13项保存原件边界通过，原31项不重跑；没有实际传输或新postboot身份。

最终冻结来源及收据以`delivery.json`为准；未验实际刷写、IRQ递送、图标延迟或整机恢复。
