# 367：A5 异常重启后的正常基线恢复

366已经实际修好静态固件内存引用并通过四颗传感器取流，但A5响应3超时后出现modem watchdog／新Linux启动，完整ICP握手与正常清理均未通过。旧事务和ramoops只保留证据；临时模块／节点已不在，专用固件副本按哈希清理，没有重试A5 CPU释放。

恢复启动SSC file server exit4，SLPI回滚offline、电源关闭，依赖它的SensorProxy和桌面未启动。按现有正常停服务、DSP停机、EUD退休流程进入bootloader，仅发送fastboot reboot，**不刷任何分区**。固件继续366、DT来源365、Image／模块363、r29/r24用户空间与私有Preview默认保持362。

实际重启、恢复和相机回归状态以各验证JSON为准。完整多摄／ISP目标active；后续优先离线原厂ELF/驱动证据，定位响应3和断电／映射回收路径，而非重复固件启动。第五颗2MP人像身份、完整IPE会话、更多模式、绝对光学/几何/同步和连续AF仍未完成。

本次正常重启完成，boot366/logdump365读回保持，taint0。SSC、SensorProxy、greetd、Phoc/Phosh及PW/WP正常启动；先等待实际服务就绪，才创建新采集事务。[重启](restart-validation.json)、[服务](services-ready-validation.json)。四颗传感器各12帧GStreamer硬件采集，主摄隔离IPA另27帧／五控制阶段及Gamma回执通过，无新相关故障。[恢复后回归](camera-runtime-validation.json)。

最终原密钥USB SSH可用，十个相机相关模块的实际loaded note与磁盘一致；没有活动实验worker、ICP模块、动态节点或临时固件。CAMSS/双CCI休眠，九相机电源关闭、users0，PW/WP各一个uid10000，taint0。[当前健康](final-state-validation.json)。没有用nodeps跳过SSC，也没有清空旧失败或ramoops来得到健康结论。
