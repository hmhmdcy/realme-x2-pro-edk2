# 当前boot：正常服务停充计时与真实回充观察

2026-10-25。计时R2已实际安装，bootbc612/chargerbef4/manifestf15ecc，[启动采用](../../charging-management-20261023/charger-timer-activation-result.json)及[本组合RTC](../../charging-management-20261023/charger-timer-rtc001-result.json)通过。用户授权无人值守操作，不能人工拔插；桌面、保护与原有预算算法保持。

第二轮原事务 `/root/charging-management-20261023/charger-full-recharge-live-20261025-02`已[实机通过并收尾](../../charging-management-20261023/charger-full-recharge002-result.json)：原worker14837/start445667终态0、receipt_error为空，worker与supervisor均已退出，服务锁fresh重新获取并释放，AUTO、独立保护Good、缓存及500/250mA/8.725V保持。adoption仅新增本组合真实回充/计时切换通过标志；不得重放已结束launch。

实际自然放电4212.953秒、415样本，全程保留Full/cause3/计时0；截止电芯4.193/4.189V。原服务AUTO后19样本观察到策略自行退出Full并恢复有效充电，未清Full或fault。随后29个已确认停充样本跨59.995秒，累计安全计时保持10秒；AUTO后六样本计时13/15/16/19/21/23秒，继续累加。全部原始样本重新经过实际IO校验。没有附加CPU负载、改电压或保护，也没有物理拔插；这是Full→自然放电→真实回充及计时切换证明，尚不覆盖低电预充到Full完整循环、温界或10小时到期。

后续原只读观察 `/root/charging-management-20261023/charger-full-return-readonly-20261025-01`已[实机通过并收尾](../../charging-management-20261023/charger-full-return001-result.json)。原worker24901/start978588、supervisor24900均退出，原worker终态0/receipt_error为空。377个真实AUTO样本跨3846.921秒，原策略自行进入Full/cause3并保持五样本/40.947秒；最后电芯4.325/4.323V。全程零新增充电控制、未改参数，全部原样本通过实际IO验证，fresh AUTO/Full/独立保护Good、缓存及500/250mA/8.725V保持，服务锁重新获取并释放。adoption已加入本组合真实回满标志，原事务不得重放。与前轮共同证明Full→自然放电→回充→Full的正常策略闭环，不是低电预充、温界或10小时到期证明。当前没有仍运行的本轮手机观察器，可以继续准备下一启动组合。

第一轮01已[完整收尾](../../charging-management-20261023/charger-full-recharge001-result.json)：放电2288.936秒、226个放电样本及70个AUTO样本均通过原IO验证；Full/cause3/计时0保留。载荷下达到4.233/4.231V，但AUTO后最高电芯回弹到4.270–4.281V，高于原4.2625V再充门槛，recharge_count始终0，未触发回充或计时测试。原worker9678/start182041终态1/已退出，无protocol或cleanup错误，原服务AUTO/健康Full保持和锁释放经fresh检查确认。此轮是不充分条件，不能标为再充通过。

第一轮约19分钟时附加CPU0普通计算负载，原worker11834/start294368在AUTO恢复时正常退出，实际1166.764秒、零充电控制动作；上限1200秒，温界33℃，没有改变CPU/调度/温控策略。因此第一轮不能称全程空闲功耗测试。第二轮没有附加CPU负载；第一轮原负载进程已确认退出。原始记录在`charger-full-recharge-load-20261025-01`私有手机目录。

`recharge-exercise-r2.py`仅把放电观察截止值由4.24改为最高电芯4.20V，为实测回弹留余量；原充电CV/温控/100mV再充策略不变。经原服务INHIBIT，保留真实Full/cause3，至截止值或最长5400秒后经原服务AUTO；达到截止值后观察最多150秒的真实Full→回充与计时累计，再做60秒确认停充及12秒恢复观察。总上限5720秒，没有清Full/fault/timeout或重查MAC。旧协议和第一轮完整原结果保留。

`worker.py`提供同boot/guard、实际模块notes/manifest/service/保护缓存实例验证、原service锁及固定非破坏寄存器读；实时要求独立保护有效、温区正常、SDP/native/硬件500mA、CC250mA、整包8.725V及无fault/latch。未知或不安全情况停止推进，不绕过保护恢复；只有新鲜状态通过时经原服务AUTO。主动取消可在原手机事务目录创建`cancel-requested`，原worker至多10秒看到，按同一安全清理路径处理；不要直接杀进程。

首次短观察01因缺supervisor输入在启动worker前失败；02原worker终态1，在任何stop/resume前拒绝，命令记录为空。两份失败保留，不能当计时暂停证明。随后手机已是真实Full/计时0，不能强清Full凑出测试条件，因而采用当前自然放电方案。

[`exercise.py`](exercise.py)的[四个定向协议案例](test-result.json)、[首版四个回充协议案例](recharge-test-result.json)及[第二版五个案例](recharge-r2-test-result.json)通过；新案例明确拒绝“放电过阈值、AUTO后回弹且Full未退出”被标成功。这些离线案例的硬件IO是模型；上述第二轮结果才是实际手机证据。状态增加recharge_wait/timer_hold/terminal阶段；实际载荷、原进程日志和样本私存，只公开脱敏结果。
