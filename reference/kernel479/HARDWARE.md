# 479：476 mode2 控制阶跃独立缓存审计

476 r1 整轮仍为 `passed=false`：测量 body 最后要求零 IPE，而实际有 **240 次 IPE queue、240 次成功回执和内核 request 1…240 的完成记录**。恢复后的正式模块计数归零，不能据此抹掉候选运行期间的 IPE。479 的 `audit_passed=true` 仅表示缓存审计完成，没有改写 476 结果。

失败原因由精确 461 源码闭合：存在 IPE media device 时创建 `ipe_`，任意 processed 输出会启动它；本案打印 `IPE enabled 320x180… requests=1 pd10=0`。240 个队列均为 revision=0、fresh=0、bytes=0、pd10=0，历史 prepared/committed=240，discarded/aborted/pending=0。这是默认 processed IPE 路径，不能称为 IPE-free 测量或自动 PD10/LTM 运行。

控制响应证据可独立分析：两次 mode guard 均为 4208×2368、crop(0,376)、LL4848/FLL3312、481930000 pixel/s；233 个真实 SOF 事件完整覆盖 0…232，pending=0。240 个 Pair、应用帧和成功 IPE 回执均覆盖 SOF 0…239；停止阶段另有 SOF240 和 request240…242 的取消，完整保留。

九次写入全部 ret=0/errno=0，开始距事件 48.958…267.709µs，写入耗时 530.731…822.554µs；均在事件后 610.470…961.044µs 完成，距下一 SOF 最少仍有 32357.104µs。事件周期中位数 33318096ns，与该 mode 的几何时钟一致。每次 `G_CTRL` 值匹配由已核 472 stepper 源码及最终 steps=9/result=0 成功路径证明；仅初值有显式读回日志，没有虚构九份独立读回记录，也没有把 V4L2 control cache 当作传感器寄存器锁存。

私有 BLS-only profile 无 sensor_controls/AGC/AWB/IPE 调校，日志两次 delayed-controls=0，且无 AE update/SENSOR_WRITE；240 个 AWB_STATE 均未计算、色增益为1。精确源码表明 Pair 的 mean 来自同 SOF 解析的原始 BHIST weightedSum/population，并在 IPE prepare/queue 前记录。曝光／增益 metadata 始终是 startup 500/64；它没有用于验证物理阶跃，不能代替该 BHIST 响应。

独立重算沿用 306 的六帧前窗、八帧后窗及三帧平台判据，与冻结 476 分析器逐步一致。九步全部通过“响应大于10倍MAD噪声且大于5%”的原条件，响应方向均与控制升降一致：

| 控制／方向 | 阶跃 SOF | 有效／总数 | 首变化偏移 | 首个三帧平台偏移 |
|---|---|---:|---:|---:|
| 曝光升 | 12、60 | 2/2 | +2 | +2 |
| 曝光降 | 36、180、204 | 3/3 | +2 | +2 |
| 模拟增益升 | 84、132 | 2/2 | +2 | +2 |
| 模拟增益降 | 108、156 | 2/2 | +2 | +2 |

没有缺失分析窗口、失败写入、跨下一 SOF 写入、低 SNR 或已知全尺度均值步骤。未提供额外饱和事实；均值不能排除局部剪切。本结论只覆盖本次及时写入、普通场景下记录精度内的同 SOF 线性统计响应，不证明逐像素／嵌入寄存器锁存、严重延迟回调，亦未提交 delay 属性或修改 profile。

原始 29 文件归档 SHA `00f825783bb16d090161e51c402414d06a82383e7d7ccba863e2eb9b5ad13389`，已逐文件对照。fixture、原 sensor、434 模块、440 r32/r27 和服务恢复有原件及外部健康记录，fault/taint=0；一条缺少可选 global configuration 的原始 ERROR 保留。全部逐 SOF均值、SNR和响应向量仅存私有 `kernel479/control-analysis-private.json`。

可复审入口：`inspect-control.py <kernel476/runtime-collected-r1> --health <kernel476/final-health-r1-private.json> --private <kernel479>`。脚本仅读缓存，使用私有保留的精确 461 源码；没有 SSH、SDK、编译或目标执行入口。
