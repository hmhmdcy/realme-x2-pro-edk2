# Image501 adoption：未执行

默认 `adopt.py` 只核本地冻结源码；没有新boot身份、endpoint或runtime pins。只有实际501 postboot目录、同事务context、root独占窗口及显式 `--execute-adopt --window-confirmed` 才能执行。计划guard由真实事务名生成，首个为 `/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt`。

`review()` 绑定原postboot receiver rc0、report/context/guard哈希、实际executed payload的完整冻结collector字节及编码请求，再调用该实际collector的纯audit重新核501/fullpair/flagY/cmdline/current_avg/500/R8/相机/服务。新kernel version从实际raw identity取得，不能使用旧guard里的#363。合成测试只写临时目录，不是未来新boot原件。

远端payload复用同一冻结只读collector的定义，重新collect+audit并核同一个真实新boot；通过后只在新的adopted目录写fresh验证原件和boot-id，fsync文件及目录。不触CSR/ring/充电控制，不修改旧guard。host先备份原globalpointer，保留一次dispatch intent；原严格kernel184密钥/IPv6/HostKeyAlias参数、stdin `python3 -`，Popen等待同一child真实终态，无timeout kill或自动重发。失败/未知保留原件，只能独立只读核实，不再运行本次adopt。

只有精确成功reply、原pointer仍等于备份时，才创建新endpoint及adoption原件，并以同目录临时文件原子替换globalpointer后fsync。两份完整candidate partition hash同时进入新pointer。中断不伪称adopt完成；旧backup始终保留。后续icon profile必须绑定实际 `adoption-result-private.json`、新endpoint及这份passed postboot，才能生成runtime pins。

3组定向actual函数检查已通过：完整合成501正例/新版本、混合pair/flag/旧version拒绝、实际publish保留旧backup与原子切换。原32/12套未重跑；无设备、网络、远端guard或native worker。执行入口和collector读回仍由root独立审阅后决定。

本修订仅新增host入口和remote payload最前的非assert `sys.flags.optimize` 拒绝门。新增normal default、优化host、优化remote三例均实际通过；旧3组保留原执行收据并按“移除两门即旧源码逐字”证明复用，未重跑。旧cce2源码/收据/delivery/README保存在 `before-optimize-gate/`；现collector、合同和source-pins均未改。
