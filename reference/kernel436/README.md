# 436：恢复原厂 BLS，定位并减轻主摄雾感与环状亮度

主摄原厂 GTM／TMC／LTM 自动链路继续运行。本轮保存同帧 IFE FULL、真实 PD10、实际 6008 字节 IPE 参数与成片，再做固定输入硬件回放和 LSC 开关对照，定位到实拍配置继承了早期内部图案实验的零黑电平。恢复本机原厂 IFE BLS 后，大面积中心暗区、外围亮环和雾感明显减轻，房间物体已清楚可辨。没有关闭原厂 LSC／GTM／TMC／LTM 来绕过问题。

修正配置完成 229 帧实拍、223 次完整 tone 数学提交，另 6 帧为显式启动处理。其中 AF 扫描 205 帧、202 次数学提交，AF 到达 Focused。正式模块、服务和资源恢复，新增故障 0、taint 0，没有永久安装。

**完整画质和多摄目标未完成。** 205 帧中没有 AWB locked；AF 期间前景发生变化，不能把 FoM 的变化全部归因于镜头改善。白平衡、颜色、均匀性、噪声及正式光学校准仍需继续，不能用可辨识画面替代验收。

## 因果定位

| 事务 | 操作 | 实拍／回放 | 数学提交 |
| --- | --- | ---: | ---: |
| r1 | 原 435 配置，增加一次同帧诊断保存 | 24 实拍 | 21 |
| r2 | 固定 r1 的 FULL／PD10／参数，原厂、LTM 关闭、仅色彩、旁路、再原厂 | 5 回放 | 不经过 IPA 历史 |
| r3 | 只临时关闭 LSC，其余仍为原诊断配置 | 24 实拍 | 21 |
| r4 | 恢复原厂 BLS 与显式范围归一化，保留 LSC 和完整 tone | 24 实拍 | 21 |
| r5 | r4 配置，复用已有真实 AF 采集器 | 205 实拍 | 202 |

r1 保存 SOF 12：FULL 和 PD10 的内核序号均 12，token 13、数学 revision 10；实际 GTM cookie／generation 5，来自统计 SOF 9。参数、队列和最终成功回执逐项相符。[逐帧审计](hardware-r1-validation.json)。

r2 的两次原厂输出逐字节相同，也与 r1 实时成片逐字节相同；所有模式的 FULL／PD10 输入哈希不变。关闭 LTM 仍能看见上游的大面积径向分布，不能将它归咎于 DC 缓存随机变化。[回放工具构建](replay-build-validation.json)。r3 关闭 LSC 后该径向分布明显减弱；它只是诊断对照，没有作为修复方案。

## 原厂 BLS 恢复与分层

追溯配置发现，324 为内部测试图案显式将 BLS 减量设为零、归一化设为 1；这个实验配置经后续私有 profile 一直进入 435 tone 实拍。正式主摄参考配置原本已有非零黑电平校正。没有完成黑电平校正就应用 LSC，会把背景基底一同放大；本轮的开关对照和修正实拍支持这是主要异常来源。

复用 324 留存的本机 Sunny GW1 调校，指纹一致。使用 306 的有界类型解码器遍历，再用原厂 ParameterParser 独立导出：IFE Default 和 Sensor.9 两根共 10 区域，offset 均为 960 U14、四阈值零。BPS 有其它值，未混入 IFE。[原厂解析器对照](main-factory-bls-export-validation.json)。主摄方案对应继承 [342 的执行器证据](../kernel342/module-variant-validation.json)，不将其冒充 EEPROM 厂商认证。

[配置导出](export-profile.py)将 IFE 参考映射为公共 U16 减量 3840、显式 Q11 范围归一化 2175／2048，只恢复这两项。原 LSC、GTM、TMC、LTM、Gamma、色彩和 PD10 字段保持逐字一致。[配置核对](profile-export-validation.json)。这不是个体暗场标定，也未修改原厂文件或写校准分区。

修复在 IPA 模式配置层复用现有 VFE175 BLS 后端；不增加应用像素补色，不修改板级 DT、传感器或内核。数值 IPA 模块、签名和代理与 435 完全相同。唯一生产源码变化是可选、每次开流最多一次的诊断保存：只读映射、每个唯一 DMA FD 配对 CPU START／END，同帧缓冲的原所有权保留。[源码检查](source-validation.json)、[两文件补丁](0048-camss-same-frame-tone-trace.patch)。

## 验证与继续范围

[汇总](hardware-validation.json)共 277 实拍、265 次数学提交、12 启动帧，另 5 固定输入回放。所有实拍逐帧复查实际 GTM 回执、同 SOF PD10、IPE 入队、最终成功历史和上一成功 lux；各流都观测两个 GTM bank。r3 可以有未消费的 PD10 和 SOF 间隔，未将其误算为最终图像。没有新增片内 DC 表逐字节读回或猜测 MMIO。

修正后的 [r4](hardware-r4-validation.json)与 [r5](hardware-r5-validation.json)分别完成 24／205 帧及 21／202 数学提交。r5 的 AF 为 Focused，AWB 全程没有 locked；前景变化与缺少标准色板／均匀场限制了画质结论。原始像素、原厂数据与完整日志只在私有 `E:/edk2-samurai-out/kernel436`。

候选 `/mnt/samurai-full282/libcamera436-tone-domain/src/libcamera-v0.7.2`，build1／IPA5，libcamera `af3bc105…`、IPA `51052914…`、proxy `093df5fa…`。内核仍为 434 的 `9bc07e63…`，未重建。后续 staging 默认使用修正配置；复现旧 r1／r3 需显式 `--uncorrected-baseline`。历史准备／解析器脚本有一次性目录前置，不盲目重放。

下一步先查 AWB 稳态、统计／有效增益语义和剩余偏色，继续原厂数据与实拍；随后扩大其它摄像头、尺寸／视频与原厂 tone 分支。第五 2MP、个体光学、多摄几何／同步等[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)仍保留。正式 420／419 环境不因临时实验被永久替换。
