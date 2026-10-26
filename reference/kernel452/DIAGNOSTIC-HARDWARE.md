# 452 r1：首个缺口位于成功FULL回调之前

2026-10-23。**首次主摄1080p隔离IPA诊断可用，严格图像链与正式恢复通过。**SOF168有PD10／统计，没有成功FULL DQ或IPE claim／queue；当前证据仍不能区分硬件未DMA、驱动未交付或物理SOF瞬间断供。内核故障另由完整dmesg补读审计支持，原时钟域错误产生的空日志不作为证据。[脱敏收据](hardware-validation.json)由主线已通过的私有审计整理；本次整理没有SSH、编译、重跑硬件或审计。

## 两段计数与正常取消

使用452核心 `e6a90a06…`、原IPA6／签名、旧444 proxy `c7887708…`、443原厂mode4配置与441 build4模块，不混入451新proxy。实际应用／IPA独立进程、候选core与IPA映射、旧proxy exe SHA、uid10000／CapEff0均已见证；CPU选择一致且停止后恢复。

| 段 | appsink消费 | 源端成功／物理IPE | 成功数学＋bootstrap | 完成未拉取 | 消费序号缺口 |
| --- | ---: | ---: | ---: | ---: | ---: |
| trace关闭 | 120 | 120 | 117＋3 | 0 | 2 |
| trace启用 | 232 | 233 | 230＋3 | 1 | 1 |
| 合计 | 352 | 353 | 347＋6 | 1 | 3 |

两段均逐图通过未过滤原始成功回执、消费者offset、同SOF PD10／GTM、实际WB context和成功历史核对。源端成功数与消费数分别保留；启用段额外完成的1张没有被冒认appsink消费。停止时没有放弃已排队图；PD10观察、未排队观察和停止未决另按原审计计数。

启用段首个消费缺口跨SOF167→169，缺168；增量有界监视器检测后约2秒，只向经PID／start_ticks／exe身份核对的应用pidfd发送SIGINT，未向fixture盲发信号。应用按既有449正常取消路径返回9、fixture返回1；这两个值是该计划的预期取消约定，`FIXTURE_RESTORATION result=0`、State NULL、StopEnd和最终idle检查均通过。没有把它改写成普通exit0。

关闭段与启用段长度不同，2个与1个缺口不能作为trace改善丢帧的比较。此次未完成插桩开关的受控时延／功耗基准；应用FD数也只是一次活见证，不是泄漏测试。

## CSV完整性与缺口证据

启用段导出单份CSV，3634条事件全部保留，8192容量未发生覆盖；从Start至StopEnd的trace时间跨度为9.859346秒，clock_errors／q_underflows为0，序号、累计计数与完整页尾通过。该范围是trace会话，不是整个worker运行时间。CSV、原始地址与完整日志只留私有目录。

| SOF168的实际记录 | 结果 |
| --- | --- |
| 相邻成功FULL DQ锚点 | SOF167与169均保留，顺序有效 |
| PD10 DQ／统计DQ | 均有 |
| 成功FULL DQ | 无 |
| IPE claim／queue | 均无 |
| 该SOF的WaitOlder／WaitIpe／WaitPd10 | 无 |

因此本次可观察缺口已经出现在成功FULL DQ回调之前。它不是仅凭“后面没有IPE”倒推的结论；两侧成功FULL锚点和未发生覆盖的完整CSV提供了该窗口的记录。但这仍没有证明硬件是否写入、驱动是否完成／交付，也没有证明哪个硬件时刻缺少可写缓冲。

相邻FULL回调括窗为66.550ms，包含2次RequestEnter、2次FULL QBUF调用／结果、2次FULL DQ及2次IPE claim／queue，NoFreeFull为0。该括窗回调快照的free FULL为1—2、outstanding FULL为0—2。outstanding是成功QBUF减DQ回调，包含硬件已完成但回调未送达的缓冲；free FULL也只是用户态库存。不能把这些数值当成SOF168瞬间的DMA可写队列，不能凭库存为正排除断供或把责任指定给GStreamer。

后续若继续定位，需要把真实DMA／驱动完成事件、交付与SOF时间对应起来，保留QBUF期间的不确定区间；本轮没有据此修改缓冲池、AF／IPA调度或原厂参数。

## 收集缺项与复审

首次collector只打包文件，漏掉关闭段真实存在但为空的 `disabled-120/captures/`。PC审计访问该路径时失败，这是收集目录结构缺项；没有把第一次失败写成硬件通过。

主线随后只读取得 `empty-captures-metadata-private.json`，确认手机目录存在、不是符号链接且成员为空，再仅在PC恢复该空目录。复用同一批原始日志、CSV、回执和终态收据重新审计后通过；原始 `diagnostic-collected-r1-private.tar.gz`未改，没有重跑相机、补造CSV／成功回执或改动其它原始数据。主线已修后续收集入口，让空captures目录也被传递。

## 恢复、日志缺口与适用范围

353个物理IPE全部完成，m2m最终无失败／取消／孤儿；CPU选择、正式440 r32／r27库和包、434三模块及服务恢复。core供电／DMA／映射／导入资源释放，四相机平台设备suspended，P/W各一个uid10000，taint前后0；r5充电manifest、loaded notes、限额、源预算、native allowance、MaxPower和三个开关十字段前后相等。独立 `diagnostic-live-r1-1-private.json`确认worker已退出、无残留进程／用户目录，正式库／包／充电复核仍通过。

**不能据旧过滤日志声称无新增内核故障。**继承434 worker以 `/proc/uptime` 的BOOTTIME起点筛选MONOTONIC域dmesg；r5已有休眠累计偏差，本轮 `kernel-log-private.txt`只有1字节。这个空文件及旧state的空fault数组均不作为零故障证据。

主线随后另取完整dmesg，以可信充电恢复snapshot的实际CLOCK_MONOTONIC为边界，[补读审计](kernel-window-validation.json)覆盖451与452两个窗口：1057条新记录、指定故障模式0、taint0。owner原dmesg最后一行仍在当前完整读回，当前最早记录也早于可信边界，未见丢日志迹象。同次1秒两样本充电健康经实际auditor重算与捕获summary逐字段相同，native allowance保持100000µA、manifest和限额未变；未扩大为长稳／拔插／功耗／温度验收。图像链、CSV及原事务收据没有改写，也没有因日志缺口重跑相机。

完整来源在私有 `E:/edk2-samurai-out/kernel452/`，脱敏JSON仅保留计数、汇总、相对括窗及来源SHA。原始地址、PID、完整boot、日志／CSV及原厂数据不公开。此次仅新增本页／脱敏收据并更新README，冻结源、脚本和既有收据保持；候选未永久安装。诊断可用不等于根因已修、无丢帧30fps、长录像或完整功耗／热验收。
# 后续窗口入口

2026-10-23：本页保留r1原件与结论；后续r2加入现有内核独立trace，见[459实机小结](../kernel459/HARDWARE-SUMMARY.md)。r2未复现gap，末次USB拔插后充电检查false；不覆盖本页r1验收。

