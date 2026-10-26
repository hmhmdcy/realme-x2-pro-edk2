# 充电管理当前进度（2026-10-25）

2026-10-26最新：[506十小时观察失败取证](timeout-live506-failure-result.json)。测试在
31,029/36,000秒处因无字段`AssertionError()`终止，全部2,976条已记录样本健康，
失败发生在下一轮校验；时间与Windows主机睡眠00:13:11–00:16:54重合，supervisor
随后读source为`ENODATA`，未见关机/模块卸载。已补原始attempt、failure-private、
last-good、errno和traceback落盘；25项观察、10项低SOC、6组负载及13项关机控制
重跑通过。未完成真实36000秒到期/AUTO锁存，整体仍未完成。

2026-10-25离线增量：[充电适配交接](charging-adaptation-handoff-20261025.md)汇总预算消费者、ADC5板级测量、PD/APSD接管及5V退出候选。预算消费者38项实际函数测试/ASan/UBSan和单KO W1/Werror通过，未部署；ADC8例函数缩放和DTB精确差异检查通过，物理精度未验；APSD 3708断言/156故障点及5V shutdown 34函数测试、6对象W1通过，完整probe整合=false、高压采用=false。用户报告EUD串口打开失败后，[82d6只读复查](console-eud-recheck506-result.json)确认tty/getty/reader未就绪，不改桌面。10小时观察仍运行：当前累计8643/36000秒、31%、26.2℃、平均+65mA、AUTO/Good、fault0、实验duty0.3；保持同一进程，不刷写/重启/切USB。

2026-10-25最新：[508 R2三项实测及自动回退通过](../charging-oem-audit-20261023/tcpm-usb-budget-candidate/phone-trial-r2-result.json)：默认Rp TCPM/native两次均500mA；软件断开共同0→重连500、原key/同boot恢复；实际关机取消释放服务锁0.272秒。300秒恢复器已回正式506 boot82d6，原两载体/充电文件/三note/PD双0重核。首次储备断言拒绝发生于写入前，原失败保留；第二次最终边界fresh读回后成功。临时20%短测门已按实际RM≥120mAh/SOC≥10%/两芯3.70V替换，原充电及保护参数不变。

同一新周期已启动[真实计时观察](timeout-live506-start-result.json)：worker6484/start68170、supervisor6483/start68160及两CPU原进程实际S，首计数587、初期885，与297.229秒实耗相符。15%低电量正常回充、平均131mA、duty0、25.2℃/fault0；新增10例低SOC检查，SOC≤25强制零实验负载，低于20要求正平均流/两芯3.70V。真实36000秒到期与AUTO不清超时尚未验收。手机本轮归该长测，不再刷写/切USB；可继续离线协议/驱动工作，整体适配未完成。下方均为各阶段历史。

2026-10-25续作：[508 R2新事务已上传](../charging-oem-audit-20261023/tcpm-usb-budget-candidate/recovered-r2-binding-result.json)，绑定当前a2c4与真实预充完成证据；19项新gate控制过，不补造supervisor终态。实际只读预检正式/收尾通过，储备不足时拒绝刷入，未改live文件/分区。guard仅ROOT变化，audit/软件重连函数不变，复用原软件结果；四套R2入口已本地检查。原只读回充observer11522/start325368仍S，实际60条、8%/24.7℃/+138mA、fault/error0。另补[长测关机取消](timeout-live-candidate/shutdown-integration-result.json)，13项实际方法/本地flock控制过，闲态手机只读检测过，真实关机/十小时未测。下一步继续等原回充到20%/两芯3.70V，再做508预算/软件重连和实际自动回退；整体未完成。

2026-10-25最新：[控制已恢复](recovery506-20261025.md)，新boot a2c4c6f2仍为506，两载体/充电文件/三note/PD双0重核、正式guard已更新。[预充03原1299条记录复核通过](precharge-live506-r3-recovered-result.json)：停充计时832保持，3.298/3.287V后AUTO，实见phase1/+82mA→连续phase2/+98/+93mA，32.866秒完成回充观察；负载join、worker0，非恒流精度或低电到Full证明。旧日志确认关机/sshd TERM，调用者未证。EUD失效getty已注释并重载，不改桌面；本次SSC失败阻止桌面，两次原桌面启动净流为负后正常停止。当前3%/25.3℃/+82mA、AUTO/Good，先命令行回充；只读观察器已启动。508-01仍绑定旧启动和缺失终态，禁止执行，须新事务/新boot guard；SOC20%/两芯3.70V门保持。下述受阻/未知为恢复前历史。

2026-10-25：连续三轮核得同一SSH拒绝条件；最新USB仍只枚举NCM、ping应答，没有其它可用管理通道。原预充进程/AUTO终态与当前电量无法读取，实际关机原因未证实。上机适配受阻，等待已询问的屏幕状态或控制连接恢复；只读host42972保留原记录，未重启观察、改保护或刷入508。恢复后先取证、确认AUTO/健康和电量，再继续，整体适配未完成。

2026-10-25：控制连接仍拒绝、ping仍通。补查[elogind参考实现](precharge-lowbattery-incident.md)：SDK版本255.24-r0对应上游两文件已核Git blob；旧PowerOff(false)为flags0，普通block仍可能被特权授权越过。不能把普通关机锁直接当作已验证的复测保护，未部署该方案或改daemon/全局策略。手机当前elogind版本、关机日志和原实验终态仍待取回，屏幕状态问题保持待答。

2026-10-25：[预充03管理连接失联](precharge-lowbattery-incident.md)，末次8877s/3%/3.611–3.612V/31.2℃、fault/error0、原五进程S；随后IPv4/IPv6 SSH拒绝，NCM仍在线且ping应答。进程终态/AUTO清理未知，未重启或刷写。缓存UPower1.91四实际函数/八项控制复现证实接外电但全放电时仍会在2%触发ACTION，OnBattery=false不能作为防关机依据；真实原因仍待手机日志。预充尚未验收通过，508未装，屏幕状态已异步询问，历史“继续运行”仅为失联前。

2026-10-25：[预充03](precharge-live506-r3-result.json)已实际触发3.50V降载，boot075f的原7505/7506/7507亲和性由4/5/7改为0/1/2并读回，占空比上限0.1。触发时两芯3.500/3.523V、净放电303mA；后续实际约81mA、3.603/3.605V、34.2℃，fault/error0、计时832保持。仍在INHIBIT放电，未到预充验收；原worker/supervisor/host42972继续，未改充电参数或抢占508。原始观测保存在private03/load-reduction-observed-private.json。

2026-10-25：508软件重连的主机只读collector已补齐，按已观察NCM MAC/类型动态取得接口编号，保留原strict key/HostKeyAlias。实际只读probe识别506/configured/index29；十二项同boot/pins/进程收尾/真实500/guard验收条件测试通过，不替代508实测。返回506核验入口复用507 R2成功检查，本地语法/身份转换检查过，保留stage储备门，尚未执行。未上传或执行软件重连；原预充03五进程live，最近约11%/34.4℃、fault/error0。

2026-10-25：新增[508软件重连短测执行器](../charging-oem-audit-20261023/tcpm-usb-budget-candidate/usb-budget-cycle.py)，仅走原soft_connect，要求实际native/TCPM共同0→500和configured恢复；断开异常也重连，独立7秒兜底及原300秒恢复保持。八项控制测试通过，host一次启动入口本地检查过；未上传/执行，手机观察成功仍须同boot严格key SSH恢复才可整体通过，不作物理拔插证明。原预充03五进程仍live、约22%/33.9℃、fault/error0、停充计时832保持，没有抢占。

2026-10-25：508只读验收补为两样本实际native500＝TCPM maximum/operating limit，确认default Rp/非PD；原“非零≤500”会误收滞留100，现[13项实际谓词案例](../charging-oem-audit-20261023/tcpm-usb-budget-candidate/audit-budget-test-result.json)通过。私有host启动器本地检查过，显式启动前拒绝未收尾/电量不足，尚未执行；暂存载荷/恢复器未变，预充03继续。

2026-10-25：[TI测试版资料补查](../charging-oem-audit-20261023/gauge-2719-bqstudio-beta-check/README.md)确认公开测试版已为1.3.130/2026-06-23，稳定版仍1.3.101.1。公开说明没有精确2719配置；两个按旧目录形式查询的新版文档404，安装包需审批且未下载，不据此断言整个配置集合不支持。无新TCA/保护语义证据，不重查MAC、不改生产策略；原预充03继续运行。

2026-10-25：[十小时执行器](timeout-live-candidate/README.md)已准备，未绑定/上传/启动。实际36000秒BOOTTIME、计数一致性、到期停充及正常AUTO后仍停充作为验收；24项采集/失败/收尾控制及六组实际负载方法测试通过，worker/supervisor仅语法检查。保持中间电量的有界CPU负载有温度/电压/SOC降载、父死/新鲜度/期限退出和join；不改原限值、不清真实故障。等当前预充和508短测收尾后绑定新boot，尚无十小时实机证据。

2026-10-25：[508真实USB预算接线](../charging-oem-audit-20261023/tcpm-usb-budget-candidate/README.md)已完成并独立暂存，未安装。QCOM回调读取实际ONLINE/CURRENT_MAX，失败/离线为0，固定5V仅限幅500；TCPM通过标准供电通知更新默认Rp、非PD ready受电端，注销在同锁等待通知退出。五组真实函数/pthread/ASan/UBSan、两个W1对象及Image通过，原配置/BQ/initramfs/builtin/导出相同；DT仅增加实际供应引用，boot3217/FAT0504及300秒原算法恢复器已校验。手机仍为506、预充03运行；待其收尾及补电后装机短测，不抢占当前观察，不冒称PD或图标已验收。

2026-10-25：507 R2已实际启动，原USB管理连接自行恢复，Type-C port/partner注册；但默认Rp分支缺少实际USB预算回调，TCPM current_max/current_now=0，两次验收失败，未接纳。300秒guard自动恢复506并重启，boot5c8d/FATb29e、原文件/模块/manifest及500/250mA/8.725V均核对，四PD控制两次0。[实测与恢复](../charging-oem-audit-20261023/tcpm-sink-shutdown-candidate/phone-trial-result.json)。原预充02主动取消，AUTO恢复、六原进程消失，非预充通过；当前boot075f开始[预充03](precharge-live506-r3-result.json)，允许健康AUTO中段起测、保留实际停充计时832秒，新增五项控制测试共17项通过。三负载自适应约300mA，3.50V降载已内建，保护和参数不变，尚未进入预充。以下“R2未安装/02运行”均为历史阶段。

2026-10-25：[507 R2固定5V收尾](../charging-oem-audit-20261023/tcpm-sink-shutdown-candidate/README.md)已补CC/PD IRQ及work/TCPM实际join、四控制零写读回、引用/CC交还与失败不重试；33原函数逐字保持、六改五新，七组真实关闭函数及四组受电测试、五对象/Image和FAT通过。Image3714…082e/59,439,616B、boot复用e48d、FAT3ebf。注释/模型对末次debounce的来源纠正后，五对象重编逐字相同，复用Image/FAT。独立phone02/host image507-sink-trial-private-02已暂存校验、manifest04542f/guardad5157，未安装；R1禁止stage，未执行过。当前506预充仍运行，源500/CC250/CV8.725、保护正常，尚未预充；原成功/AUTO/六进程退出/SOC20%/两芯3.70V门保持。试运行不接纳，300秒恢复506；完整PD及其它范围仍未通过。

2026-10-25：同一预充观察器及host27976持续真实运行，约63%/32℃、无故障，尚未进入预充。只读核得UPower OnBattery=false、原低电保护配置保持，降载18739仍S/live。[507只读验收](../charging-oem-audit-20261023/tcpm-sink-port-candidate/audit-phone.py)已补实际恢复进程/锁、同一TCPC的port/partner/PSY、原USB500与两样本健康检查；实际506按预期在版本检查拒绝，正向507仍待测。试运行不写accepted，统一等待原300秒guard恢复，避免并发restore。TCPM USB_TYPE_PD早于PS_RDY/明确合同，后续预算不能仅凭PD类型提升。未改当前手机配置或新刷写。

2026-10-25：[507固定受电TCPM候选](../charging-oem-audit-20261023/tcpm-sink-port-candidate/README.md)完成真实port改动、四组真实函数测试、W=1对象及Image、一个BDS对象、native DT与两载体封装。只对明确sink允许缺输出regulator，从首写保持SNK_ONLY，实际OPEN/Rd，拒绝Rp/DRP及VBUS/VCONN源使能，保留真实错误。Image保持配置/BQ/initramfs/builtin/导出。试运行仅5V500mA、固定device，暂禁EUD-route/APSD以免并行，不能直接采用为正式或称完整PD通过。独立暂存已上传校验，未改live文件/分区；原预充成功、AUTO/进程退出、SOC≥20%且两芯≥3.70V才可stage。300秒用户态恢复器沿用506算法，短测后主动还原boot5c8d/FATb29e。原预充继续，约73%/31.2℃/无故障；为使原300mA自适应负载达到目标，仅将11225亲和性6→7，原duty≤0.6及3.50V回CPU0–2降载保持，未改充电参数。private image507-sink-trial-private-01、precharge506-private-02。

2026-10-25：现有低电预充观察继续，新增18739/start643837只在两芯接近3.50V时，把同一实验的三负载进程从CPU4–6移回CPU0–2，以降低预充前的负载压降。原观察器、停止/恢复、温度/压差/超时和输入/充电参数保持；无I2C或供电设置写。原boot/父子进程身份及初始只读检查通过，当前尚未触发降载；源码/启动记录在private precharge506-private-02及reduce-precharge-load506-private.py。原观察或cancel结束后该进程自行退出，收尾时同时核对其terminal/PID。

2026-10-25：[电芯基础容量三字段实测对应通过](gauge-basic-capacity506-result.json)：原厂FCC/RM/SOC映射与实际I2C-5报文、Linux单位一致。两实际放电状态由RC/FCC=1361/1361mAh、原始SOC100%，变为1339/1361mAh、原始SOC99%；Linux对应1339000/1361000uAh和99%。证实查询能响应放电变化，不据此认定绝对容量标定、所有命令或2719状态位均已验证；未修改内核/桌面或新增MAC诊断查询，预充观察继续。

2026-10-25：[已清理取消桌面实验的生成编译目录](cancelled-generated-build-cleanup-result.json)，删除的WSL分配量50,511,872字节，源码逐文件保持、编译日志133,552字节校验保留；共享SDK、手机/桌面运行及当前预充观察不变。C/E实际可用19.30/153.57GB、WSL可用828.15GB；没有把删除分配量当作已归还C盘的空间，也未重试此前被拒绝的两份Windows传输包删除。

2026-10-25：[低电预充观察正在运行](precharge-live506-start-result.json)，尚未验收。实际两读REG07=0x14/REG30=0x08，按[MPS表](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/)为2S、option2/code1、名义6.8V选择；[固定原厂头文件](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/power/oppo/charger_ic/oplus_mp2650.h)及原C选择6.6V，未改现场阈值，非电气切换点实测。[观察器](precharge-observation.py)与[12项控制/收尾测试](test-precharge-observation.py)通过。01空闲观察132.625秒后因约55–61mA过慢主动取消，AUTO恢复、原两worker终态0/absent；02加入有界CPU负载，目前约216mA、25.8℃/压差6mV，主动INHIBIT、Full/cause3和计时0保持。到门槛或8小时后恢复AUTO，温度/压差/心跳异常提前收尾；原模块、manifest、参数及桌面不变。真实预充状态/正净流→连续CC才算通过，不把当前运行当成功。

TI官方[bqStudio配置历史](https://software-dl.ti.com/app_bms/bms-bgp/BQSTUDIO-STABLE/1.3.101/Readme.txt)及[发布说明](https://software-dl.ti.com/app_bms/bms-bgp/BQSTUDIO-STABLE/1.3.101/ReleaseNotes.txt)已缓存，SHA57120fe7…2588及7db92622…2694；前者列出标准2610描述，未列2719。范围仅这两份1.3.101公开文档；安装包需要登录，未下载/执行，未据此宣称整个配置库或新版本不支持2719，未更改TCA/保护解释。

[Image506跨待机修正已装机](../charging-oem-audit-20261023/eud-route-pm-candidate/README.md)：正常route改为暂停/join/complete复核，永久撤销和失败隔离保持；新增现场CSR只读双0检查及真实资源占有，零路由写。23组provider/13组整合C、实际增量Image通过，原配置/导出/电量计/initramfs/builtin元数据均保持。当前boot5c8d/FATb29e、USB161b/bef4/f6bef/服务83469/manifest8b402；只有FAT改变，永久rootfs和固件未变。两RTC驻留15.076/14.855秒、各success+1/fail0，路由complete实际出现、所选回调err0，无复核失败日志，原key/NCM和500mA/保护恢复，最终AUTO Full。两worker终态0、trace/alarm与临时guard收尾。真实PM后物理新连接/APSD、USB唤醒仍未验；下述505及更早记录为阶段历史。

[Image505已实际安装并采用](../charging-oem-audit-20261023/apsd-image505-integration-candidate/phone-activation-result.json)：boot5c8d/FATb388、USB161b、chargerbef4/保护f6bef/服务83469、最终manifest8b402。真实route/Type-C5V provider已绑定，原key/NCM自动恢复，SDP源/native/硬件500mA、CC250mA/CV8.725V和保护Good通过。[新组合RTC](../charging-oem-audit-20261023/apsd-image505-integration-candidate/phone-rtc-result.json)驻留15.195秒、success+1/fail0，12条所选回调err0，预算/保护/USB恢复、worker终态0且alarm/trace清理。仅新外部KO的正常O taint4096，无新增warning/oops。临时guard已收尾并删除，服务主体和原OpenRC保持；根目录六处最终差异及精确原504逆向已保留，恢复器改用稳定分区身份。当前APSD路由在首次PM prepare主动过期，尚无恢复；真实新连接/FLOAT/APSD、物理USB唤醒、温界/预充/10小时和快充仍待验，未声称图标改善。以下旧“尚未装机／当前504”为阶段历史。

[同组合自然回满已实机通过](charger-full-return001-result.json)：377个AUTO样本/64分6.921秒，自行进入Full/cause3并稳定五样本40.947秒，最后电芯4.325/4.323V。零额外充电控制、未改参数，所有原样本通过实际IO审计。原24901终态0，worker/supervisor退出，fresh AUTO Full/Good、500/250mA/8.725V及原服务锁释放确认，adoption已绑定。结合前轮已证明Full→自然放电→真实回充→Full，低电预充、温界/10小时及物理USB唤醒范围仍未覆盖。该504回满观察已经收尾；其后505实际部署见本页顶部。

新增[真实505成套构建](../charging-oem-audit-20261023/apsd-image505-integration-candidate/README.md)：Image b91a/59374080B、BDS EFI9393及原IRQ native DTB的d5fa第二版已产出，未装机。DWC合并完整保留504预算/PM函数；私有copy-up构建仅九项配置变化，原15097导出、BQ对象和initramfs保持，新增21导出。补足本地头文件后原增量make3.10/46.76秒均0、零诊断，第一份编译失败保留。BDS只编一对象、复用40库，链接0的原有工具链警告经缓存审查、最终PE无WX；未重放链接。实际Image参数表纠正5V命名空间为qcom_pmic_tcpm，保留当前BQ瞬时参数1。该离线阶段随后已完成同套模块/载体/逆向与实际部署，见本页顶部；原504回满worker已终态0。

新增[APSD任务与真实EUD-off路由接线](../charging-oem-audit-20261023/apsd-eud-route-client-candidate/README.md)：真实provider/client/原lease代际已接入，删除此profile全部旧COM静默调用，最终传输重新验EFI关闭结果；正常恢复与UDC退休分别处理，失败仍保留排他。九组完整owner/PD/PHY/route C、两个受影响W1对象、五原对象复用及十八内部API检查通过；二十三原函数逐字保持。组合测试发现并修正失败PHY恢复被后续join再次尝试，原失败及首次七组结果保留。默认关闭/未装机；下一块为同Image/固件/实际DT启动组合，首次物理断源、FLOAT/APSD、路由跨待机重建及快充仍待验。

新增[EUD实际producer仲裁](../charging-oem-audit-20261023/eud-route-provider-candidate/README.md)：COM、qcom_eud、earlycon三处真实硬件入口共享互斥和本boot历史，实际client/lease及撤销join保持引用，失败移除不放掉producer排他。十二组完整provider/receiver C、三处零fuzz源码及七个W1对象/默认关闭导入/内部接口检查通过；原earlycon旧unused warning及错误导出名后处理均保留，仅修受影响处和缓存审查。未部署；DWC消费者已由上述候选接通，PM仅过期本boot证据，尚不支持路由待机重建。

新增[EUD关闭结果的结构化交接通道](../charging-oem-audit-20261023/eud-route-handoff-candidate/README.md)：固件独立reserved页、原BeforeEBS成功后commit-last，内核真实EFI配置表接收并拒绝重复/不可用/损坏记录。原CSR动作、panel和日志区保持；十组实际固件/receiver C、BDS与两个kernel对象及内部接口通过，新增四个BDS导入由原41库提供。复核后仅重编receiver补EFI表可用性，并验证实际默认关闭配置零强导入。未装机，不是路由授权；下一块仍是实际资源独占/撤销supplier及DWC消费。第二轮回充和计时切换现已实际通过，见下。

底层离线新增：[APSD最终传输边界](../charging-oem-audit-20261023/apsd-final-transfer-candidate/README.md)已绑定实际owner内嵌身份、实际PD代际/PHY撤销，并在单次1341前重取稳定七字段，保留命令/post-read双错误、立即消费真实post-clear。九组backend、十八组完整owner/PD/PHY C、三个W1对象及十一内部API检查通过。另已[合入当前USB13f IRQ/PM源码](../charging-oem-audit-20261023/apsd-current-usb-integration-candidate/README.md)：prepare撤销/join，complete才重注册，十组传输/十五组IRQ-PM及唯一input对象通过，二十二原函数逐字保持。未安装或放开路由gate；可信EUD-off路由supplier、同Image builtin/Type-C设备及真实新连接周期仍须完成。

当前实际进展：[停充计时R2已冷更新并启动采用](charger-timer-activation-result.json)，chargerbef4/manifestf15ecc，bootbc612；Image504、USB13f41、保护f6bef和服务83469保持。原暂存worker终态0，保留Full到正常重启，未刷写启动载体；fastboot正常reboot及原key/NCM自动恢复，无需人工拔插。首次启动采集因保护driver尚未绑定失败，原失败保留；第二次只读采集与fresh采用均十二门通过。主机adoption已修正为读取实际成功的第二份采集，原始失败未改写。

[新版组合RTC](charger-timer-rtc001-result.json)实际驻留15.439秒、success+1/fail0，USB挂起/恢复回调0，原key/NCM自动恢复，SDP/native/硬件500mA、CC250mA及整包8.725V保持，无新fault/taint，alarm/trace清理。新boot保护缓存0/0保持；旧boot八帧证据仅作历史。

用户已授权睡眠期间操作手机、刷入和自动测试，无法人工拔插。[首轮放电/回充观察](charger-full-recharge001-result.json)已正常收尾：38分9秒放电，226+70个真实样本均通过原IO验证；AUTO后电压回弹至4.270–4.281V，高于原4.2625V再充门槛，未触发回充/计时观察，不能标通过。原worker和辅助CPU0负载均退出，AUTO/健康Full/锁释放fresh确认。[第二轮真实通过](charger-full-recharge002-result.json)：未附加CPU负载，自然放电4212.953秒/415样本后，原AUTO策略自行退出Full并恢复充电；随后29个停充样本跨59.995秒，计时固定10秒，恢复后六样本13→23秒。原worker14837终态0，worker/supervisor均退出，fresh AUTO/Good/锁释放确认；全部原样本通过实际IO审计，adoption已增加本组合回充/计时标志。未清Full/fault或改电压，不覆盖低电预充到Full/温界/10小时/物理USB唤醒。此前两次短观察分别在worker启动前、任何命令前失败，均保留。当前精确charger逆向c72589恢复97c/5ef4并保留USB13f；旧USB逆向属于不同组合。以下旧“仅离线／尚未安装／当前4e325”均为相应阶段历史。

最新离线增量：[DWC检测任务已接PHY撤销接口](../charging-oem-audit-20261023/apsd-phy-client-candidate/README.md)。真实client引用、永久撤销fence、retiring取消与解绑释放已接入；十二组完整owner/PD/PHY C组合测试、当前m/未来builtin两种私有对象W1/Werror零诊断通过。三对象私有relocatable接口检查的九个内部API已解析，不是Image/模块或实机验收。共享配置保持，未安装、未访问手机；路由授权与最终单次传输重验证继续阻止APSD命令。以下PHY组件及实机版本事实继续适用。

本轮另完成[APSD PHY撤销接口](../charging-oem-audit-20261023/apsd-phy-withdrawal-candidate/README.md)：真实client引用、解绑/关机前撤销并join、资源释放后只保留结果，失败不重试MMIO或冒作恢复成功。十组实际C/真实pthread并发测试及唯一PHY对象W1/Werror零诊断通过（3518d8e6/146064B）；未接DWC消费者、未链接Image/安装。检测任务接线、EUD-off路由授权和最终单次传输重验证仍缺，1341入口继续拒绝。全程离线，未访问手机。

当前手机已采用Image504/Y、USB13f41、charger97c、保护f6bef和服务83469。新增USB IRQ wake配置，[本组合RTC待机恢复](usb-irq-wake-rtc001-result.json)实际驻留15.019秒、success+1/fail0，前后12项检查及USB挂起恢复回调成功，NCM自动恢复、SDP500保持。前boot已完成[2719八帧真实查询](protection-profile-live001-result.json)，0056三字节和真实前后0A稳定；新boot缓存0/0未重查。

用户暂不方便现场，真实USB待机拔插窗口仅准备未启动。继续离线完成[停充计时R2修正](../charging-session-20261023/charge-timer-hold-r2-candidate/README.md)：旧实际函数复现停充后的误累计，新实际函数9组76断言、单KO/W1/54导入及精确配套通过；冷暂存、写入失败恢复与启动/PM接线已离线完成，尚未安装。另补[当前两分支逆向](../charging-session-20261023/charge-timer-cold-rollback/README.md)：十个实际文件/停止恢复场景、16个重启只读门、10个恢复验收请求及2个本地adoption/CAS检查通过；真实probe/恢复/新boot均未执行。物理USB唤醒、温界/完整预充再充、2719/TCA语义、其它源/FLOAT/APSD/PD及快充仍未闭环。桌面未改，无子代理；相机继续暂停。部署/逆向身份见[检查点](../../NEXT-SESSION.md)，实际新USB记录见[当前入口](../charging-session-20261023/usb-irq-wake-update/README.md)。以下为较早阶段记录。

**此前501现场：** [Image501已实际启动和adopt](image501-activation-result.json)：候选boot97811/logdump7e5d双完整分区读回、#501/参数Y/独立NOW+AVG与R8/正式相机/保护/服务/taint0九门通过。原启动500保持；启动CDP1.5A/native500/hardware900与随后[SDP500/100%Full保持](image501-after-replug-health-result.json)分别记录，后者NOW/AVG0/Not charging，不伪报Charging。原件回退4126+ACA，旧guard/pointer备份保持；[501采集001](icon-image501-001-result.json)到期未观测断源，264样本、全部进程退出，边沿未验。用户随后反馈更快但仍延迟、两边都有且主要插回，未给精确秒数，不冒充采集覆盖。相机paused，设备归充电。

前次[363的真实500循环](icon-r8-eud-off-result.json)稳定91秒/81样本全部SDP/native/硬件500且净充入，图标目视改善但后台仍off3.73/on3.08秒；[时序审查](../charging-ui-audit-20261023/remaining-icon-delay-r8/review.md)确认平均电流拖尾，收到状态后的桌面转发毫秒级。501只改瞬时getter与版本元数据、原initramfs/模块ABI保持，BDS参数真实启用，nativeDTB9271不动。源模式已变CDP，不能把后续改善全部归因501。首次过早init收集、一次传输截断、03的SDP假设拒绝及菜单Restart bootloader恢复枚举均保留；04新CDP明确分类九门通过，不重写失败。

用户明确取消新增桌面提示路线；私有编译已正常SIGINT并join全体子进程，未产包、未安装、未重启桌面，后续仅底层优化（[停止记录](../charging-oem-audit-20261023/phosh-private-build-inputs-501-r1/cancelled-desktop-stop-result.json)）。[PD5V真实client桥](../charging-oem-audit-20261023/apsd-pd5v-client-bridge-candidate/README.md)14组与私有W1对象通过，默认关闭，analog/1341仍拒绝。以下旧100mA、稍后测试和未部署均为对应阶段历史。

仅底层的本轮增量：501严格机型gate内的[BQ外供即时刷新候选](../charging-ui-audit-20261023/gauge-notify-immediate-candidate/notify-immediate.patch)移除明确HZ/2等待，7组定向真实函数测试与私有W1/Werror单对象编译通过，[Image502](../charging-ui-audit-20261023/gauge-image502-notify-candidate/README.md)实际构建通过（085d0306…b25955），仅BQ和版本身份叶改变，未部署；[USB两命名IRQ候选](../charging-oem-audit-20261023/usb-input-irq-candidate/README.md)16例、私有对象及独审通过，DT/boot/两ko配套已离线构建，实机尚待。原R8 [启充顺序/计时短审](../charging-oem-audit-20261023/mp2650-attach-sequencing-r8/README.md)确认没有多等整轮的启充实现，Full/再充/10小时均按BOOTTIME，保留原安全采样与计时；未新增短poll或伪报Charging。

新增离线结果：[默认关闭USBIN集成候选](../charging-oem-audit-20261023/usbin-init-provider-candidate/README.md)复用冻结off-only core，10组/17真实函数、私有k363模块编译和[根审查](usbin-init-provider-root-review.json)通过；真实模块自持引用、锁内准备/轮询、待机取消/暂停及未知历史已落实，原1秒轮询/预算算法保持。没有加载或开启，采用前仍须临时helper实体结果。

实际[CSR两次全字0x01010101](eud-csr-r8-result.json)促成[boot-only R2](../charging-oem-audit-20261023/eud-boot-policy-r2/README.md)的两行限定修改，5项受影响案例/独审通过。先[私有重链接基线](../charging-session-20261023/eud-bds-baseline-relink/README.md)逐字复现实际a30 BDS，再[仅编译R2平台单库并链接](../charging-session-20261023/eud-bds-r2-build/README.md)，EFI `a0e30c69…61768`、110592B，其余40库与父191文件/挂载保持；[根来源复核](eud-bds-r2-root-review.json)核8产物/16原件摘要、编译宏和原告警。未封装firmware/boot.img，未部署；不能据此称EUD-off/直连/500或图标通过。

既有RAM ring范围0x9ffe3000/0x14000由当前源码Reserv与实际iomem覆盖支持，单次O_RDONLY/PROT_READ读取81984字节；magic/version/81888数据区正确、head7445/tail3852/drop0、三次头一致，完整raw/history仅私有。当前旧boot没有新EUD-OFF行属预期，读取通路可用不保证未来DEBUG未丢失，也不把receipt缺失判成callback失败；无需读关闭后的EUD MMIO。

前一窗口：相机469/471均串行终态并交还，471报告PW17594/WP17597。用户回复“稍后再测”后根曾明确交回相机并获接管确认；自471交回以来根及充电子代理没有SSH/USB/launch/arm/helper加载或硬件写。

[最小off-only初始化](../charging-oem-audit-20261023/apsd-usbin-init-candidate/README.md)12组/私有in-tree模块和[执行器](../charging-oem-audit-20261023/apsd-usbin-init-host-candidate/README.md)35项及[独立收尾复审](../charging-session-20261023/usbin-init-host-independent-review/README.md)通过，根check-local通过，但尚未部署或实体复测。boot-only EUD-off最初仅核路径，后续R1/R2及私有模块链接证据见上文；各生成收据中的未编译事实属于生成时状态。

该[boot-only EUD候选](../charging-oem-audit-20261023/eud-boot-policy/README.md)现已冻结，12个新增实际helper/CoreExitBootServices/CoreRestoreTpl host案例通过，[独立静态复审](../charging-session-20261023/eud-boot-policy-independent-review/README.md)未发现限定范围新增阻断。只做独立启动回调、两处EUD token删除及当前native COM disabled，panel代码逐字不变；未知CSR全字拒写，旧注释的replica许可已明确撤回。未构建固件/新Image或触碰设备；上电CSR全字、真实链接输入、Linux/host通路和合法native预算仍缺实证，不能直接部署或当图标修复。

[当前R8源码整合](../charging-session-20261023/r8-source-integration/README.md)也已完成：12内核文件与4当前已安装服务依赖、必要Kconfig/Makefile及独立DT增量，构建→R8 manifest→三loaded-note映射完整。根仅正常恢复原32GiB卷并git show导出3个ba61固定blob到私有缓存，未写共享source/build或绑定SDK；补丁对这三份完整缓存的fuzz0干跑/临时应用及最终字节比对通过。[根完整性复核](r8-source-integration-root-review.json)另外核24交付文件/16源码/14已有收据/确切patch目标及实装映射。未重编译、重跑旧套件或新增部署；旧根patch/delivery继续保留历史，后续维护使用新入口。

最新实装为 **R8/320316c3…c10a1f**，仅换charger `10ec06fb…6297f`和manifest；USB仍R7 `7d4e0f94…c4f70`，service/保护/Image/boot/guard保持。[单次更新](r8-update-result.json)与[终态复核](r8-handoff-result.json)通过，worker11892已退出、自己的lease已释放，明确交回相机并获接管确认。29.1℃、fresh保护/error0/taint0、NORMAL4、实际SDP/raw native/effective/双输入100、CC250/CV4.3625V每芯保持，四服务/相机PM/m2m保持。末次瞬时+4mA是单点，不覆盖此前净放电，也不证明持续净充电或图标通过。当前不需用户再拔插。

原厂[APSD/DPDM生命周期](../charging-oem-audit-20261023/apsd-lifecycle/README.md)确认Type-C首轮SDP/CDP一次复测缺口；[实际源码/DTB接口核对](../charging-oem-audit-20261023/apsd-integration/current-r7/README.md)已将必要DWC/PHY/EUD/PD边界落到具体函数。R8温区已单独加载，未混入USB识别改动。此前[唯一R7 USB500诊断](../charging-oem-audit-20261023/usb500-r7-trial-audit/usb500-r7-result.json)55样本全addressed/native100、主机无Status5，已恢复100、全进程退出；EUD/功率拒绝因果仍未证，r5 PM失败未改判。

467后一次[选定控制字节只读](pd-controls-r8-result.json)完成并交还相机：两次0x1358 bit7=1，与[原厂Type-C初始化清零后置条件](../charging-oem-audit-20261023/apsd-lifecycle/pd-controls-r8-correlation/README.md)不符；0x1362 bit3已经启用。PD PHY控制为0不能单独证明合同inactive，不在现有活跃连接上盲写。末次29.4℃、100/250及CV帽、fresh保护/taint0、相机和四服务保持；瞬时+3mA不证明持续充电。DWC R1默认退出回归已复现，R2仅修相关两处判断并通过5个新增边界及gadget对象编译；EUD软件静默候选9组及私有对象编译通过，两者正在独立复审。候选均无自动消费者，未部署，不覆盖硬件路由、APSD、SDP500或图标验收。

离线增量：[DWC R2独立复审](../charging-session-20261023/dwc-r2-independent-review/README.md)未发现新增可证问题；[PHY窗口](../charging-oem-audit-20261023/apsd-phy-window-candidate/README.md)的原厂三组高阻写/精确旧位恢复、8组实际函数和私有对象编译通过，根限定复审已记录。[一次复测协议核心](../charging-oem-audit-20261023/apsd-once-candidate/README.md)14组通过，明确拒绝旧DONE、重复尝试和旧epoch，保留主错误及晚到bus errno。EUD R1独立复审发现remove撤销console前最后一次RX排队可能未join；[独立R2](../charging-session-20261023/eud-runtime-window-candidate-r2/README.md)已在全部producer撤销后最终join RX/TX，4组新增边界及单对象编译通过，R1保留为失败历史。三组件完整owner/硬件交接仍待接入；另依[原厂独立init作用范围](../charging-oem-audit-20261023/apsd-lifecycle/start-on-cc-scope-r8/README.md)准备只在实际detach时修正1358 bit7的最小候选。CSR保存/恢复阶段也在独立目录实现，均未部署。

## 历史r5状态

原厂审查确认两个真实缺口：温区拒绝被当作永久硬故障，以及Full挂线也累计到10小时。已合入精确温控reason/外界2℃恢复迟滞，以及健康完整REG13 Full重置本轮计时；不清除真实fault、IO或既有超时。按原厂易失初始化，不新增跨boot强制到期daemon。当前core/周期helper和真实step整合分别通过6016/113/8原回归、590温控、98周期、12序列65断言ASan/UBSan。

图标链离线审计：[r4事件](../charging-ui-audit-20261023/r4-ui-audit.json)含600秒520次重复charger通知，唯一battery事件到UPower Display约48ms（单时钟锚估计）；没有录到这次用户物理拔插，r4已deadline且worker退出。用户稍后明确报告仍明显延迟。不能把r4当物理事件时延验收；已修正只凭尾部SDP就标成“物理SDP通过”的审计标志，r1/r2/r3仍通过、r4为false。

r5每秒安全采样保留，新增原bq即时STATUS/errno及charger实际离散状态变化通知，supplied_to保留；54个实际通知函数案例/100稳定poll通过。仅charger ko 9d9e1cd7…31016在私有O目录W=1/MODPOST构建并部署，USB/保护不动，manifest f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf。[更新](charger-update-result.json)及39.53秒[实机INHIBIT/AUTO通知](runtime-notification-result.json)通过：稳定2–10秒重复charger事件0、恢复健康、原SDP100/250mA/8.725V保持、相机四服务不变、taint0/新fault0。原屏幕绘制/物理拔插图标速度仍未确认。

500mA尝试没有验收通过：r4及物理off等待器各自deadline退出；另一次软件gadget重枚举在500配置时Windows复合设备启动失败，无合法native500回调。独立worker60秒后自动解绑回100/重新绑定，NCM/严格SSH自然恢复，taint0/相机不变；主机restart-device因Access denied未执行成功。两份实机USB启动脚本和项目创建路径均已恢复100，不遗留未接受的自动迁移。[终态](usb-reenumerate-result.json)、[脚本回退](usb-startup-rollback-result.json)。

新r5/SDP100的RTC s2idle原终态已回收。用户短按能亮屏，同口拔插后NCM/严格原key SSH恢复，同原boot，21491确认退出；[恢复读回](pm-r5-recovery-result.json)确认三模块/manifest精确、充电fresh/native100、taint0/指定新增fault0、相机PM/m2m/四服务保持。未重启、未重放PM，手机已明确交回相机，充电暂停实机访问。原计划15秒，实际睡眠3396.192秒，raw true因遗漏时长/唤醒归属门槛被[独立审计](../charging-ui-audit-20261023/pm-r5-qualified-result.json)判为失败；50.468秒console准备缺口发生于charger回调之前，RTC IRQ+1不能证明唤醒因果。旧CDP/V3结果不能覆盖本轮。

离线软件Full/再充v1候选六组测试通过：6016策略/113事务/8源序列、19实际step序列111断言、14保持事务序列97断言、7采集序列20断言、16 Full序列251断言及52原厂差分。真实私有k363 in-tree W=1模块编译通过，ko046b902c…89da；全部启用CONFIG与共享ABI相同，仅新增显式关闭CAMSS_ICP注释。[编译收据](oem-full-build-result.json)绑定八源码及测试hash，主r5不变。该候选还在补用户态安全TCA/Full分类兼容与手动INHIBIT门控；已冻结v1仅供离线审查，不代表可部署或当前手机健康。

以上待补项现已在独立[v2候选](../charging-session-20261023/kernel-v2/README.md)完成：手动INHIBIT清未完成计数、保留既有Full，实际step26序列223断言；配套用户态103项真实函数测试覆盖TCA/温控启动等待、参数错误拒绝与Full周期分类。[v2实际模块编译](oem-full-v2-build-result.json)通过，ko fac827cf…89cb6，无warning/有效CONFIG变化，源码/收据/模块已冻结为私有离线审查产物；未部署。未来PM worker29项及primitive27项离线测试通过，但当前内核无pm_wakeup_irq，不能直接用这些候选认证或启动新PM。

主机只读USB hub查询确认EUD中间hub为总线供电，当前只有control端口连接；这是500mA失败的候选限制，没有当时端口状态，不能认定根因。[主源及查询范围](USB-HOST-POWER.md)。新PM事务库已离线修正先arm再sync的窗口问题；原r5现场原因仍须恢复日志后判定，不重放旧事务。

## 已完成

- 原厂19781温区/限流/限压参数生成、策略与寄存器事务核心6016+113案例、ASan/UBSan；输入预算基础复用134的只读PMIC观察器。
- 与相机会话交接的第二个窗口：本机只读MAC完整36字节报文，命令回显、固定偏移校验和、长度均验证；器件返回0x2719，0071双电芯和51/53/54/57保护状态报文有效。0x58一次NACK，不初始化保护芯片。实测CDP源许可1.5A。
- 新增真实保护状态提供端、严格电芯报文解码、SDP原生DWC3预算回调接收端、挂起时预算失效；三个模块在私有source-view/O目录通过W=1/MODPOST，真in-tree与k363 ABI匹配。公共源码/build、相机SDK未修改。
- 2027协议/保护错误输入和910 USB预算案例，含6份本机真实报文回放，通过ASan/UBSan。PF_EN当前为0，保持原状；不能将无故障状态解读为永久故障功能或所有物理阈值已验收。
- 第三个只读shadow窗口已保存现充电配置：输入两路900mA、充电300mA、继承单芯目标4.3625V、WDT关闭、终止及安全计时器开启。仅查询，不写MP配置。

## 本次shadow失败及恢复

首轮模块注册时，动态platform设备和同名power_supply复用software fwnode，形成sysfs重复链接；USB提供端卸载触发software_node引用计数WARN，taint从0变512。未发生Oops。三个充电模块均已卸载，原mp2650观察器已重新绑定，十项配置寄存器逐字节未变；四相机设备仍suspended、完整m2m状态及Phoc/Phosh PID/UID未变。后续独立核对确认正式440 r32/r27包与三个434模块磁盘/加载note仍匹配，PW/WP各一个uid10000，资源空闲。

代码已修正：runtime USB设备的power_supply不再共享父software fwnode；DT设备仍保留固件关联。修正版已重新通过集成构建，未在带WARN的旧启动中复测。影子采样的返回因finally断言失败而未保存，不能宣称首轮影子功能验收通过。

已与相机会话确认后复用367静默/EUD退休/bootloader→原环境reboot序列，完成一次不刷写的恢复重启。新启动taint0，正式440包/434三个模块加载note匹配，四相机休眠、资源全释放，四个用户服务就绪。恢复静默准备曾因脚本误改num_users断言为512而提前终止，已保留失败并只从未完成的检查续行；没有盲重放状态切换。事件证据保留，不清日志/篡改taint。[恢复结果](recovery-result.json)。

修正版shadow在新启动完整加载/采样/卸载通过：有效温度27.6℃、电芯4315/4312mV、CDP许可1.5A、保护状态有效且故障0；十项配置不变，原观察器恢复，三个候选模块全卸载。本启动sysfs重复链接、refcount underflow、WARNING/Oops计数均0，taint0；相机PM/完整m2m和Phoc/Phosh/PW/WP PID/UID完全不变。[结果](shadow-result.json)。窗口明确交还相机后，446已完成并再次恢复正式组合。

私有证据：`E:/edk2-samurai-out/charging-management-20261023/window3/`、`recovery/`。不要盲重放已完成的有状态步骤。

## 后续

第五窗口普通控制通过：900/300mA下连续净充入83/88/93mA，双路降500mA输入、越界拒绝、INHIBIT和原配置精确回退成功，taint0、相机/服务不变。[控制结果](control-trial-result.json)。回退实际策略26例离线通过。

第六窗口持久服务启/停/重启/原配置回退通过后，新增8文件及开机项。默认900mA输入/250mA充电，以原厂最低运行降额为保守上限，温区/实时源预算仍可继续限缩；未抬高继承单芯4.3625V。随后基于实际390只增DWC3的usb-psy-name，固件解析确认其它DT属性及所有固件代码/内核/相机保持；只刷boot，实际读回a30fb444…ec280，回退390 e0256ff5…0884f保留。

新启动自动接管成功：新鲜电芯/保护、CDP许可1.5A、原生DWC3实际UDC额度100mA、输入900mA/充电250mA、净充入61mA、故障0、taint0；UDC额度与原配置MaxPower100一致。核验脚本最初误期望500mA的失败已保留并根据实际配置修正，没有改变USB配置来迎合断言。native提供端因DWC3引用自持到下一启动，正常服务stop不卸载它。

实际新boot、三个充电模块loaded-note、正式440包/434相机模块loaded-note、四相机休眠/m2m epoch0/资源释放及四用户服务全部通过。[开机充电](managed-boot-result.json)、[相机状态](postboot-camera-result.json)、[服务](service-test-result.json)。手机已明确交回448，相机同意保留常驻充电栈和900/250mA作为新基线。

448终态后获得独立窗口，为充电器/保护提供端增加两条gauge PM设备依赖并只换两模块/manifest；USB提供端保持驻留，更新后服务/采样/相机/进程/taint0通过。实际RTC s2idle驻留15.1689秒，success+1/fail0/IRQ+1；轨迹证实正常停充挂起、gauge与源先恢复、充电重新采样，配置和native100mA额度保持，BOOTTIME计入休眠，无新增故障。prepare/complete也使用suspend/resume动词导致的审计脚本重复计数，已只从缓存修正，没有重复测试。[PM最终结果](charging-pm-result.json)。手机/SDK已交还449，guard不变。

普通5V管理的实现、部署、开机和短时PM闭环已完成。用户选择保持现连接，真实SDP换口/拔线重连暂缓；全温区实物激励、长期、预充/终止再充及跨重启累计未验收，SuperVOOC/PD未适配，不冒认这些功能已通过。当前已有[内核集成补丁](kernel-integration.patch)与配置片段导出，未改共享checkout。

## 用户在外期间的续作

补齐此前未直接覆盖的实际gauge-i2c.h传输边界：复用六份旧实物报文，154例ASan/UBSan通过，NACK/超时/短传输/旧echo/坏checksum/长度错误均拒绝，13种非白名单命令不访问总线。仅替换测试中的Linux I2C与delay边界，未复制一份假协议实现；[结果](gauge-transport-test-result.json)。部署源码和三模块没有改变。

新增只读健康观察工具，与449交接后取得一次120.076秒、13样本：全部valid/protection_ok、age 2–775ms、28.3℃、两芯最大差1mV，session 2847→2967秒，无故障/锁存/源等待；硬件状态均Full。900/250mA及8.725V上限、native100mA、同boot、相机完整m2m/PM及四用户服务保持，taint0且新故障0；[结果](health-observation-result.json)。这增加满电硬件状态证据，不冒认为完整低电量预充/终止再充或长期验收。手机/SDK已明确交回449。

R1可选电池属性查找误用了bq27*前缀，未找到实际bq28z610-0；已改为按Battery类且仅单一候选查找，41个分类/异常/发现案例通过。原执行源码及原35例测试留在私有目录，接受判定函数AST逐字一致，结果仅用原缓存重审；不伪造此次SOC/净电流，不重复采集。当前观察器修正版未安装为常驻服务。

后续软件缺口仍有10小时会话预算跨模块重载/重启的持久化：目前BOOTTIME覆盖睡眠、服务stop不卸载，因此同模块会话继续计时；模块重载/重启仍会新建会话。不能只保存一个墙钟时间就称已解决，需把掉电缺失记录、时钟回拨与真实断源重置一并设计/验证；本轮不改变既有控制实现。物理SDP/插拔继续按用户要求暂缓。

## 用户回家后的USB实物验收与图标修复（进行中）

三次物理断开/重连已完成，均确认硬件INHIBIT、真实断源重置会话、重新采样自动恢复、输入遵守原生额度、同boot/相机/四服务保持、taint0/新故障0。r1为CDP→SDP，断开稳定采样10.18秒；r2/r3均SDP→SDP，分别6.10/7.13秒。返回原口后真实识别仍SDP100mA，没有冒认恢复CDP。记录为usb-hotplug-r1/r2/r3-result.json及私有对应capture。

发现实际供电缺口：旧NCM配置MaxPower仅100mA，本机净放电约51–59mA。已将本机两份USB启动脚本及项目两条创建路径改为500mA申报；持久服务对旧initramfs配置迁移会重新枚举后再申请，不直接写power_supply预算。当前实时配置尚为100mA，必须等物理断开时修改配置、重接主机接受后再由DWC3回调授权。首次等待器误用了UDC not-attached，缓存证明拔线期间UDC仍configured，实际未改实时描述符；旧进程已按pidfd退出。修正版以PMIC在线与MP2650 Power Good共同判定断源。

用户新增报告拔插图标延迟。已确认bq27xxx默认poll360秒且原充电器未建立supplied_to关系。仅charger模块新增按实际gauge父设备查找Battery并建立标准供电通知关系（bq回调延迟0.5秒），模块a57770de…f50b，保护/USB模块不变，manifest78332c70…5abe，未刷写/重启。首轮更新启动器不支持卸载后的未绑定状态，硬件保持INHIBIT、输入/保护仍在；已从实际未绑定状态先恢复旧模块，再修正加载分支，r2新模块正常接入，taint0/相机及服务保持，失败与恢复保留。

上述r4已结束，未覆盖用户随后拔插；软件500mA重新枚举也未获主机接受，已自动回100mA，两份USB启动脚本恢复原件。r5通知修正安装后仍需新的真实图标采集；旧等待器不能继续当作已armed。

## r6部署与当前取证

r5/SDP计划15秒待机实际驻留3396秒，计划失败；用户亮屏并同口重插后NCM/严格SSH恢复，同原boot。原21491已终态退出，原日志全部取回，充电/相机/服务恢复通过后，窗口先交相机451/452，再交蓝牙r2；蓝牙明确恢复并归还后，本线才重新访问手机。

r6首次只读预检因DT序号节点不存在而终止，无充电mutation、无launch。确认本机实际SoC序号接口后，更新器固定该接口并通过67项事务/拒绝测试；随后单次worker25670成功换charger/service/manifest并退出。新manifest944f2d91…4202d、模块fac827cf…89cb6、服务61451ffe…55aa4。独立INHIBIT/AUTO worker25737也已退出，通过硬件停充及恢复读回。保护新鲜有效、native/双路100mA、CC250mA、继承4.3625V/芯、taint0，当前窗口前后相机PM/m2m及四用户服务保持。

0x0c瞬时电流已实际读回，停充约−58mA、恢复约−3mA；标准bq0x14平均电流独立保留。更新验收只覆盖安装和停充/恢复，不代表实体Full/再充、图标或r6待机通过。新只读图标collector25830确认两次新tick/PID及剩余预算后才提示用户同口拔线10秒再接；600秒/567连续样本未观测断源，最终deadline、监视清理完整且worker退出。[本轮结果](icon-r6-capture-result.json)保留未通过实体循环的事实，旧拔插提示已明确暂停，不在采集结束后要求用户操作。

交回前再次核944f…4202d和三模块loaded-note、fresh保护/故障0、native双路100/CC250/CV原上限、24℃、taint0、同boot/窗口内相机和四服务。以蓝牙交回原日志最后64行唯一连续锚点审之后9新行，指定fault0。手机明确先交相机457，再由相机恢复终态后交蓝牙；本线停止SSH。另一次Windows独立只读100基线成功取得182个GET响应、真实NCM在EUD hub端口7；空端口全零响应被严格decoder拒绝导致5.1秒提前退出。仅从缓存修正并62案例验证，无500试验，也未修改USB。

## USBIN003实体结果与下一变量

当前永久充电为R8/USB R7，最新范围以[README](README.md)与[需求矩阵](ADAPTATION-REQUIREMENTS.md)为准。001/002超时零写的原失败及002传输不明后的显式qualification收尾均保留；003才完成一次新鲜就绪后的同口电脑数据线实物循环。

[003](usbin-init-r8-003-result.json)在断电期间单次清1358 bit7并正确读回0xc0→0x40，重接观察61.14秒、362样本完整循环通过；正常零IO commit/卸载及全部原进程absent。输入仍100mA，重接Battery51样本均净放电−45至−20mA，没有验收额度升级或图标修复。用户目测拔线约6秒、插回逾一分钟无图标独立保留；[时序独审](../charging-ui-audit-20261023/usbin-init-r8-003-review/review.md)显示拔线正确State2约4.11秒，重接外供Online约15/9ms、OnBattery=false约39ms，与无Charging State且持续净放电相符。

新鲜保护/限额/CV/相机idle/四服务/taint0核验后明确交相机481/482串行窗口，充电全员零设备。离线EUD R2的实际BDS构建与原封装分层基线已完成：首次compact失败保留，原工具SEC重定位后整FD逐字复现，独立gzip及全payload也逐字等a30；仅BDS/nativeDTB的[候选封装](../charging-session-20261023/eud-boot-two-ffs-candidate/README.md)随后一次通过，96MiB/SHA4126a297…bbfcf，99完整FFS/SEC/尾部和写后解析均通过；尚无刷写/重启，激活工具在离线准备。DEVICE同步恢复候选只到定向测试和对象构建，不是待机实测通过。

## EUD 启动工具与电量计候选续作

[激活 host](../charging-session-20261023/eud-boot-activation-host-candidate/README.md)与冻结 worker 已完成实际函数边界及独立审查；根实际执行本轮 `eud-boot-r2-live-001` prepare，三秒左右真实 SSH rc0，仅上传工具并做完整只读校验。原 a30/363/R8、相机481 r33/r28及 fresh 保护通过；同事务 fetch 确认原 boot、无 quiesce/restart worker、原 prepare/fetch 进程全部 absent。[阶段结果](eud-activation-prepare-result.json)明确零硬件写、未静默/重启/刷写，不能作为 EUD-off、预算或图标通过。

离线 [gauge 候选 B](../charging-oem-audit-20261023/gauge-current-samurai-candidate/README.md)将显式本机 opt-in 的 CURRENT_NOW/STATUS 同用原厂已证实的 0x0c，CURRENT_AVG 保留 0x14；默认关闭，真实函数差分/ASan/UBSan及私有 W=1 对象编译通过，[根审查](gauge-current-root-review.json)未见额外阻项。它需要一致的新 Image，未安装，也未混入保留 Image363 的 EUD 实验；不能把003约4.11秒全部归于平均电流，100mA下实际净放电仍应如实显示。

本轮[R2 fastboot操作者](../charging-session-20261023/eud-fastboot-operator-r2/README.md)另分 candidate/original 两个显式、各一次的 reboot，并绑定最后成功 image 的原 claim/result 摘要；两条实际状态序列通过，旧17组复用。[R3 postboot验收](../charging-oem-audit-20261023/eud-postboot-readonly-candidate-r3/README.md)修复 Full/session0 精确一致性和第二条截断 marker 被忽略的验收缺口，11个 Full/normal 差分及6个受影响 decoder 病例通过，旧其它9组复用；[独审](../charging-session-20261023/eud-postboot-readonly-independent-review/r3-review-result.json)与[根复核](eud-boot-tools-root-review.json)未见新增阻项。根只另做惰性本地检查及Windows当前PnP/NCM29只读快照（接口Up），未发fastboot/停机。新现场可用性问题已发送，未答前保持prepared-only；原prepare owner保留，不沿用旧USB ready。

## 当前静置状态与后续底层接入

新现场启动问题仍待用户回复。根在自己的手机窗口仅做两次同步只读SSH，均真实rc0、未留worker/观察器：16样本15.46秒的[0x0c/0x14对照](gauge-current-steady-readonly-result.json)fresh保护/error0、最大age1020ms、同boot/taint0，全部预算100mA和Battery Charging，瞬时+21至+46mA、平均+40至+42mA；随后UPower Display实际charging/icon battery-full-charging-symbolic、OnBattery=false。实际UPower1.91.0-r2对应缓存上游v1.91.0，但未认证发行patch；Phosh0.57.0-r3/Phoc0.57.0-r1已从实际包DB确认。UPower原dump解析首次遇空前导块失败，只修缓存解析，无额外SSH。静置正净流不覆盖003重接61秒负净流，更不证明边沿或像素通过；没有INHIBIT/AUTO或USB动作。

完整APSD仍缺真实TCPM/route/bus owner。源码已定位sink-bc12仅固定delay，pending PD RX不受pd_events完全覆盖，qcom SIG_RX的reset早于TCPM hard-reset通知；正在分别补DWC真实bound生命周期消费者与独立PD取消接口依据，不能以DT disabled/PHY enable0冒认inactive。另从既有363对象/命令缓存核最小一致Image路径，避免拿当前5b0工作树或Rust探测变化冒充纯gauge增量；本轮仍未构建/采用新Image。

502已完成[离线内核和FAT载体](image502-offline-result.json)：Image085d0306…b25955、新logdump ace2e261…763ed1，仅/Image改动、DTB/其它内容及所有非Image字节保持，读回与fsck-n通过。回退本轮用当前7e5而非ACA，boot97811保持；未刷写、未新物理验收。桌面路线维持取消。

502只写logdump工具完成22例增量检查与独立审查；根一次[prepare](image502-prepare-result.json)原SSH终态rc0，实际501/完整97811+7e5/R8/相机/保护核验通过，只上传工具，硬件写0，未quiesce/restart/flash。新boot只读检查与adoption工具已冻结，8+10例及独审通过；新现场协助问题待回复，旧USB-ready不沿用。USB IRQ板级DT静态编译通过，965个旧节点全部属性及保留区保持，仅新增PMIC2 usb-input@1300和两个OEM IRQ；配套去重ko7cbf10c0已实际链接、44强导入由502满足、W1无诊断。配套对仍离线，不能给旧R7单配新DTB，必须实际probe/双IRQ注册及拔插计数后才接受；不改已prepared的502 logdump-only事务。

502边沿采集模板完成14例身份/bind窄检查与独审，真实runtime pins仍不存在；仅实际502新boot验收并adopt后才能生成。原worker/audit、有限300秒总期限、90秒稳定观察、双fresh heartbeat和原child退出/cleanup保持；没有新桌面提示或UPower修改。记录状态信号时间与人工像素观察分别说明。当前无新采集器、未再安排拔插，等现场协助回复后执行既有一次启动流程。

继续离线完成三项底层续作：IRQ DT-only boot eddadec3/96MiB实际封装通过，payload6680318/used6684672，100其它完整FFS、BDS071a参数、SEC0xfe8、header门及绝对tail保持，无Image/SDK重建或rootfs cohort；新protection原包采证候选21项/私有W1对象及独审通过，固定root一次沿原段锁保存完整36字节帧/阶段错误，正常六命令/Health/TCA/Full不变，新3查询尚未实读；当前502 adopted PM工具实现与定向检查完成，原primitive逐字保留，RTC精确IRQ/console有限trace及独立清理、缺reason记null，15±5s与返回事实/原因/根主机恢复独立。审查修正了primitive已返回但RTC清理失败时returned被抹掉的报告缺口，仅新反例复验。整轮零手机/SSH/USB/PM，未修改已有502准备事务；现场协助问题仍待回复。


本轮继续底层离线收敛：保护observer实际intree ko已链接（7848cfab/88856B、note fc0d253d），原502配置/31强导入匹配、W1/Werror无诊断；与USB IRQ ko组成[实际三文件配套包](../charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/README.md)，正向51736B/9dee06dd、新manifest5fca8e5a，精确R8回退44194B/5ecae1f5。7项封装边界和[根独审](../charging-session-20261023/usb-irq-protection-cohort-independent-review/README.md)通过；真实重读两个包、五处manifest差异及四个新旧模块note，保持charger/服务/startup500/相机。它依赖新IRQ boot/DT和502载体，未安装、未建现场guard，不改prepared502事务；磁盘新/驻留旧只能为staged/runtime_pending。

[原包保存文本解析器](../charging-oem-audit-20261023/protection-evidence-parser-candidate/README.md)实际复用provider C校验器，13种实际capture/show输出集成与13种拒绝边界、单次CLI通过；旧21/149未重跑，独审未见限定范围阻断。完整坏包负rc保留、短传输不冒作36字节，mask稳定和协议完成独立；compat/freshness/boot/TCA分类/充电许可/物理验收均不提升。新三帧仍未实读，2719准确型号/语义未证。

[DWC DEVICE start局部候选](../charging-session-20261023/dwc-device-start-recovery-candidate/README.md)填补被吞掉的__gadget_start错误，锁内原stop清两EP0/DEVTEN、跳过本次RUN_STOP并沿既有同步恢复。6组20例/14实际函数、私有gadget.o W1/Werror及[独审](../charging-oem-audit-20261023/dwc-device-start-recovery-independent-review/review.md)通过（0718bc5e/466888B）；当时仅对象，后续一致Image见下。core PM仍忽略primary且保持powered-success；HALT/reset和负返后的安全IRQ/work/core unwind仍未闭合，不能宣称r5或USB恢复已修。

后续已完成[DWC Image503一致构建](../charging-session-20261023/dwc-image503-start-recovery-candidate/README.md)：沿真实502的9242条依赖缓存确定8个受core.h影响的DWC builtin对象，全部真实增量编译一次，最终Image969b0158…b613500/59243008B；3238其它archive叶、32stub、initramfs/BQ与15097导出保持，W1零诊断。原构建handle/私有最终读回均终态rc0，[根复核](stage-image503-offline-root-review.json)通过。未封装载体、未部署，未混入prepared502或IRQ配套；core PM unwind及物理恢复仍未验收。

未来IRQ/保护[暂存worker](../charging-ui-audit-20261023/usb-irq-protection-stage-candidate/README.md)26例通过：实际502 adopted前置、原flock内同步INHIBIT并核REG08、旧文件/note备份后原子写两ko/manifest、fsync/失败保留阶段。新磁盘/旧驻留仅staged/runtime_pending，无热卸/启充/重启。[host R2](../charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2/README.md)新增3例处理原SSH Popen receipt失败/部分输入异常时close owned stdin→wait原child，及截断远端父receipt仍unknown+raw可取；原20与内存接口仅复用，R1原件保留，[独审](../charging-ui-audit-20261023/usb-irq-protection-stage-host-independent-review/README.md)通过窄修范围。默认本地检查真rc0，未创建实际request/lease/guard；新stage专用重启路径尚缺，旧502控制器不可复用。

[IRQ postboot设备组件R2](../charging-oem-audit-20261023/irq-cohort-postboot-readonly/README.md)核配套manifest、实际OF provider/五DT属性与两唯一IRQ，按CPU集合/映射检查可比计数。独审发现共享action目标名在列表前面时漏判，R1反例与原件保留，只改parse_interrupts，新增10例通过、旧27例复用；[最终独审](../charging-session-20261023/irq-cohort-postboot-independent-review/README.md)接受限定组件范围。首次R2收据引用摘要误写已保留并修正元数据，执行/当前脚本分别记录，未假称重跑。归档镜像预审另发现R1 README移入历史目录后相对链接失效，首次同步在copy前拒绝；布局修订3将原字节保存为README-original.md.inc、保留原R2 delivery和显式路径映射，软件/补丁/测试收据均不变。host对真实stage/guard/endpoint的绑定仍未接入，IRQ注册/增量不等于实体或图标时延通过。

当前手机仍501；本轮零设备/SSH/USB/PM/SDK/桌面动作，prepared502不变。相机暂停且其线程已归档，未自行恢复；现场启动协助问题仍待回复，未新发拔插提示。

后续离线补齐[stage-aware设备重启门](../charging-session-20261023/usb-irq-protection-restart-candidate/README.md)：真实stage14原件/两child terminal0、源502 adoption原fresh proof、新disk/旧live与fresh INHIBIT分别核对，全程持原service flock；实际OpenRC为oneshot，两处充电stop都不重入同锁，其余硬件静默尾和完整RESTART2尾精确保持。12组新函数/4项安全默认与优化入口通过，初次fixture问题保留，旧套未跑，未创建真实guard。独立纯stage审核13项及[boot-only操作者/完成材料审核](../charging-oem-audit-20261023/usb-irq-protection-fastboot-candidate/README.md)31+13项、实际默认入口和[独审](../charging-ui-audit-20261023/usb-irq-protection-fastboot-independent-review/README.md)通过；实际原child wait/log/hash与最后flash/reboot绑定，saved结果仍不证明新boot。只允许IRQ boot edd/原boot97811，logdumpace2不写，[根薄审](irq-deployment-offline-root-review.json)通过。host单次activation调度及精确三文件rootfs回退仍未实现，不能拿boot回退冒认模块已恢复；不属于prepared502事务。

另完成[DWC SUSPHY失败回退](../charging-ui-audit-20261023/dwc-pm-error-unwind-candidate/README.md)：system suspend临时改位后gadget失败返回时，仅RMW恢复本attempt实际变过的各port SUSPHY，保留其它当前位/primary errno/ACTIVE资源；quirk可以清位、multiport旧位可混合，不能直接全局false。24个实际函数/原失败反例及成功写序对照通过，旧20/126不跑；唯一私有core.o W1/Werror真rc0（219528B/7a93b92b），原503/shared inputs及helper后mount保持，原284窗口已归还，[根实际对象薄审](susphy-offline-root-review.json)通过。该阶段完整resume unwind及原!softconnect吞HALT错误未修，后者当前attempt的后续修正见下文；未冒称r5/整机数据恢复已修。

本轮仍零手机/SSH/USB/PM/SDK/桌面动作，实际运行501，现场协助未答；所有新增均离线，未启动新拔插采集。502单logdump准备事务保持，先验证该最小通知修改，再安排独立IRQ链路。

[IRQ postboot只读host](../charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/README.md)已冻结：原pure stage认证13项完全复用，新增18边界及实际默认源检查rc0。completion API原始命令材料、源stage/真实adoption、原key probe/source/argv/同child终态、两次同新boot≠源boot全部认证后才封装；明确区分原activation guard/hash与stage tx的collection_guard投影。collector命令另含execute/window/newendpoint，原probe argv不冒称采集，实际十门audit重新计算，失败raw保留。没有transport dispatcher，未绑定真实endpoint/request/guard；实际activation调度和精确三文件回退仍缺，完整IRQ流程未就绪。

随后独审定位R1仅同目录保存payload、未与child输入绑定的证据缺口，未上机。原R1 delivery/host/README字节保留，R2仅在saved_transport新增child与terminal的stdin_sha256均等于预期payload；5个新增正/缺/漂移案例与默认入口真0，旧18/13/31不重跑，[最终限定独审](../charging-ui-audit-20261023/irq-cohort-postboot-host-independent-review/README.md)通过。pure stage-proof及原pins保持，未新增dispatcher或未来运行材料；未来原Popen owner须在发送前保存输入摘要并沿用到同child终态，不能凭目录名推断输入。

本轮新增[DWC挂起HALT错误返回](../charging-ui-audit-20261023/dwc-suspend-halt-error-candidate/README.md)：仅在!softconnect的失败分支返回原errno，使当前attempt进入既有SUSPHY恢复并阻止core_exit/PHY掉电；13例实际函数组合含旧吞错反例，ASan/UBSan/Werror通过。私有gadget.o W1/Werror零诊断，原GCC793 wait0、466856B/3ce30b25，原503/shared源与挂载保持，284窗口已释放；[根薄审](halt-error-offline-root-review.json)通过。后续pullups=false早退重复attempt、原DMA/request处理及完整resume仍未闭合；没有链接Image/部署。

另完成[IRQ新boot adoption](../charging-oem-audit-20261023/irq-cohort-adoption-candidate/README.md)：原host R2完整raw/actual输入链审核后，fresh十门审查与同新UUID通过才先proof后guard写入/fsync/readback；原owned SSH EOF/wait、requested/interop observed argv与stdin SHA保留，旧502pointer原字节两次比较后才原子发布。20个新增函数边界/default0/优化入口拒绝及[限定独审](../charging-ui-audit-20261023/irq-cohort-adoption-independent-review/README.md)通过；测试身份/IO为明确fake边界，没有实际request/guard/endpoint、SSH/USB/PM/SDK或桌面动作。手机仍501，prepared502保持；本轮不新增拔插提示。

[IRQ activation host R2](../charging-session-20261023/usb-irq-protection-activation-host-candidate/README.md)补齐实际单次调度/原进程取回/7raw上下文输出。R1的12例与3默认已通过，但独审发现communicate异常后未先关闭owned stdin，可能双方互等；R1与该拒绝原件保留。R2只改ssh_worker/terminal_job，新增3例和默认0：先尝试EOF再wait同child，收尾/日志/发布错误分别保留，clean finalization及真实terminal SHA不成立不得晋升。remote/supervisor/原静默重启worker和7raw导出逐字保持，原operator实际兼容检查复用，旧12/13/31不重跑。没有真实bind/request/guard或连接动作。

[三文件精确回退worker](../charging-oem-audit-20261023/usb-irq-protection-rollback-candidate/README.md)现21例/纯saved-proof6例、两默认真0及[根薄审](irq-rollback-offline-root-review.json)通过；10原helper含atomic/两层stage终态校验逐字复用。三种显式boot/驻留组合分别核对，不依赖新的整套postboot验收通过。fresh独立保护/电芯/实际limits及INHIBIT成立后只恢复USB→保护→manifest，未知源预算仅记录，valid0/缺fresh电芯仍零恢复；不启充/卸模块/改载体。部分写入、原子持久化或close错误不冒报成功，成功也仅staged_original/runtime_pending。当前身份/request物化和连接式监督未实现，后续复用既有owner，不另扩调度层；未上机。

下一轮实质增量：[无pullup挂起重试门](../charging-ui-audit-20261023/dwc-suspend-retry-candidate/README.md)关闭了无并发两attempt软件false flag假HALT路径。active分支需DSTS.HALT且DCTL.RUN_STOP0，miss在原复连块前-EAGAIN，不新增stop/DMA/reset/poll，runtime-suspended不加MMIO。15个实际函数组合/ASan/UBSan/Werror与唯一私有gadget.o真终态0（GCC847、466720B/a199defc），[独审](../charging-oem-audit-20261023/dwc-suspend-retry-independent-review/README.md)通过限定快照范围；旧13/24/20/126复用。post-snapshot producer仍可破坏证据，测试反例保留，不称完整PM互斥。原284已归还，零Image/设备/SDK。

[resume unwind反例审查](../charging-session-20261023/dwc-resume-unwind-candidate-r2/README.md)的17实际函数/7组合及[根薄审](resume-unwind-r2-root-review.json)完成：保留原powered状态直接负返、HALT未知直接core_exit、仅HALT+IRQ join而遗漏recovery work均不成立；同primary还可能对应最终恢复成功。提出[stack outcome API](../charging-session-20261023/dwc-resume-unwind-candidate-r2/OUTCOME-API.md)与具体caller/owner顺序，但失败HALT authority、producer join和pending IRQ/PM配对未闭合，结论changes-required、无deploy patch。GCC762/fixture773原handle0，没有284/新对象/Image/设备/SDK或旧套重跑。

[回退probe/request binder](../charging-oem-audit-20261023/usb-irq-protection-rollback-host-candidate/README.md)也完成12新例/两默认0与[限定独审](../charging-ui-audit-20261023/usb-irq-protection-rollback-host-independent-review/README.md)：先原source/profile认证，再原key/Popen/双stdinSHA/终态与双identity夹完整carrier/实际notes，actual worker profile/unpack均过才mkdir；identity只取probe，不从old pointer填。未真实绑定，lease/launch/status/fetch/supervisor仍未接线；不重跑旧21/6/20。

本轮另做[一次普通只读](image501-readonly-current-02-result.json)，严格原key实际rc0，源/当前#501与adopted guard一致、Y/taint0；SDP预算/native/REG00输入属性500mA，100%/23.5℃、NOW/AVG0，fresh sample age523ms、full_holding1、保护error0。只取当前快照，未重读双载体/全部notes/相机基线，不充作完整验收；没有控制、PM、采集或拔插提示。满电保持下不强求Charging闪电，下一轮按实际Online/正确Battery状态计边沿。prepared502未变、相机仍按用户暂停。

本轮继续纯底层：[DEVICE恢复结果接口](../charging-session-20261023/dwc-device-resume-outcome-candidate/README.md)19项新检查（18 outcome＋1 HOST）、16场景legacy差分及8对象W1/Werror实际原wait0通过。源码15文件293a2e96冻结，编译只新增object-build补充288bc757；原284在guard内恢复挂载，编译前后原source503/shared与helper后的mount保持，已归还。primary与最终成功事实分离但core未接入，未链接Image/上机。

[USB退出恢复任务寿命修正](../charging-ui-audit-20261023/dwc-recovery-exit-lifetime-candidate/README.md)实际修正cancel之后IRQ/恢复发布重排，以及mutex_destroy早于UDC pullup/unbind的寿命孔；8新案例含真实pthread work join、限定独审与单gadget.o W1/Werror原GCC803/exec86801实际0，旧反例保留、原284已归还。gate只关闭该gadget lifetime的recovery生产者，不能替代完整failed-resume owner，未改core/PM政策。

[连接式三文件回退](../charging-oem-audit-20261023/rollback-connected-candidate/README.md)补完复用原binder/worker与regular-fd supervisor的最小执行接线，29新wire/owner例、3实际transfer分支及3默认原Popen入口通过，[根薄审](rollback-connected-offline-root-review.json)核18文件/9来源：同原SSH/worker实际终态、EOF先于wait、日志先close后终态、原launch rc0/响应/原supervisor匹配，跨boot不归因当前PID，35秒父等待只pending、设备lease120秒。原非0/畸形/close失败不晋升；无真实bind/request/lease/连接或三文件写入，最终runtime验收仍false。本轮零手机/桌面/SDK/重启/刷写，prepared502不变、现场协助问题仍待答。
