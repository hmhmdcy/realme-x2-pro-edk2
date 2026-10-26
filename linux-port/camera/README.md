# Realme X2 Pro 相机适配

用途：相机资料与后续实现导航。整理日期：2026-10-24；相机按用户要求暂停，当前优先充电，本文更新不恢复设备操作。完整进展与恢复步骤见[491交接](../../reference/kernel491/HANDOFF.md)；实际部署和回退以[检查点](../../NEXT-SESSION.md)为准，[484](../../reference/kernel484/README.md)保存r33/r28工作基线的真实三相安装及默认路径证据，[440](../../reference/kernel440/README.md)保留原r32/r27历史。

最新候选为[489增量core](../../reference/kernel489/README.md)与[490签名r34/r29七包](../../reference/kernel490/README.md)，仅core改变，继续复用IPA6／签名／代理／驱动／四原厂profile。ARM64 SDK加载、验签与路径解析及缓存依赖模拟已过，尚未安装到手机。[491](../../reference/kernel491/README.md)的单次升级→8例短验→精确r33/r28恢复工具已完成离线归档、进程、传输与独立复核，未绑定、上传或执行。恢复工作必须先等用户明确恢复，再取得充电维护的新boot／guard／endpoint和正式基线。

## 当前推进方式

遵循[操作规则](../../WORKING-BOUNDARIES.md)和[原厂资料优先工作流](../docs/PORTING-WORKFLOW.md)。复用已提取的四摄配置、EEPROM、模式树、HAL算法和现有构建；缺项才提取原厂固件或定向检索公开仓库。先匹配模组、模式、位深和处理域，再转换接入，实测补齐缺失标定。

[449](../../reference/kernel449/README.md)同Manager六周期263图／265IPE通过，旧长测重复回执仍记失败。[450](../../reference/kernel450/README.md)统计淘汰修复9000图严格原始回执通过，同SOF PD10／GTM／WB／历史匹配、重复0，仍5缺SOF。[451](../../reference/kernel451/COMPARISON-HARDWARE.md)隔离1080p旧→新→旧proxy共540图严格通过，返回尾部缩短但基线漂移。[452](../../reference/kernel452/DIAGNOSTIC-HARDWARE.md)353物理IPE取证：缺SOF168有PD10／统计，无成功FULL用户态DQ／IPE配对，DMA／驱动交付及瞬时供给待区分。

[459／452 r2](../../reference/kernel459/HARDWARE-SUMMARY.md)新增2738消费／2739物理IPE严格回执，90秒未复现gap；尾环有覆盖，V4L2过滤误选RDI0，不能宣称根因修复。当时正式栈、服务和独立trace已恢复，随后USB拔插使外部充电检查false，该轮不记通过。441几何、442 LTM、443原厂16:9 DS4、444 IPA6及448租约等后续实装范围以484为准；光学、编码视频、HDR、第五摄像头和多摄未完。

## 资料入口

[484实际安装](../../reference/kernel484/README.md)已完成r33/r28升级→r32/r27精确回退→再升级，三个native APK add exit0；最终保留441三模块＋468 sensor＋四原厂profile。两次forward的14个默认路径用例通过：四摄Gst256张640×480、RAW-only24帧、主摄dual12帧，268次IPE成功＝242数学＋26bootstrap；实际/usr、有效签名native IPA、UID10000／maps／lease／回执逐案核对，RAW-only零IPE。新七pins／本地repo通过默认系统仓库simulate，外部健康通过，fault0／taint0，设备已交回充电。候选系数／数学不变，复用既有两尺寸LTM因果证据；未宣称光学、录像或长期验收。[481](../../reference/kernel481/README.md)／[482](../../reference/kernel482/README.md)／[483](../../reference/kernel483/README.md)保留当时准备历史。

[479控制响应](../../reference/kernel479/README.md)补齐原厂长焦mode2九步曝光／增益升降：240 Pair、233 SOF，全部达到原SNR条件，首变化与三帧平台均SOF＋2，与现有delay2／2一致，未改profile。依据IPE前同SOF线性BHIST，metadata恒startup值未作证明。476整轮仍false：工具错误要求零IPE，实际默认单遍IPE240次成功；[478](../../reference/kernel478/ipe-r1-correction.md)保留并更正静态误判，未重采。正式栈／服务／R8恢复，fault0／taint0；非寄存器锁存、无IPE隔离或完整控制范围验收。

[480目标包解析](../../reference/kernel480/README.md)已用手机原信任集verify七候选APK＋索引，并对精确七包simulate／no-network解析成功；全局APK清单、db／world／repo／keys／日志及属性保持，未安装。475离线root缺provider失败保留，该轮未实装；随后真实三相事务及当前r33／r28见484。

[474组合验证](../../reference/kernel474/README.md)复用441模块／原厂长焦mode2，将473 core和451 proxy组合，1080原生／隔离各32帧：64消费／64 IPE＝60数学＋4bootstrap，原始回执无重复／负值，两段短测无SOF缺口，70Q／64DQ。实际进程、IPA／proxy、Manager动态mask与正常stop恢复均核对。固定SOF12的FULL／参数，仅换PD10四次回放：三完整输出互异、真实重复全字节相等，实际GST采样hash匹配，确认1080p LTM消费。正式sensor／栈／R8恢复，fault0／taint0；不作长期功耗或光学验收。

[475](../../reference/kernel475/README.md)收敛七包r33／r28及当前440 r32／r27精确回退，保留已测ELF／IPA签名；该轮仅离线候选，随后真实安装见484；APK root因可信缓存缺provider在r32基线失败，r33事务未发生，不能声称升级/回退通过，后续目标solver见480、实际安装见484。[476](../../reference/kernel476/README.md)复用472现成工具准备mode2独立曝光／增益阶跃，其后实际响应见479，原零IPE断言失败保持。

[473](../../reference/kernel473/HARDWARE.md)将现有Manager容量租约扩到processed IPE，固定旧proxy做长焦1080旧core/新/旧各32帧：96消费/IPE严格过，B实际动态mask与停止恢复通过；串行中位38.272/29.403/38.389ms，缺口3/0/3。支持本短段改进，非长期/功耗/物理根因验收；原sensor/正式栈/R8恢复。候选已编、未永久安装，后续组合451 proxy及1080独立LTM见474。

[471](../../reference/kernel471/README.md)新proxy返回尾部缩短但A2自行迁CPU4，不能归吞吐因果。[472](../../reference/kernel472/BUILD.md)已编复用306的mode2控制阶跃工具，当前0.7.2接口通过、未上机；曝光/增益mode2响应其后见479。

[469](../../reference/kernel469/README.md)复用原厂mode2和468候选，720p GST32帧严格同SOF与FULL FD通过；固定FULL/参数仅换PD10四回放，三完整输出互异、真实重复字节一致，与实际消费采样hash匹配。正式sensor/栈/R8恢复，fault0/taint0。原厂全局pipelineDelay2不等于mode2控制生效延迟。[470](../../reference/kernel470/README.md)缓存显示1080串行Pair→receipt约38ms、参数返回尾部约15.8ms，下一单变量复用451 proxy；FULL timestamp为完成时间，邻DQ窗不冒认物理SOF。

[468](../../reference/kernel468/README.md)已将原厂4208×2368 mode2以单模块接入并实测：720p/1080p各32帧自动选新模式，64消费/IPE、严格同SOF及LSC参数上下文通过，正式sensor/栈/R8恢复。原mode3及全部原厂IQ/本机unit保留。驱动S_FMT控制缓存修正、28有限C例及363 ABI模块通过；近16:9画幅已开流，1080仍有3缺SOF、该尺寸长焦独立LTM回放/控制延迟和光学/录像待验。

[467](../../reference/kernel467/README.md)新增长焦mode3两尺寸各32帧隔离正常消费，64消费／64IPE＝58math＋6bootstrap，严格同SOF及真实FULL FD通过、正式／R8恢复。1080仍缺SOF14/21/28、队列零快照；720无缺口。capacity因未绑定lens为inactive，未改策略。[464](../../reference/kernel464/README.md)只把461 lifecycle两次断供与旧图I/O对齐，不推广为本次缺口根因。

[465](../../reference/kernel465/README.md)复用原厂mode2全53写入与516次相同IQ选择，私有LSC几何草稿保留；[466](../../reference/kernel466/README.md)同SX表／MIPI元数据支持mode2 link候选723.2MHz，尚未接入／实机验。mode3两尺寸是4:3缩放，LTM主摄因果仍引用442，未冒认长焦独立四回放。

[461](../../reference/kernel461/HARDWARE-SUMMARY.md)修同步IPA回执重入stop的UAF，原函数ASAN复现／修正版10例通过；保持IPA／旧proxy／原厂配置的两模式各三尺寸周期已实测285消费／286IPE，严格同SOF通过、正式恢复。[463](../../reference/kernel463/README.md)已实际核FULL拓扑／应用FD及303 qbuf／286 dqbuf，跟踪无覆盖。native1080p仍有两处缺口，软件队列零快照提供新线索，未证物理根因；原厂LTM因果按相同调校复用。

[462 r1](../../reference/kernel462/README.md)与[r2](../../reference/kernel462/r2/README.md)冻结；[r3](../../reference/kernel462/r3/README.md)确认旧FD真实寿命缺口，用registered/release延后对象析构，18实际C例、两ASAN反例及单对象通过。需0064＋r2内建mux＋r3组合，未部署；受控解绑须禁止新open/stream，supplier强制解绑／全并发仍待验，无第五节点。

镜头[455寿命修正](../../reference/kernel455/README.md)已编出模块、原C案例通过，所需[456 V4L2 core Image](../../reference/kernel456/README.md)已构建并核ABI，未启动；[454第五单色摄像头](../../reference/kernel454/README.md)已验证原厂表与控制，[458](../../reference/kernel458/CONSTRAINTS-NEXT.md)补齐模式约束并发现初始帧编码差异，真实link_freq／共享资源／单色RAW仍缺。[匹配HAL与ODM配置](../../reference/kernel453/AF-CONFIG-ACQUIRED.md)已只读取回，[460原指令](../../reference/kernel460/README.md)核默认AF覆盖后数值不变，认证／姿态／光学仍未验。后续采集须用[MONOTONIC边界](../../reference/kernel451/CLOCK-NEXT.md)，不能接受睡眠后旧工具的空日志。

| 内容 | 位置 |
| --- | --- |
| 已安装组合、失败报告与回退 | [484 r33/r28实装](../../reference/kernel484/README.md)、[440历史](../../reference/kernel440/README.md)、[软件包配方](../packages/libcamera/README.md)、[配置配方](../packages/samurai-camera-config/README.md) |
| 最新候选与交接 | [489 core](../../reference/kernel489/README.md)、[490 r34/r29候选及回退](../../reference/kernel490/README.md)、[491暂停交接](../../reference/kernel491/HANDOFF.md)；候选未安装 |
| 未闭环历史 | [450统计淘汰修复](../../reference/kernel450/README.md)、[451 proxy](../../reference/kernel451/README.md)、[452 FULL诊断](../../reference/kernel452/README.md)、[453 BU64253](../../reference/kernel453/README.md)、[449生命周期／失败历史](../../reference/kernel449/README.md)、[442 LTM消费因果](../../reference/kernel442/README.md)；按各阶段实测范围解释 |
| 原厂自动调校 | [437主摄](../../reference/kernel437/README.md)、[438广角/长焦](../../reference/kernel438/README.md)、[439前摄](../../reference/kernel439/README.md) |
| 新底层候选／数据边界 | [455 BU64253寿命](../../reference/kernel455/README.md)、[454 OV02A1B](../../reference/kernel454/README.md)、[AF个体分支](../../reference/kernel453/AF-INDIVIDUAL-NEXT.md)、[匹配配置来源](../../reference/kernel453/AF-CONFIG-SOURCE.md)；软件验证，未实机 |
| 原厂模式/DS4与下一轮尺寸 | [426](../../reference/kernel426/README.md)；其它尺寸未绑定时先恢复对应模式 |
| EEPROM、WB/LSC及原厂数学 | [304布局](../../reference/kernel304/README.md)、[328 WB](../../reference/kernel328/README.md)、[原厂分层与来源历史](../../reference/kernel276/OEM-TUNING.md) |
| 尚未完成的完整范围 | [363范围](../../reference/kernel363/REMAINING-CAMERA-SCOPE.md)、[硬件清单](../docs/HARDWARE-STATUS.md#当前功能与待办) |
| 早期桌面/GPU问题与配置 | [240交接](../../reference/kernel240/HANDOFF.md)、[269失败](../../reference/kernel269/README.md)、[desktop副本](snapshot-launcher/org.gnome.Snapshot.desktop)、[D-Bus副本](snapshot-launcher/org.gnome.Snapshot.service) |
| 其它实验与失败原文 | [会话/Reference索引](../../sessions/INDEX.md)；各阶段结论只覆盖当时载荷和测试范围 |

本目录旧[部署锁](deployment-lock.json)只描述其记录阶段；当前组合从检查点取得。原厂参考、个体校准与实际画质分开验收；非零图像、AWB锁定或原厂数学一致不等于完整画质通过。原厂文件、系数和私人照片保持私存。
