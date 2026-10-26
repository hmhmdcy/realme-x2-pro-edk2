# 182：活跃录音期间的一次合成 ADSP 崩溃报告恢复

继续音频goal，并答复用户关于一加/Realme相关Linux移植的研究。使用已部署kernel181，没有重新编译或刷写。原parecord在Mic PCM RUNNING时经历一次debugfs remoteproc合成MMU故障报告；自动重建声卡/两regmap/PulseHiFi，旧FD均EIO、供电恢复，同source-output连接到重建Mic，恢复后右声道编码音相关0.96958。

17项测试窗口错误0；最终同boot2515秒taint0、双功放18/18关闭静音，16保存控件恢复，五consumer各1、两map/一MCLK、cache-only=N、NGD suspended。20项当前全boot错误0，NV/分区/770模块132核验。保留预期crash日志、可选SoundWire提示与历史178/180失败。

原report的7.927秒字段误名：包含后续播放/等待，不是纯恢复时间。原件保留，派生摘要更名；25ms名义采样观察card资源缺口0.3615秒，之后2.2069秒capture RUNNING。只验证合成报告后的恢复，不证明真实DSP watchdog或故障期间无损连续音频。

重新读取一加7T Pro原始声学/UCM移植记录。171已利用固定一加补丁及Realme本机原厂SD1/GPIO140依据修正SD0/GPIO139，并获用户听音确认；不套用TFA9874参数到MAX98937。详见[本轮证据](../reference/kernel182/README.md)、[181实现](../reference/kernel181/README.md)、[171线路与人工确认](../reference/kernel171/README.md)。

后续：活跃播放恢复、较长重复PM、跨启动及音质/瞬态/保护；真实watchdog、耳机/耳麦/按钮仍未验收，用户暂无耳机。完整goal active。
