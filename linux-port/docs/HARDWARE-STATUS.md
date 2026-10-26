# RMX1931 Linux 硬件状态与未完成项目

2026-10-25充电离线交接：[完整接手单](../../reference/charging-management-20261023/charging-adaptation-handoff-20261025.md)。额度消费者38例/单KO、ADC5单位8例、PD/APSD 3708断言/156故障点、5V合同退出34生产函数与6对象W1均通过离线检查；完整probe未整合，高压采用未就绪，均未部署。506长测最近累计8643/36000秒、31%、26.2℃、AUTO/Good、fault0，继续占用手机。用户报告EUD tty打开失败；只读复查确认节点/getty/reader未就绪，无当前日志，不改桌面。

2026-10-24历史：USB IRQ唤醒配置已装机并通过[一次RTC待机恢复](../../reference/charging-management-20261023/usb-irq-wake-rtc001-result.json)。当时504/USB13f41/97c/f6bef/服务83469/manifest5ef4、boot4e325；真实驻留15.019秒，success+1/fail0，前后12门、USB挂起恢复回调0、原key/NCM自动恢复与SDP500保持，无新fault，alarm/trace清理。原驱动未配置IRQ wake的缺口已补；真实USB插拔唤醒仍待现场，窗口只prepare未启动。前boot的2719完整8帧证据保留，新boot MACv2/p1实例0/0未重查。该组合USB两文件逆向0c6a6恢复ebfcb/8c5b7后冷启；更早回退属于不同范围。下面旧组合/未加载描述按历史范围读取。

2026-10-25充电最新：[508合测与回退通过](../../reference/charging-oem-audit-20261023/tcpm-usb-budget-candidate/phone-trial-r2-result.json)：默认Rp预算500、软件共同0→500/原key恢复、实际关机取消释放锁。已自动回正式506 boot82d6，两载体/原充电文件/三note/PD双0核验。[预充03原1299条复核通过](../../reference/charging-management-20261023/precharge-live506-r3-recovered-result.json)。[真实计时观察已启动](../../reference/charging-management-20261023/timeout-live506-start-result.json)，初期587→885与实耗相符，低SOC零实验负载；36000秒到期/AUTO锁存尚未验收。物理USB唤醒、温界、完整PD/APSD共存、高功率等仍待完成。

用途：按功能查询已证明能力与缺口。整理日期：2026-10-23；最后部署见[检查点](../../NEXT-SESSION.md)，操作与验证范围见[当前规则](../../WORKING-BOUNDARIES.md)和[适配工作流](PORTING-WORKFLOW.md)。按本轮功能读对应行，无需每轮通读或回归全部硬件。历史部署、帧数与过程从[会话索引](../../sessions/INDEX.md)定位，各阶段原文与失败证据保留。

**149已复现的A640 CCU故障修复保持；240新增Snapshot默认Vulkan负载的GPU fault，需独立继续定位。** 147修复旧式GLES地址对齐，149修复Vulkan自动VM_BIND地址对齐。149完成185次像素读回零差异、36次Settings面板打开及PM、稀疏重绑定、旧地址重放、Vulkan/GLES并发验收。151同启动六次被动观察中无新增fault，taint0，桌面保持。150无Mesa补丁的降级候选未部署；它的验证不能混入149系统驱动的验收。

211新增相机GPU ISP退出时的`__arm_lpae_unmap`告警，保存日志可见349条、taint512；它不属于此前CCU像素读回验收。212默认CPU ISP跨启动取流没有新增告警，最终taint/fault0；GPU路径仍未修复。这个结论限定此前已复现故障和已测负载。所有Vulkan扩展、长时间压力及跨启动GPU回归仍需验收；显示交接白屏/花屏及已测开关屏已通过本轮验收，冷启动、休眠和长期显示稳定性仍开放。普通Mesa包更新可能覆盖本地修复，旧rootfs132镜像不含该库更新。

## 当前功能与待办

“未完成”包括仍有真实缺陷、功能尚未接入，以及仅做过部分验收；不能将这三类都写成完全不能用。

| 功能组 | 已证明的能力 | 尚未修复或验收 |
| --- | --- | --- |
| GPU | 149已复现GLES/Vulkan CCU修复及原像素回归保持；240停止故障Snapshot后及CPU mmap两轮新增fault0/taint0 | 240 Snapshot默认Vulkan新增GPUfault480/VK_ERROR_DEVICE_LOST，CPU回退未修GPU根因。211 GPU ISP退出IOMMU WARN另案保留；Mesa可复现包/rootfs、完整扩展和长稳待完成 |
| 原生显示 | 用户实屏确认EDK2之后无白屏/花屏，黑屏等待后显示命令行；反馈后新boot显示关键计数0；此前165的DPMS/首帧门控/稳态软件验收通过，身份与测量所属启动见[检查点](../../NEXT-SESSION.md) | 黑屏等待时长未测；冷启动、休眠、更长期稳定性开放。164首启音频WARN及157重启原因仍未知 |
| 音频 | 171人工双组滴声；183识别离线传输并清理WCD流，活跃双工合成crash原客户端恢复、2旧FD EIO、18项0，匹配左右相关0.9119/0.9312。两次s2idle实际45.33/87.04秒、success2/fail0、PM callbacks全err0；醒后原生/桌面左右通过。1473秒taint0、20项全boot0，PCM关、功放23/23与22/22静音、16控件恢复、五consumer各1/两map/一MCLK | 耳机/耳麦/按钮、实际watchdog、跨启动/更长可靠性和音质/瞬态/保护开放，用户暂无耳机。新发现181活跃STOP −107/ASoC3及旧178/180失败、183首轮脚本mute假设错误均保留，不改成通过 |
| 电池与充电 | 508短测默认Rp500、软件0→500及关机取消通过，已回506/5c8d/b29e，boot82d6原件/三note/PD双0重核。USB161b/chargerbef4/保护f6bef/服务83469/manifest8b402。预充1299条、phase1→连续phase2/正净流及负载收尾通过。506两RTC、旧回满/停充计时及[基础容量查询](../../reference/charging-management-20261023/gauge-basic-capacity506-result.json)保留 | 真实36000秒观察运行中，最近只读累计8643秒；手机归该长测。PM后新连接/FLOAT/APSD、物理USB唤醒、2719/TCA语义、温界、低电到Full/恒流精度、高功率/快充与长稳待验。离线候选与后续整合顺序见[充电交接](../../reference/charging-management-20261023/charging-adaptation-handoff-20261025.md)。旧逆向按组合。[当前进度](../../reference/charging-management-20261023/PROGRESS.md)、[完整要求](../../reference/charging-management-20261023/ADAPTATION-REQUIREMENTS.md) |
| 摄像头 | [484](../../reference/kernel484/README.md)实际r33/r28升级→r32/r27精确回退→再升级通过，保留441三KO＋468 sensor/四原厂profile；3 native APK exit0。14默认/usr用例：四摄Gst256张640、RAW-only24、dual12，268IPE=242math+26bootstrap，RAW-only零IPE；有效签名native、UID/maps/lease/回执及最终repo/world/属性核对，外部健康过、fault0/taint0。441/442主摄两尺寸、469长焦720及474组合1080同帧PD10/LTM实证复用。479 mode2九步首变化/平台均SOF+2，与原delay2/2一致 | 相机按用户要求暂停。[489/490候选与491交接](../../reference/kernel491/HANDOFF.md)：r34/r29仅离线SDK/签名/依赖及工具复核通过，未上机。原厂系数/数学保持；bootstrap单遍，新工具无硬件pass计数；不代表光学/长期验收。441整轮统计积压失败、476错误零IPE断言及工具失败保留，见484/478。绝对crop/LSC/AWB/AF、录像/热功耗、多摄/第五及长期共享lease等仍待；[完整范围](../../reference/kernel363/REMAINING-CAMERA-SCOPE.md) |
| 其它传感器 | 204第二boot自动真实readiness及三个DSP/SensorProxy三Has通过，首轮文件服务就绪失败清理offline仍保留；200新boot三项Has与标准Claim/Release通过，早期门控后SLPI running；187 A.11实际三轴204/202/197及五种CLI通过；230真正树内2abde新启动taint0，实测保活1→2→1、五流67/44/9/10/1与活动Wayland用户Claim；189 FastRPC freezer等待修复与自动服务已部署，连续三轮驻留45.2至45.3秒、success3/fail0/RTC3，醒后四种CLI与原daemon身份保持；三轮后真实active Wayland UID10000 Claim/Release通过 | 188原PM崩溃保留；普通信号重试/freezer竞态、共享池stop/start/reclaim−22及SSR仍未解决。269板级安装矩阵及桌面重新发现传感器后，用户确认整屏自动旋转正常；首次整机启动顺序、3D安装/精度及更广运动回归仍待验。亮暗响应与绝对精度、接近日常、跨boot/冷启动/长稳开放；平放undefined/被动lux0至8不等于这些验收 |
| 蜂窝通话与数据 | MPSS、QRTR/QMI、ModemManager/IPA基础接入；207两次普通启动modem running，原厂MCFG目录自动复制且mdtime可读；PDC活动平台/软件存在、无pending、1平台/25软件列表通过；用户确认未插SIM，当前Power1、failed/原因2与条件一致 | 269保存到一次modem watchdog并伴随整机意外重启，原因和与Snapshot的关联未明。mcfg.tmp仍零字节，整体配置初始化与真实SIM注册/数据/通话/SMS/UIM仍待验；221再次只读得到两槽no-atr/absent/active，与191相同，该历史结果不作为插卡故障证据，真实业务待有卡；电源策略/SSR/冷启/休眠开放 |
| GNSS定位 | [260](../../reference/kernel260/README.md) 普通桌面GNSS-only室外300秒280次更新，其中262次严格校验、时间戳新鲜且随更新变化，默认LOW、无额外HIGH客户端；GPS去重最多9颗TRACK/46.7dB-Hz，自动上线/LOW_POWER回收与设置恢复。[258](../../reference/kernel258/README.md) 原生287份SATELLITE坐标/286秒、去重12颗TRACK/44.4dB-Hz/PGA+2；原厂256去重10颗/45.5dB-Hz/PGA+2。GeoClue10项/电源14项回归及实机四轮开停通过 | 旧采集器拒绝Accuracy=0，18次余下更新未分类，不能直接计丢星或实测精度；本轮PGA未观测。259在OFFLINE下失败不能作ONLINE对照。完整5MiB连续内存/SCM provider、室内PGA/RF根因、冷启/PM/长稳/绝对精度仍开放。位置/启动/辅助未单变量控制，初始化未证明相同 |
| 指纹 | 尚无功能验收 | 本机传感器/SPI/供电、安全环境及用户态认证链 |
| NFC | NCI控制器初始化、上电查询、关闭和重复通过 | RF读卡/标签、时钟请求及eSE业务，尚无真实读卡验收 |
| 振动 | AW8697驱动与电气检查通过 | 物理振动和桌面反馈未确认；按当前任务安排验证 |
| 蓝牙 | 234实际RTS模型三变体16/2、16/0、16/2及H4回放8例通过；暂时诊断取得2个完整phase5回包/UART对应/1301事件无丢失，未复现错误。扫描因预上电属性Not Powered未完成，已恢复原185模块/config/helper/keys/787文件、最终健康0；裸RTS模型不满足真实锁契约，未部署功能补丁。[234](../../reference/kernel234/README.md)。205两次普通启动/8轮上下电/4次重注册未复现phase5，206已恢复原185模块/helper/BlueZ并核对keys；这不是phase5修复。204 RX wake/sleep已部署；首轮前9/45.14秒RTC PM后13、错误增量0，第二boot启动重组0，外部BT事件唤醒未验；首轮phase5仍1。200新boot startup及8秒只扫描发现10设备、退出恢复、重组增量0；185功率脉冲前导NUL及短写/flow修复保持；当时原扫描错误1/候选0、3模式响应及开启状态s2idle/延后扫描通过；189三个传感器PM窗内重组增量0、密钥保持 | 189旧boot出现phase5/3.2Mbps/chunk13/partial0/firstff重组1，区别于旧phase2前导00，需继续修复。配对/连接/音频、冷启动及长稳未验收，按当前任务安排；原Wi-Fi组合失败保留 |
| Wi-Fi | 200新boot自动connected，早期管理端点超时保留；2.4/5GHz通信已有回归；189三轮传感器PM的第1/3轮观察约5.33/0.53秒关联5180，最终5180，未手工重绑驱动 | 第2轮35秒窗内仍未关联，之后又执行第3轮PM，不能称第2轮自行恢复；185立即醒后2秒检查失败仍保留。冷启动、完整休眠通信恢复及长稳开放 |
| 普通USB与OTG | 200新boot新peer/原严格公钥SSH/SCP、约6MB归档及逐成员核对通过；USB 2.0 Type-C；历史NCM/SSH/SCP与EUD共存；203大SCP停顿后严格原密钥Wi-Fi同boot取得完整候选，最终USB/Wi-Fi小命令响应，无reset/unbind/reboot | 190 USB归档尾部中断、双向IPv6探测不通，单次gadget重绑后恢复无正向证据；Windows网卡复位拒绝访问。213再次1MiB分块截断、后续USB小SSH超时，原密钥Wi-Fi两次同boot可达后也无法完成归档/最终健康复查，未盲目复位；214重新发现同地址USB邻居后严格密钥连回同启动，64KiB完成213全部227成员和214全部167成员归档核对，当前连接恢复；根因和大传输稳定性仍未证明修复；NCM稳定性、OTG/角色切换/冷启/PM及EUD接收/退出路径待验收；USB3不是本机目标 |
| 触摸 | 用户确认可解锁、操作应用，原生驱动工作 | 边缘/方向/多触点与休眠后恢复、长稳 |

已有基础还包括UFS访问、CPU调频表、PMIC温度与按键/EUD。CPU高频压力、UFS持续负载、整机功耗、冷启动及系统休眠唤醒仍需跨功能验收；不能以驱动注册或短窗口健康代替日用完成。

USB规格更正：用户指出此前误列USB3；[X2 Pro规格](https://www.gsmarena.com/realme_x2_pro-9904.php)标注USB Type-C 2.0。[厂商规格](https://www.realme.com/in/realme-x2-pro/specs)只标注Type-C接口，没有声明USB3；SoC具备更高速度控制器不代表整机接口支持该速度。

## 下一阶段顺序

按当前用户目标和检查点选择下一功能；先复用原厂提取物与公开仓库实现，缺项再测量，不以所有功能完成为单项迭代的前置条件。显示交接白屏/花屏与已测开关屏已有验收证据；音频发声/拾音、停止和所测短时s2idle恢复也已通过。后续补音频SSR/重复长时PM、耳机和音质，同时推进充电控制保护、完整传感器、实体摄像头、蜂窝业务与GNSS冷启/PM/长稳；GNSS原生258及桌面260室外定位已通过。指纹、NFC读卡和外围设备功能保持待办。Wi-Fi/USB独立休眠告警保留，和触摸一起补稳定性；蓝牙继续区分已验收的扫描与尚未验收的连接/音频，整机冷启动和长期可靠性仍需验证。

参考证据：[显示140至145](../../sessions/145-dsi-deployment-and-session-closeout.md)、[SLIMbus139](../../sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)、[DMIC104](../../sessions/104-native-digital-microphones-and-first-boot-radio-failure.md)、[充电132](../../sessions/132-persistent-mp2650-real-boot-and-complete-rootfs.md)、[充电138](../../sessions/138-readonly-charger-recharge-threshold.md)、[实体camera前的TPG126](../../sessions/126-tpg-dma-guards-full-rootfs-and-real-deployment.md)、[传感器112](../../sessions/112-startup-sensor-registry-and-reboot.md)、[Wi-Fi128](../../sessions/128-wcn3990-pairwise-key-delete-and-5ghz.md)、[蓝牙130](../../sessions/130-standard-bluez-discovery-and-startup-integration.md)。

阶段151以前的完整状态记录已经移入[历史快照](../../archive/HARDWARE-STATUS-through150-2026-10-13.md)，不再把旧136 GPU故障或145设备状态写作当前待办。
