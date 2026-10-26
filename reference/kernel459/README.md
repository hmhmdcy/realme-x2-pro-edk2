# 459：独占内核 trace 实例生命周期 helper

**后续主线已执行一次有界实机窗口：**见[实机小结](HARDWARE-SUMMARY.md)与[原始回执审计](camera-r2-validation.json)。以下“未实机”描述初始helper子任务的边界；不能覆盖后续实际结果及USB拔插后的失败收尾。helper冻结文件保持原SHA。

本轮仅准备并宿主验证 [trace-instance.py](trace-instance.py)。导入没有文件操作，CLI 默认渲染计划，显式 `--execute` 才会执行本机文件接口；没有 SSH、挂载、手机进程控制、SDK、编译或候选部署。它只管一个新建 `k459-*` 实例，完整相机事务、可信交接、载荷身份、GST watchdog、取消和正式恢复仍由主线 runner 负责。实际 tracefs 尚未执行，宿主模拟通过不等于内核接口或开销已实机通过。

## 输入与稳定 API

`Plan(probe_bytes, selection_bytes, extra_bytes)` 纯校验输入；`Session(plan, files, evidence_dir)` 使用可注入文件接口。三入口独立：`start()`、`stop_read()`、`cleanup()`。`RealFiles()` 构造也不操作文件。CLI 参数为 `--probe`、`--selection`、`--extra`、`--evidence-dir`，`--action start|stop-read|cleanup`；省略 `--execute` 时三种 action 均只渲染，不读写 tracefs。

`probe_bytes` 是主线实际取得的457 `trace-capabilities-private.json`，`extra_bytes` 是实际只读补充 `trace-extra-private.json`。两份原件均只在私有457目录；selection 必须用 SHA256 绑定这两份原件。不得把过期探针当作新 handoff。外层 runner 在同次已授权窗口重新核启动／充电／正式栈，并保证 helper 操作期间实例名独占。

selection 字段如下。`instance` 使用本次新名称，`ownership_token` 使用本次新32位小写十六进制随机值；测试私有 `selection-private.json` 的固定 token／host-review 名称仅供宿主模型，不能充当已批准的运行事务。

```json
{
  "schema": "samurai-k459-trace-selection-v1",
  "probe_sha256": "实际probe文件SHA256",
  "extra_sha256": "实际extra文件SHA256",
  "tracefs": "/sys/kernel/tracing",
  "clock": "mono",
  "instance": "k459-本轮新名称",
  "ownership_token": "本轮新32位小写十六进制值",
  "full_video_node": "video0",
  "full_minor": 0,
  "vfe_irq": 225,
  "vfe_irq_action": "acb3000.camss_msm_vfe0"
}
```

上例 node/minor/IRQ/action 来自本次实际探针，不是通用默认值。helper 验证其存在于该探针，执行前再读实际节点 dev/name、IRQ/action、格式原文与 CPU 集；不枚举猜测节点。下一启动／拓扑变化后须重新选取。

`evidence_dir` 必须是绝对规范路径，末级名与 instance 相同，位于 `/sys`、`/proc`、`/dev` 之外；其父目录须已存在、由执行用户拥有且不可被组／其它用户写入。`start()` 创建新的0700证据目录，拒绝已有实例或证据目录、路径穿越／软链接。所有原始 owner、地址、boot ID、完整 trace、统计、probe和selection只存私有证据目录。helper 不输出原始 trace 到 stdout。

## 内存和时钟边界

[容量源码证明](capacity-source-validation.json)对应5b0固定源码，相关 trace.c／trace_snapshot.c／ring_buffer.c 与原Image363提交逐字相等；原363为4KiB页。新实例 `mkdir` 会先按 `trace_buf_size` 分配，默认每CPU1441792字节，即8CPU请求11264KiB。不能用 global 当前 `7 (expanded: 1408)` 的7KiB推断新实例默认尺寸。

主线本次补读在线0—7、MemAvailable 5782428KiB，expanded值与源码默认和cmdline解析相符。helper 执行前重新核 MemAvailable≥524288KiB、cmdline原文未变、expanded默认一致，并用实际 possible CPU 数在创建前计算上限。允许创建主ring不超过16384KiB，创建后立即核实际报告容量，再请求每CPU512KiB，稳态主ring报告总量必须≤8192KiB。CPU超限或不足以证明默认尺寸时拒绝，不改global以改变新实例默认。

内核按数据页容量上取整，写512可能报告513KiB；helper允许 `[512,516)` KiB的单CPU报告值，总上限仍严格核对，分别保留请求值、初始报告值及最终配置。8CPU请求总4096KiB，宿主舍入模型报告4104KiB；这不是实际 tracefs 读回。16／8MiB指主trace ring容量，不是内核分配器RSS峰值；创建另有最小snapshot页及对象／页元数据。helper不启用或扩容snapshot，512MiB可用内存门槛为余量。未声称整个创建过程≤8MiB。

只对新实例选择 `[mono]`；不改global的 `[local]`。trace记录时间按MONOTONIC与452 `mono_ns`关联；payload timestamp的语义和精度另查，不能把回调时间当物理SOF／FIFO接受时刻。

## 三阶段行为

`start()` 在实际 tracefs 精确挂载点、新实例不存在、事件格式与探针逐字匹配、实际CPU／节点／IRQ吻合后创建。记录启动身份、实例设备／inode／所有者及私有token。先关闭本实例记录，配置 nop／mono／overwrite／在线CPU mask，清空本实例初始trace及PID过滤，再仅启用以下8事件：

- `vb2:vb2_qbuf`、`vb2_buf_queue`、`vb2_buf_done`、`vb2_dqbuf`：过滤 `type == 9`。这会保留其它捕获队列，后续必须通过 owner/index 和 V4L2 minor 的邻接关系识别FULL，不能只比index。
- `v4l2:v4l2_qbuf/dqbuf`：过滤选定FULL minor，保留 sequence／ERROR 边界。
- `irq:irq_handler_entry/exit`：过滤实际VFE0 IRQ。

不使用当前固定源码没有调用点的 `vb2_v4l2_*`；不启用PID过滤来排除IRQ上下文。验证没有其它事件开启，保存全部所管配置后才开启记录。只读留存global及其它实例的部分控制快照，不改变global／display／radio，不读取或清空它们的trace。

`stop_read()` 重新核token、plan、boot、实例身份和完整所管配置。先停本实例并核0，再从非消费型 `trace` 完整读到EOF、读完每个possible CPU的stats；全部句柄关闭后才允许后续删除。文本导出流式进行，上限128MiB；超限／中途错误保留私有部分文件和停止的实例，收据记失败。重试使用新编号文件，不覆盖部分证据。原始每CPU stats完整保存；overrun／commit overrun／dropped／实际覆盖窗须由主线审计，不能把“完整读到EOF”当“未丢事件”。覆盖窗口或CPU热插拔不满足时，不据空事件声称没有完成。

`cleanup()` 仅接受成功完整捕获，重新核本实例已停、身份和全部所管配置未漂移，才 `rmdir` 本实例；不递归删除证据目录，不删除其它实例。记录global／其它实例选定控制快照差异；外部变化会留痕，不由helper回写。删除失败会抛出并保存 `cleanup_failed`，可在相同身份和配置下重试，不吞错误。

新实例部分配置失败时，仅回滚本次刚创建且身份仍相符的实例；先停，保存失败配置，再删除。回滚失败同样保存并抛出，不能当作清理成功。已有实例、身份更换、配置漂移时拒绝盲目接管；配置漂移可能让本实例仍在记录，主线必须明确处理失败，不得忽略异常后继续释放手机。

## 宿主验证与冻结

运行 `python3 -B reference/kernel459/check-helper.py`，仅使用实际457探针原件作离线输入和内存中的tracefs模型。[24例收据](helper-validation.json)覆盖正常三阶段、global记录开／local时钟与display／radio不变、目录碰撞、部分start回滚、回滚失败、部分导出／独立重试、配置漂移、inode更换、cleanup失败／重试、错误selection／路径、CPU／内存／cmdline拒绝、导入无I/O、默认CLI不访问tracefs。模型不模拟内核分配失败概率、真实ftrace时间戳、调度开销、IRQ身份关联或清理内核引用。

[render-validation.json](render-validation.json)只证明计划渲染。helper／测试／两份收据已冻结供主线集成，README和容量来源补充不改变API。未运行实际tracefs、未形成新的缺口根因或修复结论；441／452／456及共享source354、SDK、现驻模块／原厂调校均未修改。
