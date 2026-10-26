# 247：启动期MEMSHARE真实请求与OEM配置差异

2026-10-17。保留Linux，未刷Android、boot或新内核；完成一次普通Linux重启，当前**247启动/boot235/Image183**。用户补充：手机未拆机、装机完整，最后一次Android正常定位时间未知；接收位置仍为室内开窗窗边。这些条件不证明天线损坏，也没有Android正常接收的同机基线。

**首次捕获modem启动期的MEMSHARE请求：`0x24`、client=1、proc=0。找到对应OEM源码中的5 MiB初始配置，但尚未证明它导致零CNR。** 定位仍不可用，goal保持active。

## 从运行期零请求推进到真实启动请求

245只在modem已运行后发布服务52，113秒无请求；246提前建立的是DIAG端点。本轮临时OpenRC项在`samurai-radio`之前发布MEMSHARE52/v1/i1，独立第二个socket查namespace确认本服务实例/端口，并启动独立接收线程；它不受DIAG的VERSION等待或D-Bus调用阻塞。

发布后的dmesg尚无`Booting fw image ... /modem.mdt`，结束时存在一次，因此证明早于**本轮Linux首次启动modem**，不声称早于SBL或整机上电。服务存在和独立回读均早于收到请求。[启动报文核验](inspect-boot-request-validation.json)、[观察器报文回归](memshare-wire-validation.json)

| 实际收到的请求 | 结果 |
| --- | --- |
| QMI request `0x24`，总21字节、payload14字节 | TLV1为u32 client=1；TLV0x10为u32 proc=0 |
| 请求到达时间 | 观察器创建后约8453 ms；不是modem启动后8453 ms |
| 当前观察器应答 | FAILURE/INVALID_ID，即result1/error41；没有地址字段 |
| 启动及两轮搜星期间其它请求 | GPS client0请求0，alloc `0x22`请求0，free请求0 |
| 416.82秒观察结束 | 1个请求、1个应答；79个raw record包含namespace通知，不能称79次分配请求 |

此前观察器只实现GPS client0大小查询，其初始大小按板源为0；分配申请会返回NO_MEMORY。**本轮观察器对client1的应答不等价于OEM服务，不能用“没有GPS分配请求”排除服务间依赖。** 原始request已按7字节QMI头和完整TLV逐字核验；记录应答发送成功不等于modem采用或后续功能启用。

## 已确认的源码差异与尚未复现的路径

锁定的19781板源`sm8150.dtsi` SHA256 `dfbb2407…`包含三个modem客户端；OEM MEMSHARE实现按已注册client/proc返回`init_size`。源码来自[realme Android R内核](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/tree/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/soc/qcom/memshare)。[逐项核对](oem-query-difference-validation.json)

| client | 初始大小 | allocate-boot-time |
| --- | ---: | --- |
| 0，源码枚举GPS | 0 | 有 |
| 1，本次实际查询 | 5242880（5 MiB） | 有 |
| 2 | 0 | 无 |

对已注册client1/proc0，OEM查询路径应返回SUCCESS及5242880。该源码路径还会在probe时为非零保证客户端实际分配连续内存，并将该区域从HLOS转交MSS_MSA读写；**仅回复大小没有复现这些动作**。板源及实现说明预期行为，没有证明Android实际运行DT或该配置与本轮零CNR的因果关系；不将client1查询直接叫做GPS申请。

完成两轮搜星并关闭首次启动端点后，另建大小查询候选，按0/1/2客户端分别回复0/5242880/0；分配仍明确失败，不提供地址。发布和回读成功，30.08秒内无重新查询，因此没有执行额外搜星。候选不能算已被modem采用，更不能算5 MiB已提供或定位修复。[候选回归](configured-query-wire-validation.json)、[实际重发公告结果](poll-configured-query-validation.json)

本轮两次服务实例的物理分配、物理地址返回、SCM所有权变更均0。下一步可先在启动前验证完整客户端查询行为；若推进真实provider，必须持有自有连续内存、核实际申请和SCM权限，且在modem可能DMA时保留所有权。不能搬用其它SoC的固定物理地址；运行期重新公告无请求，也不替代启动期试验。

## RF、时钟与零C/No复核

保持同一组DIAG socket跨两轮90秒，先确认本次watch已运行、时间准备完成且完成计数大于0；第一轮MM PowerState1，第二轮标准SetPowerState(3) online，之后回到1。两个VERSION均55字节、两个DIAG_ID；没有新增control17。共623个QRTR datagram，含1240份实际日志，解帧/长度错误0。[最终采集](poll-firstboot-validation.json)

| 日志 | 首轮 | online新增 |
| --- | ---: | ---: |
| Clock 0x1478，body174/前导3 | 93 | 92 |
| PRX 0x147e，body722/前导5 | 91 | 91 |
| Spectrum 0x1635，body331/前导2 | 77 | 77 |
| GPS/GLO/Gal测量，各自 | 90 | 89 |
| Config 0x1516 | 3 | 0 |
| IMD 0x1596 | 90 | 89 |

首轮624份、online新增616份；online快照先验证并剔除首轮387322字节完整前缀，未重复累计。[首轮](baseline-off-preview-validation.json)、[online增量](comparison-online-preview-validation.json)

沿用锁定MobileInsight v0头、count和stride严格解码，不在未知RF长包上猜C/No偏移：

| 接收指标 | 首轮 | online |
| --- | ---: | ---: |
| QMI有效SNR字段，全部0/SEARCH | 768 | 3912 |
| 缺卫星列表事件，不计零 | 60 | 2 |
| GPS原始C/No字段，全部0 | 377 | 1392 |
| GLO原始C/No字段，全部0 | 7 | 522 |
| Galileo原始C/No字段，全部0 | 无记录 | 288 |
| 正C/No、TRACK、有效定位 | 0 | 0 |

合计2586个实际原始C/No字段全0。GPS/GLO ObsState原值1、MeasStat字节11062000；online Galileo为246条0/00002000和42条1/11062000，仍全零，未把状态位变化称为卫星捕获。GPS周数2440；`ClkFreqUnc`原始浮点值再次从1500变为94。两轮为顺序A/B，不是A/B/A；没有未验证的单位或物理XO锁定结论。[首轮严格解码](baseline-off-satellite-validation.json)、[online严格解码](comparison-online-satellite-validation.json)

原始零值再次确认问题已在modem测量中存在。PRX722/Clock174完整字段仍未验证；246的ADC经验对应和谱算术结构不证明LNA电压、接线或干扰强度。本轮未改RF GPIO、regulator、时钟寄存器、NV或校准。

## 其它手机Linux移植的可用经验

本轮继续使用Exa Search技能：三条有效查询请求15项结果，另一次缺少连接器必填参数的调用未执行查询；相关网页已去重筛选并读取两份一手资料。未找到可直接套用本机的SM8150 LNA接线修复。

[postmarketOS合并记录](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/2039)明确将MEMSHARE驱动列为多数MSM8916的GPS依赖，实测成功包括Motorola harpia/osprey、Samsung a2015/serranovelte、LG m216及小米wt88047。[开发者补丁](https://lists.openwall.net/linux-kernel/2021/03/19/1292)解释了请求物理连续内存及保证分配，并指出部分固件需要特定地址。该经验支持检查本机服务，不能证明SM8150同样需要GPS 2 MiB，也不能照搬其reserved-memory布局。原[测试PR](https://github.com/msm8916-mainline/linux/pull/158)中的部分ASUS机型当时仍未验证定位，不能把收到NMEA或无dmesg错误当作GPS成功。

## 当前身份与收尾

当前guard **`/var/lib/samurai/k247-runtime/boot-id-private.txt`**；246及更早guard失效。运输[host.py](host.py)，私有USB端点在`E:/edk2-samurai-out/kernel247`；原严格SSH密钥保留。预重启脚本使用的是旧246 guard，不可重放。[新boot核对](observe-nextboot-validation.json)

重启前核当前guard、Image183、F2FS根sda16、34个modem固件部署哈希与原NV源哈希；先停消费者、解绑ath10k，再停DSP和显示，保留相机providers。一次普通RESTART请求已在主机预记，USB断开后只观察，未重发，随后确认不同boot ID。没有进入Android或bootloader。[前置核对](pre-reboot-health-validation.json)、[停流](poll-quiesce-validation.json)

采集及候选worker均退出，两轮Stop/release/close通过；mask清零/实时模式释放已发送，socket关闭并撤回MEMSHARE，临时hook及stale started项移除，本地DIAG/52服务0。没有mask原位图getter/撤销ACK，不称逐字恢复原mask。[最终健康](final-health-validation.json)

MM PowerState1、DMS读回offline、锁MT、standalone、location0/Signalsfalse/rate30；watch运行且空闲、timepreparedtrue/dataworker0。只证明MM枚举回到1，不声称DMS等于本次首轮未查询的初始值。三个DSP和Wi-Fi正常，本次boot WARN/Oops/GPU/DSP fatal0、taint0，原NV源哈希保持；其它外设沿用240验收，本轮不是全机验收。

53成员完整原生归档及两份各12成员活动快照，逐成员大小/SHA核验；原始DIAG/NMEA/坐标/标识和完整状态只保存在工作区外。[完整归档](evidence-export-validation.json)、[首轮快照](baseline-off-snapshot-validation.json)、[online快照](comparison-online-snapshot-validation.json)

后续优先补齐启动期client1的真实配置/内存服务对照，同时继续依据确切字段和板级证据排查RF/LNA、时钟。当前没有正C/No、TRACK或真实fix，不能称根因已定位或GPS已修复。
