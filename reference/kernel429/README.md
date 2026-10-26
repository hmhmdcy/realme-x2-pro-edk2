# 429：四摄恢复通过；真实 PD10 双遍完成，统计与重复性仍未通过

完整多摄／ISP 目标未完成。四摄 IFE／PD10 的 [428 验收](../kernel428/README.md)保留。本轮已将真实 PD10 与 FULL 成组接入底层 IPE 请求，主摄已采集的同 SOF 图像对完成四个实际双遍作业。**DC 统计写出、LTM 对该统计的消费、GTM 生效版本和 IPA 数学历史的同帧关联均未验收。**

单核隔离中新增的寄存器诊断越过内核映射窗口并触发 Oops；诊断已删除。用户完成硬件强制重启后，[新启动核验](postboot-validation.json)确认正式模块磁盘摘要和加载版本一致、taint 0、无遗留 DMA。[四摄恢复实拍](camera-recovery-validation.json)每颗 12 帧，共 48 帧完成正式 IPE，桌面服务与资源正常。随后修正版单核 r4 完成四个双遍作业并恢复正式模块／服务，无新增 fault，taint 0；统计和重复性仍未验收。[故障历史](INCIDENT.md)保留。

## 底层接入与适用范围

[维护补丁](pd10-runtime.patch)连接三层：

1. **原厂几何**：复用完整本机 HAL／固件，生成粗级 DC 加全尺寸 IP 两遍。第二遍的模块配置和 stripe 指针均随 pass 基址移动。只编码已核实的几何字段，不复制原厂 opaque blob。
2. **SoC 核心**：新增类型化可选 PD10 输入、会话配置和帧端口 1。DMA-BUF 路径持有第三份导入引用，检查与 FULL 输入／输出不重叠；不确定完成继续保留所有权。CPU 夹具的 PD10 放在同一请求 parcel 内，不借用未拥有的地址。所有释放／保留判据均覆盖第三缓冲。
3. **V4L2 队列**：实验格式 `QN10` 的 OUTPUT plane 0 为连续 NV12、plane 1 为原生 PD10；CAPTURE 仍是单平面 NV12。调用者必须提供同 SOF 已完成图像对，两个源平面共同持有至 DQBUF。普通 NV12／NV21 与既有 6008 byte 参数包不变。FourCC 未上游保留，未把额外图像平面冒充普通 NV12 定义。

当前双遍编码器明确限制 640×480 NV12、display port 8，DC 开启时要求 IP 与 mask；支持原厂 core-count 1／2 输入。其它尺寸、输出端口和缩放未扩展。双核 r2 和修正版单核 r4 均完成作业但重复性失败，单核隔离未解决该问题。

新建 root-only、最大 256 KiB 的临时 scratch 快照用于调查，含请求号／长度／CRC／预填变化数，只在完成后复制，不暴露活动 DMA 内存。快照不是正式统计接口；scratch 也尚未确定为 LTM DC 统计存放位置。未修改 SoC 电源策略、板级 DT、传感器、NV／OTP／persist 或正式安装。

## 原厂与软件证据

[实际 C 检查](runtime-validation.json)将维护源码的几何与帧编码函数在 ASAN／UBSAN 和 ARM64 qemu 执行，11472 bytes 输出一致。新 PD10 端口地址、容量、重叠、32 bit 范围、无效输入不写输出和 DC 关闭保持原单遍几何通过。完整原厂 HAL striping 与固件 prepare 生成的 job、整 512 KiB 命令均与候选一致；模型停止于硬件 enqueue 前，不能代替物理统计验证。

[单核输入对照](one-core-oracle-validation.json)确认同一候选几何送入原厂 core-count 1／2 时，各自完整命令与对应原 HAL 输出一致。[引用与退出检查](owner-validation.json)执行实际第三缓冲释放函数、核心和 adapter 所有权判据：只有 coarse 引用时仍识别持有；每个释放失败保留剩余引用，pending／FW map 时一项也不释放，重试完整释放。

[源码／补丁复放](source-validation.json)、[最终匹配 10 模块构建](intree-build-validation.json)通过，维护树干净，共享构建输出恢复。最终 HEAD 见 [状态](source-state.json)。**build r2 的 core 含错误诊断，禁止再加载；最新修正为 build r3。** 当前正式磁盘仍是 420 r31／r26 与 419 core／adapter。

## 实际回放结果与未通过项

[硬件审计](hardware-validation.json)的 `passed` 仅表示证据与传输审计通过，`feature_acceptance_passed=false`。

| 实验 | 实际结果 |
|---|---|
| r1 | video 节点名称匹配错误，启动 IPE 前退出；正式模块／服务已恢复 |
| r2／双核 | 主摄 428 的 FULL／PD10 同 SOF 17 对，原厂主摄 424 LTM 包，四个 direct job 完成，资源与正式模块／服务恢复 |
| r2／反事实 | FULL 固定，依次真实 PD10、黑／白中性色 PD10、再次真实 PD10；没有重新拍摄传感器 |
| r2／scratch | 四次均为 71488 bytes，仍全为预填值，没有证明 DC 写出 |
| r2／重复性 | 相同真实输入两次输出差 152871 bytes，Y 平均绝对差约 3.405，不能把黑／白对照的输出差当作 PD10 因果证明 |
| r3／单核 | 新增越界诊断触发内核 Oops，客户端未完成交付；实验无效，正常重启请求后当时未核实新启动 |
| 恢复／正式四摄 | 用户强制重启后核实新启动与正式模块；前摄、广角、长焦、主摄各 12 帧，48 次 IPE 完成，服务恢复、无新 fault、taint 0 |
| r4／修正版单核 | build r3 完成四个 direct job，正式模块／服务／资源恢复；71488 bytes scratch 四次保持预填值，真实重复输出差 138366 bytes，Y 平均绝对差约 3.174 |

r2 无新增相关 fault，taint 512，jobs／completed／direct=4、failed／cancelled=0；其恢复成功不能覆盖随后 r3 的故障。r3 taint 640、worker 终态失败，客户端在内核取消路径不可终止；未强制卸载、提前解除映射或谎报释放。后续物理重启恢复与 r4 分别有新证据。[故障审计](incident-validation.json)、[单核审计](single-core-hardware-validation.json)均将传输成功与功能验收分开。r4 复用 428 图像对，不是新的自动 IPA 实拍，没有数学历史提交。原图／反事实结果、全部寄存器命令及日志只私存。

## 接续顺序

硬件重启后的正式四摄恢复已通过。`host.py` 使用新 429 guard 和原密钥，`prepare-runtime.py` 从当前正式模块与计数生成受保护基线，只允许移除错误诊断的 build r3；不再复用旧 394 guard、taint 512 或旧 jobs 假设。

单核与双核都出现真实重复输入不稳定，接下来追踪原厂 DC 的真实存放位置、bank 选择、初始化及遍次同步。固定参考源码包含 DC／IP 平均表 bank 的 SW override 字段，但本机实际策略仍需从原指令／硬件证明；不能猜 bank 值或把 scratch 未写解读成 DC 统计天然不存在。

最后接生产 IPA 的真实 PD10 队列，保留 [424](../kernel424/README.md) 的实际曝光／gain／lux、同 SOF BHIST 和最终成功才提交历史的规则。GTM 属于 IFE／BPS 上游，LTM 属于 IPE；还要建立统计→后续 IFE GTM 生效版本→对应图像 IPE／历史提交的因果链，不能宣称刚获取的统计已经影响同一张上游图。前摄原厂关闭 TMC 的策略保持，其它模式／视频／第五 2MP 等[剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)不缩小。
