# 459 r2：实际内核 trace 的共同尾段审计

[离线检查](inspect-runtime-trace.py)和[脱敏收据](runtime-trace-validation.json)已通过。它们只读取实际收集的459 trace／state／逐CPU统计、配对452 CSV及保留源码；没有SSH、SDK、编译或重跑相机，也未改冻结7文件、452旧审计或主线报告。原始trace、owner、buffer指针、完整启动身份和关联明细只留私有kernel459。

本审计证明约18.158351秒共同完整尾段内的FULL软件交付关联。**本次90秒窗口未复现缺口，不能据此定位原缺口根因、宣布长期无丢帧或全程trace无丢事件。**2738消费／2739物理IPE与原始图像回执由主线独立审计；整体窗口及后来USB拔插／充电收尾边界见[主线实机小结](HARDWARE-SUMMARY.md)，不由本trace收据覆盖。

## 实际覆盖与生命周期

核对原trace SHA、6083193字节完整EOF和8份stats SHA／长度；逐CPU entries之和与trace头39131保留事件相等，entries＋overrun之和与63647写入相等。文本中实际只有以下6种事件；启用的两种v4l2事件均为零条。

| 事件 | 保留条数 |
| --- | ---: |
| vb2_qbuf | 7251 |
| vb2_buf_queue | 7251 |
| vb2_buf_done | 4691 |
| vb2_dqbuf | 7242 |
| irq_handler_entry／exit | 各6348 |
| v4l2_qbuf／dqbuf | 各0 |

| CPU | entries | overrun |
| --- | ---: | ---: |
| 0 | 14956 | 21240 |
| 1／2／3 | 各0 | 各0 |
| 4 | 4488 | 0 |
| 5 | 9986 | 3276 |
| 6 | 8180 | 0 |
| 7 | 1521 | 0 |

合计覆盖24516条。每CPU commit overrun、dropped events、read events为零，分别不代表overrun为零。不同CPU保留起点不同，整个导出文件不能当作同一连续全窗。

配对CSV有39340总事件、8192保留、31148覆盖，正常页尾与记录编号连续，clock-errors／q-underflows均为零。本审计取CSV保留起点、所有发生overrun的CPU最早保留事件之后以及共同结束边界的交集，得到18.158350932秒；该区间已越过所有CPU的覆盖边缘。未用早期只剩部分CPU的trace反推事件缺失。

实例时钟确为mono，在线CPU集合保持不变；CSV使用同源MONOTONIC。trace文本只显示微秒精度，下面的trace时间比较按这个精度处理。state、controller-live2和收集result的重叠字段一致；实例完成清理、controller worker已退出，只余原display／radio。global、display、radio的**选定控制字段**在start／stop-read／cleanup逐项相同；这不声称其内部trace内容不变，也不覆盖后来USB状态。实际实例名与固定示例token的偏差已由主线小结保留，本检查没有把它重写成随机token。

## 为什么不能使用本次零V4L2事件诊断FULL

457缓存 `drivers/media/v4l2-core/v4l2-ioctl.c`、vb2 core和两份trace事件头，与Image363原提交 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`逐字相等。v4l2-ioctl约3485行的trace调用位于video_usercopy成功返回分支；约3147行的dev_debug开关在另一个函数中只管ioctl打印，不包围这些trace调用。因此没有找到以debug gate解释零事件的源码依据。

实际selection与实例配置均过滤minor0。匹配本次441模块SHA的源码中，RDI0的line id为0，PIX的line id为3，注册名按line编号生成 `msm_vfe0_video<i>` 并从对应source pad链接；配对用户态从PIX相邻NV12节点选择image_。现场probe明确列出 `msm_vfe0_video0`为81:0、`msm_vfe0_video3`为81:3。**本次minor0过滤目标是RDI0，没有覆盖PIX/FULL。**该目标错误足以解释为什么本次记录不能提供FULL的v4l2事件证据；不能据available_events、enable=1或源码调用点声称minor3已实际发射。

下一窗口应从当次媒体拓扑和应用实际打开FD重新确认FULL角色及dev minor，再生成新selection并验证事件确实出现。此处未改冻结helper、旧selection、现场配置或既有回执，也不把节点号3当作跨启动通用值。

## 独立于minor过滤的FULL owner关联

vb2事件没有minor，bytesused也不能唯一识别FULL。本次FULL与M2M输出都是相同尺寸，而且M2M复制输入timestamp；546条成功FullDq中，545条仅按timestamp都会得到两个owner候选。

实际采用三层交叉约束：

1. 按原 `v4l2_buffer_set_timestamp` 与用户态转换路径，将vb2 payload timestamp截到微秒后，精确匹配CSV hardware_ns；没有把hardware_ns减去mono_ns。
2. FULL的内核dq必须先于imageReady开头记录的FullDq回调。对微秒文本精度留出边界后，546条均只剩一个候选，且归于同一个owner。复制timestamp的M2M输出dq发生在该FullDq之后。
3. 545组CSV FullQbufBegin／成功Result区间内，各找到唯一同owner qbuf及buf_queue；由此建立四个用户buffer与四个vb2 index的一对一稳定映射，再核对全部546条dq的index。没有凭相邻index、事件总数或bytesused选owner。

全部546条成功FULL dq均有同owner、同index、同原始payload timestamp的唯一done，形成 `done → dq → FullDq回调`；SOF连续。共同区间总计545条qbuf、545条buf_queue、547条done、546条dq，其中多出的1条done在StopBegin之后，不属于上述成功链；vb2 trace没有state字段，不能把停流收尾事件当成新增成功图或缺口证据。

| 时间差 | 中位数 | p95 | 最大值 |
| --- | ---: | ---: | ---: |
| vb2 done → vb2 dq | 39µs | 300µs | 1623µs |
| vb2 dq → FullDq回调 | 10.846µs | 13.485µs | 29.013µs |

这些是本次共同尾段的软件事件／回调延迟，含trace微秒显示误差；不是物理SOF、DMA接受或FIFO耗尽时间。

## 计数能说明什么

下面仅统计StopBegin之前的FULL事件快照：

| 事件 | queued_count | owned_by_drv_count |
| --- | --- | --- |
| qbuf | 2—3 | 1—2 |
| buf_queue | 2—3 | 2—3 |
| buf_done | 2—3 | 1—2 |
| dqbuf | 1—2 | 1—2 |

这些事件快照没有零值；它们没有测量任意时刻的连续最低值。源码在qbuf加入vb2队列后增加queued_count，dq时减少；buf_queue在调用驱动前增加owned_by_drv_count，done时减少。因此queued_count包含尚未DQ的完成buffer，driver-owned包含尚未完成的驱动持有buffer；两者都不是VFE硬件FIFO深度，也不证明SOF瞬间一定有可接受buffer。

本次可确认保留尾段的成功FULL交付链及软件队列计数，没有在缺口现场观测到DMA／驱动不交付或SOF瞬间断供。后续诊断先修正trace选择与覆盖计划，再等待有界复现；不能由这次未复现将原问题归因或关闭。

复核命令仅访问缓存，WSL／ext4源码读取前先执行449 mounted_build守卫：

```text
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel459/inspect-runtime-trace.py' --all
```

输入指纹、原363源码对等、实际事件数、CPU覆盖、关联数量、选定控制保持和明确限制均在脱敏收据；完整匹配链留私有 `kernel459/runtime-pairing-private.json`。
