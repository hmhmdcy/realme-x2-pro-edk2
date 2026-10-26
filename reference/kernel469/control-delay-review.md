# 长焦 mode2 / mode3 曝光与增益延迟审计

**mode3 的 2 帧有既有光学实测依据；mode2 的 2 帧仍是继承配置，未获独立生效延迟证明。** 原厂 descriptor / HAL 确有全局 probe `pipelineDelay=2`，但该调度字段不能直接等同每个模式的 exposure / gain apply delay。本审计到此收束，不继续扩大 HAL 逆向或进行实机测试。

[control-delay-review-validation.json](control-delay-review-validation.json) 固定本轮原件、缓存源、指令片段、既有测量收据的 SHA256。完整私有分析保留在 `E:/edk2-samurai-out/kernel469/control-delay-inspect-private.py`；没有使用手机、SSH、SDK、构建或修改共享源码、468 冻结候选。

## 已保存原厂数据实际说明了什么

239 A/B 的 `sensorDriverData.xml` 只投影了 module_version、slaveInfo、resolutionInfo（B 另有 initSettings）。XML 未包含完整根，故不能因 XML 无 delayInfo 就断言原 BIN 没有延迟信息。

独立重读两个原件：115 `com.qti.sensormodule.qtech_s5k3m5sx.bin`（383232 字节，SHA `e3877077…2c488`），及 326 当前保留的 description（383800 字节，SHA `823404fc…8bc77`）。两者各有四个模式、816 字节 sensorDriverData 根；根 qword88…91 均为 `[0,0,2,1]`。这些值属于全局根，不是 mode2 / mode3 各自独立的延迟表。

复用已保留的实际 HAL（SHA `e2b1b9b6…0dde`）root-loader 小片段，输入两个原件及一组不同值 sentinel，三例各执行 **53 条原指令**，将四槽分别写到 native root `+584/+588/+592/+596`。再执行实际 `0x4e4bc0…0x4e4bc8` 两条原指令，将 `root+592` 的值写为 probe command `+18` 的 16 位字段，原件均得到 2，sentinel 得到其相应槽值。没有执行完整 parser、HAL 调用者、外部 provider 或硬件。

该 packet 拷贝与缓存 `ImageSensorData::CreateProbeCmd()` 的 `pProbeCmd->pipelineDelay = …maxPipeline` 对应，构成**原厂全局 maxPipeline / probe 调度为 2**的直接支持。其余旧槽未强行套用较新的公开结构命名；本轮也未把尾槽 1 确认为原厂 frameSkip 值。

缓存 XSD 的 `DelayInfo` 文档分别描述 linecount、gain 为应用相应值所需的帧数；maxPipeline 是最大管线延迟，frameSkip 是启动时跳过的坏帧数。较新结构还含 type、Exists 和 FLL 等信息，与本机旧四槽 ABI 不同，不能把新结构字段偏移直接套进旧 BIN。缓存 `SensorNode::HandleDelayInfo()` 还用 `maxPipeline - linecount/gain/FLL delay` 选择请求队列的历史项，说明这些量在原厂算法中承担不同角色。**frameSkip、最大请求管线调度量、写寄存器后首次光学生效帧，并非同一测量。**

本机 115 的传感器库 SHA 为 `f3325310…c5e48b`。已核 `GetSensorLibraryAPIs@0x18e0` 注册曝光计算 `0x1018`、寄存器填表 `0x10c8`；曝光计算直接读入 realGain 和 lineCount，没有读模式索引。第三回调槽与新缓存 header 的 ABI 不一致，本轮不强命名。没有取得独立的 mode2 / mode3 apply-delay 回调或模式表绑定，因此这些回调不能作为“两者曝光／增益都为 2 帧”的证明。

## mode3 的实际 2 帧依据

[306 独立时序分析](../kernel306/delay-analysis-r1-validation.json) 明确限定 **2104×1560、pixelRate481930000、LL9648、最小 FLL1663**。240 个配对帧、233 个 SOF、9 次独立写入中，7 次满足既定信噪比条件：3 次曝光、4 次模拟增益；首个可辨变化和首次连续三帧平台均在写入 SOF＋2。其余两次小曝光变化未计作时序证明。测量程序没有预设 DelayedControls 延迟。

[306 联合控制核对](../kernel306/joint-physical-validation.json) 另有 480 帧、18 次联合变化和 36 次写入，均位于关联元数据生效 SOF 前 2 帧；限定观察域内没有检出混合 EV 瞬态。该证据不证明所有像素或嵌入式寄存器锁存，也不覆盖严重迟到写入。

因此现用 mode3 两帧设置有上述实测支持，来源应写为**本模式写入到光学响应的既有测量**，不应改写成原厂明确声明的曝光／增益延迟。mode2 的 LL/FLL、读出与原厂表均已改变，不能把 mode3 测量直接扩为 mode2 结论。469 固定 FULL／参数、仅替换 PD10 的 LTM 因果回放也没有测量传感器控制阶跃。

## mode2 剩余的最小实测项

后续独立控制时序实验至少需要：

1. 确认 active mode 为 4208×2368、LL4848、FLL3312，并记录实际帧间隔；测量路径不预设两帧 DelayedControls，不运行 AE。照明和另一控制量固定，选择不饱和、有足够信噪比的 RAW／线性统计区域。
2. 分别做曝光 500↔1200 行（固定增益）和模拟增益码 64↔128（固定曝光）的重复升降阶跃。记录每次标准 V4L2 写入的开始／结束时间、相对 SOF 偏移、返回值及真实 buffer sequence↔SOF 绑定；保留写入后连续帧，分别判定首变化和三帧平台偏移，不预填结果为 2。
3. 曝光和增益分别获得可重复且一致的观测偏移，覆盖升降方向，剔除低信噪比、饱和或写入过晚的样本。若两者不一致，应保留各自结果并检查当前 IPA 要求相等的配置约束；不能为满足现配置而把结果取成同一个数。

这能补 mode2 的 write-to-response 延迟缺口；逐行锁存、联合更新是否有混合帧及严重迟到写入仍需另列边界。本轮没有修改 profile 的两帧值或声称完成这些测量。
