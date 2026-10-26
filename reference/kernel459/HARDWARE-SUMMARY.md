# 459：452 r2 有界内核跟踪与原始回执

2026-10-23。主线在充电明确交回后，重新只读采用r6 manifest与正式440基线，执行一次1080p隔离采集。**原始回执严格通过，90秒内未复现缺帧；根因和长期无丢帧仍未验收。**正式相机恢复之后发生用户真实USB拔插，末次充电检查未通过，故本窗口整体验收保留false。

[441](../kernel441/README.md)的720p／1080p同帧PD10几何与自动双遍、[442](../kernel442/README.md)两尺寸真实／替代PD10的LTM消费因果证据继续复用。本窗口针对1080p FULL交付缺口，不新增720p硬件结论或重复未改的LTM扰动测试。

| 项目 | 实际结果 |
| --- | --- |
| 关闭用户态CSV段 | 120消费／120物理IPE，117 math＋3 bootstrap，0序列缺口 |
| 启用CSV段 | 2618消费／2619物理IPE，2616 math＋3 bootstrap，1源图未被应用拉取；90秒上限后以已核身份的pidfd发SIGINT |
| 合计 | 2738消费／2739物理IPE，2733 math＋6 bootstrap；无回执过滤，同SOF PD10／GTM／WB／历史通过 |
| 载荷 | 452 core `e6a90a06…`，旧444 proxy `c7887708…`；441模块与443原厂模式4调校，未混入451新proxy |
| 退出与恢复 | fixture1／应用9为预期取消，worker0；controller终态无错误，两个实际进程已退出、无用户目录／子进程；正式模块／库／包、相机PM、服务和CPU租约恢复 |
| 相机日志 | 新worker使用MONOTONIC；2799行非空日志均在控制器实际窗口内，指定fault0、taint0，且完整保留于之后的全量dmesg |

[原始回执独立审计](camera-r2-validation.json)复用452的严格原始审计器，只读缓存原日志、实际进程见证和CSV。它明确将回执通过、事务内恢复、外部退出与后来充电状态分别记录，**没有删掉失败的外部收尾，也没有把原452 r1报告覆写成r2。**[内核窗口复审](kernel-r2-validation.json)确认后来98条充电 `error=-61` 在相机控制器终态之后；它不证明该充电问题已修复。

## 实际 trace 生命周期与覆盖

457现场探针确认现有8类vb2／V4L2／IRQ事件、独立实例及mono时钟可用。459 helper在实际tracefs上创建新实例，主ring最初报告11280KiB，随后512KiB/CPU请求得到513KiB/CPU、总4104KiB；没有改global尺寸或时钟。使用mono、VFE0 IRQ及minor0过滤，不用排除IRQ的PID过滤。**后续源码／拓扑复核证明minor0是RDI0，而PIX/FULL接minor3，本次V4L2过滤选错节点。**零V4L2记录不能解释成FULL没有发射；下一窗口须用实际媒体拓扑与应用打开FD重新证明角色，不能默认video0。

内核trace共63647写入／39131保留，导出6083193B、读至EOF，逐CPU stats完整。overwrite尾环发生覆盖，不能将完整文件读取等同于全程事件无丢失。452 CSV共39340事件／8192保留、覆盖31148条，尾部18.158351秒，clock错误／Q下溢0、正常StopEnd页尾存在。只能对实际保留的共同区间作关联，不能靠全窗空事件反推硬件没有完成。

本次误复用了宿主模型selection文件，实际实例名为 `k459-host-review`、token也是模型固定值。原CLI渲染因预期末级名不同而拒绝、没有tracefs I/O；主线随后执行的独立runner按实际Plan名称创建了自己的全新实例，重新核probe、boot、完整配置、inode身份和新鲜preflight。命名及随机token偏差保留，不能将该示例作为未来运行授权。本次实例已实际删除，只余原display／radio；global及这两个实例的选定控制逐项相同。所有终态事务禁止重放，下一窗口应使用新私有selection文件名及随机token。

[运行跟踪分析](RUNTIME-TRACE.md)已在共同完整尾段18.158351秒内，将546条成功FULL唯一关联为同owner的done→DQ→用户回调，并核545组QBUF区间与四个buffer/index映射。单比payload时间戳有另一M2M owner歧义，实际使用回调前的因果关系和Q/index交叉消歧。done→DQ中位39µs／p95 300µs；DQ→回调中位10.846µs／p95 13.485µs。它证明这段无缺帧窗口的交付链可取证，不证明旧缺口根因、物理FIFO最低量或候选常驻条件。

## USB拔插后的收尾

控制器和worker终态之后，充电任务告知用户回复旧图标提示并实际拔插USB。外部相机检查读取source `current_max` 得到ENODATA，保留 `passed=false`；随后只读健康两样本均waiting_source，`valid=0`、`protection_ok=0`、`error=-61`、`source_inhibit=1`、`desired_enable=0`、`age_ms=-1`。fault／stop_error／latched／taint为0，限值与native预算未改，但这**不是健康恢复通过**。

主线已明确将手机交回充电任务核查，蓝牙排其后；相机停止SSH。不重放采集、不重启、不做PM或USB／充电状态写入。完整原件私存在PC `kernel452/runtime-collected-r2`、`kernel459/runtime-collected-r2`和`final-health-after-replug-private.json`。相机集合29项、控制器集合21文件；原tar保留，原厂调校与私人日志不公开。
