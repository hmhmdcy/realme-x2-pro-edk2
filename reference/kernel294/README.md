# 294：VFE175 统计通路和 metadata 生命周期

本轮从实际 #293 构建、部署了 #294。启动、boot/logdump 读回、778 个独立模块和加载模块 build-id 核对通过。DTB、boot276、固件和用户空间包保持。完整 R2 构建 149.13 秒、五阶段诊断 0、40 个 CAMSS 组件严格编译通过。早期 R1 未部署；发现生命周期问题后已保留并替换为 R2。

- 实际源码：`samurai-stats294` / `456e46ca43142e7123a3bd353e559a5cb6bf768d`。三个本地提交分别处理 metadata DMA 启停、VFE175 BHIST、图像重启和部分启动失败的缓冲回收。未推送，也未证明上游接受。
- 标准接口实测：S5K3M5 图案2，经真实 CSI/CSID0/VFE175 FULL，99 帧图像、90 个 QCST 统计包、7 次混合 WB/BHIST 参数完成、10 类非法参数拒绝。QBUF 后修改用户 buffer，内核仍使用快照；11 阶段白平衡颜色参考最大通道误差 <1.235。[采集](stats-capture-validation.json)、[颜色](stats-pixel-validation.json)
- 生命周期通过：图像重启而统计队列保留，以及图像继续时统计 STREAMOFF/晚启动；每次重启后三个统计 buffer 都重新出现。媒体图和供电恢复、fault/taint 无新增。[主机负对照与修复](fixed-restart-metadata-validation.json)
- **BHIST 功能验收失败**：90 个包的 1024 个 bin 全零；全幅期望 820560、半幅 410280、最小 ROI 2，实际均 0。因此 metadata 传输和回收通过不等于统计内容有效。[定量失败](statistics-pixel-validation.json)
- 在本机拥有的活动标准 V4L2 流内做了一次独立只读 MMIO 诊断：DT 与 PM 检查通过，未写寄存器。ROI/config、统计 WM16 和完成组均已配置，但使能是 `0x44 bit5`。第二次 99/90 帧仍全零；只读诊断与纯标准接口测试分别记录。[诊断](stats-readback-capture-validation.json)

原厂资料确实有用，但初次指令解读缺少端口枚举，误把 RS 的 bit5 当作 BHIST。补齐固定公开 Camx 端口枚举（BHIST16、RS12）和 `UINT32 path` 布局，再核对本机原厂 HAL：偏移64打包到 bit4，偏移48打包到 bit5。现已保留[初次错误解释](initial-protocol-contract-validation.json)，[纠正证明](enable-correction-validation.json)明确 BHIST 为 `0x44 bit4`，下一版 #295 在驱动修正，不采用用户空间 MMIO 写入兜底。协议事实来自固定源版本；未执行原厂二进制，也未复制原厂实现或其它手机调校数据。

本次默认 SSC 启动约100秒才完成，早期 `/run/samurai-ssc/state.json` 尚不存在；提前读取报 FileNotFoundError，私人日志保留。随后 SSC 默认启动成功，没有重试或临时 nodeps 恢复。不能据一次启动成功关闭 #293 的偶发 EPERM 根因问题。

统计/BLC/IPA、产品 libcamera 硬件 pipeline、完整画质、主/前摄硬件路径、AF Continuous/距离映射、Shine OV02A1B、GUI录像及长期稳定性仍未完成。普通应用依然使用 RAW＋CPU ISP。原厂 DT 提供接线与模组信息，厂商驱动提供协议参考，HAL/调校及本机校准仍须按语义分别处理。

本阶段所有构建/切换/采集均已终态。当前实际启动身份以[根检查点](../../NEXT-SESSION.md)为准；本文件是阶段294历史，勿使用其 guard 操作后续启动。
