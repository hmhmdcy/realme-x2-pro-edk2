# 451离线比较候选：同450核心，旧／新／旧proxy

此处仅准备可审查链路，没有SSH、remote stage、实机运行或重建。451已有构建源码、产物与指纹未修改；450既有证据保留。[计划](comparison-plan-validation.json)中的passed仅表示离线准备通过，hardware_validation_passed仍为false。手机窗口与新交接manifest由主线决定。

固定为隔离IPA主摄1920×1080三段A1旧→B新→A2旧，每段appsink实际消费180图，共540图。沿用450核心3503c173…、444 IPA4c90047d…／签名f5c351bd…、441三模块、443原厂mode4配置、449长fixture／GST和450原样用户启动器。仅worker由c7887708…换为35526054…再换回。三段复用同一个用户路径、相同环境及载荷；启动前逐个核对哈希。

## 文件与离线检查

- prepare-comparison.py：先执行存储挂载守卫，再核对现有产物，生成私有worker、计划及文件清单。无handoff时不生成可stage包；已有就绪包拒绝覆写。
- capture-body-comparison.py：手机端函数定义，导入不执行设备操作。复用434模块／服务事务外壳和既有fixture，三个消费者依次运行；不包含温度／频率／充电观察器。
- observe-comparison.py：默认仅生成检查代码，显式--live并提供新handoff才会只读访问手机。终态检查worker／fixture／用户进程／proxy已退出、用户目录清除，并重新核对正式库／包、四设备suspended、P/W各一个uid10000和充电状态。
- check-comparison.py：只读收集缓存，复用443完整同SOF PD10／GTM／WB／成功历史审计，仅将120图约束参数化；不删除或改写任何原始回执。

已用450 r3的9000图原始缓存验证严格审计通过，并插入一条重复成功回执确认拒绝；结果仅写私有kernel451/comparison-auditor-cache-validation.json。没有将这份缓存冒认为451实机结果。

## 新交接约束

当前未提供新handoff，因此计划ready_for_manual_stage=false、payload_generated=false。旧450 charging-snapshot中的manifest常量不会进入新worker。

主线取得新手机窗口后，再向prepare-comparison.py同时传--handoff和--baseline。handoff为主线当次只读preflight生成的私有JSON，字段为：

~~~json
{
  "schema": "samurai-camera-handoff-v1",
  "window_id": "k451-proxy-comparison-r1",
  "window_owner": "camera",
  "fresh_preflight_verified": true,
  "issued_at_utc": "当次交接时间",
  "boot_guard_path": "当次实际boot guard绝对路径",
  "formal_baseline_sha256": "同传baseline文件的实际SHA256",
  "formal_library_sha256": "正式已安装libcamera.so.0.7.2的实际SHA256",
  "charging": {
    "manifest_sha256": "当次实际manifest SHA256",
    "notes": {"三常驻模块名": "各自实际note SHA256"},
    "limits": {"input_current_limit": 0, "constant_charge_current": 0, "constant_charge_voltage": 0},
    "source_type": "实际类型",
    "source_budget_ua": 0,
    "native_udc_allowance_ua": 0,
    "gadget_maxpower_ma": 0,
    "service_enabled": true,
    "native_retained": true,
    "control_enabled": true
  }
}
~~~

示例零值仅描述字段，必须用现场实际读数替换。baseline沿用434／450事务的当次formal notes／status／core结构。worker在停止用户服务或切换模块前，核对新handoff、boot guard、内核ABI、完整载荷manifest、正式库及实际充电快照；充电模块用当前samurai-charging实现verify／loaded_matches核对。第三段结束、正式恢复后再取同一组稳定字段并要求完全相等。没有硬编码旧源类型、预算、MaxPower或manifest。

只有新handoff及baseline具备、450严格回归通过，才在私有comparison-prepared-r1生成comparison-payload.tar.gz。prepare没有stage或launch功能。主线应审查后复用既有安全stager：新根目录不存在、逐文件哈希、0700事务目录、fixture／launcher可执行、正式恢复和原事务不重放。不得拿半成品worker直接启动。

## 活见证与性能口径

每段第一次出现有效IPA统计后，事务只进行一次有界/proc见证：确认应用与实际统计IPA为不同PID、两者uid10000／CapEff0，实际映射同一450核心及指定IPA模块，并直接哈希/proc/IPA_PID/exe。需要其真实exe路径等于本段用户proxy路径、SHA等于A或B预期，并用start_ticks前后核对防PID复用。写私有live-proxy-private.json；仅payload拷贝哈希不能替代它。

见证记录起止时间和结束时已消费帧号。随后停止轮询，等待同一个客户端正常完成；没有常驻观察器。性能三段采用相同起始帧max(60，三段最晚见证结束帧＋8)，若晚于120则拒绝性能窗口。报告dispatch、AF→tone及返回尾部、焦点CPU／墙钟、配对到入队／回执、PTS间隔的中位数／p95／p99／最大值和SOF缺口。日志区间包含调度和IPC，不是worker CPU计费。

A1／B／A2各自产生180个消费者样本；停止时已完成但appsink未拉取的图、已入队但停止中放弃的图，继续按严格原审计分别计数，不冒认全都被消费。每段核对CAPACITY_STOP原掩码恢复，最终核对驱动物理计数、资源释放、正式模块／服务、无新增内核故障和taint0。

先以observe-comparison.py --live取得明确terminal且worker退出后的独立残留收据，再运行check-comparison.py --root 收集目录 --residual 该收据。内部finalize不能代替worker自己退出的外部见证。完整日志、proc路径和见证只留私有kernel451。

这是一次短A/B/A，受场景、缓存、温度及调度随时间变化影响；不锁频、不改原厂调校或AF。A1与A2漂移必须一并报告，不能凭一次B更快宣称33缺SOF根因已修、无丢帧30fps、功耗／热或编码录像验收。
