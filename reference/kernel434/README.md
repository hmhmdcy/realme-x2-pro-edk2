# 434：原厂 GTM 实机生效、双 bank 重复性及重开流修复

原厂 TMC11 生成的 GTM LUT 已经在真实 IFE 上改变 FULL 和 PD10 像素，按实际统计回执的 cookie／generation／bank 与 SOF 对齐。修复后的第二轮完成 61 组测试图和 19 组实景的同 SOF FULL／PD10／统计；正式模块、服务和资源均恢复，无新增 fault，taint 0。候选没有永久安装。

**本轮是 IFE GTM 硬件验证，不是生产 IPA 的 GTM＋IPE 完整自动链路。** 本轮 IPE job 为 0。生产真实 PD10 自动双遍及 48 次成功数学历史仍沿用 [431](../kernel431/README.md)；GTM 生效 cookie 与不可变 TMC／ADRC、对应图像 IPE 消费及最终数学历史尚待接通。完整多摄／ISP 目标继续 active。

## 实机结果

[硬件验证](hardware-validation.json)与[按 SOF 分析](capture-analysis-r2.json)使用主摄 S5KGW1 4608×3456 输入，FULL NV12 640×480 和真实 PD10 160×120。保留原厂 DS4 系数，以固定曝光单独检查 GTM 功能。参数 QBUF 后故意改写用户缓冲，结果仍来自内核校验后的副本；参数 DQ 只解释为提交，实际分组按统计中的已 ACK cookie。

测试图共有九个阶段：关闭、恒等、明确标注的半增益诊断表、两套原厂 TMC11 GTM LUT、同一原厂表重复两次、关闭、重新启用恒等。诊断表只验证硬件功能，不作为工厂调校。

| 检查 | 真实结果 |
| --- | --- |
| 关闭与恒等 LUT | FULL 和 PD10 有效数据分别完全相等 |
| 半增益诊断表 | FULL 平均 Y 从 175.6234 降至 127.8636，PD10 同时改变 |
| 两套原厂 LUT | 平均 Y 分别为 178.3989、182.8306，FULL 与 PD10 各自得到不同且稳定的数据 |
| 同一原厂表重复，两个 GTM bank | 所有 FULL 和有效 PD10 字节分别完全相同 |
| 修复前后测试图 | 九个阶段的像素哈希分别完全相同 |
| 实景关闭→原厂表→关闭 | 平均 Y 约 79.34→87.20→79.34；19 组均有对应 SOF 的 FULL／PD10／回执 |

每个测试图回执组都只有一种 FULL 哈希和一种有效 PD10 哈希，观测到的版本切换与像素变化边界一致。完整 64 项 canonical CPU DMI 上传和两个 bank 的硬件结果支持 [433](../kernel433/README.md) 的低字→高字实现；没有硬件逐项读回 LUT，也没有把回执视为 SRAM 导出。

PD10 每行 768 bytes 中只有前 640 bytes 为有效打包像素，60 行；其余是 padding。probe 每次重新排队前改变哨兵，所以整块 PD10 哈希变化不能用于判断画面不稳定。上述相等比较使用有效数据，FULL 使用完整 NV12 内容。统计按实际内核 SOF 连接，未用当前提交阶段标签代替物理生效版本。

第二轮测试图的保留 SOF 为 0–3、8–64，中间存在缺号，三个输出的保留集合相同。本轮包含同步落盘、缓冲重排队，不验收连续视频帧率，也不宣称无丢帧。实景 0–18 连续。实景像素已有识别得到的室内物体，仍明显雾感、偏绿，绝对画质、颜色和光学校准未验收；这组固定曝光 IFE 样本不代表自动 IPE 成片质量。

## 首轮失败与底层修复

[首轮](runtime-r1-validation.json)成功完成 61 组测试图和九个阶段，随后第二次实景 FULL STREAMON 返回 ENODATA，0 帧。日志和失败样本保留，没有隐藏失败或重复启动未确认状态。worker 仍恢复正式环境，taint 0，无新增 fault。

根因是旧流停流时的最后一次 PIX REG_UPDATE 在软件中留下 pending 位。重开流时像素默认状态会清除 DS4 配置；新的 GTM defer 检查发生在既有 `vfe_enable_output_v2()` 清理该位之前，于是把包含 WB／原厂 DS4／GTM 的整个首包留在队列，DS4 输出校验发现尚未配置，返回 ENODATA。不是原厂系数缺失，也不是重新猜测 DC 地址。

[修复补丁](gtm-reopen.patch)仅修改 SM8150 17x 开流顺序：输出尚未 ON 时，在装载首包参数前、持 output_lock 清理该 PIX 软件更新标志。保留其它 RDI 位，运行中的 GTM 排队、armed ACK 和 SOF 快照逻辑不变。后续第二轮在同一次模块加载内连续完成测试图及实景开流，验证实际重开流恢复。

[实际开流函数检查](reopen-validation.json)执行当前 `vfe_enable()` 函数体，覆盖旧 PIX 位、保留 RDI 位、不重载模块的再次启动、prepare／enable 错误回收和非 PIX 路径，主机 ASAN／UBSAN 通过。[源码检查](source-validation.json)核对唯一修改文件、补丁零 fuzz／offset 重放及实际候选模块哈希。未改动 433 的 GTM 数学、DMI、ACK／SOF 函数，原有实际函数 host／ARM64 检查继承。

维护内核分支 `samurai-vfe175-gtm-reopen434`，HEAD `9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3`，父 `04f8c5a3c815e2fa4244564da108227561a0321b`，clean。[匹配构建](intree-build-validation.json)十模块 W1／Werror 通过，诊断零，共享构建输出恢复。CAMSS 2935224 bytes，SHA256 `3edb28d1fc5f23eb208ecc9532db4fcb1617f3f0f3ff821c0af2f60a90006ca2`；ICP core `d391fa24…`、m2m `e6828a0c…` 均与 431 相同。板级 DT、传感器、电源及生产 libcamera431／IPA4 未修改。

## DC 与自动链路边界

GTM 的 LUT bank 0／1（DMI selector 24／25）与 IPE 的 DC 平均值表是不同资源。本轮没有将前者验证冒称为后者读回。DC 证据仍为 [430](../kernel430/README.md)／[431](../kernel431/bank-validation.json)：RT type 2→context kind 0→DC／IP bank 0；粗遍 DC=1／IP=0／sum_clear=1，随后全尺寸遍 DC=0／IP=1／clear=0，消费同一 bank。最终分发器丢弃 DC 配置的问题已修，固定输入在冷启动和持久 session 下重复相等；固定 FULL、仅改变真实 PD10 会因果性改变最终图像。

真实同 SOF PD10 已在 431 生产候选的普通／隔离 IPA4 自动双遍中完成 48 帧与 48 次最终成功历史提交。这些结果不等于片内 DC 整表逐字节导出，后者仍未完成；旧 a7 scratch 不属于统计。禁止恢复 429 的越界诊断或加载其危险 build2 core，不猜 MMIO 位置。

接下来将 432 已逐字节对齐原厂的 model2 GTM 数学和原厂数据选择接入生产 IPA，以统计 N 生成后续 IFE 参数；根据真实回执 cookie 为图像 M 找到不可变 TMC／ADRC，再让该图像的 FULL＋PD10 进入 IPE／LTM，最后成功才提交对应数学历史。图像 M 的新统计不能逆因果地声称已影响其上游 GTM。IFE 已 ACK 的物理状态与 IPE 成功历史分开；IPE 失败不能伪造回滚已生效的 IFE。保留前摄原厂禁用、非零 GTM 份额、缺统计 hold 与失败历史规则。

原厂二进制、LUT、系数、完整日志、像素和场景 PNG 仅在 private kernel434。公开内容是自有 probe、补丁和脱敏证据。其他摄像头自动链路、尺寸／视频、第五 2MP、个体光学及多摄同步仍见 [363 剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。
