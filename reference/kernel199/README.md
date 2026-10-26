# 阶段199：CAMSS运行时MMCX性能请求，恢复正常频率实体取帧

2026-10-15。修复已接入CAMSS运行时PM，保持原VFE/CSID频率表，在未加载独立性能辅助模块的情况下，两轮采到6帧IMX471实体1928×1088 RAW10。静态DT和持久模块尚待成对部署与启动验证，完整外设goal继续active。

## 证据与实现

198的400MHz成功与950MHz复位失败提示频率/性能等级不匹配。本阶段先创建独立虚拟genpd消费者，不改原CAMCC消费者：MMCX聚合等级64→384时原安装CAMSS内部TPG连续3帧成功，移除消费者后回到64。辅助模块默认禁用检查也通过；没有直接改电压或寄存器。

正式驱动改动在`camss-cpas.c`：从CAMSS自己的`mmcx`电源域取得虚拟消费者，运行时恢复先请求原厂最高950MHz档位所需的TURBO384，再设置并启用相机时钟；运行时暂停撤销请求。device link负责供电者随CAMSS运行时状态恢复/暂停。暂停失败会保留性能请求与时钟，并恢复互连带宽；资源释放删除自己的link/消费者。[Linux设备链接文档](https://kernel.org/doc/html/latest/driver-api/device_link.html)说明了这种运行时供电依赖。

源DTS及绑定新增第四个具名电源域`mmcx`，原来的`ife0/ife1/top`保持。SM8150的MMCX索引由实际绑定定义为9，现场provider phandle124；未照搬其它SoC索引。现阶段运行时活动统一按资源表最高档请求384，未实现按传感器模式细分性能等级。

保持原频率表的实体实测：

- 同一普通IMX471、CCI1 master1、CSIPHY2/CSID0/VFE0链路，sensor/CSID pattern0。
- 两次独立STREAMON/OFF各3帧，SRGGB10P1928×1088、stride2416、2628608字节/帧，序号0/1/2、时间戳递增，活动区>99.9%预填充被DMA覆盖。两轮保存的首帧均按RAW10解码，像素/行有变化，帧间不同。
- 两轮活动窗口均观察到CAMSS自己的`genpd:3:acb3000.camss`处于active/384，VFE约847MHz、CSID600MHz且硬件时钟启用；不依赖198的400MHz上限或独立性能辅助模块。
- 两轮之间各进入运行时暂停，自己的MMCX消费者回到suspended/0，再次恢复后又成功出帧。其他消费者保持原请求，最终MMCX聚合回64。

实际CPAS/运行时回调提取的17个ASan/UBSan场景通过，覆盖性能请求失败、时钟失败、CPAS/QoS失败、暂停失败带宽恢复、资源释放等；去除性能请求的变体被测试拒绝。并非硬件故障注入。四域候选板级节点严格schema通过，旧三域、缺少MMCX、错误名称三个反例均被拒绝；不称全板schema验证通过。

## 产物、恢复与限制

CAMSS模块82cbc052…，源CPAS3ee20b59…、core53d8a710…，W=1零诊断。一次纯缩进修正后的重编译模块与实测模块逐字节一致。驱动、DTS和binding分为三份补丁，分别checkpatch及反向apply通过；25个tracked改动及既有11个untracked条目保持未暂存。Image183、canonical DTB22c1f2ad…、config和16793行符号表/770行模块顺序保持。

静态DT候选2e2f8e64…/108410字节，基于canonical22c1…，仅修改CAMSS的`power-domains`和`power-domain-names`。908个节点及其余属性、phandle逐项相同，CAMSS节点schema通过，原文件没有覆盖。此候选尚未打包启动或刷写；新驱动需要四域DT，持久模块仍为旧e9b73f4c…，部署时必须成对处理。

本次热加载为验证新DT契约，overlay替换了两个既有属性，OF框架明确输出两条`memory leak will occur if overlay removed`警告。原生6帧与运行时请求检查通过，但原总警告断言因此失败。两条警告已保留；本轮没有新增内核WARN事件、Oops、GPU fault或SLPI fatal，不能据此称整个实验零警告。后续静态DT启动应避免该属性替换路径，并进行实机复核。

退出后恢复原CAMSS模块及三域属性/22实体空sensor图，临时MMCX辅助、MFD/VIO/CCI/IMX471/overlay模块、适配器及FW全部撤销。三脚实际CTL1/0/1及低输入、七Q LDO采样、P0/Q1恢复，VIO1.8V关/用户0，S8C1.352V/用户3。最后23456.64秒同189第二boot/#183，taint512保留193旧WARN；日志`WARNING:`总3=旧内核WARN1+本轮OF属性警告2，BT重组1为旧记录。三个DSP running、SensorProxy三个Has true、MM191/PowerState3/GPS0保持。没有刷写或重启。

证据：[原生请求与6帧](front-native-validation.json)、[RAW结构](physical-raw-validation.json)、[17项C场景](mmcx-host-validation.json)、[模块](mmcx-module-build-r2-validation.json)、[schema](mmcx-schema-validation.json)、[静态DT](static-dtb-validation.json)、[健康](native-health-validation.json)、[源码与补丁](source-final-validation.json)、[89份私人证据逐成员验证](evidence-export-validation.json)。图像、统计、图像/归档指纹均仅私人保存于`E:\edk2-samurai-out\kernel199`及手机`/var/lib/samurai/k199-*`。

续作：成对准备静态DT/模块启动产物与回退，读取新鲜设备身份后部署，复核冷启及采集/休眠。其它模式、曝光/色彩/方向/光学质量、其它镜头、用户态、长稳和PLDO四路父网络仍待验；GNSS/蓝牙/传感器/蜂窝完整范围见[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
