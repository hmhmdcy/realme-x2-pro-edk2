# 470：长焦1080p实际串行处理超过帧节拍

仅分析467／468已收集原件，无手机、SDK、编译或参数改动。[分析器](analyze-cached.py)重关联四案128张消费与真实FULL DQ；每案排除3张bootstrap，以其余29张成功数学图计算相同范围的墙钟区间，[结果](timing-validation.json)通过。原缺口、负结论和历史失败保持。

| 案例 | tone日志→host返回 | Pair→成功receipt | 前receipt→下一Pair | Pair→下一Pair |
| --- | ---: | ---: | ---: | ---: |
| 467 mode3 720p | 4.128 | 11.982 | 21.970 | 33.988 |
| 467 mode3 1080p | 15.905 | 38.031 | 0.442 | 38.587 |
| 468 mode2 720p | 4.120 | 12.264 | 21.776 | 33.934 |
| 468 mode2 1080p | 15.798 | 38.087 | 0.405 | 38.639 |

单位ms、中位数；相邻图28对，单图29张。1080p的Pair到tone日志中位仅3.436／3.361ms，其后返回尾部仍约15.9／15.8ms，IPE queue到receipt另13.733／14.042ms。实际461源码先等待成功receipt提交数学历史，才解除`ipeActive_`、归还内部FULL、完成应用并尝试下一FULL。1080p下一Pair紧接前receipt，且串行段约38ms，已出现处理积压；720p有约22ms等待。这些是日志边界墙钟，包含IPC、调度和日志；tone日志在数学、参数赋值和hash之后，不能将Pair→tone日志称为纯数学CPU耗时，也不能把返回尾部全部归因序列化。

同一内部FULL index的下一次QBUF，在1080p比自己的receipt晚40.500／40.485ms，却只比下一张receipt晚1.593／1.585ms，且先于下一张GST_IMAGE。这个关联说明供给还经过应用／框架的归还与事件链；不是464中图像拷贝及求均值的直接重现。449实际客户端只抽样约4096个字节位置，代码在GST_IMAGE之后`gst_sample_unref()`，现有日志没有unref、GstMemory最终归还、pool通知及Camera queue的独立时间戳，不能选定某个GStreamer属性或队列为唯一根因。capacity因无lens为inactive，不冒认已有主摄租约已覆盖长焦。

## 三种时间必须分开

441实际匹配源码`camss-vfe.c`（SHA `42a8d6ff…`）在`vfe_output_done()`将`ts`写入FULL buffer timestamp，注释明确是 **completion timestamp**。它不是物理SOF边沿。客户端SOF行又只打印序号，没有打印内核事件携带的时间戳；该行是用户态收到事件后的日志。

| 案例／缺SOF | 相邻FULL完成timestamp跨度 | 相邻DQ墙钟跨度 | 缺SOF日志处最近软件快照 queued/owned |
| --- | ---: | ---: | ---: |
| 467／14 | 66.587 | 66.579 | 0／0 |
| 467／21 | 66.720 | 66.200 | 0／0 |
| 467／28 | 66.689 | 65.943 | 0／0 |
| 468／17 | 33.317 | 29.573 | 1／1 |
| 468／23 | 66.635 | 67.374 | 1／1 |
| 468／31 | 66.704 | 71.086 | 0／0 |

快照取自该日志之前最近一次同owner的vb2事件；JSON同时保留快照年龄。它不是物理FIFO深度或真实SOF时刻。特别468序号16的FULL完成timestamp，晚于SOF17用户态日志25.502ms；因此16→18的DQ窗口和完成窗口均不包住缺SOF17日志。不能把六处都写成同一个66ms窗口／三次空队列。六处缺口均有PD10／统计、没有对应成功FULL DQ，物理原因仍未证明。

## 下一最小增量

优先复用[451一次分配proxy](../kernel451/README.md)，只替换当前旧444 worker proxy，保持461 core、444 IPA6、468 mode2、原厂IQ和同一消费者，做长焦1080p单变量比较。已有协议字节等价和主摄实测可复用；本案仍须验证实际proxy身份、原始成功历史、处理区间和缺口，不能预先称修复。无需因本轮证据改PLL、缓冲数、亲和或数学提交顺序。

若仍需细分供给链，现有461 core已经包含[452有界环](../kernel452/README.md)：新窗口显式启用`LIBCAMERA_CAMSS_FULL_TRACE_DIR`即可取得`PixSof.hardware_ns`、RequestEnter、InternalReturn、RequestComplete和QBUF前后时间，无需新增内核寄存器读写或重编。它可补事件原始时间与回调延迟，但仍不能把软件状态当物理FIFO。只有还需区分返回尾部时，再补worker编码／host解码的墙钟和线程CPU边界；应用归还链则补unref／最终pool归还／Camera queue边界。

完整逐图时间、源代码摘录和探索失败仅存私有kernel470。公开结果不包含原始PID、地址、boot、图像或原厂系数。分析器仅在自己的新目录写派生结果，不改467／468原件。
