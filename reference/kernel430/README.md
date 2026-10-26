# 430：修复 DC 遍次被丢弃；同输入重复性与 LTM 粗级消费通过

复用本机原厂 HAL、ICP 固件和 424 原厂调校包，本轮将问题定位到 **IPE 的最终调度，而非此前检查止于 enqueue 前的参数准备**。维护补丁只改两个内核文件；相同真实 FULL／PD10 输入重复输出已逐字节一致，单独改变 PD10 会改变 FULL 输出。新主摄同 SOF 实拍输入与连续请求均通过。**DC 表逐字节导出、GTM 生效版本与 IPA 数学历史关联、完整自动链路和画质校准仍未完成。候选未永久安装。**

## 定位与底层修复

旧 425／429 oracle 执行完整帧参数准备后停在 `HardwareDriver_EnqueueJob`；job 和整 512 KiB 程序相同仍不足以证明后续 DC 遍次执行。本轮继续执行原厂 BL 上下文初始化、`DistributeJob` 和 `BLGenerator_GenerateBL`，才发现旧配置的粗级 stripe mask 是 `[0,0]`，全尺寸是 `[3,0]`。成功 ACK 不能证明粗级 DC 执行。

本机原厂 HAL `IPENode::PostPipelineCreate` 的有界 ARM64 片段确认：PPS profile 2 且至少两遍时，IO topology 为 3。16 个条件组合执行一致。固定版本 CamxChi 参考也有 PPS 多遍对应的 topology；本机指令为实际依据，未把更新源码当二进制等价。

[小补丁](dc-topology.patch)做两项修正：coarse 存在时使用原厂 PPS 多遍 topology 3；补齐粗级 Y／chroma 写出范围的六个半字字段。只改 topology 仍丢弃粗级 stripe；两项同时修正后，原厂分配结果为粗级 `[1,0]`、全尺寸 `[3,0]`。固定尺寸范围仍为 FULL 640×480 NV12、PD10 160×120／stride 768、display 8、DC＋IP＋mask。

[最终原生对比](native-bl-validation.json)中，实际编译 C 的 IO／striping 与完整原厂 HAL 对应结果生成完全相同的 512 KiB 程序、2 MiB heap、全部存活分配、work／context 及队列命令；共比较 40 个二进制对象。未复制 opaque striping 的未使用脏填充。窄范围内存读观察不改变程序或 heap。队列、互斥等 OS provider 属于离线夹具，没有冒充原厂 OS 或硬件执行。

[维护 C](runtime-validation.json)通过 ASAN／UBSAN 与 ARM64 qemu，11472 bytes 一致，保留无效输入不写出、DC 关闭单遍行为与粗级重叠检查。[IO 检查](io-validation.json)保留 legacy NULL coarse。[源码与构建审计](source-validation.json)确认 patch 零 fuzz／offset 重放、源码干净、10 模块匹配 cohort W=1／Werror 零诊断，共享构建输出恢复。未改 UAPI／6008B 包、DMA 所有权、m2m／传感器驱动、板级 DT 或电源策略，没有新增 MMIO 读取。

## 实机证据

[硬件审计](hardware-validation.json)区分四组测试：

| 路径 | IPE 作业 | 真实输入首尾差异 | 补充证据 |
|---|---:|---:|---|
| 正式模块 FULL-only 对照 | 4 | LTM 关：0 bytes；仅 IP 无 DC：164373 bytes | 复现旧不稳定性依赖 LTM |
| 修复后，复用 428 主摄 SOF17 | 4 | 0 bytes | 仅替换 PD10 黑／白，输出均变化 |
| 新主摄 scene，6 对 FULL／PD10，选 SOF5 | 4 | 0 bytes | 同 SOF 已完成缓冲、尾部未改；黑／白对照均变化 |
| 同一 IPE 开流的四个连续请求 | 4 | 0 bytes | 请求序号 0…3，request DONE；四种输出与分别开流逐字节一致 |

共 16 个实际 direct 作业，其中修复候选 12 个。新采集 FULL 与 PD10 各 6 帧，没有重复旧四摄饥饿矩阵。固定 FULL、只改粗级 PD10、ANR／TF 关闭且 LTM 开启的对照，结合真实重复输出相同，提供 LTM 消费粗级输入的因果证据；不是凭普通像素变化宣布 DC 正常。

每次实验均终态退出，正式模块／服务／资源恢复，无新增相关 fault，taint 0；正式磁盘模块未改。当前仍 420 r31／r26、419 core／adapter、Image363／DT389。前轮 Oops 是已删除的自身越界诊断；[429 故障与恢复](../kernel429/INCIDENT.md)继续保留，不能改写为原厂问题。

## 统计位置、初始化和同步的证据边界

修正后原厂所需 scratch 从 71488 变为 46128 bytes，四种输入及连续请求中仍全为预填 a7。**scratch 不是已验收的 DC 表导出**。固定原厂参考存在独立 `LTMAverageLUT`，avg3d 是平均值 DMI ping-pong 缓冲，区别于提交的 13 张调校 LUT；本机固件按粗级／全尺寸遍次生成控制。当前行为证明恢复粗级执行后输出可重复，并且连续黑／白请求不会破坏再次真实输入的结果；尚未完成片内平均值 RAM 的具体 bank／reset／读出逐字节验证，不新增猜测寄存器读取。

## 尚需完成

将生产 libcamera 的已完成同 SOF PD10 队列接入 `CamssIpe`：两源平面共同持有至两队列和 request 完成，停止时先 join 再释放。当前测试仍使用 424 的固定原厂包，不是自动 IPA 调校；本轮 IPA 数学历史提交为 0。

GTM 属于 IFE／BPS 上游，LTM 在 IPE。原厂 TMC 分配非零 GTM 份额，不能清零或把“版本 0”当已生效。仍需恢复本机 GTM 树／数学／寄存器应用，再关联“统计→后续 IFE GTM 生效版本→对应图像 IPE→最终成功历史提交”，不能用当前图像直方图倒称已经改变其上游 GTM。前摄原厂 TMC 关闭策略保持。

四摄其它模式、视频、第五 2MP、光学个体校准与多摄几何／同步等范围见 [363 剩余清单](../kernel363/REMAINING-CAMERA-SCOPE.md)。原厂二进制、反编译内容、系数和图像只在私存，公共仅自有代码及脱敏证据。本地 scoped 提交，不 push。
