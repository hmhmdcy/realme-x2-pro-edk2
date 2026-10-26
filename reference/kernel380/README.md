# 380：原厂 striping 完整执行与内核 IPE 帧编码器

继 [379 两路 IO 配置实机通过](../kernel379/README.md)，本轮进入图像数据面的实际格式和算法。优先复用既有固定 CAMSS 原型、Realme GPL 管理器、CamxChi 源与本机 HAL/固件；补充搜索未取得 `ipe_data.h`／`ipeStripingLib.h` 的可用定义，未据此断言所有仓库都没有。原厂汇编、生成数据与回包只私存。

## 原始算法与固件证据

本机 HAL 静态包含 `IPEStripingLibraryContextCreate`、`IPEStripingLibraryExecute`、完整 wrapper/分条算法与 destroy。已在 Unicorn 执行全部相关算法，只有 malloc/free/memset/memcpy/memcmp 按标准语义提供模型，分配器返回非零旧字节；没有用桩替代 striping 算法。覆盖 640×480、1920×1080、4608×3456，输出端口 8/9，核心参数 1/2 共 12 组，输出边界 canary 与上下文分配释放均通过。[算法证据](striping-validation.json)。

测试使用零 IQ（模块关闭）和合成全帧 zoom 参数。输出为一 pass，640 宽 2 stripes、1920 宽 6 stripes、4608 宽在核心参数 1/2 时分别 15/16 stripes。固件实际消费长度为 `2268 + 624 × Σ stripes`；算法给出的 BL 容量分别为 156512、228512、396512 字节。这些是离线布局证据，不能作为画质、裁剪语义或引擎像素输出验收。

原厂完整 `ProcessAsyncCommand` 与 frame callback 进一步执行，使用上述真实算法生成的 stripe 以及实际 C 编码器生成的帧。确认间接 FRAME_PROCESS 命令 40 字节、外部 payload 3816 字节、IQ 2584 字节；header 92 字节，每个 frame set 232 字节（14 端口、各 2 plane 地址和 2 metadata 地址，另 2 个 ICA 命令偏移），最大结构含 16 组。单帧实际拷贝 324 字节；BL 大小在内部命令中扣除 32 字节，命令数组偏移按 CDM base 修正。[分发与回复证据](frame-abi-validation.json)。

FRAME_PROCESS ACK **72 字节**，header 32 + callback 有效数据 32 + 清零尾部 8；并非配置 ACK 的 56 字节或旧 packed 声明长度。原始 callback 执行证明该行为；provider queue、cache、分配、日志及 postMessage 有模型，自动引擎电源分支关闭，真实引擎 handler 和像素 DMA 没有执行。payload 的 userArg 3808 偏移另由本机 HAL 保留的 store 指令确认，完整 HAL request 函数未执行。

## SoC 内核修改与边界

新增 [camss-icp-a5-ipe.c](camss-icp-a5-ipe.c) 与 [接口头](camss-icp-a5-ipe.h)，加入现有核心模块。`camss_a5_ipe_striping_bytes` 检查 pass/stripe 长度；`camss_a5_ipe_encode_frame` 为单帧线性 NV12/NV21 编码原厂格式，计算 Y/UV 起始地址，保留当前 IO 布局和输出端口含义。

写入前检查 32 位 IOVA 范围及对齐、六类缓冲区两两重叠、plane 乘法与容量、scratch/BL 最小需求、IQ/stripe 长度与端口/核心数参数。55 个非法输入检查无越界且不改写目的缓冲；12 个实际函数体生成结果送入原厂固件消费模型。[编码器检查](frame-builder-validation.json)。

这是帧编码接口，尚无 DMA 映射、提交或完成所有者。它不验证 IQ 内容、CDM 命令语义、实际 SMMU 映射或缓冲区生命周期；调用方仍须负责这些。当前命令数组为空，不能把该接口当作可提交任意帧的运行后端。未修改板级 DT、主线媒体框架、传感器或用户空间。

维护源 `/mnt/samurai-full282/source354`，分支 `samurai-a5-ipe-frame380`，提交 `1f0038ccbdc2efb71d97fc85c1f64452f9ce41a6`。候选核心与未改动的测试模块以实际 k363 配置 in-tree W=1/-Werror 构建，无诊断；[构建结果](intree-build-validation.json)。没有安装或启动候选模块。

## 当前硬件与下一步

只读核对当前仍是 378 恢复后的启动：guard 有效、Image363/boot366/DT365/r29/r24 保持，taint0、CAMSS/双 CCI 休眠、临时 ICP 模块/固件无残留；379 同启动四摄及主摄隔离 Gamma 证据复用。本轮没有设备状态切换、刷写、相机重采或帧提交。SSC attach 失败、SLPI offline 和 SensorProxy 停止仍未解决，沿用 379 已恢复的桌面。[当前检查](current-state-validation.json)。

实际静态 ICP node 仍只有 A5 SID `0x2222`。原厂 SM8150-v2 组合 ICP 域还声明 `0x2080/0x20`、`0x20a0/0x20`、`0x2100/0x20`、`0x2120/0x20`、`0x20c0/0`、`0x2140/0`；按 mask 核对不与当前 CAMSS 的 SID 组相交。尚未逐项确定各引擎的 SID 角色，也没有证明这些引擎已附着或可 DMA。

下一步落实引擎 SMMU 域与受控的映射所有权，准备 IQ/stripe、scratch、BL、输入输出图像，接 FRAME_PROCESS/72 字节完成回复及失败保留/复位清理，再做实际像素输出与 libcamera m2m。底层完成后继续原厂 Gamma/LTM/CCM 的组合、第五摄身份、更多模式及光学/几何/同步/AF；整体目标 active。
