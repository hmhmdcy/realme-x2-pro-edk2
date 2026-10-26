# 259：GeoClue 定位生命周期修复与室外复测

GeoClue 2.8.2-r1 已通过签名 APK 安装到原 958 包系统，实际只替换 GeoClue。修复了停止定位后仍将 ModemManager 通知保持开启、刷新率保持 0，以及旧异步请求覆盖新状态的问题。**生命周期修复通过；这轮室外桌面测试仍没有获得坐标。** [安装核对](deployment-validation.json)、[实机开停](lifecycle-validation.json)

原后端在发现 modem 时就改刷新率，释放 GPS 时也不恢复原通知设置，并会清除其它客户端已启用的来源。新实现只在实际请求 GPS 时保存和修改设置，记录自己新增的来源位，等待真实 MM 回包后处理取消/重启，最后释放时恢复原通知与刷新率。没有增加射频、增益或时钟寄存器写入。[包源码](../../linux-port/packages/geoclue/)、[功能补丁](../../linux-port/packages/geoclue/geoclue-modem-location-lifecycle.patch)

原生 x86_64 和 ARM64/qemu 的 10 个回归场景通过，测试包含真实生产后端，而非另写一份状态机。实机 UID10000 四轮请求（立即停止、25秒、立即停止、35秒）Start/Stop/Delete 全部返回成功；停止后观察90秒、移除临时配置后再观察45秒，最终 Enabled0、SignalsLocation=false、刷新率30。成功路径没有手工恢复这些 MM 设置；桌面隐私开关和原配置也恢复。

用户随后将手机放到此前原厂能定位的位置并拔掉 USB。300秒标准桌面请求没有位置事件。被动 LOC 观察器不发送 Start，完整315秒观察中 GPS 最多1颗去重 TRACK；在后来 HIGH 请求之前的前240秒，最高 C/N₀ 32.1 dB-Hz。其频率估计来源均1，1884份测量的重置计数均28，没有在采集中递增；漂移不确定度68.85—71.61 m/s。没有收到 PGA 报告，不能把缺失值写成0。[聚合结果](summary-validation.json)

在桌面测试约258.54秒处另启动90秒原生 HIGH 对照。固件接受 HIGH=3，后续 GET 也返回3，但没有有效 QMI 位置、有效 GGA 或 active RMC，GPS 仍最多1颗 TRACK。它与桌面测试最后约41秒重叠，不能把完整300秒都称作纯标准请求；前240秒分析不受该客户端影响。这个结果也不能证明 HIGH 在正常 ONLINE 下无用。

本轮 modem 实际为 OFFLINE。正常 ONLINE 请求返回 InvalidTransition，LOW_POWER 请求随后也被拒绝；普通 MM Reset 返回成功后实际仍为 OFFLINE。259没有成功执行在线对照。复核258原始日志还发现：258开始前虽然 MM PowerState同为1，DMS实际是 SHUTTING_DOWN，结束时恢复PowerState1才写成OFFLINE。不能把这两个固件状态当作等价的初始状态。

用户拿回并连接 USB 后，59份导出逐件核 SHA。系统 suspend_success=0，无系统休眠进入/退出或 WLAN/remoteproc 崩溃记录；无线 SSH 间歇超时的原因未确定，不能归因于成功休眠。原生258的持续卫星定位通过仍成立；本轮没有修复完整MEMSHARE provider，也没有识别室内 PGA/RF/物理时钟根因。后续新启动及电源管理修复见[260](../kernel260/README.md)。

原始坐标、NMEA、卫星编号、无线端点和启动身份只保存在工作区外私人目录。公开[分析器](analyze-desktop.py)验证导出清单并只生成聚合结果。
