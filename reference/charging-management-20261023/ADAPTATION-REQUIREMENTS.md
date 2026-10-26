# 充电管理完整目标：当前证据与剩余范围

2026-10-25离线进展：[MP2650预算消费者](../charging-oem-audit-20261023/tcpm-charger-input-candidate/README.md)38例函数测试和单KO通过；[ADC5板级候选](../charging-oem-audit-20261023/tcpm-measured-vbus-board-candidate/README.md)确认processed值单位为µV并精确改3个DT属性，未验证实物精度；[PD/APSD接管](../charging-oem-audit-20261023/tcpm-apsd-handoff-candidate/measured-start/README.md)与[5V合同退出](../charging-oem-audit-20261023/tcpm-contract-shutdown-candidate/README.md)各自离线验证通过，但完整probe整合=false、高压采用=false，未部署。500mA/保护策略保持。506十小时试验仍占用手机；EUD tty/getty/reader未就绪，不改桌面。

2026-10-25最新：[508 R2实际合测通过并回506](../charging-oem-audit-20261023/tcpm-usb-budget-candidate/phone-trial-r2-result.json)，覆盖默认Rp/native500预算、软件断开共同0→500及原key恢复、真实关机取消/锁释放；两载体/原文件/三note/PD双0恢复确认。未代替物理USB唤醒、PD高功率或APSD共存。[真实计时观察已启动](timeout-live506-start-result.json)，36000秒到期及AUTO锁存仍待实际结果。

2026-10-25更新：[506控制恢复及预充取证](recovery506-20261025.md)，1299条原记录复核、预充phase1→连续快充phase2/正净流、正常AUTO和负载收尾已确认。未完成本次低电到Full、恒流精度、温界/10小时及高功率。当前新boot仍506，清理失效EUD getty，低SOC命令行回充；508未装且旧暂存事务不得执行。

[Image506跨待机修正已装机](../charging-oem-audit-20261023/eud-route-pm-candidate/README.md)：正常route改为暂停/join/complete复核，永久撤销和失败隔离保持；新增现场CSR只读双0检查及真实资源占有，零路由写。23组provider/13组整合C、实际增量Image通过，原配置/导出/电量计/initramfs/builtin元数据均保持。当前boot5c8d/FATb29e、USB161b/bef4/f6bef/服务83469/manifest8b402；只有FAT改变，永久rootfs和固件未变。两RTC驻留15.076/14.855秒、各success+1/fail0，路由complete实际出现、所选回调err0，无复核失败日志，原key/NCM和500mA/保护恢复，最终AUTO Full。两worker终态0、trace/alarm与临时guard收尾。真实PM后物理新连接/APSD、USB唤醒仍未验；下述505及更早记录为阶段历史。

[Image505已实际安装并采用](../charging-oem-audit-20261023/apsd-image505-integration-candidate/phone-activation-result.json)：boot5c8d/FATb388、USB161b、chargerbef4/保护f6bef/服务83469、最终manifest8b402。真实route/Type-C5V provider已绑定，原key/NCM自动恢复，SDP源/native/硬件500mA、CC250mA/CV8.725V和保护Good通过。[新组合RTC](../charging-oem-audit-20261023/apsd-image505-integration-candidate/phone-rtc-result.json)驻留15.195秒、success+1/fail0，12条所选回调err0，预算/保护/USB恢复、worker终态0且alarm/trace清理。仅新外部KO的正常O taint4096，无新增warning/oops。临时guard已收尾并删除，服务主体和原OpenRC保持；根目录六处最终差异及精确原504逆向已保留，恢复器改用稳定分区身份。当前APSD路由在首次PM prepare主动过期，尚无恢复；真实新连接/FLOAT/APSD、物理USB唤醒、温界/预充/10小时和快充仍待验，未声称图标改善。以下旧“尚未装机／当前504”为阶段历史。

[同组合自然回满已实机通过](charger-full-return001-result.json)：377个AUTO样本/64分6.921秒，自行进入Full/cause3并稳定五样本40.947秒，最后电芯4.325/4.323V。零额外充电控制、未改参数，所有原样本通过实际IO审计。原24901终态0，worker/supervisor退出，fresh AUTO Full/Good、500/250mA/8.725V及原服务锁释放确认，adoption已绑定。结合前轮已证明Full→自然放电→真实回充→Full，低电预充、温界/10小时及物理USB唤醒范围仍未覆盖。该504回满观察已经收尾；其后505实际部署见本页顶部。

新增[真实505成套构建](../charging-oem-audit-20261023/apsd-image505-integration-candidate/README.md)：Image b91a/59374080B、BDS EFI9393及原IRQ native DTB的d5fa第二版已产出，未装机。DWC合并完整保留504预算/PM函数；私有copy-up构建仅九项配置变化，原15097导出、BQ对象和initramfs保持，新增21导出。补足本地头文件后原增量make3.10/46.76秒均0、零诊断，第一份编译失败保留。BDS只编一对象、复用40库，链接0的原有工具链警告经缓存审查、最终PE无WX；未重放链接。实际Image参数表纠正5V命名空间为qcom_pmic_tcpm，保留当前BQ瞬时参数1。该离线阶段随后已完成同套模块/载体/逆向与实际部署，见本页顶部；原504回满worker已终态0。

新增[APSD任务与真实EUD-off路由接线](../charging-oem-audit-20261023/apsd-eud-route-client-candidate/README.md)：真实provider/client/原lease代际已接入，删除此profile全部旧COM静默调用，最终传输重新验EFI关闭结果；正常恢复与UDC退休分别处理，失败仍保留排他。九组完整owner/PD/PHY/route C、两个受影响W1对象、五原对象复用及十八内部API检查通过；二十三原函数逐字保持。组合测试发现并修正失败PHY恢复被后续join再次尝试，原失败及首次七组结果保留。默认关闭/未装机；下一块为同Image/固件/实际DT启动组合，首次物理断源、FLOAT/APSD、路由跨待机重建及快充仍待验。

2026-10-25最新：[真实Full回充和停充计时](charger-full-recharge002-result.json)已通过：自然放电70分13秒后原策略退出Full并回充，确认停充59.995秒计时10秒不变，AUTO继续13→23秒。原worker终态0/已退出，AUTO/保护Good与锁释放fresh确认，本组合adoption已绑定。另补[EUD三producer实际仲裁](../charging-oem-audit-20261023/eud-route-provider-candidate/README.md)，十二组C及七对象、默认关闭和内部接口通过；DWC接线现由上述候选完成，尚未装机，PM路由重建未证，不能当完整APSD支持。

2026-10-25最新：[EUD固件到内核结构化交接](../charging-oem-audit-20261023/eud-route-handoff-candidate/README.md)已实现并完成十组真实C、实际BDS/EFI/receiver对象及内部接口检查，实际默认n配置不引入handoff依赖。原关闭写读序列、panel/日志区不变。该证据通道未部署，尚不提供路由独占/撤销权；真实supplier、DWC消费及最终同Image/新boot验证仍需完成，APSD gate继续拒绝。

2026-10-25离线增量：[最终1341传输](../charging-oem-audit-20261023/apsd-final-transfer-candidate/README.md)及[当前USB13f IRQ/PM接线](../charging-oem-audit-20261023/apsd-current-usb-integration-candidate/README.md)已完成实际身份/租约复核、稳定源重读和prepare撤销/complete发布，九+十八及十+十五组实际C测试、三个旧目标/唯一新input W1对象与内部接口检查通过。真实路由gate仍拒绝；未安装、未改变TYPEC=m，可信EUD-off路由supplier/最终builtin配置及实际连接周期未验，完整Type-C/PD和快充范围保持。

2026-10-25当前：[停充计时R2实际启动采用](charger-timer-activation-result.json)，504/USB13f41/chargerbef4/保护f6bef/服务83469/manifestf15ecc、bootbc612。本组合[RTC驻留15.439秒](charger-timer-rtc001-result.json)、success+1/fail0及前后十二门通过，原key/NCM自动恢复无需人工拔插，500/250mA和整包8.725V保持。自然放电/回充及60秒计时暂停实测已通过；真实USB物理唤醒未验。用户授权无人值守操作和刷入，但无法拔插。当前charger-only逆向c72589恢复97c/5ef4，保持USB13f；下面旧组合和“未安装”描述按历史读取。

[首轮38分9秒实物放电](charger-full-recharge001-result.json)已恢复AUTO并正常清理，原Full/cause3/保护保持；恢复后电压回弹到4.270–4.281V，高于原4.2625V再充阈值，未触发回充，不能当完整循环或计时切换证明。第二轮仅调整放电观察截止值为4.20V、保留原充电参数和真实Full，70分13秒后成功回充并完成计时暂停证明，无附加CPU负载。

2026-10-24当前：USB IRQ唤醒配置已装机并通过[一次RTC待机恢复](usb-irq-wake-rtc001-result.json)。当前504/USB13f41/97c/f6bef/服务83469/manifest5ef4、boot4e325；真实驻留15.019秒，success+1/fail0，前后12门、USB挂起恢复回调0、原key/NCM自动恢复与SDP500保持，无新fault，alarm/trace清理。原驱动未配置IRQ wake的缺口已补；真实USB插拔唤醒仍待现场，窗口只prepare未启动。前boot的2719完整8帧证据保留，新boot MACv2/p1实例0/0未重查。当前USB两文件逆向0c6a6恢复ebfcb/8c5b7后冷启；更早回退属于不同范围。TCA语义、温界/完整预充再充、FLOAT/APSD与高功率仍未完成。下面旧组合/未加载描述按历史范围读取。

2026-10-24最新：[USB通知修正实机结果](native-pm-notify-r2-result.json)已装入504/ebfcb/94a659并采用。原12门在启动及PM前后通过；RTC单次实际驻留14.874秒，success+1/fail0、无新fault，原key/NCM无需拔插恢复、SDP/native/硬件500mA保持。trace证实挂起内的软件自唤醒消失，通知改在complete发布。物理USB唤醒、温界/完整预充再充和协议/高功率分支仍待验。下文旧未stage、d046和PM失败描述属于此前记录。

2026-10-24：PM03实际栈已确认一条软件通知在挂起内自发激活wakeup源，r2 ebfcb/94a659及精确逆向已构建、8组C与W1/47导入过，已冷更启动12门过；当前504/ebfcb/94a659，PM复测进行中。完整温界/预充再充/协议/快充等范围不缩减。

目标保持为原厂资料优先、底层适配、与相机/其它会话串行实机、可并行离线。以下是需求覆盖，不把已经工作的保守普通5V子集重新定义成全部完成。

2026-10-24增量：[504实际启动及采用](native-pm-504-activation-result.json)完成，4453/d046/34ead和原97c/7848/bootedd真实驻留通过12门，stateless供电依赖、冷boot SDP500/250/8.725V及保护/原481/468保持；NCM自动恢复。此为启动与当前状态检查，PM001实际单次mem被-16拒绝、未入睡；前后12门及预算正常，仍未通过PM驻留/恢复；温界、完整Full/再充与快充待验。新增空间目标：清理可重建的过时构建/废弃残留，保留原厂/个体资料、实机证据、当前增量构建和有效回退；同时核C/E物理盘与WSL逻辑空闲，不把fstrim报告当C盘已回收。

2026-10-24当前：[IRQ／保护配套已实际启动并fresh采用](irq-activation-result.json)，bootedd/logdumpace2与新USB/保护驻留十门通过；#502/Y、相机481/468/服务/startup500/SDP500保持。用户现场正常拔插后[单charger热更97c/manifest18e8成功](charger-reattach-update-result.json)，USB/保护同实例及MAC缓存保持；原boot-adoption pointer仍5fca，另有runtime overlay。IRQ完整回退须原R8三文件＋boot97811，本次charger-only回退为10ec/5fca。[IRQ001](icon-irq-001-result.json)三次手动短断源中IRQ计数0→6/4，source→目标Charging约2.1秒；长周期门未过、像素未测。新[reattach001](icon-reattach-001-result.json)完整周期过、134样本正常收尾，source→Display2.103秒，用户仍2–5秒，未证提速。MAC一次0050/52过，0056完整length7与4-byte候选冲突-90且无0A后值，失败保留不重试。早期启动/传输失败保留，不称USB/PM已修复。

2026-10-25新增离线[APSD DWC/PHY接线](../charging-oem-audit-20261023/apsd-phy-client-candidate/README.md)：沿[PHY撤销接口](../charging-oem-audit-20261023/apsd-phy-withdrawal-candidate/README.md)接真实client/永久fence/retiring取消，十二组完整owner/PD/PHY组合C、两个私有owner对象W1/Werror及内部九API的relocatable接口检查通过。未部署、未变实际TYPEC=m；路由授权、最终单次传输重验证、完整APSD/Type-C/PD及快充仍待实现，不提升当前普通输入预算。前轮十组provider真实pthread与单PHY对象结果保持。

| 要求 | 当前证据 | 仍需完成 |
| --- | --- | --- |
| 本机原厂资料与板级匹配 | 固定Android R提交、19781 DTS、2719实物报文、MPS/TI缓存及明确哈希 | 新协议和高功率分支仍逐项匹配，不能把近型号默认当本机 |
| 双电芯/保护查询 | 六命令完整36字节白名单、实际报文/传输拒绝、族协议Safety/PF/Operation/Manufacturing状态；未证实TCA分类错误。新增[一次原包采证候选](../charging-oem-audit-20261023/protection-query-observer-candidate/README.md)21项及私有单对象通过：沿原锁固定batch保存完整帧/阶段错误，普通六命令/Health不变；实际ko7848及两ko/manifest一致包已产出，26边界的保存文本解析器沿实际C校验，现已作为IRQ配套实际采用；主机解析器独立使用 | 已从两旧完整0002帧固定11字节FW指纹（缓存解析13例），无需重查；原[六份选取索引](../charging-oem-audit-20261023/gauge-2719-index-check/README.md)结论保持；新增F.10[vendor](../charging-oem-audit-20261023/gauge-2719-vendor-name-index/README.md)与[system/工程应用](../charging-oem-audit-20261023/gauge-2719-system-oem-check/README.md)实际提取/只读索引：分别129目录2884路径和606目录5333路径，无四描述后缀文件名；定向配置/库、APK34688项DEX字符串只得QTI/Oplus服务、工程PSY/HIDL接口，异常电池XML的consumer/单位未证；不推全ROM或嵌入内容无数据；精确0x2719型号/固件字段语义、TCA自然事件和0050/0056/0052仍缺实证；新接口已[单次实读](protection-capture-live001-result.json)：0050/0052过，0056 length7报-90且缺0A后值；不重试、不推定兼容，零告警不代表状态稳定或物理安全；新增默认关闭、fresh2719门控的0056三字节schema2诊断profile离线11组C/18解析边界过，独立保护ko f6bef8a2已冷更采用，[新实例完整8帧实读](protection-profile-live001-result.json)及当前组合15.610秒PM通过；前后真实0A已补足，完整TCA事件/语义仍缺。PF_EN继承0不等同其它保护全关闭，不绕过原MAC事务锁 |
| 普通输入预算 | 正常startup500保持，501启动CDP1.5A/native500mA/hardware900mA按原帽通过，用户反馈后SDP源/native/硬件500及100%Full保持通过；旧363真实SDP500循环稳定91秒/81样本均500且净充入保留 | 当前506新组合冷boot/两轮RTC PM恢复500已验；物理USB唤醒、FLOAT及完整Type-C一次APSD仍待验；SDP与CDP预算分别记录，不能泛称当前硬件500；旧R7失败保留 |
| CC/CV/温控 | 默认900/250mA请求帽、源继续限缩；不抬4.3625V；原厂方向effective band已作为R8单模块加载，函数差分/step/真实构建及NORMAL下停充→恢复、实际caps/三notes/相机保持通过 | 温界物理刺激未验；原厂更高功率与场景降额未全部接入，NORMAL加载不能覆盖全部温控范围 |
| 预充/终止/再充 | 保留硬件预充180mA、终止100mA和安全计时；软件Full/六温区再充及手动停止门控v2已部署。新增[506实际预充→快充](precharge-live506-r3-recovered-result.json)：1299条原记录、phase1→连续phase2及正净流通过，AUTO/负载收尾确认 | Full→自然放电→策略自行回充→稳定Full已另行实测通过；本次低电预充到Full完整循环、恒流精度及物理断源再充仍未验 |
| 计时与错误恢复 | [R2修正](../charging-session-20261023/charge-timer-hold-r2-candidate/README.md)已安装bef4：保留已累计值，仅暂停已确认停止的时段，计入stop实际耗时；9组76断言、单KO/W1/54导入通过，实际冷更新/新boot采用/本组合RTC通过。保留真实断源复位、旧fault/timeout和未知源保守计时 | 非Full有效计时→60秒确认停充→AUTO继续累计已实机通过；10小时/TCA/温界仍待验。[两分支逆向](../charging-session-20261023/charge-timer-cold-rollback/README.md)十场景、16重启门/10验收请求/2本地adoption离线通过，实际逆向未执行 |
| 电量计瞬时属性 | [Image501已部署](image501-activation-result.json)，严格本机参数Y：NOW/STATUS用原厂0x0c，AVG留0x14；完整双载体/静态ABI/实际R8及相机加载/独立电流字段九门通过，原getter与C默认关闭保持 | 001无断源不能验收新图标边沿或改善幅度；实际CDP源模式不同，不能全归因gauge；原构建/传输及SDP假设失败保持 |
| 图标状态 | 原363 SDP500循环目视明显更快但后台off3.73/on3.08秒；501启用瞬时属性，001采集无断源，不能量化新边沿。桌面原版，502去半秒等待的Image/FAT已部署、九门与fresh adopt通过；USB IRQ DT/ko/boot与配套包已构建，暂存/设备检查R2离线通过。新增stage-aware门12组+4入口、原stage审核13项、boot/完成材料31+13项及限定独审/根薄审通过；只读hostR2输入绑定5项、activation hostR2异常EOF3项及新boot adoption20项已离线；三文件回退worker21+6与原key当前probe/request binder12项通过 | 当前IRQ配套已完成实际stage、boot写入、新boot十门及fresh采用；新增250ms/3s短观察单ko97c/双包及当前IRQ更新设备14组/host六组覆盖、同boot采集14新例完成；先前健康Full预检在停充前拒绝；正常拔插进入Managed后97c/18e8已真实热更、原USB/保护同实例保持、runtime overlay已绑定，新reattach001完整周期/清理通过，source→Display2.103秒，用户仍2–5秒，未证提速；图标专项先收敛，不再以追零延迟阻塞其余充电适配；原502两个窗口无断源不用于新IRQ验收；连接式rootfs回退29新wire/owner＋3 transfer/3默认入口保持，新增[恢复后重启接线](../charging-session-20261023/usb-irq-protection-rollback-restart-candidate/README.md)6组/5默认入口过，成功rollback＋后置probe接原owner与原boot-only operator；尚无真实bind/lease/launch或新boot runtime验收；离线接线不代表实际采集或runtime恢复。新IRQ001已有真实断源与中断递送，但未达原长断源样本门；三段source→目标Charging约2.1秒，像素/连续周期仍未验。独立新boot/guard/事务已使用，不混prepared502。保留真实Full/保护，不伪报Charging，状态事件不代替屏幕像素 |
| USB供电PM顺序 | 当前506/USB161b保持IRQ/PM预算函数；route正常暂停/join与现场CSR复核已接通，两轮RTC15.076/14.855秒通过，实际路由complete出现、无复核失败日志，原key/NCM及500mA/保护恢复 | 实际PM后的新连接/APSD传输、物理USB唤醒、其它源及长待机功耗仍待验；未用正常RTC代替物理唤醒证明 |
| 待机/启动 | 当前506/5c8d/b29e、USB161b/bef4/f6bef/83469/manifest8b402实际采用，两RTC和USB自动恢复通过；原OpenRC/桌面保持、临时guard删除 | 物理USB唤醒、异常断电/其它源/长期循环待验；旧失败保留 |
| 厂商/协商快充 | [固定AndroidR快充恢复与codec](../charging-oem-audit-20261023/oem-fastcharge/README.md)已解析19781 STM8S/type22、DA9313/握手GPIO、两条件固件数组和七位上下文通知，原厂gate/dispatch差分通过；没有把第三方defconfig或镜像0x18当实物MCU身份 | SuperVOOC/PD/QC/FFC未完成；实物MCU身份/供电与独占握手owner仍缺，原厂版本getter会reset/写，不能直接当只读查询。当前SDP/CDP不满足OEM DCPgate，不抬预算或照搬4.465V FFC目标；普通5V不等同全部充电模式 |
| 包与版本一致性 | 当前506仅FATb29e改变，boot5c8d、USB161b/bef4/f6bef/83469/manifest8b402及全部builtin元数据沿已采用505保持 | 本轮逆向只恢复505 FATb388；boot和rootfs相同，实际逆向未执行。再回504需上一轮完整edd/4453及bf28a19 rootfs逆向，不混用旧c725 charger-only包 |
| 会话互不干扰 | 用户暂停相机、只用本会话，无子代理；原481/468及四服务文件没有纳入本轮写入，当前仅本会话串行操作。没有恢复/消息唤起已归档相机会话 | 相机恢复需用户明确恢复及届时新鲜boot/guard/正式基线；实机继续串行 |

完成需补足实际剩余项并按其范围验证；不能用离线单元测试代替失联手机的恢复，也不能以旧PM、旧manifest或只读健康片段支持新范围的通过结论。
