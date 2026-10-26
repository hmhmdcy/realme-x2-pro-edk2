# 待机：软件自唤醒已修正，后续验物理USB唤醒

2026-10-24当前：USB IRQ唤醒配置已装机并通过[一次RTC待机恢复](usb-irq-wake-rtc001-result.json)。当前504/USB13f41/97c/f6bef/服务83469/manifest5ef4、boot4e325；真实驻留15.019秒，success+1/fail0，前后12门、USB挂起恢复回调0、原key/NCM自动恢复与SDP500保持，无新fault，alarm/trace清理。原驱动未配置IRQ wake的缺口已补；真实USB插拔唤醒仍待现场，窗口只prepare未启动。前boot的2719完整8帧证据保留，新boot MACv2/p1实例0/0未重查。当前USB两文件逆向0c6a6恢复ebfcb/8c5b7后冷启；更早回退属于不同范围。TCA语义、温界/完整预充再充、FLOAT/APSD与高功率仍未完成。下面旧组合/未加载描述按历史范围读取。

2026-10-24最新：[USB通知修正实机结果](native-pm-notify-r2-result.json)已装入504/ebfcb/94a659并采用。原12门在启动及PM前后通过；RTC单次实际驻留14.874秒，success+1/fail0、无新fault，原key/NCM无需拔插恢复、SDP/native/硬件500mA保持。trace证实挂起内的软件自唤醒消失，通知改在complete发布。物理USB唤醒、温界/完整预充再充和协议/高功率分支仍待验。下文旧未stage、d046和PM失败描述属于此前记录。

## 此前定位记录

2026-10-24 PM001：[原件复核](native-pm-504-smoke-001-result.json)。原27例primitive仅写一次mem，RTC至少余14秒时内核以-EBUSY拒绝；failed_suspend/fail各+1、success0，未实际休眠。原child终态1、自己的alarm已取消；前后12门/500预算、原boot与USB原key保持，无新fault。21原件已完整取回并复核源码与监督链。日志未给具体failed_dev，USB供电通知wakeup仅为待查方向，不称因果或PM恢复通过；不重派001。首嵌入脚本换行错误在本地ast检查及mkdir前拒绝，raw模板修正后实际模板检查过。

2026-10-24当前：[504/4453/d046/34ead实际启动并fresh采用](native-pm-504-activation-result.json)，原97c/7848/bootedd、SDP500及481/468保持，12门含实际stateless依赖通过，NCM自动恢复。下面未stage/502等为准备阶段历史。下一步15秒真实驻留与原key/NCM/500预算恢复，仍未验；不把新boot通过当作PM通过。后续用postboot-host叶的原owner薄入口，完整回退7cb/18e8/ace2。

当前PM核心仍为实装#502原DWC；现USB7cb/charger97c/保护7848、manifest18e8。
新增[冷stage设备](../charging-oem-audit-20261023/irq-native-usb-pm-stage-candidate/README.md)11项和
[当前overlay主机接线](../charging-session-20261023/irq-native-usb-pm-stage-host-candidate/README.md)六项离线通过并冻结；
仅磁盘USB/manifest暂存、保持旧驻留实例与INHIBIT，Full事实不被AUTO清除。
未实际bind/lease/SSH/stage；现已完成[当前启动设备门／单logdump工具](../charging-session-20261023/irq-native-usb-pm-activation-device-candidate/README.md)，
八项集成按未变源码复用、四项context补测通过；001事务正则失败保留，002材料及默认入口过。
17份stage原件与原硬件尾绑定，bootedd只读；单ace2载体回退不能冒作模块完整回退。
[当前主机调度](../charging-session-20261023/irq-native-usb-pm-activation-host-candidate/README.md)六项及三默认过，原23/10函数和supervisor保持；
当前export/current-operator context已接通，原SSH255不当成功，两个预检fd独立释放。
[留存source审核／路径薄入口](../charging-session-20261023/irq-native-usb-pm-retained-source-candidate/README.md)四真实缓存＋两stage模型＋两适配检查通过，
全局pointer读取0。原source执行/终态/保存字节审核保持，WSL绝对路径拼接缺口已由薄适配修正。
后续正向入口用该叶activation-controller.py，沿原current-pointer门与R2监督；不直接用C5入口。
[当前三分支冷回退设备执行器](../charging-session-20261023/irq-native-usb-pm-cold-rollback-candidate/README.md)七项和默认过：
仅USB/manifest两文件，原12函数/20方法与17原件规则复用；source boot结束不认领当前旧PID，
未捕获cache0/0可原样保持，未知预算不提额，Full/fault/timeout不清，partial不重放。
[原动作审核/当前原key probe/binder](../charging-session-20261023/irq-native-usb-pm-rollback-host-candidate/README.md)七组/三默认离线通过；
原七文件上下文/命令回放/R2传输审核保持，实际profile/逆向包绑定，不冒认新boot已验收。
[当前连接式回退](../charging-session-20261023/irq-native-usb-pm-rollback-connected-candidate/README.md)七组/三默认离线过，
11原owner函数逐字复用，原压缩只读probe与regular request/同child监督保持，新增cache/source观测绑定。
[恢复设备检查](../charging-session-20261023/irq-native-usb-pm-rollback-restart-device-candidate/README.md)六组/三默认离线过：
14原件/独立后置probe/当前cache/三profile及6818保护复用，15helper/硬件尾不变，目标仅ace2，bootedd只读。
[恢复host/operator](../charging-session-20261023/irq-native-usb-pm-rollback-restart-host-candidate/README.md)六组/三默认离线过：
显式PRIVATE、后置probe/六文件安装/七原件context接通，C5监督/两fd预检与current logdump-only原worker复用。
[双profile postboot设备](../charging-session-20261023/irq-native-usb-pm-postboot-device-candidate/README.md)六组/两默认离线过：
25原函数及collector主体复用，504正向/502回退各12门、同fd cache和stateless依赖/撤销；模型非新硬件证据。
下一步host启动记录审核/原-C传输/12门结果审核，
以及新boot postboot/adoption。设备还原成功仍仅runtime_pending；回退不要求新postboot全过。
齐备再约现场。
不能套旧501/502/R8 activation身份；用户取消子代理，根会话独立续作。
[当前只读依赖快照](native-usb-pm-current-readonly-result.json)确认legacy控制器
on/active，五个supplier中没有input，不能以旧501快照代替本次事实。

本轮已把原stateless系统PM依赖合入[当前IRQ源码](../charging-oem-audit-20261023/usb-input-irq-native-pm-link-candidate/README.md)，
8个新增probe/IRQ组合通过，[实际单ko d046](../charging-oem-audit-20261023/usb-input-irq-native-pm-link-module-candidate/README.md)
47强导入匹配502、W1/Werror零诊断；原decoder与16个IRQ函数保持。
该依赖仅约束PM回调顺序，仍需配已构建Image504的budget-work fence；现成4453
载体可复用，bootedd/IRQ DT及97c/7848保持。尚未部署或做PM测试，不把这个增量
当成r5恢复、完整UDC/DMA或auto/direct_complete已经通过。

此前仅传播 `dwc3_gadget_resume()` 负返回的候选仍为
[changes-required](../charging-session-20261023/dwc-resume-error-independent-review/README.md)：
core/PHY初始化成功后若gadget失败，负返回会使PM记为suspended而资源仍初始化。
被停止的三个终态字段/IRQ停车草稿继续禁止采用。

本轮核查固定Image363/ba61的原
`apsd-integration/current-r7/snapshots/drivers--usb--dwc3--gadget.c`，SHA
`9eec86e42945a786447e6a6548a25b495e29a01bed8e8fbfc13e02903e1ff0c5`。
原4787行worker已有connect_mutex、soft_disconnect、sleepable disconnect、
IRQ join、既有count/MAX3和soft_connect，因此同步复用不必依赖整套未装的
R2检测窗口。拟议范围是DEVICE-only、core已初始化并保持供电时的一次恢复，
保留原PM返回政策、SUSPHY恢复和runtime pending尾处理；没有实施或编译。

当前configfs/NCM断开链的源码短审未见反向connect_mutex、同步PM-get或
disconnect内flush_work等待。该结论限所选function。runtime回调期间为
RESUMING，必须避免同步PM-get等待自己；pending IRQ对应的put/clear/enable
仍只由原runtime尾处理，synchronize_irq只等待已运行handler。HALT仍可能
有界超时，恢复0也不能当成host配置或NCM枚举成功。

根短审拒绝直接采用“worker锁内仅当err_state==RECOVERY才执行”的去重：

1. 同步恢复开始，err_state为RECOVERY。
2. soft_connect期间，新IRQ错误可再次设置RECOVERY并排worker。
3. helper成功尾若无条件写NONE，会覆盖这个新事件。
4. 新gate随后把worker判为stale，丢掉本应处理的新错误。

原4674行schedule本就只赋RECOVERY后排work，只有一个state值不能区分旧请求
与恢复期间的新请求。原worker成功尾还在释放connect_mutex后才发布NONE。
这些是从实际函数控制流得到的反例与待解决项，不是手机已发生该竞态的证据。
下一方案需保留新事件并明确旧排队worker的收尾语义，再决定是否值得做小增量；
不能用改变IRQ深度、清count或永久拒绝绑定掩盖问题。

后续已形成[原Image363上的DEVICE同步恢复候选](../charging-oem-audit-20261023/dwc-device-sync-recovery-candidate/README.md)：
以原IRQ锁保护唯一新增u64事件序号，成功/失败发布都只消费同代事件；恢复中
出现新事件则保留RECOVERY并单次交给原worker，不吞掉新IRQ。原count/MAX3、
首次soft_connect错误、core.c整文件、PM返回与pending IRQ引用尾均保留。
11组/8个实际函数的新增测试和私有gadget.o W=1构建通过，独立薄审无新增阻项。
硬件/调度边界仍有fake，不能当作完整并发证明。

候选未链接Image/ko、未部署或作PM实测；struct字段变化要求未来完整一致内核，
不能注入当前Image。原负返回候选与被停止草稿的拒绝结论不变，历史r5因果仍未证。
USBIN003现已完成一次真实off-only初始化并正常卸载，但未改善SDP100预算；
它与该PM源码候选分别收敛，不能合并成待机恢复或图标验收。
