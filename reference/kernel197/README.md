# 阶段197：修复CAMSS端点校验，建立实体前摄媒体链路

2026-10-15。完整外设goal仍active。本阶段修复CAMSS拒绝Qualcomm D-PHY时钟lane 7的问题，普通IMX471成功连接到CSIPHY2/CSID0/VFE；实际取帧仍失败，不能称摄像头已可用。

## 已修复并验证

- 阶段124的通用端点校验只接受clock lane 0–4，因而196的真实`clock-lanes=<7>`端点在CAMSS重新probe时返回`-EINVAL`。保留数据lane范围、重复和C-PHY检查，允许Qualcomm固定D-PHY clock lane 7。[官方内核绑定](https://android.googlesource.com/kernel/common/+/fb73974172ff/Documentation/devicetree/bindings/media/qcom%2Ccamss.txt)解释了该硬件编号；本机OEM SM8150 DTS中的CSID地址/中断也已核对。
- 直接提取实际解析函数的29个场景通过ASan/UBSan；旧函数在真实lane 7配置上失败。候选树内CAMSS模块W=1无诊断，标准媒体/V4L2采集工具通过host、QEMU及原生自检。新增两个Alpine视频工具包采用正常签名验证和离线安装，没有升级ModemManager。
- 通过普通CAMSS重新枚举与IMX471异步绑定，出现23个媒体实体及`imx471 7-0010 → msm_csiphy2 → msm_csid0 → msm_vfe0_rdi0 → msm_vfe0_video0`。三次物理采集尝试均明确关闭sensor和CSID测试图案，设置1928×1088 packed RAW10，stride2416、sizeimage2628608。

## 仍未通过的实机部分

1. 第一次CAMSS端点刷新被旧clock lane校验拒绝。修复后，三次物理采集均在CSID复位超时返回`-EIO`，没有收到帧，也没有生成RAW文件。超时诊断增加了标准驱动内的只读版本/IRQ/mask/strobe信息，四项均为0；CSID中断计数未增加。
2. 活动窗口的三个独立快照显示TITAN/IFE0域on，IFE0时钟约847MHz、CSID600MHz和CPHY RX400MHz均报告硬件启用。core AHB80MHz却是enable/prepare4而硬件N。该不一致是后续调查线索，尚未证明根因，也不能直接归咎传感器或CSI走线。
3. 移除实体传感器后，原模块和新候选模块各执行一次320×240内部TPG对照，都在VFE复位超时失败。阶段126的3帧TPG成功仅是历史证据，不能代表当前#183/同189 boot状态已通过。下一步应核对复位/时钟/PM时序及当前控制路径，再继续实体帧。

## 恢复与证据

四轮完整前摄会话均保留，另有一次在加载overlay之前发现准备目录名称不匹配的脚本错误；该次只建立空证据目录，未探测或采集。首份宿主错误日志被通用runner后次覆盖，错误原因保留在本报告；四轮原生会话和构建失败日志完整保留。本阶段单模块modpost缺VB2导出；最终按实际Kbuild组合目标链接videobuf2-common/memops/v4l2/dma-sg与CAMSS，最终W=1零诊断。

所有临时IMX471、PM8008、VIO、CCI、overlay模块/节点/适配器及固件文件已移除；原CAMSS模块e9b73f4c…和无传感器拓扑恢复。实际GPIO12/15/29 CTL1/0/1与低输入、七Q LDO采样、P0/Q1均恢复。主要相机时钟引用在退出后与196基线逐项一致；活动窗口的不一致未被隐藏或直接MMIO改写。

最后健康检查21014.32秒，同189第二boot/#183，taint512保留193历史WARN；全boot WARN1/Oops0/GPU fault0/SLPI fatal0/BT重组1，无本阶段新增所列故障。ADSP/SLPI/modem running，SensorProxy三个Has true，MM191未变、PowerState3/GPS0。VIO1.8V关闭/用户0，S8C1.352V/用户3。没有刷写、重启或修改校准/NV。

源码新改动仅CAMSS端点校验和超时诊断，196相机代码及此前14个其它tracked源哈希保持；21个tracked改动，6个相机新文件和5个既有备份保持未暂存。Image183/DTB/config及16793行符号表/770行模块顺序恢复。CAMSS候选仅临时加载，持久模块未替换。PM8008四路PLDO父网络仍未知，不将开发overlay称为完整上游板级DT。

证据入口：[端点回归](camss-lane-host-validation.json)、[原生链路与失败边界](front-native-validation.json)、[健康](native-health-validation.json)、[源码/补丁](source-final-validation.json)、[归档逐成员校验](evidence-export-validation.json)。原始日志、模块/APK、网络身份与私有采集目录保留在`E:\edk2-samurai-out\kernel197`及手机`/var/lib/samurai/k197-*`，未发布。

GNSS有效fix/CNR、蜂窝注册与数据/通话/SMS、蓝牙剩余重组/长稳、传感器普通信号/freezer/共享池和物理变化验收继续开放，见[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
