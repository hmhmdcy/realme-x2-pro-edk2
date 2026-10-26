# 阶段198：前摄首次实体RAW取帧，定位高频运行问题

2026-10-15。IMX471通过普通驱动和真实CAMSS链路，连续采到3帧1928×1088 RAW10；sensor与CSID测试图案均为0。该结果来自临时400MHz配置，完整相机和其它外设goal继续active。

## 本机对照结果

| 配置 | 结果 |
| --- | --- |
| 原安装CAMSS，950MHz TPG | VFE复位超时，0帧 |
| 同等最高频率、增加只读时钟诊断 | VFE复位超时，0帧 |
| 只读诊断及SM8150 VFE/CSID最高400MHz，内部TPG | 320×240，连续3帧，活动区预填充全部被DMA覆盖 |
| 同400MHz配置，普通IMX471/CSIPHY2/CSID0/VFE0实体链路 | 1928×1088 SRGGB10P、stride2416、2628608字节/帧，序号0/1/2、时间戳递增，活动区超过99.9%被不同缓冲区预填充值以外的数据覆盖 |

实体首帧已按MIPI packed RAW10结构解码，确认像素值和行数据变化，排除未写入的预填充或恒定缓冲。保存的RAW、图像统计、哈希、采集原始日志及包含图像的归档校验值仅在私人证据目录；公开报告不展示画面或图像指纹。没有证明曝光、颜色、方向、光学质量、其它模式或长时间稳定性。

## 更新故障判断

独立tracefs instance捕获1762/1762条CAMCC regmap/时钟记录，没有丢事件。普通框架向core AHB的0xc1c8写1后，后续读回0，期间没有软件写0；原root tracer/on/events状态保持，私有instance退出后删除。树内临时诊断模块进一步确认：`soc_ahb`刚启用、VFE复位之前就返回hw0。

关键的反证是：400MHz TPG和实体取帧成功时，core AHB仍返回hw0。因此197的“引用非零/hwN”不能单独作为复位失败的原因，不能据它直接修时钟门控寄存器。这里没有直接MMIO写，也没有强制门控或绕过保护。

当前上游CAMCC DTS只请求MMCX low-SVS，而无传感器时CAMSS选择VFE最高950MHz。本机原厂CAMCC的VFE400MHz对应较低电源等级，高频有不同等级；临时实验只将SM8150四个VFE/CSID资源表的上限/固定源档位收敛到400MHz，没有改其它SoC、充电、电压或性能等级。950失败/400成功证明频率配置相关的区别，尚未区分MMCX等级、PLL/高频配置及其它时序原因。不能把临时限频直接作为完整的动态频率/供电修复。

原厂与上游的core AHB定义均是0xc1c8、BIT(0)、BRANCH_HALT_DELAY：[原厂内核源](https://android.googlesource.com/kernel/msm/+/ae8d33fa220cfd210a0983ed27d09662753c5b75/drivers/clk/qcom/camcc-sm8150.c)、[上游源](https://code.googlesource.com/linux/torvalds/linux/+/8abc1c8badc11c859bb4ba43211611347e59c55c/drivers/clk/qcom/camcc-sm8150.c)。本机GPL源码中的时钟/CSID/VFE契约另外保留私人副本与可重复检查脚本；没有复制其它机型的供电或GPIO。

## 产物与恢复

- 只读时钟诊断模块cc3ebabf…、400MHz诊断模块9c637d05…均由树内Kbuild生成、W=1零诊断，补丁apply/checkpatch通过。默认关闭诊断，加载时显式启用。编译后立即恢复三个源码文件、config、符号和模块顺序；当前内核源码仍为197状态，没有把临时限频写进最终源码。
- 实体会话退出后恢复原CAMSS模块e9b73f4c…、22实体无sensor图，移除临时overlay/IMX471/MFD/VIO/CCI/适配器/FW。实际三GPIO输入低、CTL1/0/1和七Q LDO采样一致，P0/Q1，VIO1.8V关/用户0、S8C1.352V/用户3。
- 八个相机时钟的enable/prepare引用均回到基线。VFE/CSID最后编程值分别约400/400MHz，基线约950/600MHz；不声称所有时钟速率恢复。模块恢复不自动恢复闲置时钟的最后频率。
- 最后22018.82秒，同189第二boot/#183，taint512和旧WARN1/BT重组1保留，Oops/GPU/SLPI fatal0；无本阶段新增所列故障。三个DSP running、SensorProxy三个Has true、MM191未变/PowerState3/GPS0，没有刷写或重启。

证据：[原生对照与实体帧](front-native-validation.json)、[RAW结构校验](physical-raw-validation.json)、[退出时钟](exit-clocks-validation.json)、[健康](native-health-validation.json)、[源码恢复/补丁](source-final-validation.json)、[87份私人原生文件逐成员校验](evidence-export-validation.json)。私人证据在`E:\edk2-samurai-out\kernel198`和手机`/var/lib/samurai/k198-*`。

接下来应在原厂支持的性能等级范围内，用正常genpd/RPMH/OPP接口验证最高频率所需条件，并检查PLL/高频配置，再实现动态供电与频率管理。保留本轮400MHz实体3帧作为可复现实机基线；之后还需更多模式、其它镜头、冷启/休眠/长稳、用户态相机和完整硬件验收。PLDO四路父网络仍未确认，GNSS/蓝牙/传感器/蜂窝剩余问题见[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
