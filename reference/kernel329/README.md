# 329：通用 WB 校准与 CCT 查表数学

2026-10-20。已将本机原厂WB个体校准、MWB比值转换、CCT查表拆成独立C++17数学函数，放在[libipa/awb_calibration.cpp](libipa/awb_calibration.cpp)。主机和AArch64结果与原厂指令仿真完全一致。尚未接入IPA、安装新包或启用个体WB；完整目标active，部署保持327/328记录。

本轮继续使用328保留的精确AWB组件，不重复取原厂包或读取EEPROM。在主机Unicorn ARM64 2.1.4中只映射所需ELF代码/常量和自建数据内存，限定小函数/算术块范围，日志调用全部stub、异常和系统调用拒绝，没有Android加载器、原厂本机执行或手机代码运行。仿真分别覆盖校准0x9e30～0xa8fc、MWB算术块0x8f24～0x9114、CCT正向查表0x9bc0～0x9d70；可重跑入口[check-math.py](check-math.py)。

校准输入按相同记录索引配对unit/golden，使用**工厂CCT数组**分组；改变所有unit payload CCT为999，五份真实配置的输出均不变。由此补齐328未确认的对应语义：HAL payload与golden标称CCT不同不是新的阻塞，也不是强行用最近CCT替换单位数据。光源分组门限为6000、4500、4000、3425、2575 K，对应D65、D50、CW、TL84、A、H；重复分组保留最后一项，缺失分组沿用邻项，荧光灯和双点情况按实际规则处理。

输出是**unit/golden的R/G、B/G比值因子**，方向与LSC的golden/unit不同。MWB的RGB增益先转成G/R、G/B，再乘上述比值因子；这些结果是后续查表使用的通道比值，不能直接当作ISP颜色校正增益。`awbCalibratedMwbRatios()`明确这一层语义。

正向CCT查表在以下K节点线性插值比值，超出两端沿用端点；它不是mired插值，也不是当前场景的CCT估计器：

| K | 比值表索引 |
| --- | --- |
| 12000 | 0 |
| 7500 | 1 |
| 6500 | 2 |
| 5000 | 3 |
| 4000 | 5 |
| 2850 | 7 |
| 2300 | 8 |
| 1500 | 9 |

覆盖全部63个非空光源分组子集、各分组边界/重复覆盖和五份真实校准，共78个校准条件；19份真实工厂MWB转换；每个节点、相邻区间及两端范围共589次查表。独立C++分别在主机及已有AArch64 SDK Werror构建/执行，每架构3118个float值、合计6236个，全部与原厂指令输出相同，最大误差0。[结果](math-validation.json)。这些数量是覆盖范围与观察结果，不是日后新增固定帧数/重复测试门槛。

私有中间数据在kernel329/calibrated-ratios-private.json、math-input-private.bin、stock-expected-private.bin及各架构输出；未放进公共仓库。仿真环境/home/cy122/x2pro-linux/private-k329-venv；ARM工具与数据SDK/private/camss329-math。本轮没有相机采集、手机状态切换、模块/软件包安装或分区写入，未改未测试组件复用此前证据。

下一步把这些函数接入可选IPA调校，先实现有真实单位参考的色温/手动WB控制，再衔接CCT估计与动态LSC；不把灰世界AWB的固定占位色温当测量值。AEC lux函数已定位但调用输入、参考指数/亮度和物理域仍待核对，不能拿曝光EV直接替代。正常光线光学、多摄几何/同步、曝光语义、连续AF等原目标范围保持。
