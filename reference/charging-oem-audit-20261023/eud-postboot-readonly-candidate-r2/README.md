# Postboot R2：精确 Full / normal 验收修正

本叶是冻结R1 `eud-postboot-readonly-candidate` 的独立修订，不修改R1任何字节。R1完整device SHA `8850cf7a…f6cda`、10组收据和全部文件hash保留于原目录及本叶revision-source-result；原收据不能当成已覆盖本次Full一致性边界。

已确认真实软件反例：原Full测试仅把481缓存样本设为logical/hold/full_holding=1、cause2、desired0，保留session969。R1实际check_charging接受它；normal仍残留full_cause2也被接受。这是采集器验收缺口，不是新实机Full故障。

唯一行为修正是静态抽取固定 `apsd-usbin-init-host-operator-r2/common.py`（SHA `5c737abf3a5d23d71260dd4c49048191615ca5f1436ac49ea18282f8ccd17c38`）的 `healthy()` 两条真实full/mode赋值，形成纯helper并在原telemetry分支前核它：

- logical_full、hold_requested、full_holding、full_cause任一非零，必须三flag全部1、cause为1/2/3、desired_enable0、session_seconds0。
- 四字段全部零才进入normal，并要求desired_enable1。

没有另造充电状态机，不更改已知source预算、保护、温区、文件/分区、RAM、服务或传输策略。`r1-to-r2.patch` 是完整device差异；`healthy-mode-source.inc` 和revision-source-result绑定实际来源。默认check-local和原root显式execute/window/newendpoint契约保持。

`test-full-result.json` 只执行受影响11个Full/normal病例，并与固定common.healthy实际函数逐例差分：健康normal、session0的三种Full cause接受；Full969、normal残留cause/hold、Full desired1/缺holding/缺logical/缺cause均拒绝。还仅对两个已知回归执行R1实际函数，证实它原先错误接受。原10组未跑，原其余9组仅复用其冻结收据；这不是新设备采集或全套验收。

独审另报“合法marker+截断/畸形marker前缀”可能仍被R1过滤判ready的问题，已送root定范围，当前Full窄补没有混改它。不要把Full测试通过解读为该marker问题已解决或整条postboot链已实机验收。

没有设备/SSH/USB/SDK/Git、boot/guard创建或恢复动作。root的已完成prepare只为本次现场状态来源，不在本叶测试范围。
