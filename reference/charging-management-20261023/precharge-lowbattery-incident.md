# 预充03失联事件：控制已恢复、原结果已取回

2026-10-25更新：原密钥SSH恢复，新启动仍为506。原1299条记录复核通过，实际预充→快充和AUTO收尾已确认；旧日志也证实进入关机并停止sshd，发起者尚未证明。EUD失效getty已清理，本次SSC失败导致桌面未自启；当前低电量命令行正常回充，508未装。详见[恢复记录](recovery506-20261025.md)及[实际预充结果](precharge-live506-r3-recovered-result.json)。

## 恢复前的失联阶段记录

2026-10-25。[原观察](precharge-live506-r3-result.json)已实际完成3.50V降载，尚未验收预充。host42972最后成功读取在boot075f的8877.296秒：SOC3%、电芯3.611/3.612V、31.2℃、净放电75mA、fault/error0、停充计时832；原五进程当时均S。随后SSH的IPv4/IPv6端口都主动拒绝连接，原NCM网卡仍在index29且ping应答，路由确认经过该网卡，无可用串口。

当前无法读取原worker/supervisor终态，也未确认AUTO清理。原host观察器继续轮询，没有重启实验、刷写或放松保护；最后正常样本不代表当前手机仍在正常放电。508仍只暂存，未安装。屏幕状态已异步询问用户，等待其方便时提供。

已复用缓存的UPower v1.91.0原始归档，与此前手机报告的daemon版本一致。[源码控制复现](precharge-lowbattery-source-result.json)直接执行四个完整函数、八项输入组合，ASan/UBSan通过；fixture只提供AC输入、显示缓存和setter收集。接外电且所有电池均放电时，2%会得到ACTION，即使同次OnBattery为false；3%为CRITICAL，接外电且并非全放电则NONE。不能再把OnBattery=false当作本实验不会触发低电动作的依据。

[上游固定版本源码](https://gitlab.freedesktop.org/upower/upower/-/blob/v1.91.0/src/up-daemon.c)的get_warning_level_local保留上述全放电分支，ACTION会安排20秒后调用backend；Linux backend通过logind执行可用的低电动作。此前缓存运行查询为PercentageAction=2、critical-action=PowerOff。这与失联时序吻合，但本次真实关机日志尚未取回，不能据此认定已证明关机或其卡住位置。

原始源码/归档SHA、最后成功记录和首个连接错误保存在private03/ssh-loss-private-01；私有audit-upower-lowbattery-private.py可重现控制案例。首轮fixture漏了显示缓存更新入口而编译失败，保留日志；仅补fixture后通过，未改UPower源码或手机桌面。没有调用真实PowerOff。

关机协调审查补充：缓存SDK开发包为elogind-dev-255.24-r0，已取得并核对上游v255.24的[logind-dbus.c](https://github.com/elogind/elogind/blob/v255.24/src/login/logind-dbus.c)和[bus-polkit.c](https://github.com/elogind/elogind/blob/v255.24/src/shared/bus-polkit.c)，Git blob分别650d5961…b91、904b8979…d79，完整原件存private03/ssh-loss-private-01/elogind255-primary-source-cache.json。手机当前运行版本未取回，这只是参考实现的方案审查。

该实现的旧PowerOff(false)入口转为flags=0，缺少ROOT_CHECK_INHIBITORS。即使普通block锁存在，权限校验仍可接受具有相应特权的发送者；UPower1.91 Linux backend正是调用旧式方法。因此不能把“拿到普通shutdown:block锁”当作已验证的低电实验保护。没有为此更换daemon、修改桌面/全局策略或调用实际关机方法。

恢复管理连接后，先取原观测终态、系统/UPower关机日志和实际elogind版本，核AUTO、保护和电量，再决定后续实验。重复低电观察之前须选定并验证有界的实验协调办法，不能直接套用上述未证实可靠的锁。充电/温控、电芯下限及原始故障保护保持，不能把中断观察当作预充通过。
