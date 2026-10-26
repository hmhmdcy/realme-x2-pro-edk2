# 473：processed IPE 的 Manager 容量租约已实际比较

2026-10-23，独立新r1完成旧core→473新core→旧core，每段长焦mode2／1080p各32帧。新core `a21fcedd…`仅扩大现有Manager租约获取条件；三段固定旧proxy `c7887708…`、444 IPA6／签名、468 sensor／profile、441模块及449客户端。没有结合451新proxy，也没有改原厂数学、PLL或缓冲数。候选未永久安装。

[缓存审计器](inspect-capacity-comparison.py)与[实际结果](hardware-validation.json)复用471完整严格审计、452有界FULL环和实际CPU事件解析。统计、CPU／mask、原始失败回执和终态均已核对；本分析没有重新访问手机或重放事务。

## 实际租约与执行位置

B的唯一实际pipeline TID与live `/proc` Manager task匹配，Tgid及start ticks由现场采集器前后核对。获取前允许CPU0—7；本轮fresh capacity为CPU0—3=294、CPU4—6=837、CPU7=1024，动态选择高于允许集合最小值的CPU4—7。live task的`Cpus_allowed_list`与该selected集合相同。该结果来自运行时值，不是硬编码选核或借用448历史分组。

| 段 | 租约 | FULL QBUF实际CPU | FULL DQBUF实际CPU | 停止结果 |
| --- | --- | --- | --- | --- |
| A1旧 | inactive，允许0—7 | 0—3共32次，4上3次 | 0—3共27次，4上6次 | inactive |
| B新 | active，选择4—7 | 4上23次，6上12次 | 4上21次，6上12次 | 同TID restored |
| A2旧 | inactive，允许0—7 | 0—3共35次 | 0—3共32次，6上1次 | inactive |

B的35次QBUF／33次DQ事件均落在实际selected集合内。正常停止日志为status0、reason restored、active0／users0，original和selected均与开始／during见证一致；未改448 helper只有在syscall恢复后读回原mask相同时才返回该reason。本轮恢复证明采用这个原helper读回及日志，没有外部poststop `/proc` 采样。

租约只明确作用于Manager。隔离worker在Camera start获取租约之前已创建；本轮没有显式修改其mask，也没有采集worker CPU／频率，不能由Manager的CPU分布外推worker驻留。表中CPU也是FULL ioctl事件点，不代表整帧CPU驻留时间。

## 三段图像与原始回执

| 段 | 消费／物理IPE | 成功数学＋bootstrap | 原始回执／其中失败 | 成功FULL DQ／未进入IPE或消费 | 消费SOF缺口 |
| --- | ---: | ---: | ---: | ---: | --- |
| A1旧 | 32／32 | 29＋3 | 33／1 | 33／1 | 13、22、30 |
| B新 | 32／32 | 29＋3 | 33／1 | 33／1 | 无 |
| A2旧 | 32／32 | 29＋3 | 33／1 | 33／1 | 14、21、29 |

合计96消费＝96物理IPE＝87成功数学＋9bootstrap。99条原始回执全部保留，无重复或过滤；每段各有一条正常stop之后的未入队失败观察，分别为A1 SOF35、B SOF32、A2 SOF36。它们已有数学prepare、没有IPE queue，由各自历史`discarded=1`核对，不计入96消费／96IPE。两段旧core各另有4条停止未决观察，历史`aborted=4`保留；B为0。不能写成所有原始回执均成功。

逐图同SOF FULL／PD10、GTM bank、WB revision、成功数学历史及96张LSC上下文通过。三段实际core文件SHA和映射路径、固定旧proxy真实/proc exe SHA、隔离IPA与FULL FD、UID10000／CapEff0均核实。105次FULL QBUF／99次成功DQ唯一关联有界环、v4l2及vb2；额外3张FULL没有进入IPE／消费。三个环分别556／528／557条，完整页尾、零覆盖、clock error／计数下溢均0；八CPU内核跟踪overrun／commit-overrun／drop均0，专属实例已清理。

## 同一统计范围的处理时间

单位ms，数值为“中位／p95”。每段使用全部29张已消费数学图，相邻／再排队指标使用28对；完整最小／最大值见JSON。bootstrap和未消费的停止prepare不进入这些性能样本，但原始回执审计仍覆盖它们。

| 区间 | A1旧 | B新 | A2旧 |
| --- | ---: | ---: | ---: |
| Pair→成功receipt | 38.272／41.169 | 29.403／30.650 | 38.389／39.794 |
| host返回→IPE queue记录 | 5.070／5.675 | 0.519／0.545 | 4.818／5.796 |
| IPE queue→imageProcessed | 13.905／16.833 | 10.644／11.981 | 13.670／17.164 |
| tone日志→host返回日志 | 15.880／16.920 | 14.535／14.740 | 15.945／17.104 |
| 内部FULL归还→下一RequestEnter | 40.255／48.433 | 33.121／41.568 | 40.237／46.176 |
| 下一QBUF调用 | 0.377／0.410 | 0.124／0.186 | 0.378／0.393 |

本轮前后旧段的主要中位接近，B串行Pair→receipt中位较两侧分别缩短8.869／8.986ms，29张数学样本该区间最大32.554ms；两侧旧段中位仍约38.3ms。B短段没有消费SOF缺口，完成timestamp消费约30.011fps，旧段约27.370／27.368fps。结合实际mask及CPU事件，本轮比较支持扩大Manager租约改善该长焦processed IPE路径的处理和供给节拍。

这些是墙钟边界，含调度、IPC、日志以及完成事件回调。尤其IPE queue→imageProcessed不是纯硬件执行时间；没有据此推断ISP硬件变快。旧proxy的tone返回尾部仍约14.5ms，没有结合451快编码，也没有worker CPU计量。该短A/B/A不能给出稳定功耗／热收益、永久无缺口或所有摄像头的吞吐结论。

## 缺口时间和适用范围

两段旧core的6处缺SOF都有PD10／统计、没有成功FULL DQ。以452环的原始内核SOF事件timestamp定位，当时最近FULL软件queued／owned均0；快照年龄4.812—8.170ms，下一软件QBUF在事件后0.722—11.352ms。用户回调时仍有1—2个空闲内部FULL及1—2张等待处理图，IPE active。这里已经区分原始事件时间、用户回调、完成timestamp与DQ墙钟；事件时钟仍是内核IRQ时间，软件快照仍不是物理FIFO／bank状态，不写成物理断供根因已证明。

本轮验收覆盖长焦mode2、1920×1080、隔离IPA、固定旧proxy及各独立Manager进程的正常start／stop。三段相继开流，未验证同一Manager的重复配置／重开。已有lens路径获取／释放位置及helper字节保持，当前无lens的processed路径新增租约已实测；不把它扩大成多摄并发、所有启动失败、非隔离或RAW-only的实机新验收。主摄原路径、长焦720p LTM因果等旧证据按各自范围保留；长焦1080p独立LTM扰动因果、光学／AF、录像及长期目标继续推进。

worker实际退出，原sensor文件／note、正式440／434栈、PM及服务恢复，非空内核日志与外部fresh健康审计通过，fault／taint为0；本窗口R8与100mA／CC250／原电压上限保持。手机已明确交回充电，相机仅做本地后处理。52份原件及190438字节归档私存在kernel473，归档SHA `a3fa69991b1c2b5eb0674db9d46a18cdbaba477a6e56caf6c071ad292e388bb6`；完整日志、地址时间与原厂／个体数据不公开。
