# 423：主摄原厂 TMC／LTM 接入 IPA、同帧请求与数学历史实拍

主摄单曝光路径已形成实际闭环：同 SOF 的 BHIST、曝光、增益和 lux → 原厂模式／AEC 叶选择及 TMC11 → LTM13 与 IPE Gamma → 6008 字节 MediaRequest → 最终图像回执 → 提交数学历史。主摄普通与隔离 IPA 均完成现场自动曝光／白平衡实拍。本轮是候选验证，正式系统仍为 420 部署的 r31／r26 和 419 驱动；完整多摄与原厂画质等价目标未完成。

## 分层与数据来源

仅修改 libcamera IPA、私有 IPC 和 CAMSS 流水线调用方；没有修改 SoC／板级 DT、传感器或主线内核／驱动，没有增加应用滤镜。沿用既有 6008 字节类型化内核接口，私有 IPA 接口升至 3，库／IPA／代理配套使用。[完整补丁](0044-camss-ipa-request-tone-history.patch)、[零 fuzz 复现和实际链接符号](source-validation.json)、[最终构建](build-validation.json)。

[IpeToneProfile](ipe_tone_profile.cpp)复用 350、407–416、422 数学实现。原厂调校文件及编译默认表沿用已留存固件提取结果，未重新读取 NV／OTP／persist。原厂系数、配置、汇编、日志与原始图像留在私有 kernel423 输出目录；公共实现不含这些表。[配置导出器](prepare-profiles.py)、[模式绑定](profiles-validation.json)。

仅启用实际主摄 sunny S5KGW1 的 4608×3456／4608×2592 普通 Preview 调校根；本轮硬件实测前一种。后摄 IPE CCM 的所有选中叶验证为 identity，既有 IFE CCM 保留在原阶段。原厂前摄 TMC 关闭，不将其开启；其他传感器本轮未扩展或重新拍摄。

## 实际触发、统计和历史

IPA 从拥有的 `IpeFrameObservation` 读取 1024 个 pre-WB 线性 BHIST 计数、同 SOF 实际曝光与增益、IFE Gamma 状态和已计算 lux。按原厂 AEC 控制轴选择并插值 LTM179／TMC44／Gamma257。新调用方中的 LTM 插值与实际原厂 ARM64 例程比较 30 组、21480 字节零差，host ASan／UBSan 通过：[插值证据](interpolation-validation.json)。

`prepareIpeParameters()` 同步返回类型化参数；流水线核对 epoch／请求仍有效后，通过现有 `CamssIpe::queue()` 把参数附到该帧 MediaRequest。每摄像头仅允许一个未确认数值提案，忙时可复用已经提交的程序；复用不会推进数学历史。最终图像处理及 RAW 配对完成后的 `frameProcessed()` 才提交对应 epoch／SOF／token／baseRevision 的状态，失败丢弃，停流清空。

真实 ARM64 IPA 模块直接调用验证了失败不提交、忙时持有、成功提交、旧 epoch 无效、旧 token 不可复用和重启清历史；签名检查通过。真实生成的三个 6008 字节包均通过当前内核实际 validator：[IPA 检查](ipa-validation.json)、[内核参数检查](packet-validation.json)。这部分是 SDK／QEMU 验证，硬件证据另列。

当前明确采用 `single-exposure-linear-ae-no-face` 策略：DRC、HDR／dark exposure split 为 1，LED 关闭，无人脸 AEC 过渡，每次新计算强制更新 TMC 直方图。这是原生单曝光适配策略，不是恢复出的 Android HDR 双曝光槽、raw AEC124／140 或完整原厂 AEC。DRC=1 直接命中原厂父叶，不对其他 DRC 轴作任意丢弃。原厂 TMC 的 GTM enable 被保留为元数据，但本轮未新增或证明 IFE GTM 分支，不能宣称完整原厂全局／局部曝光分配等价。

## IFE／IPE 处理域

实际原厂 IFE Gamma 发布代码只写 64 个 green 基值（取 DMI 低 10 位），结构虽有 65 项，第 65 项未在该发布段写入；实际 LTM 搬运代码读取全部 65 项转 float。4 组不同初始填充和 delta 的实际 ARM64 片段执行确认这个差异：[处理域证据](domains-validation.json)。候选显式使用当前 IFE 最后 segment 的 base+delta 重建物理端点，不把它声称为已恢复的 Android 元数据端点。实际三色 IFE Gamma 必须相同，否则拒绝此简化绑定。

NV12 经已验证的 CST／CV 转换对进入和离开 IPE；LTM 使用当前 IFE green 逆 Gamma，随后使用选中原厂 IPE Gamma。先用固定 5004µs、gain1、WB1 和相同 IFE CCM 的传感器模式 2 比较旁路／色彩回环／Gamma 回环，各 24 帧。色彩回环 Y／U／V 平均绝对误差约 0.160／0.430／0.761 码值，Gamma 回环约 0.161／0.410／0.755；局部边缘最大差可达 18，不能说逐像素无损。[像素对照](roundtrip-validation.json)。转换对来源于已有 400 诊断夹具，本轮以该模式实拍回环验证其适用性，不宣称恢复所有 OEM 模式色彩元数据。

## 硬件结果与边界

[r2 回环](runtime-r2-validation.json)新增 72 个 IPE 作业；[r3 原厂曲线与现场](runtime-r3-validation.json)新增 72 个，均成功且 direct，错误／取消／first_error 均为 0。新增内核故障 0、devcoredump 0。停流后 IPE 的电源、时钟／域所有权、映射、DMA 和导入缓冲均释放，PipeWire／WirePlumber 各恢复一个实例，正式文件未改，历史 taint512 保留。最终 jobs=completed=direct383，starts=stops23，owner_refs53 为桌面持有的 CAMSS 句柄。

| 采集 | 图像帧 | 数值准备／成功回执 | 不同参数摘要 |
|---|---:|---:|---:|
| 旁路模式图 | 24 | 0 | 0 |
| 色彩回环 | 24 | 23 | 1 |
| Gamma 回环 | 24 | 22 | 1 |
| 原厂 TMC／LTM 模式图 | 24 | 22 | 6 |
| 现场自动，普通 IPA | 24 | 22 | 12 |
| 现场自动，隔离 IPA | 24 | 19 | 6 |

共 144 图像帧、108 次同 SOF 数值提交，其中原厂曲线场景 63 次。逐项核对观测直方图摘要、准备参数、同帧入队与最终回执，所有新提案都完成确认，无未决数学历史：[硬件归属检查](hardware-validation.json)。普通／隔离现场分别有 12／13 组曝光、增益、白平衡组合更新，关闭传感器测试图模式。原厂模式图相对中性 Gamma 回环有 312864 个字节改变，平均绝对差约 10.8；证明非零程序影响像素，不代表画质必然改善。[样本统计](scenes-validation.json)。

已查看实际保存图像：现场可见近距离物体，但明显失焦或遮挡；本次没有触发对焦扫描，不能用这些图验收锐度、色准、噪声或高动态画质。LTM DC 标志来自原厂配置，但粗级统计内容／IP 依赖尚未独立导出证明；动态程序影响像素也不能替代这项证明。缺 BG／无有效 lux 的已存在观测目前会拒绝新数值计算，后续应增加持有已提交曲线的恢复策略。完整 OEM GTM／HDR／人脸策略、其他摄像头、视频模式硬件验证与永久打包仍未完成。

## 真实失败记录

首次源码准备错误地认为 reset 序列只出现一次，实际有 init／configure 两处；在准备完成前启动了编译，且编译期间又改了源文件。随后增量构建虽退出成功，仍保留了请求 IPA2 的旧流水线对象，导致 r1 设备枚举失败，IPE 作业没有增长；服务正常恢复，内核无新增故障。已强制重编全部改动调用方／接口，直接反汇编确认产物请求 IPA3，才进行 r2／r3：[失败记录](preparation-r1-failure.json)、[失效旧构建](build-r2-validation.json)、[编译产物核对](built-caller-validation.json)。

测试夹具也曾使用错误输入尺寸、旧 BG 网格／长度，导致配置或统计被正确拒绝；已修正为有效的独立 16×16 数值测试网格，未放宽生产统计校验。本机缺 ffmpeg 时仅使用标准 NV12→BT.601 PNG 解码查看原始样本，没有添加调色。后续直接接本轮实拍证据继续推进，不重跑已有大算法矩阵或旧事务。
