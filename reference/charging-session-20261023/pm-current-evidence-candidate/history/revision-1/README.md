# 当前 Image502 adopted boot：一次 PM 定向取证工具

已完成离线实现和10个新增实际函数测试方法；两个默认入口实际rc0。没有生成真实request、访问手机、配置trace、执行PM或编译；旧27／29／126套件未重跑。`PLAN.md`、`finding-result.json`是保留的先前核查阶段记录，最终状态以本README／delivery为准。502准备事务及旧拒绝候选未改。

仅新增三个实现文件：`prepare-request.py`、`worker.py`、`trace-evidence.py`。`pm-transaction.py`逐字复制原库，SHA `fd3fd4be…da0a1`。原worker的healthy／services／configuration_preserved／audit_trace与已测有序日志重叠算法保持，来源及复用边界见`reuse-scope.json`。

## 先绑定真实 adopted 身份

默认只核本地源，不读取global pointer或生成runtime身份：

```text
python3 -B prepare-request.py
python3 -B worker.py
```

只有根已经完成实际#502 postboot/adoption后，才能本地生成新request：

```text
python3 -B prepare-request.py --bind-request --context <image502-notify-live-001/host-context-private.json> --postboot-directory <本事务内真实passed采集目录> --adoption-directory <本事务/adoption-01-private> --transaction charging-pm-current-001 --output-root /root/charging-management-20261023 --output <新的绝对私有request路径>
```

它复用冻结adopt.review重核七原件／完整collector audit，再核真实adopt request/result、同child终态rc0、严格reply、原执行payload、当前pointer和新endpoint。仅接受本轮#502、新guard、boot97811、logdump ace2、R8／481／startup500，未adopt或混合旧501一律拒绝。request含实际身份、原件SHA和固定只读collector／live.state源码；输出仅request SHA。没有guard/pointer/充电/USB写入。

## 根后续独占窗口的顺序（本轮未执行）

1. 根用当前采用身份及原严格key，将该request与hash绑定的`worker.py`、`trace-evidence.py`、`pm-transaction.py`放入新的工具目录；不沿旧r5目录。先仅运行`worker.py --inspect-current --request <request> --request-sha256 <实际SHA> --window-confirmed`，完整stdout/stderr保留私有。inspect没有trace／RTC／PM写入。
2. inspect实时核新guard／boot／SoC／rootfs／loaded notes，再复用固定postboot只读审计和原live.state寄存器读取。保存真实事件format／clock／trigger catalog、唯一RTC IRQ、console清单及实际producer PID/startticks；不沿旧EUD线程。缺`pm_wakeup_irq`保存available=false、errno、null，不造0。
3. 根可先单独启动已有只读Windows `usb500-r8-eud-off-candidate/watch-one-hub.ps1`＋`UsbHubReadOnly.cs`，新私有输出和owned hidden reader，最长180秒；它按唯一0525:a4a1／62BC28A1实际找直连root-hub。**不能启动其host-parent**，该parent会派发USB500控制；也不用旧EUD拓扑query脚本。本叶没有新Windows协调器。
4. 根再次确认同一窗口后，仅一次`worker.py --execute --request <request> --request-sha256 <实际SHA> --window-confirmed`。执行前重复实时前置；唯一事务目录存在即拒绝重放。新建独立trace instance，先安装并逐项回读所有精确过滤器／有界128次stack trigger，之后才enable。RTC只跟踪实际唯一IRQ号；console仅当前worker和确证producer；无function_graph/kprobe或全IRQ fallback。必要能力不足就不arm。原primitive完成sync／count等候后、arm前还复核trace/filter/enable/剩余栈预算。
5. 原primitive至多一次mem；正常或异常均独立保存primitive、trace、cleanup、后样本与result。所有新增清理只作用于自己的instance和尝试过的项，逐项回读，不清全局trace、不新增stopper。SSH未知只观察原owned worker，不新dispatch／重播；不要timeout-kill它。若实际硬件不能按时返回，工具本身不保证强制唤醒或USB恢复，继续由根按原现场恢复路径收敛。

本工具没有host dispatcher。`window-confirmed`只沿用根已协调的窗口声明，不是新的常规审批步骤。

## 结果含义

进程rc0表示证据调度完成，不表示PM通过。分别保留returned、原始BOOTTIME−MONOTONIC驻留、15±5秒检查（**10..20秒**）、预算／保护／配置／服务／相机事实、RTC alarm与IRQ时序、原因接口、trace覆盖与清理。9.99／10／20／20.01已定向覆盖；早退或原因未知不抹掉已证returned和时长。

`pm_wakeup_irq`即使存在并匹配RTC也只记录该原因旁证；该接口不能排除并发来源。本工具始终`unique_wakeup_reason.proved=false`，不把RTC时序或计数+1升级成唯一原因。RTC set事件没有设备字段，亦明确保留此限制；无名称映射证据不启用广域wakeup-source事件。

`local_functional_checks_passed`与`whole_system_accepted`分开。后者始终false，待根同步实际Windows NCM及原严格key的数据恢复证据；configured、回调0、local检查或新Image源码均不替代主机恢复／整机验收。不更改桌面、UPower、预算、CHG、AUTO／INHIBIT或DWC。

## 离线验证范围

10个新增测试方法直接调用新实现，使用临时身份原件和fake sysfs/tracefs边界；事件format来自hash绑定的旧实际console inventory，未来runtime仍必须重新核验。覆盖真实adoption/current pointer拒绝、缺reason不造值、IRQ歧义／format缺失零写、精确过滤与arm前预算、部分write失败及仅owned cleanup、adapter清理不受arm门拦、RTC时序和功能事实分离、10..20秒边界、post/cleanup失败仍留returned，以及原函数／primitive逐字复用。未测试完整Linux tracefs或硬件。

首轮有一个Windows fixture因Linux-only fcntl import失败；源和失败收据保留在history。仅在该测试的模块导入边界加入惰性fake后通过，生产代码仍为Linux实现。没有切换环境、构建或读取设备来补测试。
