# 与摄像头/ISP会话的实际交接

2026-10-24当前：USB IRQ唤醒配置已装机并通过[一次RTC待机恢复](usb-irq-wake-rtc001-result.json)。当前504/USB13f41/97c/f6bef/服务83469/manifest5ef4、boot4e325；真实驻留15.019秒，success+1/fail0，前后12门、USB挂起恢复回调0、原key/NCM自动恢复与SDP500保持，无新fault，alarm/trace清理。原驱动未配置IRQ wake的缺口已补；真实USB插拔唤醒仍待现场，窗口只prepare未启动。前boot的2719完整8帧证据保留，新boot MACv2/p1实例0/0未重查。当前USB两文件逆向0c6a6恢复ebfcb/8c5b7后冷启；更早回退属于不同范围。TCA语义、温界/完整预充再充、FLOAT/APSD与高功率仍未完成。下面旧组合/未加载描述按历史范围读取。

2026-10-24最新：[USB通知修正实机结果](native-pm-notify-r2-result.json)已装入504/ebfcb/94a659并采用。原12门在启动及PM前后通过；RTC单次实际驻留14.874秒，success+1/fail0、无新fault，原key/NCM无需拔插恢复、SDP/native/硬件500mA保持。trace证实挂起内的软件自唤醒消失，通知改在complete发布。物理USB唤醒、温界/完整预充再充和协议/高功率分支仍待验。下文旧未stage、d046和PM失败描述属于此前记录。

**2026-10-24挂起根因已收窄并完成修正候选：** [03实际栈与计数](native-pm-504-wakeup-003-result.json)证实DWC在dpm_suspend内撤销预算，经USB setter的power_supply_changed持有唤醒源；count163/state0xa30001产生进行中事件，随后-16中止。trace5016B、8CPU无丢失/溢出，当前预算与前后12门保持。02仅trace预检把内核1*误当未启用，PM前拒绝且完整清理，原件/旧源码保留；修正后03取得实证。[USB通知候选](../charging-oem-audit-20261023/usb-input-pm-notify-candidate/README.md)通过8组实际C函数及单KO构建，W1/Werror零诊断、48内建导入，16原函数/decoder保持；prepare至complete仅延后软件通知，真实IRQ独立上报唤醒。KO84005/manifest2419与精确d046/34ead逆向两文件包已生成，Image504/4453/bootedd、97c/7848保持；尚未stage/驻留，不称PM修复。下一步当前504新guard/cache绑定冷更新与正常重启，不热卸USB、不刷载体。

2026-10-24 PM001：[原件复核](native-pm-504-smoke-001-result.json)。原27例primitive仅写一次mem，RTC至少余14秒时内核以-EBUSY拒绝；failed_suspend/fail各+1、success0，未实际休眠。原child终态1、自己的alarm已取消；前后12门/500预算、原boot与USB原key保持，无新fault。21原件已完整取回并复核源码与监督链。日志未给具体failed_dev，USB供电通知wakeup仅为待查方向，不称因果或PM恢复通过；不重派001。首嵌入脚本换行错误在本地ast检查及mkdir前拒绝，raw模板修正后实际模板检查过。

2026-10-24当前唯一根会话已完成504/4453/d046/34ead实际stage、收拢、仅logdump写入、新boot12门及fresh adopt；原481/468/四服务/桌面保持，NCM无需拔线自动恢复。无相机消息/唤醒或子代理。后续待机测试独占；新增存储清理只处置可重建废弃项，保留当前构建、原厂资料、个体备份与回退。

2026-10-24根独立续作：postboot双profile设备0e8aa940完成六组/两Linux默认及根审冻结；504正向/502回退各12门，25原函数及collector主体复用，新增同fd cache/stateless依赖与撤销，仍只验证DEVICE/on/active，非PM或USB恢复。旧实机缓存派生模型原件保持；Windows默认fcntl失败保留，Linux过。全程无手机/SSH/USB/实际request/lease/adoption/重启/刷写/SDK，相机继续暂停归档且未消息；最近502/edd/ace2/7cb/97c/7848/18e8保持。下一步当前host/adoption接线，齐备才串行实机。

2026-10-24根独立续作：恢复host/operator bf0adcc5完成六组集成/三默认及根审冻结。原C5、22cf四设备文件/原supervisor/两fd预检复用，显式PRIVATE避免旧函数默认目录；后置probe接原-C/R2审核，六文件安装/new bound→run及七原件context→current logdump-only operator/原worker模型命令通过。动作只恢复ace2、bootedd只读，SSH255不当启动成功。全程无手机/SSH/USB/实际request/lease/收拢/重启/刷写/SDK，相机仍暂停归档且未消息；最近502/edd/ace2/7cb/97c/7848/18e8保持。下一步当前正向/回退的新boot核验/adoption，齐备才串行实机。

2026-10-24根独立续作：冷回退恢复设备检查22cf5980完成六组定向/三默认及根审冻结。旧R8/502/boot目标已换当前三profile/14原件/独立后置probe/cache，15helper/原收拢及RESTART2尾保持；实际6818停充/保护/Full/fault保持，预算未知不提额、cache零新查询，目标仅ace2/bootedd只读。首测试语法拒绝保留后通过。全程无手机/SSH/USB/实际request/lease/重启/刷写/SDK，相机继续暂停归档且未消息。手机最近502/edd/ace2/7cb/97c/7848/18e8不变；下一步恢复host/operator及新boot核验，齐备才串行实机。

2026-10-24根独立续作：当前两文件冷回退连接式监督8902891c完成七组定向/三默认及根审冻结，11原owner函数、regular request fd/同child wait/35秒pending沿用；只读probe接原固定压缩严格密钥接口，新增当前cache/source帧进程观测绑定，真实当前worker模型输出经fetch仍仅runtime_pending。首派生路径匹配失败保留。全程无手机/SSH/USB/实际request/lease/回退/重启/刷写/SDK，相机仍暂停归档且未消息。手机最近502/edd/ace2/7cb/97c/7848/18e8不变；下一步恢复重启/新boot核验，齐备才串行实机。

2026-10-24根独立续作：当前冷回退主机saved-action/原key当前probe/binder已冻结38bd3b78，七组受影响检查与三默认入口通过，首轮两处夹具错误保留后只补测两组；原R2同child审核/七文件过去上下文/实际6818 profile及6ff逆向包复用。没有实际request/lease/SSH/手机/USB/回退/重启/刷写/SDK，相机继续暂停归档且未消息。最近手机502/edd/ace2/7cb/97c/7848/18e8保持；下一步连接式监督/恢复重启和新boot验收，齐备后再串行实机。

2026-10-24根独立续作：当前PM两文件冷回退执行器6818939b已完成三驻留分支、七项定向组合/默认与根审冻结；12原函数/20方法及17原件规则复用。只还原实际6ff包USB7cb/manifest18e8，live/provider/cache/保护/Full/fault保持，不热卸、不AUTO、不写载体；partial保留无重放。尚缺saved-action/当前原key probe/binder/连接式监督/恢复重启和新boot验收。全程没有手机、SSH、USB、实际request/lease/回退、重启/刷写/SDK；相机继续暂停归档，未发消息或唤醒。最近手机502/edd/ace2/7cb/97c/7848/18e8基线不变，齐备后才安排串行实机。

2026-10-24根独立续作：冷回退的留存source审核和WSL路径适配已完成四真实缓存/两stage模型/两薄入口检查及根审冻结。禁止读取全局pointer的实际重审通过；不改指针、不冒认当前健康。新增薄入口沿原C5进程监督与正向门，仅修正规定host绝对路径，首fixture路径及生产拼接失败保留。全部本地child终态0，没有SSH、手机/USB、实际bind/guard/lease/stage/收拢/重启/SDK。相机仍暂停归档，未发消息或唤醒；手机最近502/edd/ace2/7cb/97c/7848/18e8保持。下一步完整冷回退执行器/三分支及新boot验收，齐备再安排串行实机。

2026-10-24根独立续作：当前IRQ/97c启动主机调度已完成六项定向组合、三默认和根审冻结；原R2监督/23主机+10remote函数及supervisor保持，新增预检两fd释放/current export→单logdump operator接通，模型原SSH255仍标未证实启动。没有实际bind/guard/lease/SSH/USB/收拢/重启/刷写/SDK，相机继续暂停归档且未消息。最近手机502/edd/ace2/7cb/97c/7848/18e8保持。完整冷回退和新boot核验仍待接齐；已定位global pointer推进会影响旧forward材料重审，回退须走真实留存原件、不能先要求新postboot全成功。齐备后再约串行实机。

2026-10-24根独立续作：当前IRQ/97c启动设备门和单logdump operator完成离线派生/根审冻结。原硬件收拢/RESTART2尾保持，bootedd只读；八项集成按未变源码复用，补充context发现事务正则缺字并在设备动作前拒绝，修正后四项通过。失败001保留；有效002材料化和本地默认均原child wait0。全程没有SSH、USB访问、手机stage/guard/lease、SDK、重启或刷写，相机继续暂停/归档且未发消息。手机最近基线502/edd/ace2/7cb/97c/7848/18e8保持。完整模块冷回退、主机调度和新boot核验仍待接齐，之后再安排串行实机。

2026-10-24本轮：用户明确不再需要子代理，两个正在运行的子代理已中断；后续不启动或恢复。根会话只接手离线文件，完成当前IRQ/97c/18e8冷stage设备11项与主机六项的根审冻结；没有SSH、运行绑定/租约、手机文件更改、停充、重启或刷写。当前手机仍#502、bootedd/logdumpace2、USB7cb/charger97c/保护7848/manifest18e8；相机481/468及原桌面保持。相机继续暂停/归档，未恢复或发送消息，SDK不占用。待504/4453仅logdump启动/完整回退及新boot验收工具完成，再安排串行现场窗口。

2026-10-24最新窗口：Image504的64MiB载体4453已实际生成，原exec47694/packager579/mcopy803+808/fsck820均终态0，Image f647读回、A823及非Image字节、父输入/mount保持，原source10文件不变；根实际载体薄审通过。单USB2691＋manifest f74a包正向2e1320/回退4575已一次物化并只读audit0，各精确两成员，原R8六其它文件/保护75b/charger/限额/startup500保持。1938载体身份缺绑定由911d实际receipt字段门补齐，原10案例/6函数逐字复用、4新检查及独立物化复核通过。无活builder/工具/observer，无新stage、guard、绑定或设备/SDK/storage操作；手机按最近501记录保持，prepared502与待答现场窗口不变。首实体仍502，后续PM配套须独立新事务和正常重启；完全回退须原USB＋manifest＋502 ace2，不热卸provider。相机仍暂停/归档，桌面原版，未恢复或发送新交接。

2026-10-24当前窗口：DEVICE outcome19新例/16差分与8个私有DWC对象W1/Werror终态0，原284已归还；exit-only gate8新例/限定独审/单gadget.o实际0，固定UDC同步解绑链已审，284亦已归还。连接式回退29新边界＋3 transfer/3默认通过，仍未真实bind/lease/launch。代理本轮零设备/SDK，root仅本机审查/文档，未重复只读手机。手机仍501、最近SDP500/23.5℃/Full保护0快照属上一轮；prepared502不变，现场协助问题待答，无新拔插提示。未链接新Image/改桌面，完整PM abort与ACTIVE恢复未闭合。相机仍按用户暂停，归档线程未恢复，手机/SDK窗口无并行冲突；先验既有502单logdump，不混IRQ/503/新DWC。

本轮最后：[真实同口拔插完成](icon-r8-eud-off-result.json)，原collector14799已absent/terminal，事件monitor正常清理；重接稳定91秒/81样本native/源/硬件500且净充入，用户反馈图标明显更快。fresh末检保护/CC250/CV/原R8与相机notes/taint0保持，后续截图闪电可见。当前无充电观察器、reader或设备worker存活，不追加现场操作；相机仍按用户暂停，未交回。源→Display off/on约3.73/3.08秒不是精确像素计时。

2026-10-24充电续作：EUD-off新boot下500诊断通过并恢复100后，根已一次安装正常startup500请求、执行一次normal start；新host configured/native/源/硬件500、原进程正常退出，R8/相机notes无变化。当前截图有闪电且净充入，实体时延尚待验。相机继续按用户暂停，不交回或唤醒。手机新增检查点见[500正常启动结果](usb500-default-result.json)；Gauge首次新UTC构建的额外叶差异被拒原件保留，随后原复现时间戳阶段已离线通过最小构建/静态ABI，未封装/上机，原Image363保持。

2026-10-24最新：相机本线程用户明确“先暂停相机适配，准备先完成充电适配”；相机会话已暂停并撤回491设备/Git窗口，确认无SSH/USB/PM/SDK/构建存活。手机继续归根充电；静置后失联经一次用户接线恢复，原quiesce终态0/原进程不存在后，已完成一次boot-only4126切换、原密钥新boot与R3全过并采用新guard，R8和相机481/468正式基线通过。未交回或唤醒相机。相机恢复需用户明确恢复以及届时真实boot/endpoint/guard/正式基线，旧“已连接”不可复用。原storage anchor33058由原进程确认explicit_stop，未卸载共享卷；后续OEM最终修正对象仅经明确Ubuntu/root原guard恢复卷后私有编译，零设备/SDK。

用户直接授权双向协调。相机会话为“验证441候选双遍与LTM链路”（01a1659d-52ea-74f1-b09f-f75f32471eee），本会话为“梳理可并行的适配工作”。手机事务与SDK绑定分别交接，不因过去空闲而推定现在可用。

本轮先离线分析和构建；只读窗口核实电芯/保护协议、0x58一次NACK和CDP预算后交还。相机445/446之间再交给充电shadow窗口：首次software-node卸载WARN已告知双方，保存证据并延长窗口；相机确认无跨启动状态后，按367既有静默/EUD退休流程不刷写地恢复一次干净启动，修正版shadow通过才交还。

446、447分别实测并恢复正式440后，充电接普通控制及boot元数据窗口，900/300、500限流、停充和精确回退通过；读回当前boot确认为390，随后交还447。447终态后交充电持久服务/DT窗口：服务启停和回退通过，再只刷单个boot的DWC3引用增量，不刷Image/logdump/rootfs/相机/NV。原密钥保持，实际新boot读回、native100mA额度、自动250mA充电、正式440包/434模块note及四相机休眠/资源/服务/taint0均核对后明确交还448。

当前新guard为/var/lib/samurai/charging-usb-dt/boot-id-private.txt；旧446/447 guard失效。相机已同意把永久samurai-charging和三模块、900/250mA作为新基线保留，不卸载samurai_usb_input。SDK短窗单独交给448构建，充电从未使用该SDK；共享ext4不卸载，公共source354/build只读参考。

448终态恢复后另交充电约5分钟窗口：先只换两充电/保护模块，增加gauge的显式PM设备依赖；native USB模块/boot/guard保持。实际RTC唤醒、15.1689秒s2idle、独立PM trace均通过；充电器先于源/gauge停充挂起，源/gauge先恢复再重新采样充电。回调prepare/complete与正常suspend使用相同事件动词的审计问题仅在缓存修正，没有重复休眠。taint0、相机完整m2m/休眠及四用户进程保持，手机/SDK已明确交给449继续；本会话不再访问手机。

最终manifest为34d46f4c…4d5a7，两更新模块为dca3211e…69063和75b97e0d…783c7，USB模块c77724ba…2e3e不变。相机449已确认采用更新的常驻充电基线。用户选择保持现连接，实物SDP换口/插拔暂缓；以后需要现场条件时仍先协调窗口。

用户在外时授权继续无需现场的工作：449清理完成并明确交还约120秒只读窗口，采用其/var/lib/samurai/k449-adopted/boot-id-private.txt，同原a30启动。一次120.076秒采集13样本全有效/Full、会话不倒退、限值/native100mA保持、taint0/新故障0、完整相机m2m/PM及四用户进程保持。脚本仅在Python进程内执行，无上传/安装/服务控制/PM/SDK操作，结束已明确交还449继续。可选电池属性发现遗漏只在工作站修复和缓存重审，没有再访问手机；已部署三模块和manifest未改变。

用户回家后三次真实插拔完成；现连接实际SDP100，返回原口也未恢复CDP。图标供电关系增量78332c70…5abe曾安装，软件500请求未接受且已自动回100、两份USB启动脚本恢复。此终态明确交给450 r3完成9000帧，450核实该manifest/预算及相机恢复后再次明确交还本会话。

本会话r5只换charger9d9e1cd7…31016，manifest f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf；更新和INHIBIT/AUTO通知短测保持taint0、相机/四用户服务。随后SDP100 RTC待机数据连接未恢复，目前等待用户短按电源确认屏幕；尚未核实设备worker终态，不能交出未知状态。相机与蓝牙会话“适配蓝牙完整功能”（01a16724-4235-7f41-a9c6-4149c2b0bcf1）均已获知只继续离线，不自行SSH/重启/刷写。蓝牙用户的直接协调授权已通过read_thread核实。本线仍持手机恢复窗口，SDK已由相机452明确释放，本线不使用。恢复后先回收PM日志、核实模块/预算和所有worker终态，再明确串行交给蓝牙。

最新恢复与交回：用户确认短按能亮屏，同口拔插10秒后NCM/严格SSH恢复，同原boot。原PM21491已退出，全部trace/dmesg/原始终态取回；raw true因未验15秒计划而无效，实际驻留3396秒，50.468秒准备缺口发生于console_suspend_all范围且在charger回调之前。最新[恢复收据](pm-r5-recovery-result.json)确认manifest/三模块精确、fresh充电/native100、taint0/指定新增fault0/四相机PM+m2m/四服务一致。已明确交回相机会话，并通知蓝牙必须等待相机串行交出，不可自行访问。本线即刻停止SSH，继续独立PC/WSL候选与原件离线审计；不追加整机待机。所有r5模块、USB脚本与boot不变，guard仍k449-adopted；新Image/重启影响ABI/guard时先协调。

本轮后续：相机451/452核恢复后明确交给蓝牙GATT r2。蓝牙会话一度因模型容量中断，本线没有据此假定设备worker结束或自行接管；其恢复取回实际终态、配置及密钥恢复证据后，才明确归还充电。当前手机由本线持有，双方均已确认停止SSH。音频服务在蓝牙基线已是23403/23476，phoc/phosh仍3631/3762；本线按本窗口实际状态比较更新前后一致，不把更早恢复快照PID当永久条件。

r6单次更新和定向INHIBIT/AUTO均通过、worker退出，新manifest944f2d91…4202d、charger fac827cf…89cb6、service61451ffe…55aa4；USB/保护/boot/guard保持、native与双路100mA、taint0、当前相机PM/m2m及四服务一致。已通知相机和蓝牙采用新基线。本线继续最多600秒的独立只读实体图标采集，真实新tick与PID就绪后才提示用户拔插；不改USB、不PM、不使用SDK。待采集终态和当前状态核对后明确交回，现不能因单次更新结束自行抢窗口。

上述collector25830现已真实退出，600秒未观测断源，567连续样本；原件/审计完整取回，D-Bus子进程受控结束、cleanup确认。用户尚未回答本轮提示，已明确通知旧拔插提示暂停、保持连接。独立Windows只读100基线reader96376也自然退出（decoder空端口全零响应拒绝、未arm，无设备trial）。[r6交回核对](r6-handoff-result.json)通过后，手机已明确先交相机457，蓝牙排后，已要求相机恢复终态后直接交给蓝牙并抄本线；本线停止全部SSH/实机操作，继续纯离线候选。SDK保持不占用。

其后用户晚回旧图标卡，确认实际再拔插且仍延迟。本线立即通知双方，不自行SSH。相机459原worker/controller均终态退出、正式恢复通过，外部健康审计因source等待保持false，明确先交本线排查。根3次实际PMIC/status确认FLOAT0x10+native100、current_max ENODATA，硬件REG08=0x0e抑制。独立fresh保护Safety/PF0/error0、标准gauge24.1℃/8.417V/SOC100、taint0；charger telemetry valid0/source_inhibit1/-61仍保留，缓存fault0不是fresh REG14读。蓝牙明确同意按这套安全停充等待基线测试已配对音响，现已由本线明确交蓝牙约10分钟；充电再次停止全部SSH/实机操作，蓝牙结束直接归还本线。

r7源解码修复已独立编译/冻两文件包、未安装。原native provider不能热卸，需蓝牙实际终态后协调新事务加载并正常重启，不能复用旧taint512 recovery目录/旧guard。相机明确无跨启动内存依赖，正式440/434磁盘文件及全部已取回原件需保持；新boot必须以原key和新manifest重新采用，不复用k449旧guard。500诊断候选仍只离线，R6 PIN会拒绝R7，须R7实证后定向迁移。

蓝牙现已明确归还：r3/r4音响worker、捕获及播放器全部终态，peer断开、Powered/默认sink/原keys已恢复，全部post原件回收；出声验收未过与充电窗口无关。充电已接管手机并通知双方保持离线，按已授权计划推进R7两文件stage及同Image正常启动；不重放旧事务、不刷写、不追加PM。相机正式包/模块/四配置需在新boot重新核对，再采用新的boot guard后明确交回。

R7实际stage31466已退出、result=staged，旧provider仍c777、REG08 INHIBIT，备份与新两文件均核对。新独占静置事务31587退出0、所有quiesce/taint0和restart inspect通过；已单次提交EUD退休/RESTART2候选。SSH最后仅收到filesystem_frozen后断开255，主机暂未见EUD/NCM或fresh fastboot身份，因此没有发送fastboot reboot，不能把SSH断开当syscall执行/新boot成功证据。无分区写入，未重复restart/CSR，正在问用户实际屏幕。双方已获知继续离线，本线仍持恢复窗口，原guard未替换。

随后用户确认屏幕fastboot，排除把EPIPE潜在路径归因为本次；同口重插后首次仍无主机设备，用户再次报告已重新连接fastboot后fresh exact serial与msmnile通过，只发一次fastboot reboot。新boot原key、k363 exact版本/rootfs、5638 manifest及7d4e USB loadednote、其余r6两模块/614服务全部通过。五组postboot核对通过，实际CDP1.5A/rawnative100/input900/CC250/25.8C/+98mA，taint0/十类bootfault0，440/434正式文件/四配置/相机idle及四用户服务/BT/SSC/SensorProxy保持。Windows NCM29地址丢失，New-NetIPAddress被权限拒绝，已从真实USB IPv6邻居以原HostKeyAlias严格原key恢复；root helper支持该私有endpoint，大源码用stdin运行。新guard单独创建并采用，旧guard保留。root继续持图标复测窗口、先问用户ready；相机仍离线，蓝牙按其用户指令转纯静态，无需实机排队。此次CDP不能冒称已实体覆盖FLOAT。

用户明确ready后才启动R7 collector6751，fresh两次PID/tick status通过即发新拔插提示。真实断接11.2秒、重接稳定28秒，77样本无gap、20uevent/44D-Bus，cycle_complete、worker absent、D-Bus受控退出且cleanup完整，原件已全取回。用户反馈拔出较快、插回很久不变；源→UPower拔出约2.52秒，重接后记录内无State，当前真实SDP100/净放电，不伪报充电。最新r7-handoff核三notes/manager/newguard、双路100/CC250、26.2℃/瞬时−48mA、fresh保护/error0/taint0，正式相机PM/m2m/core/四PID与postboot一致，64行连续唯一锚点后831新行指定fault0。已明确交回相机461并获其接管确认；本线停止全部SSH/设备，仅离线准备R7 USB500预算诊断，另协调新窗口。

随后相机461 r2两尺寸六次开停、正式恢复与全部进程终态后，明确交本线单次预算窗口。R7 USB500 worker9274、PC reader及父进程均真实退出，500阶段仅addressed/native100，已finally回100并持续合格超过12秒；最终SDP100/CC250、28.5℃/净−11mA、fresh保护/taint0、四服务保持PW8860/WP8882、phoc3571/phosh3688。已明确交回相机并获确认，本线再次停止全部SSH/USB调用。相机更新NEXT归属为其持有，下一设备动作先协调；蓝牙按用户要求纯静态，不排实机窗口。主机683完整sweep无Status5，未证明EUD或功率拒绝；不在相同条件重放500或要求用户继续拔插。

相机确认full282并非刻意卸载、没有活跃build/SDK且允许复用原helper后，本线用storage.mounted_build()正常恢复原卷；仅独立私有O目录构建charger方向温区模块和R8包，SDK未绑定、共享源码/build未写。APSD接口审查同样只读已有源码。当前R8尚未部署，实际manifest仍5638。

其后相机明确无worker/SSH/trace/SDK并交出约5分钟独占窗口，R8只读预检通过后唯一更新worker11892成功且已absent。仅替换charger10ec06fb…6297f及manifest320316c3…c10a1f，23个受影响事务案例和7个launcher PID/终态案例通过。真实旧INHIBIT、新模块fresh INHIBIT与NORMAL恢复、精确原100/250/CV上限、USB/保护note保持；最新29.1℃/age768ms、全部保护/error/latch0、taint0、相机PM/m2m及四PID3571/3688/8860/8882保持。末次瞬时+4mA仅单点。自己的lease已释放，无USB/PM/boot/SDK变更，根已明确交还且相机确认接管准备k467长焦短窗口；本线停止全部SSH/USB/实机，继续离线组件。

新私有采用记录为E:/edk2-samurai-out/charging-management-20261023/r8-adoption-private.json，仍同R7 guard/boot/原key和r7-transport.py/IPv6 endpoint；旧R7 adoption保持历史。新charger loaded-note为f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d，USB/protection两note不变。相机已明确将新validator迁移至R8，不能复用旧R7 owner-return。原件r8-update/fetch-1792749921278700617及postcheck-stdout-private.json已回收；公开r8-update-result/r8-handoff-result仅证明本次加载和NORMAL，不覆盖温界、Full再充、SDP500或图标。

相机467长焦两尺寸消费者终态、正式恢复后，明确交出一次短只读PD/Type-C窗口。根仅选读16个既有控制字节两次，没有整图dump、PD收发/IRQ读取或硬件写；r1生成脚本语法错误、r2可选ADC无数据使记录失败均保留，r3完整原件及[公开结果](pd-controls-r8-result.json)已收回。两次APSD仍SDP，0x1358=0xc0、0x1362=0x18、PD PHY enable/TX/filter/BIST为0；后者不能证明PD合同inactive。末次29.4℃、fresh保护/error0、SDP/native/双路100、CC250/CV原上限、taint0和四服务3571/3688/12628/12634保持，瞬时+3mA只属单点。采样Python已结束，无观察器遗留；手机已明确交回且相机确认持有。充电根及子代理继续纯离线DWC/EUD/PHY/协议工作，不因相机暂时离线而自行访问手机。

其后相机468原厂mode2独立r2完成并恢复正式组合，worker14687 absent、46份原件全收；相机报告fresh R8/三notes/100/250/CV保护健康、fault0/taint0、camera PM/core/m2m idle，PW/WP更新为14912/14915，phoc/phosh3571/3688保持。相机明确停止SSH并交还，根已确认接管，暂仍纯离线准备最小USBIN初始化候选；尚无新的根设备操作，后续以新鲜预检为准。相机继续离线后处理/按文件镜像，Git窗口另行协调。

最小USBIN候选离线构建期间，根确认自468以来没有SSH/设备worker后明确把短窗交相机469。其worker16219退出、原厂长焦mode2固定FULL/参数的PD10四回放完成、正式440/434及传感器文件恢复，fresh外部R8/100/250保护/taint0后明确归还。根接管后只进行[一次有界只读预检](usbin-init-preflight-result.json)：helper absent、1358仍0xc0、R8三notes匹配、实际100/100/100mA与CC250mA/CV整包8.725V、29.7℃/fresh保护/error0/taint0、相机idle和3571/3688/16422/16425均确认。没有load/arm/PMIC写/USB重枚举/PM/SDK。相机继续离线，手机由根持有；469/470文档镜像另给1分钟Git静默窗，不影响设备归属。

后续471同样串行完成并正式恢复，worker17358 absent后明确交还，最新相机报告PW17594/WP17597、phoc3571/phosh3688及R8/保护/caps/taint0保持。根仅完成USBIN执行器35项、独立收尾复审和本机check-local；自471交回以来没有任何SSH/USB/helper加载或写入。用户新回复“稍后再测”后，根已明确将空出的手机窗口交回相机，停止全部实机操作，不启动180秒观察器、不arm、不沿用旧ready。473离线core增量构建的SDK仍由相机capacity_path代理独占；根及充电子代理不用SDK/共享构建/卸载。下一次实物USBIN必须重新串行交接并取得用户新ready。充电冻结叶子的按文件镜像不改相机NAV、Git index或分支。

相机473随后串行完成并明确交回根：worker18715已退出/terminal/passed、旧/新/旧96帧消费/IPE后正式440/434及原sensor恢复，4相机PM suspended/core+m2m idle，trace/userdir不存在、fault0/taint0，52文件190438B原件回收。最新PW18953/WP18956、phoc3571/phosh3688；相机两点外部fresh R8/三notes/保护/error0/100mA SDP/CC250/原CV帽保持。根已确认接管，用户仍稍后，根继续零实机、不发动作卡；SDK已由相机卸载释放，根不占。473独审纯离线；充电先取约30秒61叶子--files镜像窗，无index/NAV/stage/commit/push，结束再交Git给相机。

其后61叶子镜像完成、pre/post clean后交相机34文件/NAV镜像，后者明确终态释放；根再串行完成69个新增离线充电叶子（R8完整源码整合、boot-only EUD候选/独立复审及根复核/入口）镜像，pre/post clean、3个旧镜像备份，无index/NAV/stage/commit/push。根只通过既有storage helper恢复原32GiB卷并git show导出3固定ba61 blob到私有缓存，未写共享source/build、未绑定/卸载SDK。自473归还以来仍零SSH/USB/PM/load/arm/硬件写，无新增设备worker或observer。用户仍稍后，现明确将手机交相机474约5分钟串行窗口，由其先fresh预检；475 capacity_path也独占SDK做离线打包。根及充电子代理再次停止全部实机，不发旧动作卡、不提前启动采集。下一次USBIN须474正式恢复/原件/进程终态交回及用户新ready；这段交接只本机补记，未在释放Git窗后追加镜像。

474随后终态退出，worker20378 absent、63原件回收、正式440/434及原S5K恢复，四相机PM suspended/core+m2m idle，trace/userdir不存在、fault0/taint0，明确交回根且根已接管。四服务为phoc3571/phosh3688/PW20600/WP20603。用户仍稍后；根只执行一次有界CSR只读、一次apk版本及一次EFI/iomem元数据查询，未load/arm/写PMIC/改USB/PM/重启。实际CSR两次0x01010101，最新fresh保护/error0/taint0、100/250/CV原帽、相机及四服务保持。不存在运行的充电observer/helper。普通只读操作仍由根串行持有，摄像头及子代理明确零SSH。

475离线包工作终态后已卸四overlay/释放SDK，无bind；其严格APK事务因r32缓存provider缺口失败，r33未装，不能当作手机基线变化。相机45文件/NAV按文件镜像终态exit0并明确释放Git短窗，index/无关status保持。476仍是离线模板，需要实机时另申请串行窗口；根的R2 BDS私有链接和默认关闭USBIN候选均不占SDK/不写父共享源码/构建，不据此授权刷入。下一次用户USBIN动作仍须新ready、新鲜采集就绪及正式设备交接，不沿用本轮延期前的ready。

根随后完成一次81984字节既有reserved RAM ring只读，2.68秒exit0、原件全回收，零MMIO/硬件写，无helper/observer/worker。读后29.7℃ age926ms、fresh保护/error0/taint0、native/source/input100mA、CC250/CV8.725V、四PM suspended/m2m idle及3571/3688/20600/20603保持。现在明确交相机5–8分钟设备窗口，仅一次k477-target-deps-r1私有simulate（禁脚本/不安装/全局db/world/repo/keys保持）和一次k476-control-delay-r1后正式恢复；相机先fresh预检、回收原件并核所有worker终态再交回。充电根及子代理自交出起停止全部SSH/USB/PM/硬件，仅离线，不因R2已编译而发boot动作。RAM原件位于私有eud-ram-read-1792759858790213272目录。

476随后明确终态交回：worker23019退出，原sensor/434模块/440包及相机PM/core/m2m均恢复，报告PW23240/WP23243、phoc3571/phosh3688与独立两样本fresh R8健康、100mA/caps/fault0/taint0。采集末尾“应无IPE”断言因实际默认IPE作业而失败，原件保留并离线分析，不重采；477首次stage被owner-age480秒门拒绝，发生在target写入/worker/APK调用之前，无重试。根已确认接管，当前没有启动设备操作或观察器，用户仍稍后；相机全员停止SSH，477准备好需新申请短窗，不续用失效owner。充电继续只在电脑上做封装与PM源码工作。

相机随后报告480离线solver已ready并申请新3–4分钟窗口。根自476交回以来零SSH/USB/PM、无worker/helper/observer，现明确交出：owner精确范围[k476-control-delay-r2,k480-target-deps-r1]，scoped仅476r2，后者只fresh只读预检、不启动控制/采集；480仅verify+simulate不安装并保持全局APK清单/db/world/repo/keys。采用新fresh/bind与原480秒门，不续用旧授权；终态/原件/不变清单后再交回。root及充电子代理继续纯离线；上述基线PID仍来自476报告，未冒充根新采样。

480现已正式归还，根已确认接管：worker24107退出，verify/精确七包simulate各exit0，未安装，原全局APK文件名字/字节/owner/mode保持，19原件取回。相机报告外部fresh R8/保护/100/250/CV、四PM/core+m2m idle、正式notes/sensor及23240/23243与3571/3688保持、fault0/taint0；不是根新采样。当前根仍零实机，没有USBIN/helper/observer，继续离线封装和PM候选；用户稍后不变。相机全员停止实机，后续Git镜像另行申请。

用户回家后根接USBIN串行窗。001的60秒arm和002的300秒arm均先于有效现场操作到期：两次helper均零配置写，原observer/control/load终态已回收并关闭；002取到晚于timeout的实物断接，但重接仅23秒、完整settling未通过。002首次close因SSH传输不明保留unknown，取回同实例全部终态后显式qualify，再按其close-expired授权成功收尾，未删unknown或盲重放。相机始终全员零设备，SDK未占。

临时操作窗R2只把helper等待从60改为300秒，host观察上限480秒，独审及受影响测试通过；永久provider候选的原60秒core没有随改。用户再次新ready后，003在新鲜gate许可时发唯一同口电脑数据线提示。真实断开约9.48秒，在off期间单次1358 bit7清除0xc0→0x40并读回，重接观察61.14秒，362样本/cycle_complete，身份/环境/CV/健康保持。用户目测拔出约6秒、插回逾一分钟仍无图标；51重接样本Battery均净Discharging，未发生100→500mA升级，不能据此验收图标。

003原observer27065/start1906002终态absent后，正常零IO commit释放自身引用、rmmod退出/owner释放；最终fetch全部原load/control/observer/unload精确进程均absent。根随后一次只读交回核验：三个事务原进程全absent、helper sysmodule/sysfs/owner均不存在；同a30 boot/原guard/R8 manifest和三notes保持，fresh age272ms/27.9℃/protection1/error0/taint0，SDP/native/input100mA、CC250mA、CV8.725V；四相机PM suspended/core+m2m idle，3571/3688/23240/23243保持。1358当前0x40是唯一硬件基线增量，永久模块/服务/USB描述未改。

原件回收后已明确交相机481/482约10分钟串行窗，执行实际升级→精确降级→再升级及已装默认路径短验；相机483独审/准备与17文件镜像已结束并释放Git窗。根及全部充电子代理自交出起零手机/SSH/USB/PM/SDK，预计时间不自动授权重叠；相机实际终态/恢复/原件及明确归还前继续只做离线工作。新鲜交回私有证据位于charging-management-20261023/usbin003-handoff-private.json，实体结果见[003摘要](usbin-init-r8-003-result.json)。

481已实际终态并明确归还，根已确认接管。worker28188/start2003163及active child均absent，r33/r28升级→r32/r27精确降级→再升级全部exit0、两次forward默认路径14例通过；最终保留441三KO＋468 sensor＋四原厂profile的新r33/r28工作基线，不能再用旧440固定哈希复核。相机交回proof及精确期望仅私有保存在kernel481/return-to-charging-private.json和formal-expected-private.json。外部health-r2两样本确认同boot/guard/R8三notes、真实100/250/CV原帽、四PM/core+m2m idle、taint0/fault0；PW28681/WP28687为新服务，phoc/phosh保持。以上是相机提供的实际证据，不是根重复采集；根自接回后仍零SSH/USB/PM，仅离线准备。相机全员已零设备，484独审只读缓存；下一次boot-only EUD候选如可用，仍先核此新相机基线和真实回退/启动顺序，不沿用早期相机身份或自动重启。

随后根在仍独占手机的前提下完成一次正常 Python 前提只读核对，并实际 prepare `eud-boot-r2-live-001`：仅上传冻结两 worker、481 wrapper 与新私有 guard，原密钥/同 boot、完整 a30/logdump、R8 文件与三 notes、fresh 保护及相机 r33/r28 新基线检查通过。唯一 prepare SSH 真实 rc0；后续同事务只读 fetch 确认仍原 boot、无 quiesce/restart 进程，prepare/fetch 的原 supervisor/SSH 均 absent、rc0。[公开阶段结果](eud-activation-prepare-result.json)仅说明 prepared-only；尚未静默、写 CSR、重启、调用 fastboot 或刷写，owner 保留，不创建新事务绕过它。

相机485–489的独立 SDK 短窗已明确完成并释放，充电未使用/绑定/卸载 SDK。根另明确给相机一次短 Git/NAV 窗口，仅同步其485–489公开文件及两份检查点；充电暂不镜像、双方手机归属不变。下一启动实验须等恢复/验收工具窄修冻结及用户新的现场可用回复，旧 USB ready 不作为本轮按键/接线窗口。

根116项工具/四记录选定镜像随后完成并释放Git；普通WSL用户首个复制前因既有root-owned目录权限失败，原日志/备份与目标未变证据保留，改用既有WSL root在同范围完成，pre/post clean/public equality、index/保护NAV/范围外status保持，无stage/commit/push或全局chown。相机490的17项短镜像也随后明确完成并释放。其491只准备package-only工具，仍全员零设备/SDK；手机prepared-only继续归根，不因490新包就绪自动交出。

本轮根仅两次已终态rc0的同步只读SSH核0x0c/0x14及UPower当前Display，未留观察器/worker，未改模块、配置或现场窗口。后续静置已正净充入且Display charging，见[实物只读结果](gauge-current-steady-readonly-result.json)，不是重新拔插验收。现场可用问题仍待答，未quiesce/CSR/reboot/fastboot/flash；根与代理仅在独立新叶继续DWC协调、PD接口来源和一致Image输入工作，零SDK/共享源码构建变更。


2026-10-24：用户新确认手机在身边后，root独占完成image501-gauge-live-001。相机继续按用户暂停，只另行协调其已完成441–491公开文本提交/非force push的Git/NAV短窗，零相机设备/SDK；其8368d8a9提交未纳入充电workingtree，窗口已明确释放。root新双载体写入/重启终态成功，新#501/参数Y/完整pair/R8/正式481+468/保护/服务/taint0九门通过并新adopt。当前实际CDP1.5A/native500/hardware900及Full保持，未解除保护、未安装Phosh。首次有效期本地拒绝未发restart；后续唯一restart到fastboot，正常菜单Restart bootloader后恢复USB枚举；均保留原件。首次过早init采样/截断传输/03 SDP假设失败保留，04新明确CDP分类全过。原363/4126/ACA是回退，旧guard不能用于现boot。501图标001采集300秒未观测断源，264样本安全Full保持；observer7893及监视器已终态/absent，旧物理提示已撤回，不启动新窗口或复用ready。手机仍归充电，Phosh原版本私有依赖/构建离线继续，下一实物步骤需新鲜采集就绪。

用户随后回“快了，但仍有延迟；两边都有、主要插回”。实际操作时刻未获记录，不把主观改善写成001覆盖；新同步只读核同adopted#501、SDP源/native/硬件500mA、capacity100%、NOW/AVG0/Not charging、fresh保护/Full保持通过。启动时CDP/hw900快照仍保留。当前无采集器/设备mutator，Phosh私有构建继续，旧315依赖精确闭包缺原包的失败如实保留，正在核同源构建输入而非替换手机runtime。

Phosh原版四包已取回并以原钥验签/精确C核对，72个实际文件SHA/mode与回退完全一致；当前只读UPower两LINE_POWER在线、Display fully-charged。独立r3001接电标记仍私有构建，未安装或重启桌面。尝试向原相机线程同步计划时App返回该线程已归档，消息未发送；未自行恢复会话。相机暂停及手机归充电的原有约定继续，零相机/共享SDK操作。

用户随后明确取消新增桌面提示，要求从底层优化。原Phosh两轮owned ninja已正常SIGINT/join，最终PID761及9个原身份全部absent（停止记录SHA1ef86372…66d92），未产APK/GTK测试/安装/桌面重启。根及全部代理已撤销该分支续作，旧Phosh源码/私有中断产物仅存历史；当前仅USB IRQ事件、BQ外供刷新及R8实际时序/保护分析。

仅底层502新内核实际构建通过并冻结（Image085d0306…b25955），只BQ外供通知与版本身份变化；USB IRQ和PHY生命周期也各完成离线定向检查/对象及独审，未接入手机。桌面仍原版，当前无新物理采集或启动窗口；FAT载体/新logdump-only工具离线准备中，手机仍501/97811+7e5。

随后502 FAT ace2及logdump-only工具、postboot/adoption/边沿模板已全部冻结；根只执行一次新prepare，原SSH rc0/硬件写0，仍未quiesce/restart/flash，现场协助问题待回复，无拔插提示或采集器。未来USB IRQ的DT/ko及DT-only boot eddadec3已离线产出，当前BDS/原100其它FFS/尾部保持；它不属于已prepared的502事务，未生成rootfs cohort。原包采证与新PM取证也仅离线实现/验证，不访问设备。相机仍按原约定暂停，其线程最近已归档、同步未送达，未自行恢复；无相机/SDK操作或其它会话设备窗口。


本轮仅离线推进：真实保护ko、USB IRQ＋保护＋manifest三文件包/精确回退、保存文本解析器及DWC start错误局部对象均完成，实际构建handle已wait终态；代理已串行归还原284卷窗口，无SDK或设备操作。root薄审并重读未来两包，未创建现场事务/guard、未上传/停充/重启/刷写，既有prepared502保持。手机仍501及原相机基线，原相机会话仍按用户暂停；现场协助问题尚未答复，未新发拔插提示。


本轮仅原厂资料离线补缺：已从既有F.10 ZIP完成vendor-only解码，镜像905a/1711276032B；原extract91865与Node终态0。只读目录1079及后续七文件子进程全0，129目录/2884路径，inode0空槽失败与窄修均保留；[索引/静态内容结果](../charging-oem-audit-20261023/gauge-2719-vendor-name-index/README.md)不提升2719协议或快充兼容性。没有手机/SSH/PM/SDK/挂载/刷写或新采集提示，prepared502仍为首个实体步骤、现场协助问题仍待答。相机继续按用户暂停，未恢复其已归档线程或占用共享设备窗口，桌面原版。


本轮system离线补查：同F.10 ZIP只解system成员，原79585/Python206860/Node220352均实际终态0；system f7a3/4487905280B，索引59344及606目录子进程全0。五相关文件和内嵌工程镜像只读，APK/DEX、异常电池XML及充电HIDL库静态分析仍未给精确2719协议；[结果与源码](../charging-oem-audit-20261023/gauge-2719-system-oem-check/README.md)。零手机/SSH/PM/SDK/挂载，未恢复相机会话或新开设备窗口；原prepared502、现场待答、桌面原版保持。


另完成回退后启动的最小离线接线：[成功rollback＋后置probe→原owner/原boot-only operator](../charging-session-20261023/usb-irq-protection-rollback-restart-candidate/README.md)，6组原tool6dcd86终态0，五默认入口tool7aaeae的原Popen均wait0；两轮fixture失败保留。只复用已有调度和硬件尾，修WSL路径及真实子入口，限定独审/根静态接线审查完成；原R8磁盘与旧/新驻留notes分开，正常新boot仍待实际验收。无真实身份/guard/request/bind、无手机/SSH/SDK/重启/刷写；原prepared502、现场待答及相机暂停保持。


用户新回复现在在旁，root已取得现场窗；App新快照确认相机仍暂停/前轮终态、未恢复其会话。原502事务完成quiesce28202终态0及取回、inspect/RESTART2、fresh唯一fastboot/msmnile/几何、仅logdump写ace2与reboot-candidate原终态0，当前新#502。boot97811未写且完整读回，R8磁盘/相机载荷未改。首次83秒采集因启动未完失败；187秒服务/R8已live，后续大JSON两次同1703936B中断，native小probe正常后压缩连接超时，原件全保留。当前完整postboot/adopt未过，旧pointer仍501，新guard/采集未创建；新的屏幕检查问题待回复，未要求再次拔插/重启，见[实际阶段记录](image502-activation-progress.json)。


后续连接小查询/ping恢复，未再次重启或拔插；改native原Windows OpenSSH加-C，仅改变传输封套，collector源码/原key/peer保持。postboot-r1-05原child终态0、九门全过，fresh adoption原child也0，新502 guard及pointer已建立，旧501备份完整。原boot97811/logdumpace2、R8/481/468/服务/保护/startup500均过。新采集charging-icon-image502-001（worker8106）单次launch/实际ready后3秒内发10秒同口拔插提示，当前观察原事务；旧屏幕检查已明确不用再操作。原两次1703936B截断、一连接失败与早启动失败全部保留，不当已修USB大传输。相机继续暂停，零IRQ/PM/其它候选安装，见[实际采用结果](image502-activation-result.json)。


本次charging-icon-image502-001到300秒deadline，262样本未记录断源，不能验收图标延迟。已明确撤回旧拔插提示，native原key加-C取回同一原事务；原worker absent/terminal、dbus原child -15且monitor_errors空，cleanup与同boot均确认。原audit离线重审无edge/physical_passed=false，样本/日志/原失败完整保留，见[收尾结果](icon-image502-001-result.json)。当前无观察器/新拔插提示，不重播旧launch；手机保留已adopted502及R8/相机基线，未安装IRQ/flat/PM配套，也未恢复相机会话。


2026-10-24：相机仍按用户暂停（fresh inactive snapshot，未恢复/未向归档线程冒领交接）。真实IRQ stage-live-001与独立activate-live-001完成，boot-only写edd，logdump ace2/原#502保持；十门postboot与fresh IRQ adoption过，原charger/481/468/服务/保护/500预算保持。旧pointer/guards备份保留，后续必须用新activation-adopted guard。一次protection-capture-live-001已终态/取回：0050/52过、0056实包length7报-90，失败原件保留，不重试。新icon pins已绑定，尚无观察器，等待用户准备后再开窗口；旧ready不能复用。完整IRQ撤销须R8三文件＋boot97811及新启动验证，不能只回boot。


IRQ001在用户新鲜准备答复后单次launch、ready确认后提示，用户回“约2至5秒出现”。现已deadline终态并取回：274样本/84 uevent/134 D-Bus，worker absent、监视器正常收尾、同boot。三段短source/ACOK断开各仅1/2/2份off样本，原连续长断源门未过；实际最后ACOK off/on事件相隔约2.205秒，不能据离散样本说用户未拔。两路IRQ计数0→6/4，三次source上线到目标Display Charging约2.1秒，Battery变更与目标D-Bus紧邻，像素未测。用户随后确认连续手动试了几次，三段不当连接抖动；无观察器、无新拔插提示，手机与相机状态未改，后续仅离线核底层观察时序。见[收尾结果](icon-irq-001-result.json)。


随后仅离线补齐：接回250ms/3s短观察源码六组定向检查过（首fixture signedness编译失败保留），root唯一单ko构建exec62616终态0，原prepare779/module2585均wait0，新charger97c16c3d/156800B、note fe15a2fc，54强导入匹配实际Image502，shared/旧ko及源码保持。当前手机仍charger10ec与已采用IRQ/保护，不改manifest、无安装/重启/新采集。另0056 fresh2719显式三字节schema2 profile仅离线11组C/18解析边界通过，不重新查询或重载保护。相机继续暂停、未占SDK；模块增量/精确回退双包现已物化，7项检查过；仅charger与manifest两文件，USB/保护及其它清单字节保持。旧R8更新器绑定旧清单/guard/100mA基线，不直接套用，新的当前IRQ更新/验收/采集绑定仍待补；尚未创建安装事务。


当前IRQ单charger更新设备14组与host六组受影响覆盖完成，原R2 supervisor/transfer复用，仅固定-C；同boot采集profile14新边界和三默认入口完成，原采集/时钟/清理不改。root新bind live001为纯本地实际IRQ adoption审查；原handle63421终态0。随后preflight-e20fd19777f88469-private原SSH rc0，当前健康Full、native/source/输入500/CC250、同boot/载体/原USB保护与已消费MAC保持，eligible=false在任何停充前拒绝。无launch claim、无远端新租约/worker、未热换或重启、未写manifest；旧global adoption pointer仍5fca。fresh App快照确认相机线程继续按用户暂停/归档，未唤醒相机或占SDK。现场准备问题待答，未新开观察器或提示拔插。下一步仅真实健康Managed窗口更新，再从实际成功原件绑定runtime overlay，不把Full预检晋升成更新成功。

用户现已在现场：先正常断开约10秒接回，同一live001的launch新鲜预检进入Managed，原host session71657终态0；原worker/supervisor更新及取回均成功，charger97c/manifest18e8实装，原USB7cb/保护7848同实例、已消费MAC、500预算、相机481/468与桌面保持。完整成功原件fetch-b6c23bb0619b2bce审核通过，runtime绑定session90285终态0，旧boot pointer仍5fca。新charging-icon-irq-reattach-001唯一launch session16773终态0、worker18900，原status连续ready且roundtrip门通过后立即提示一次同口拔插；用户反馈约2–5秒，保持连接等原记录终态，未判定提速成功。无刷写/重启/保护新查询/相机操作。离线另已完成0056显式profile独立ko f6bef8a2，原prepare/module均wait0、284归还，默认关闭且未加载，不混本次更新。

reattach001已cycle_complete，原fetch session52961终态0、原件hash取回及原audit离线重审一致。134样本完整数字周期通过，source→Display2.103秒、Battery事件→Display约2ms，未证短观察提速；结束正常Full/输入500、fault与stop0。worker18900 absent/terminal，monitor_errors空、dbus -15正常收尾，未进行额外stop/清理动作；无新观察器或新操作提示。根继续离线定位，不要求用户再重复拔插。另独立SOC温区Full源候选11组91断言已完成，未构建/上机或混入97c。

本轮根仅做一次实际tracepoint只读可用性查询：原strict-C child wait0、同boot/18e8/三notes前后相同、taint0；13选定event及4 live函数可用，没有mount、trace instance、trace启用或总线访问。用户询问继续图标优化是否必要，根判断该专项先收敛，转USB恢复/预算与Full保护；备用trace worker尚未实施即停止，不再安排图标专项拔插。独立SOC温区Full单ko824e1f38已构建，原session79319及prepare792/module2603 wait0，54强导入/配置一致，284归还；未装/未改97c或18e8，未做新payload/host/cohort。相机继续按用户暂停、无设备/SDK冲突。

图标收敛后转USB PM：根一次当前18e8只读依赖快照strict-C wait0，三notes/guard/boot前后保持、taint0，legacy controller on/active且五supplier缺input；无bus/PM/控制写。基于实装7cb C合并原stateless PM link，保留a17/16原函数与IRQ，8新probe/IRQ组合过；唯一单koexec30261及原prepare832/module2647均wait0，d046/92144B、47强导入全502、W1/Werror零诊断，284已归还。另一代理只读复核现成504/f647与4453载体可保留bootedd/IRQ DT13d3；当前两文件cohort原exec9d758d、build243104/audit237908 wait0，manifest34ead、forwardf116、精确7cb/18e8回退6ff66已实际物化，原五函数检查复用、新三绑定过。根另直接读取两实际包/ELF/清单逆向字节，限定复核通过。全程无SDK/相机/新Image构建，手机仍原502/7cb/97c/7848/18e8，未stage/重启/刷写或请求PM。独立cold stage设备源码/小组合检查正在准备，未创建真实request/lease；新PM启动和NCM恢复未验收，旧r5失败保留。
