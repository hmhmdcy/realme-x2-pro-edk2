# PM current evidence：冻结R1薄审

审阅对象为session叶delivery `59121dd38e9fcff0ddbef534d51629b72ecf32610292156c2036c81a76e3aee6`；worker `db747bff…aa1a5`、trace `a1ed46dc…ead74`、prepare `ca171f2a…d3343`、10方法收据 `3be04aee…6d5d7`。仅阅读源码/收据，没有执行作者入口、测试、trace、PM、设备、构建或Git。

发现一个需窄修的事实报告缺口：`classify`的`functional_facts.returned`取自同时要求`mem_returned=true && outcome=='returned'`的严格功能门。原逐字primitive在mem实际返回后，若RTC清理失败，会保留`mem_returned=true`但将outcome置为failed。因此R1会把真实返回事实写false，且与`trace_evidence.returned=true`矛盾。应只把原始mem_returned用于事实字段，严格功能通过门仍可要求outcome returned。原10方法只覆盖外层trace cleanup失败，未覆盖这个原primitive RTC cleanup终态。已报根并获确认为实际缺口，作者准备保留R1后窄修。

其它限定新增范围未见第二个阻断：502实际adoption才绑定；新guard与动态进程身份；primitive逐字/旧四函数复用；缺pm_wakeup_irq不造值；唯一实际RTC IRQ、实时format、精准事件filter与有界stacktrigger在enable和arm前复核；失败/耗尽在arm前拒绝；只撤销新独占trace instance及尝试过的项；10..20秒功能窗口；整体接受始终由根独立整合主机恢复证据。不把源码审阅、callback0、UDC configured或reader计数当整机验收。

本审阅尚未批准实机PM。根另要求README写明detached owned worker、stdin DEVNULL、私有普通日志和真实PID/startticks/argv收据；不能直接以前台SSH承载会断USB的PM。后续只核这些窄差异与新反例，不重跑旧27/29/126或原10方法。
