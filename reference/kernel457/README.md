# 457：FULL供给窗口细化与现有内核trace审查

本轮只读核对441实际模块所对应的5b0e7a9a…源码、原363嵌入配置和452原始CSV，**没有访问手机、编译或修改驱动**。子任务中断后主线完成缓存复审和本说明。[源码清单](source-inspection.json)保留精确模块／输入SHA，[inspect-source.py](inspect-source.py)先经mounted_build并核共享index不变。完整源码副本和带地址CSV仍私存kernel457／kernel452。

## 真实CSV中的26.988ms窗口

[inspect-gap.py](inspect-gap.py)复用452原解析器，重新验证未覆盖的3634条CSV记录，再按真实request／buffer身份交叉核对。下面时间均相对PixSof166的**用户态回调**，只减mono_ns；未将hardware_ns混入。

| 事件号／事件 | SOF | 相对ms | outstanding FULL |
| --- | ---: | ---: | ---: |
| 2567 PixSof | 166 | 0 | 1 |
| 2584 FullDq | 167 | 57.205 | 0 |
| 2590 PixSof | 168 | 66.446 | 0 |
| 2597 FullQbufBegin | 未知 | 84.193 | 0 |
| 2598 FullQbufResult成功 | 未知 | 84.326 | 1 |
| 2614 FullDq | 169 | 123.755 | 1 |

FullDq167之后26.988ms内没有新QBUF开始，所有保留回调快照outstanding均为0；该区间覆盖PixSof168回调。下一个QBUF耗0.133ms，确为随后FullDq169的同一request／buffer。[细化收据](gap-callback-validation.json)通过；源地址未写入公开结果。

它支持下一步优先检查供给和SOF标记选择，不能直接证明物理SOF瞬间硬件FIFO为空。回调可能晚到，outstanding是成功QBUF减DQ回调；硬件寄存器是否接受地址、DMA／IRQ发生情况仍未测。根因保持未证，不把26.988ms当已证修复触发条件。

## 当前驱动的真实路径

camss-video.c的video_buf_queue进入vfe_queue_buffer_v2；持output_lock，根据输出是否ON、active_num是否小于2选择直接更新地址／reg_update或放入pending。上层QBUF成功不等于每次都立即写硬件。

camss-vfe-17x.c的vfe_isr读取已有IRQ状态，SOF走vfe_isr_sof，复合完成位走vfe_175_comp_done。后者将comp位交vfe_buf_done；按输出comp_group选择vfe_output_done。FULL为主图输出，PD10／统计各自完成，不可因辅助输出完成就推断FULL也完成。

vfe_output_done从buf[0]取ready，按输入SOF标记填写sequence、接入pending／更新地址；无ready则返回NULL。vfe_buf_done离开锁后调用vb2_buffer_done，缺SOF标签为ERROR。vfe_isr_sof为每个输出第一个尚未标记的active buffer赋同一输入序号；完成计数本身不能补出输入身份。后续追踪要分别保留QBUF接收、驱动持有、完成／ERROR、成功DQ及用户回调。

## 可直接复用的事件及限制

原Image363启用TRACING／EVENT_TRACING／TRACEPOINTS／DEBUG_FS；KPROBES和FUNCTION_TRACER关闭。当前CAMSS没有专用tracepoint，不能假定可以动态探任意函数。先用实际已有事件，不新增逐帧printk或MMIO读取。

| 事件 | 实际调用边界 | 能提供的内容／缺口 |
| --- | --- | --- |
| vb2:vb2_qbuf | vb2内部排队，可能在交驱动前 | owner/index/type、计数、timestamp；不是地址提交完成 |
| vb2:vb2_buf_queue | __enqueue_in_driver，调用driver buf_queue之前 | 对应交驱动尝试；不含FULL comp状态 |
| vb2:vb2_buf_done | done状态/计数更新后、唤醒DQ等待者前 | kernel完成到用户DQ的区分；没有minor/sequence字段 |
| vb2:vb2_dqbuf | vb2出队路径 | 与owner/index和相邻V4L2事件关联，不单独当成物理时间 |
| v4l2:v4l2_qbuf/dqbuf | ioctl内部func返回0后、copy_to_user前 | minor/index/sequence/flags，可定位FULL与ERROR；仍可能随后copy_to_user失败 |
| irq:irq_handler_entry/exit | IRQ handler边界 | 实际IRQ名称/编号/耗时；不含VFE FULL comp0或WM状态 |

include/trace/events/v4l2.h另有vb2_v4l2四事件的声明／导出，但固定源码drivers＋include中**没有调用点**。仅有v4l2-ioctl.c两处trace_v4l2_qbuf/dqbuf；声明或available_events出现不保证会发出该事件，不能用空轨迹证明没有完成。

下一轮先按实际video minor、owner/index/type关联FULL队列；不能凭同index把PD10／统计／IPE队列混在一起。通用owned_by_drv_count也不等于硬件FIFO深度。若现有事件仍无法区分完成中丢弃和没有comp0，再设计仅记录已有IRQ局部状态／已有队列字段的默认关闭tracepoint；本轮未准备该补丁或新模块。

## 下一串行窗口

[probe-tracing.py](probe-tracing.py)默认只渲染私有查询，语法和无写调用检查已执行；**未live**。显式--live还须同次可信handoff＋baseline，重新核guard、正式库／模块、taint及当前充电十字段。它只读实际tracefs的available_events／format／clock／instances、video节点及interrupts，不创建挂载、实例或改配置。r6等新充电版本须重新取完整基线，不沿用r5。

查询后才决定控制器：只创建本任务独占命名实例，固定每CPU和总内存上限，选实际可用MONOTONIC时钟；按已确认FULL minor和VFE IRQ过滤，通用vb2按可验证owner关联。保留每CPU覆盖／丢事件统计和缺口前后实际范围。不要用PID过滤排除IRQ上下文，也不要用未证IRQ名称或静态节点号。

消费者继续复用452的默认短段＋首缺口后约2秒正常取消／90秒上限和pidfd身份守卫。内核trace只在本任务窗口启用，终态后先停本实例、读取完整尾窗和统计、核其它实例／全局配置保持，再移除本任务实例。不能停止别人的tracing、读空后清全局buffer或吞掉cleanup失败。实际控制器、运行开销、事件关联和清理尚未验证，未生成可stage载荷。

当前手机窗口由其它会话串行持有，457不访问。下次先取得明确交回，核新boot／充电／正式栈后再做查询。所有原始地址、事件和完整日志私存；原441／452／456源码、产物和调校均未改。
# 后续实读

主线已在新的r6交接窗口只读查询实际8类事件、mono、CPU及video节点，见[probe收据](probe-validation.json)。仅available不证明发射，video0也不证明FULL角色；459实机过滤误选RDI0的纠正与实际尾环分析见[459](../kernel459/HARDWARE-SUMMARY.md)。以下保留最初源码／工具准备结论。

