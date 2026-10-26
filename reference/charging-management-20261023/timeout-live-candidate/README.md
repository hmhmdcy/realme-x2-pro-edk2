# 十小时安全计时实测：506 周期在校验瞬变处失败

2026-10-26只读取证：[失败结果](../timeout-live506-failure-result.json)。测试在
boottime 31,124.625秒、驱动计数31,029/36,000秒处结束，原因为无字段的
`AssertionError()`；已记录的2,976条样本全部健康，最大间隔10.409秒，尚余
4,970.543秒。最后健康样本为AUTO/SDP/500mA、59%、27.8℃、双芯3.930/3.935V、
fault/source_inhibit/error均0。失败发生在下一轮采样校验，恰与Windows主机
00:13:11–00:16:54睡眠区间重合；supervisor随后读source得到`ENODATA`，无关机事件，
模块仍live。不能把本次记作真实36000秒到期或AUTO锁存通过。

验收器已补诊断：每轮在`validate()`前保存原始attempt，失败时写
`failure-private.json`（阶段、字段、实际/期望值、errno、traceback、partial与
last-good），supervisor清理也记录阶段和堆栈。控制案例25项、低SOC 10项、负载6组、
关机13项均重新通过；未重跑实机长测，硬件结论仍为false。

2026-10-25最新：[实际启动](../timeout-live506-start-result.json)绑定508已验证回退后的boot82d6/新guard，原源码和载荷已冻结到private timeout506-private-01及手机timeout506-live-20261025-01。supervisor6483/start68160、worker6484/start68170、CPU6485/6486/start68240；原进程均实际S，已观察587→885秒、297.229秒实际BOOTTIME相符。首次之前的587秒不冒作连续采样；实际到期目标仍36000秒，没有改时钟、计数或时限。当前未到期、不能标通过。

为利用本次正常恢复的新周期，补[低SOC正常回充检查](low-start-test-result.json)10例：最低10%，低于20%仅接受正平均电流及两芯≥3.70V；已有balance在SOC≤25时将全部实验负载duty固定0。加入正常current_avg只读属性；温度/压差/电芯范围、保护、caps及真实观察器保持。初期实际15%、平均131mA/瞬时136mA、25.2℃、duty0，fault/error0。正常到期后不要求保持正充入，仍须实际停止/超时锁存。没有为了省时模拟到期或降低36000秒要求。

本次手机由该长测占用，期间不再进行刷写、重启或USB状态切换；离线功能适配可继续。先查原PID/心跳/终态，不因SSH等待超时重启实验。以下“未上传/未启动/20%”为此前准备阶段，当前以本节和实际启动JSON为准。

2026-10-25。实际驱动[计时实现](../charge-cycle.h)及[已部署R2](../../charging-session-20261023/charge-timer-hold-r2-candidate/README.md)使用BOOTTIME累计36000秒；已证实的Full/再充和60秒停充计时不重复测试。本执行器补真实到期停充与AUTO不清除到期周期，仍未装机、未绑定新boot、没有十小时实机通过结论。

失联恢复后补上[关机检测](shutdown-observer.py)：依据本机旧日志中真实的`/sbin/openrc shutdown`入口，核实际可执行文件dev/inode、root UID、精确参数、存活状态及两次startticks。worker取消并join自有负载、正常关闭服务锁；supervisor收到同一事件会先join worker，跳过关机期间的fresh服务IO。也覆盖worker先退出、关机随后开始的分支。未修改UPower/elogind策略，不依赖未经验证的普通block锁。

[13项控制检查](shutdown-test-result.json)执行实际检测器、worker.cancelled、timeout观察取消/负载join、supervisor两个关机路径，并在本地真实flock上确认释放。进程内容和Popen边界为fixture，没有关机手机；实际手机上仅执行闲态只读检测，返回无待关机。[整合检查](shutdown-integration-result.json)确认worker除cancelled外13个方法AST不变，原24项观察/6组负载结果按未变函数复用，原软件证明的旧SHA保留并附新增来源。未来上传须包含新增shutdown-observer.py；正常重启下的实际取消/锁释放仍须另验，不能把上述软件案例当作硬件通过。

[观察器](../timeout-observation.py)不接受修改时限或假时钟的参数。由实际计数≤900秒的新充电周期开始，每10秒采样，检查计数与实际BOOTTIME一致且不重置；保留首次已累计值和实际观察时长，不把首次之前的时间写成连续观察。只在真实计数到36000、cycle_timeout=1、-ETIME、停止写读回成功且CHG位确实停止时确认到期。随后结束CPU负载，使用正常内核AUTO属性一次，等待安全采样后再次确认超时与停止仍保持30秒。该操作不使用服务的健康resume入口，因为它会按故障恢复路径转为INHIBIT，混淆本项测试。

[手机worker](worker.py)仅适用于精确506/原三模块/83469服务/8b402 manifest；未来从508短测恢复后生成私有baseline中的实际boot和guard，先做只读预检再启动。原MAC缓存/实例保持，不查询或rearm。持有原充电服务锁，正常500mA源、250mA充电帽和8.725V保持，所有寄存器读取沿现有安全列表，不读破坏性REG14。温度18–37℃、SOC20–70%、电芯3.50–4.15V及压差30mV观察边界，Full/源变化/保护或IO异常即不通过并停止负载。

为避免充满使计时正常重置，最多在CPU4/7各使用30%普通调度负载，以瞬时电流的移动平均接近零净电流；低电量/电压归零负载，34℃限到10%、35℃归零。没有改充电电流/电压、温控、计时或FET。子进程有父进程死亡信号、30秒控制新鲜度和绝对期限，CHG关闭/异常自行退出；父进程持有Popen句柄并join。[监督器](supervisor.py)另有90秒心跳和37030秒期限，先join worker，再检查原辅助进程身份及fresh状态，不清除真实错误、不强行恢复充电。测试后实际到期周期仍保留；后续正常重启按原厂易失初始化恢复，须另外核当时状态。

[24项控制测试](../test-timeout-observation.py)覆盖提前到期、快/慢/重置计数、Full、温度/低压/故障、采样中断、取消、停止或AUTO失败、AUTO误清超时及清理失败；时间/IO建模只验证验收和收尾逻辑。[六组实际负载方法测试](test-load.py)覆盖控制方向/上限/降载、早退、重复收尾、等待超时kill及部分启动失败join。结果见[软件检查](software-result.json)；手机worker/supervisor仅语法检查，不能据此声称实体运行、到期停充、TCA或完整充电管理通过。

当前[预充03已收尾](../precharge-live506-r3-recovered-result.json)，[508 R2三项及回退已通过](../../charging-oem-audit-20261023/tcpm-usb-budget-candidate/phone-trial-r2-result.json)。实际长测已在本次新506周期启动，状态见本页顶部；不依赖人工拔插。
