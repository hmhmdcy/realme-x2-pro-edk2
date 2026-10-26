# R7 provider 的最小 USBIN 初始化候选

独立离线候选，**默认关闭，禁止安装**。临时USBIN helper尚未完成实体检验；本候选通过测试和编译不代表实机bit7、APSD、图标或充电行为已通过。它只用于未来把已验证的一次普通配置初始化接入现provider，不向NVM/OTP写入。

基线、当前R8仍沿用R7 USB的已留存证据及原厂调用顺序，见 `baseline.json`；实现状态方案见 `DESIGN.md`。R7原C `b712764f…b7098`、FLOAT decoder `a17caa2c…d548fd`、冻结helper core `80aa4274…f11dd9` 均有完整SHA绑定。原厂同机代码支持独立初始化1358bit7，但没有证明VBUS在线修改不会间接触发自动检测，因此本候选只在完整物理off证据下清位。

`samurai-usb-input.c` 是完整候选；`provider-init.patch` 是相对固定R7 C的差异，同时编译需要本目录逐字复制的 `usbin-init-core.h`，FLOAT decoder保持原文件。没有新UAPI、EXPORT、永久服务、恢复入口、PMIC命令、预算或高压控制写。唯一写路径是 `regmap_update_bits(map,0x1358,0x80,0)`；无其它寄存器或I2C访问。

`usbin_init` 加载参数默认false、权限0444。关闭时不读1358、不运行初始化事务。opt-in先要求原DT精确native接线保留路径已经实际执行 `__module_get`：新内部 `native_ref_held` 不可被参数伪造。没有该证据时功能以ENODEV终态退出、零配置IO，原输入provider照常提供原预算。用户预设旧 `native_retained=true` 仍不能授权此新功能。retain先于prepare、首次worker排队；prepare、worker的新IO均由原mutex串行，不新增引用或owner。

probe双读配置一致且bit7已0时记录 `probe_already_zero`，没有清位尝试；bit7为1时 `wait_first_off` 沿原**1000ms**轮询观察，尚未消耗60s期限。首次新鲜完整物理off后只启动一次冻结core CLEAR事务；两相同off样本须跨至少500ms，并在写前重新读取七字段和配置、以实际BOOTTIME验证新prewrite证据不超过250ms且尚未过60s期限。1000ms采样与250ms写前新鲜门是不同约束，不改变原全局cadence。

七字段是1307/1308/1310/1506/1509/150b/150d；off要求plugin、VBUS、CC attached、state attached全off。任一字段或配置改变都重新建立off锚，读错为终态，不复用旧证据。写后读取配置与新七字段，检查原其它bit不变、目标bit为0、仍off且字段一致。明确成功后自动调用冻结core的**零IO commit**记录采用，保存实际oldbit/写返回/前后证据，不再写。失败/不确定保留unknown、pending_restore等历史；`pending_restore`只表示未知修改义务的历史字段，此候选没有恢复控制、重试或强卸出口。

尚未start的WAIT遇普通suspend只暂停，resume用新样本继续等待。已经start的事务由原stop在mutex内取消，保留原绝对deadline及历史，随后在mutex外join worker；resume不能延展、rearm或赦免终态。成功历史也不会在PM后重写：它是该次初始化收据，不宣称PMIC配置跨所有复位永远不变。现native自持生命周期仍持续到下一boot，不能热替换现provider。

新只读平台属性 `usbin_init_state` 输出schema1的缓存JSON；读取它不访问硬件、不推进事务。字段包含stage、paused、真实native_ref_held、probe双值/错误、观察七字段、core phase/running/clear_used、BOOTTIME开始/截止/first/prewrite/post、实际oldbit、attempted/write_return/readback_error/post_error/error、changed/unknown/pending_restore/committed。core phase数值逐字对应冻结header enum，stage单独区分disabled/probe_already_zero/wait_first_off/transaction/initialized/terminal；读取时now_ms不是写前时刻，真正写前时间在prewrite_ms。

源类型、online、native及effective额度、UPower逻辑没有改写。原read_status/get_budget/type/get_property/set_property、resume、board匹配与init/exit共9个函数、预算属性/desc及FLOAT header逐字校验。retain仅增加内部ref证据；poll仅在原reschedule锁内加一步初始化；stop仅追加已start事务的取消。默认路径可见变化为新增零IO状态属性/参数/内部证据、日志描述，以及首次worker排队移到原retain之后；不修改cadence、UDC暂态规则或预算接口。

`test-result.json`：10组新增集成场景，提取**17个实际provider函数**、直接包含冻结core，ASan/UBSan通过。覆盖默认零配置IO、probe0/错误/变化、native参数不能冒充引用、真实1000ms成功路径、首次off锚及重连/全字段变化、WAIT待机恢复与active取消、延迟config跨deadline/251ms fresh拒写、错误/忽略写/写后on或配置变化保留unknown不重试，以及unknown初始化与SDP100/500、FLOAT100、CDP1500预算独立、getter/status零写。硬件/锁/调度是fake边界，不是并发及电气原子性证明；状态formatter在host中stub，实际kernel格式由对象W=1编译检查。没有重跑旧helper12组或FLOAT大套。

`build-result.json`：私有source-view及O目录，仅受影响USB ko，W=1无warning/error，k363/intreeY/depends空；最终ko `7d4e008e…63b68fe`。配置与R7私有配置逐字相同 `7367d3c7…207e5`；共享原config `e48f834d…4df3` 仅少一行未启用的CAMSS_ICP注释，所有CONFIG赋值一致。共享config/Makefile/Module.symvers在构建前后未变。没有Image、固件、SDK、部署、phone或SSH动作。

顺序寄存器读取不能证明读间绝无物理重接；60s门保证截止后不开始新写，不能硬中断已开始的regmap传输或内核调度。下一步仍应先完成临时helper单变量实体结果、审阅真实收据，再决定此默认关闭候选是否可进入未来boot更新；当前不能据此声称USB100/500、EUD旁路或图标延迟已修复。
