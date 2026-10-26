# DWC window r1 独立审查

审查对象为冻结 patch `e708a98cb38f0897328ee2a796f3145e3c022bb29037ce9e0ff5d402491fc287`。发现并复现一处 P1 退出回归；没有改冻结目录、共享 source/build、Image、手机或 SDK。候选作者已在独立 R2 修复，本目录保持 r1 失败证据用于前后对照。

## P1：无 active window 的正常退出提前封住唯一断开路径

冻结 `gadget.c` 的 `dwc3_gadget_exit()` 5263 行先调用 `dwc3_gadget_window_shutdown()`，再于5265行 `usb_del_gadget()`。在正常无 window 的 IDLE 状态，`window->pm_ref=false`，shutdown 3064–3068 行不执行 park，却已在3061行设 `detect_stopping=true` 并随后清 `softconnect`。

实际 source354 `drivers/usb/gadget/udc/core.c` 的退出路径是：

1. `usb_del_gadget()` 1591行 `device_del()` → `gadget_unbind_driver()`。
2. `gadget_unbind_driver()` 1718行 → `usb_gadget_disconnect_locked()` 785行 → `ops->pullup(gadget,0)`。
3. 冻结候选的 `dwc3_gadget_pullup()` 3089行遇 `detect_stopping` 直接返回 `-ESHUTDOWN`，没有 soft_disconnect；3134行的 post-PM 门同样会挡住 off，因此只修第一道门还不够。
4. UDC unbind 没有因这个返回值停止清理，1727行继续 `usb_gadget_udc_stop_locked()` → 1265行 `ops->udc_stop()`。
5. 候选 stop3361行又调 shutdown；仍无 window PM ref，仍不 park，3371行继续 `free_irq()`，随后退出释放端点等资源。

如果正常 gadget 仍在运行，软件 RUN_STOP/pullup 不会经原来的断开路径清除，就可能带活动控制器进入 IRQ/端点释放。这不需要新消费者或模拟 PD/EUD 条件，因此是候选内部已有默认路径的回归。

[reproduce.py](reproduce.py) 只读复制已冻结的 `tested-functions.inc/types` 到本目录，所有实际候选函数字节不改；将原 fixture 的 `usb_del_gadget` 桩改为真实 UDC 的“先 pullup(0)，再 udc_stop”顺序，单独新增无 begin/token 的 main。原13组未运行。ASan/UBSan/-Werror 下得到：[result.json](result.json)：

```json
{"reproduced":true,"active_window":false,"pullup_off_errno":-108,"soft_disconnect_calls":0,"halt_established":false,"irq_freed":true}
```

原 fixture 的 `usb_del_gadget` 仅直接调 `dwc3_gadget_stop`，而 exit 覆盖又先建立了 window/ref，所以跳过了这个真实失败分支。该重现证明代码调用链错误；其中 MMIO/PM 是桩，不能把其 HALT 字段当作手机实测。

最小修复建议：stopping 保持拒绝 reconnect/on、新 begin；允许普通 teardown 的 pullup(0) 通过 early 和 post-PM 两道 stopping 门，按原 PM/IRQ/connect_mutex 路径完成 soft_disconnect。active window（含 RESTORING）中的 off 仍可只记录意图，再由拥有 active ref 的 shutdown park/drop。不能仅在 `pm_ref=false` 时无条件 MMIO park，因为正常 UDC 也可能已经 runtime-suspended。R2 作者已采用两道门均为 `stopping && is_on` 的方向，并准备当前重现及 runtime-suspended off/stopping on 的定向验证。

## 有限范围的其它审查结论

- begin 的 active-only PM get 在两把 DWC 锁之外；claim失败 put_noidle，已 claim 的 HALT失败保留 token/ref。停机赢得 claim/互斥锁时保留 SHUTDOWN，不再伪报HALTED。
- claim/PM transition/system prepare 共用 spin-lock gate；begin 成功后的 PM ref 阻止普通 runtime suspend，prepare→complete 标记涵盖 direct-complete；新 core suspend/resume 错误退出经 gate exit。没有确认另一处 ref 泄漏或未释放 gate。
- pullup 在 busy window 下仅记意图；end 两次有界重评、恢复失败再 park，HALT/restore 错误分开，失败token/ref保留。end释放与shutdown以 connect_mutex 串行，引用释放标志避免重复 put。
- error worker 在 window 内只标 pending，end复用 recovery；stop/exit 先标 stopping，再以 connect_mutex 阻住新恢复，USB/IRQ停止后 cancel_work_sync，再销毁 mutex。其无window断开缺口就是上面的P1。
- caller 仍须提供真实 bound-object 生命周期与工作 cancel/join；上述函数桩、静态审查和私有对象编译不构成 kernel lockdep、完整并发交错或物理电气验收。没有因缺少 PD/EUD/消费者而否定这个内部组件，也没有把“无消费者”当作生命周期并发已证明。

离线复现：

```text
wsl -d Ubuntu -u root -- python3 "/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/apsd-dwc-window-review/reproduce.py"
```

R1 暂不能作为修复完成的组件提交；应绑定独立 R2 patch/实际函数定向测试收据后，再作局部复审。
