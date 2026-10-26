# TCPM 默认Rp真实USB预算：508合并实测通过，已回506

2026-10-25实测结果：[508 R2三项及自动回退通过](phone-trial-r2-result.json)。真实默认Rp/非PD连接，两次TCPM max/operating与native均500mA；9条软件重连记录确认两者归零再回500，configured及同508 boot原密钥SSH恢复，原worker/兜底均退出。关机取消使用真实worker方法，实际检测OpenRC并释放服务锁，持锁0.272秒，无CPU负载或充电控制写。原300秒恢复器随后自动回到新506 boot82d6，两载体/原文件/三note及四PD控制双0均核验通过；未接纳508为正式载荷。

首次launch只在储备断言处退出，stage-began及任何live写入均未发生；精确失败输入未保存，保留原错误。第二次在最终写入前重新取得硬件读数并保存，未降低原储备谓词。[短测储备](short-trial-reserve-binding-result.json)已把临时20%改为SOC≥10%、RM≥120mAh、两芯≥3.70V及健康正净流联合判断，18例控制过；720秒/500mA规划成本100mAh为估算，不是启动峰值电流实测。原充电电压/电流、温控和恢复器保持。

新506已启动[实际计时观察](../../charging-management-20261023/timeout-live506-start-result.json)，尚未到期。物理拔插/唤醒、完整PD合同、APSD共存及高功率仍待完成。本页下方为各准备阶段记录，其中“未安装/旧01”描述仅对应当时状态。

## 准备阶段记录

2026-10-25最新：[预充03已取回并通过](../../charging-management-20261023/precharge-live506-r3-recovered-result.json)，手机已在新506 boot a2c4恢复。新[508 R2事务](recovered-r2-binding-result.json)已准备并上传，未安装；stage/audit/软件重连执行器已在独立02目录，原两载体硬链接复用，没有新构建或改live文件/分区。实际只读预检已核正式文件及原实验收尾，SOC6%时如实拒绝刷入；后续只读回充记录已到8%，仍须20%/两芯3.70V。

新[收尾判定](check-recovered-precharge.py)及[19例测试](recovered-precharge-test-result.json)核原始文件SHA、1299条已审样本、worker0/负载join、新旧boot不同、当前guard/AUTO/锁可用；不补造原supervisor终态。R2 guard只更改ROOT命名空间，其余字节与已验恢复算法相同；audit和软件重连所有函数AST保持，原13/8组结果复用。原01保留为历史暂存，绑定旧boot且不能执行。

R2私有入口位于charging-management-20261023：`launch508-r2-private.py --preflight`只读，`--execute`在fresh预检通过后只启动一次；`--status`查原事务，`--audit`核真实508预算及载体。基本验收通过且guard有足够余量后，`launch508-r2-usb-cycle-private.py --execute`及`observe508-r2-usb-cycle-private.py --collect`验软件重连；`verify-return508-r2-private.py --execute`只在实际300秒自动回到新506后核验并更新正式指针。四入口默认本地检查，无人工拔插依赖，不代表物理USB唤醒/完整PD通过。

以下为原候选实现及01暂存记录，修复[507实测](../tcpm-sink-shutdown-candidate/phone-trial-result.json)发现的默认Rp预算0。508硬件路径仍未验证。

[补丁](usb-budget.patch)沿当前内核已有的`get_current_limit`、`power-supplies`及`external_power_changed`接口接线。QCOM按[DT引用](usb-budget.dtsi)取得实际USB power_supply，未注册则真实defer，错误原样返回；读取ONLINE/CURRENT_MAX，离线、失败、非正预算均为0。单位由µA转mA。固定5V试验的500mA仅作为上限，实际许可100mA或0仍分别返回100或0，不填固定值。

USB枚举、挂起或恢复可改变许可而不改变CC。新增TCPM供电通知在端口锁内，只刷新已注册、已连接、有VBUS、默认Rp、非PD且处于SNK_READY的受电端；只在数值改变时发布。协商中、明确合同、其它角色/Rp和未就绪状态不覆盖。注销先在同一锁内置registered=false，等待正在执行的通知退出，再销毁原协议worker；没有伪造CC事件或新增轮询。

[五组测试](test-result.json)执行六个完整实际函数，覆盖100/500/0变更、单位/上限、读取错误、供应者缺失/defer/错误、PD/角色/连接/状态隔离、重复通知与真实pthread注销并发。ASan/UBSan通过；测试框架首编译曾被原注销循环的signed ARRAY_SIZE告警拒绝，按内核警告口径调整框架，运行源码未改。[增量构建](build-result.json)只编两个受影响对象再链接Image508，W=1零诊断；配置、电量计、initramfs、builtin元数据和全部导出逐字相同，共享输入/挂载不变。

[DTB](dtb-result.json)仅为实际usb-input@1300增加phandle0x15d，并在Type-C节点增加标准power-supplies引用；其它节点/属性、5V500mA PDO和临时禁用APSD的策略保持。[boot](boot-package-result.json)复用已验证BDS，仍只换原506中的BDS/native DT两个FFS；其它99个FFS、SEC、兼容段、ramdisk及绝对尾部保持。[FAT](logdump-package-result.json)在已验证R2载体中只替换同尺寸Image数据，目录、分配、另一个DTB和slack逐字保持，读回/fsck -n通过。

| 候选 | SHA256 |
| --- | --- |
| Image508，59,439,616B | d7c86e2c0ed70d4e6c3380cf2b1ef67a0962182ce35fe69a4317091bcedfbc16 |
| boot | 321702a839769bc5791d751343b022a5d00e56bc5d35689debeb1f449d3d8198 |
| FAT/logdump | 0504f0dbfa9826cf859f502ab54af8bd365ed7bc17918cf69e408974405476d5 |

[独立暂存](staging-result.json)：phone `tcpm508-trial-20261025-01`、host private `image508-budget-trial-private-01`。原件复用已核缓存，旧两载体硬链接；所有待用内容、稳定分区身份及当前原文件已核。trial manifest c92f0a…aaf76，guard f3f1bd…e9630。[恢复器等价检查](guard-equivalence-result.json)仅更改R2实际自动恢复成功版本的三类身份字面量，其余字节相同。仍为300秒用户态自动还原506；不能恢复用户态之前的硬挂，不接纳为正式版本。

[stage](trial-stage.py)要等预充03收尾、AUTO恢复、五原进程退出及SOC≥20%/两芯≥3.70V，再核实际原件后才可写入，尚未执行。[只读验收](audit-phone.py)记录实际角色/预算和错误栈再作判断，并核真实供应引用。后续短测实际预算和自动恢复，不能以软件测试当实机通过；完整PD合同预算、高功率、APSD共存及物理USB唤醒仍未完成。桌面、充电参数、保护及MAC诊断状态不变。

验收进一步限定到本轮实际默认Rp、非PD、原SDP500连接：两次TCPM maximum/operating limit都必须等于实际native500，不能只凭“非零且不超过500”通过。[13项实际谓词测试](audit-budget-test-result.json)排除0、滞留100、超原许可、PD/其它Rp、断源和错误电压。host `launch508-budget-trial-private.py --check-local`通过且未访问手机；显式执行前还会拒绝未收尾或未补足电量的状态，未启动本试验。以上只改host验收/入口，不重编、不换暂存载荷或改恢复器。

动态验证入口只读核查：实际506的`/sys/class/udc/a600000.usb/soft_connect`存在、0200，当前configured/function samurai/high-speed。固定内核udc/core.c的soft_connect_store依次走正常gadget disconnect与UDC stop，但未把内部start/connect返回值传给sysfs调用者；composite_disconnect实际请求VBUS draw0，reset为100、配置后按原500申报。因此必须以实际预算和枚举状态验收，不能凭写成功判通过。

[有界软件重连执行器](usb-budget-cycle.py)及[八项控制测试](usb-cycle-test-result.json)现已准备，未上传或执行。仅在508基本验收通过且原300秒guard仍有至少三分钟余量时，保持原描述符/500mA申报，走soft_connect正常断开，最多观察5秒实际native/TCPM共同归零；无论失败或异常都请求重连，最多25秒观察configured且两者实际恢复500。先启动的独立7秒兜底只在原试验boot、主请求未返回且仍未配置时补一次connect；原自动恢复不延期、不接纳、不并发restore。当前源码只检查了控制/异常收尾，独立进程与硬件路径尚未实测。

私有host `launch508-usb-cycle-private.py --check-local`通过且未访问手机；显式入口记录一次attempt再传输，未知结果先查原进程/文件，不能重放。手机即使观察成功也只置phone_path_passed，整体passed仍为false，须原严格key的SSH在同一508 boot恢复后另验。仍不代表物理断源、USB物理唤醒或图标延迟通过；没有写soft_connect、重枚举或中断当前预充。

主机只读collector `observe508-usb-cycle-private.py`按已实测NCM MAC/类型查唯一在线网卡，重新取得接口编号，沿用原HostKeyAlias/strict key；不扫描任意网卡、不修改网络。实际probe已通过原key识别506/configured/index29，未操作USB。十二项控制案例确认只接受同508 boot、原载荷pins、实际500mA/configured、原worker/兜底均结束且恢复进程仍在；拒绝错误boot/密钥条件、100/0滞留、PD、进程未收尾和恢复器失效。以上为主机逻辑/当前506传输证据，508动态路径仍未执行。

返回核验入口 `verify-return508-private.py --check-local`已通过，未访问手机或改当前adoption。复用507 R2实际成功的核验，限定508自动300秒恢复后的新506 boot，检查两载体/稳定分区身份、原文件/三模块note、500/250mA/8.725V、保护/MAC缓存、route绑定及四PD控制双零，再建立新boot guard/更新正式506指针。返回后的健康电芯下限用3.50V，与候选健康验收一致；stage前SOC20%/两芯3.70V储备门保持。核验结果会先保存手机以便恢复未知SSH结果；入口尚未执行，不是508返回已通过。
