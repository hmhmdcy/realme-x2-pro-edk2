# 474：组合原生／隔离1080p通过，长焦LTM实际消费已补齐

2026-10-23，新r1复用473 core `a21fcedd…`、451一次分配proxy `35526054…`、444 IPA6／签名、468原厂长焦mode2 sensor／profile及441模块。没有新增构建。原生与隔离普通GST消费者各32帧，然后以隔离SOF12保存的固定FULL／最终参数做四次PD10回放。[独立缓存审计](inspect-combined.py)及[实际结果](hardware-validation.json)通过；候选未永久安装。

| 实际路径 | 消费／live IPE | 成功数学＋bootstrap | 原始回执／失败 | 消费SOF缺口 |
| --- | ---: | ---: | ---: | --- |
| native，1920×1080 | 32／32 | 30＋2 | 32／0 | 无 |
| isolated，1920×1080 | 32／32 | 30＋2 | 32／0 | 无 |

合计64消费＝64 live IPE＝60成功数学＋4bootstrap；另4次回放，共68次物理IPE。64条原始回执未过滤、无重复或负值，没有停止未决或未消费的成功图。每张FULL／PD10、GTM bank、WB revision、成功数学历史和LSC上下文通过；实读sensor均为4208×2368，保持原厂近16:9模式，未冒认精确等比crop或光学验收。AWB locked帧仍为0。

## 原生身份、容量租约和FULL链

原生段从真实`/proc/.../environ`确认force-isolation变量缺省；未用字符串`0`强迫路径。活动IPA统计PID与应用PID相同，IPA模块及组合core均在该进程映射中。隔离段实际worker的exe SHA为`35526054…`，PID与应用不同，force-isolation为`1`。两个路径分别核实UID10000／CapEff0、组合core文件哈希、IPA映射和实际FULL字符FD；没有把原生未执行的proxy冒认为已执行。

两段Manager均从允许CPU0—7动态选出4—7；现场capacity分别为0—3=294、4—6=837、7=1024，selected恰为高于允许集合最小值的CPU，实际during task mask一致。原生FULL QBUF发生于CPU4／5／6／7，DQ同样均在该集合；隔离QBUF／DQ均在CPU4／6。各自停止均为同TID的status0、reason restored、active0／users0，原mask与selected对应；恢复证明采用未改448 helper的syscall读回，没有外部poststop `/proc` 探针，也不外推其它IPA线程或worker的CPU。

动态媒体图／角色、真实FD、有界环和内核事件共同关联70次FULL QBUF／64次成功DQ，64消费全部匹配，未有额外成功FULL。两个环各512条，页尾完整，零覆盖、clock error／计数下溢均0；六个停止取消回调不计成功FULL。八CPU内核trace的overrun／commit-overrun／drop均0，实例已清理，其它所选trace控制保持。

## 长焦1080p独立LTM因果

保存点为隔离epoch1／SOF12／token13／revision11；trace中的FULL／PD10序号、最终成功IPE queue与receipt均匹配。回放输入逐字节等于原保存副本：FULL 3,110,400B，PD10 261,120B，最终参数6,008B。只按真实→黑→白→同一真实改变PD10，FULL和参数保持。

检查器独立构造480×270、stride1920的黑／白PD10，改变135行×240组的有效八字节数据，其余padding保留；重新计算四次完整输入和输出hash，与真实客户端日志一致。四次IPE均成功，前三次完整NV12输出互异；两次真实输入输出的全部3,110,400字节相等。

真实回放与实际GST消费SOF12的约4096位置采样hash一致；没有保存完整消费图进行逐字节比较。真实重复回放之间则是完整字节比较。四份scratch均为261168＋16B，CRC相同、changed_bytes全部0；不能据此声称scratch写入。LTM实际消费结论来自固定FULL／参数、仅改变PD10后的完整输出差异及真实重复一致性。

该结果补齐此前469仅覆盖720p的长焦LTM消费因果；主摄两尺寸442证据按原范围保留。它没有额外证明画质、AWB锁定、LSC光学、AF或模式2曝光／增益的物理延迟。

## 时间观察与首次检查器失败

原始历史显示两段GTM从SOF2已ready，因此实际均为2张bootstrap和30张成功数学图。首轮缓存检查沿用471的固定3／29性能切片，在该断言失败；失败记录和修前检查器保留于私有kernel474。只将474的统计改为按实际成功历史分类，完整原始回执审计保持，没有重放硬件或补造数据。

下表ms为中位／p95，使用每段全部30张消费数学图；相邻指标为29对。FULL完成timestamp与内核SOF事件原timestamp分别保留，没有把DQ墙钟当物理SOF。

| 区间 | native | isolated |
| --- | ---: | ---: |
| Pair→成功receipt | 11.589／11.660 | 13.259／15.304 |
| host dispatch | 0.792／0.811 | 2.218／2.454 |
| tone日志→host返回日志 | 0.058／0.059 | 1.430／1.665 |
| IPE queue→imageProcessed | 10.137／10.170 | 10.167／10.683 |

完成timestamp短段消费fps约30.014／30.011。隔离段还执行了一次固定输入保存I/O，全部样本保留；两段也有不同的IPA执行方式，不据此给出纯proxy或capacity的单变量提速比例。它们是组合功能与该短段节拍证据，不代表长期无缺口、功耗／热或其它摄像头的新验收。

worker实际退出，原sensor文件／note、正式440／434库／模块／包、camera PM及服务恢复。非空内核日志与外部两份fresh健康审计通过，fault／taint为0，本窗口R8、SDP100mA／CC250及原电压上限保持。手机已明确交回充电，后续仅离线处理。本轮63份原件、11,306,790B归档私存kernel474，SHA `fa55df0c76d3b07f011f55ef9fa3ba85e7968d306e0618754b65b51382ea7ae7`。完整图像、地址时间、原厂参数和个体资料不公开。
