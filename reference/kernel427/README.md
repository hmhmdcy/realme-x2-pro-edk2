# 427：原厂 DS4 接入底层输出队列，实机定位到帧内停滞

完整多摄／骁龙 ISP 目标继续 active。维护内核已加入原厂调校驱动的 DS4 图像输出候选，实际临时加载并完成 FULL 对照采集。**DS4 仅观察到部分 DMA 写入，没有一张完整 DS4 帧；完整自动 TMC／LTM 链路尚未通过实拍验证。** 正式模块和桌面服务均已恢复，没有永久安装本轮候选。

## 已实现的底层候选

[维护内核改动](ds4-dma.patch)在 CAMSS 中注册独立 `msm_vfe0_ds4` 图像节点，使用标准 VIDEO_CAPTURE_MPLANE、DMA-SG 缓冲和独立完成组。它跟随 FULL 所属的 VFE line，不重复启动传感器，也不把 PD10 冒充 metadata 或 NV12。

原厂滤波参数来自 [426 已验证的四摄提取与模式绑定](../kernel426/README.md)。新增 DS4 参数块只配置系数，flags／reserved 必须为零；模块开启由流生命周期控制。默认不硬编码某一镜头系数。FULL 与 DS4 使用同一 SOF 标签，但只有真实完成回执才可交付图像；SOF 本身不等于 DMA 完成。

PD10 沿用本机原 HAL 的 192 byte stride／4 packed rows 对齐。640×480 FULL 对应 160×120 PD10，stride 768、slice 60、46080 bytes。WM5 活动宽为 640 bytes、高为 60，frame increment 使用包含 slice padding 的大小。未放宽 DMA-SG 覆盖、16 byte 地址对齐或 32 bit IOVA 范围检查。

`QP10` 是本地实验 FourCC，尚未保留为上游格式；像素位序尚未验证。驱动提供明确格式描述，避免共享 V4L2 核心对未知 FourCC 发出 WARN。没有修改通用 videodev 模块。

队列在持有有效缓冲后启动 WM、写入地址 FIFO，再提交寄存器更新；空队列不启动 DS4 DMA。断粮后的暂停／恢复、独立完成组、缺失 SOF 的 ERROR 回执和缺失校准的拒绝路径通过宿主与 ARM64 模型检查。[队列验证](queue-validation.json)、[初版旧 RDI 启动分支负对照](queue-negative-validation.json)。这些是代码检查，尚未替代实机断粮／恢复验收。

## 新恢复的原厂使能汇总

426 已恢复 DS410、PreCrop、RoundClamp 和 R2PD 的数据寄存器。本轮继续直接执行本机 HAL 的 `IFENode::ProgramIQModuleEnableConfig`，入口与大小见 [函数记录](module-enable-functions.json)，[原指令执行器](probe-module-enable.py)。没有替换该函数的使能逻辑，仅复用寄存器写入记录 provider。

在明确启用 FULL／DS4 的合成节点上下文中，原函数还写入 DS4 Y／C 各自的 crop／round／clamp 配置使能；候选已补齐，停流时只清理自身字段。7 组几何的原厂数据寄存器、完整使能汇总、原厂 PD10 布局和实际内核 C 输出一致，宿主 ASAN／UBSAN 与 ARM64 静态 qemu 均通过。[对照结果](runtime-codec-validation.json)。

该上下文仍是受控夹具：裁剪窗口由测试输入提供，端口启用字段按原指令访问设置。**它不证明真实传感器的完整 IFE striping／几何推导已经恢复。** 本轮实机失败表明不能把这些局部数学与控制对照视作完整硬件配置验收。

## 实机结果与失败范围

[硬件调查](hardware-investigation-validation.json)校验的是证据和恢复过程；其中 `passed=true` 不表示 DS4 功能通过，各次实际实验的 `experiment_passed` 均为 false。

| 实验 | 实际结果 |
|---|---|
| FULL 单独输出 | 最新对照连续完成 24 帧；完整 payload，映射尾部未改写 |
| FULL 与 DS4 同开 | 656 次 SOF 观测，两个节点完整交付帧均为 0 |
| 停流后检查未交付缓冲 | DS4 第一块有 4 个 packed rows 部分改写，其余缓冲未写入；FULL 第一块也只有部分内容 |
| IRQ 状态 | 捕获 status1 `0x800` 和 `0x1000`，命中原厂 CAMIF `0xefff7e80` 错误掩码；原厂驱动归为 overflow |
| IPE／现场图 | 没有提交新 IPE job；pattern 失败后 scene 分支未执行，最新成功现场图仍是 424 |

r1 是探针过严比较格式附加字段导致的前置失败；r2／r3 缺乏足够诊断，r3 还存在构建终态未先确认便准备载荷的问题，不能作为新版诊断证据。r4 起核对探针源与二进制 hash 并在构建终态后准备载荷。r5 加入 FULL 对照和 SOF；r6 修正 FIFO 顺序仍失败；r7 补原厂局部使能仍失败；r8 增加原始 IRQ 和停流后未交付缓冲检查，得到上述帧内停滞证据。失败没有被重命名为有效照片，也没有交给 IPE 或推进 IPA 数学历史。

未出现新的 SMMU fault、内核 WARN／Oops，taint 保持历史值 512；这不代表没有硬件错误，IRQ 中的 overflow 已单独记录。r8 诊断最初按前四个 SOF 的时间窗口打印，错误 IRQ 较密；最终源码收紧为只在前四个 SOF 事件打印，避免错误 IRQ 刷屏。该最后的日志收敛不改变像素配置。

各次 worker 均终止，媒体图与格式由原有 fixture 恢复，正式三模块 build-id 和 PipeWire／WirePlumber 恢复。资源状态未持有 DMA backing、映射或电源；owner_refs 回到桌面枚举的 53。首次卸载把本轮前 793 个历史 IPE 完成计数重置为新模块生命周期的 0，不是 job 失败；历史证据保留在私有 preflight，正式软件包 r31／r26 未变。

## 构建与处理域

[源码状态](source-state.json)、[源码／补丁复放检查](source-validation.json)、[最新 Werror 构建](intree-build-validation.json)。维护分支 `samurai-vfe175-ds4-dma427`；候选与匹配 core／adapter／媒体 helpers 共 10 模块构建，共享构建产物和配置恢复。最终源码包含有界诊断；最新实机候选版本在硬件调查中单独锁定，不能混称同一二进制。

| 层次／处理域 | 本轮状态 |
|---|---|
| SoC／板级／DT／传感器 | 复用现有 SM8150、DT389、四摄来源和现有模式，没有刷写或改动 NV／OTP／persist |
| 主线风格驱动／IFE | DS4 队列、格式、WM5、原厂数据与局部使能候选已接入；实机帧内停滞仍需修复 |
| IFE／BPS GTM | 仍是上游处理域；TMC 的非零 GTM 份额未接入，生效版本的同图像因果绑定未完成 |
| IPE LTM | [425](../kernel425/README.md) 的原厂双遍、端口与 scratch 证据保留；尚未消费真实完整 PD10，也没有验收 DC 统计写出和 full IP 消费 |
| 用户空间 IPA | 保留 [424](../kernel424/README.md) 的实际触发、同 SOF BHIST／曝光／lux 和最终成功提交历史；本轮没有把不完整 DS4 作为有效输入 |

下一步先对照原厂真实 IFE 几何／striping、输出端口及总线消费者状态，修复启用 DS4 后的内部 overflow 和帧内回压，验证完整帧及独立停启。随后接真实 PD10 的 IPE 粗级 backing 所有权、双遍 striping／scratch／端口绑定，证明 DC 产出和 full IP 消费，再合并 IPA 自动触发与最终成功历史实拍。不要重复宣称离线数学矩阵等于自动链路完成。其它镜头模式、视频和第五 2MP 身份等范围继续参照 [未完成清单](../kernel363/REMAINING-CAMERA-SCOPE.md)。
