# 266：相机架构复核与标准元数据候选

2026-10-18。用户明确要求以主线Linux为基础、复用SM8150公共支持、以RMX1931设备树描述硬件差异，并尽量保持发行版和应用无需修改。核对结论是**部分符合，尚未完成**。

| 原则 | 当前实现与差距 |
| --- | --- |
| 主线内核基础 | 当前源树Makefile为7.3.0-rc6，现机release为7.3.0-rc6-rmx1931-samurai-k132+；来源和上游分支见[来源记录](../../linux-port/docs/22-kernel-upstream.md)及[源码整合](../kernel249/README.md)。属于主线基础加下游补丁，尚非所有修改已进入上游。 |
| SM8150公共支持 | 复用CAMSS、CCI、时钟、pinctrl、regulator和V4L2框架；仍有SM8150扩展和实验性供电provider，不能称只靠现成上游驱动。 |
| RMX1931设备树描述差异 | [相机DTS](imx319-p-lab.dtsi)已描述供电、reset、MCLK、CSI端点及通道。已部署[IMX319驱动](../kernel235/imx319.c)仍有机型profile、PM8008 lab supplier查找与板级上电耦合，需继续正式化。传感器寄存器模式留在传感器驱动，不把命令表搬进DT。 |
| 发行版和应用尽量不改 | Snapshot应用二进制未修改，标准V4L2/libcamera/PipeWire接口正在使用；libcamera及PipeWire/GStreamer仍带本地公共层补丁，Snapshot仍有Cairo CPU启动配置。原生APK打包不等于发行版原包无修改。 |

已部署的[265公共缓冲修复](../kernel265/README.md)供标准客户端共同使用，生产复制开关已移除。其缓冲引用/图退役问题属于公共用户态库；强行挪入内核不会修复用户态对象生命周期。应维护最小公共补丁并争取上游合入，硬件缺失则修在驱动/DTS，图像调校放在libcamera通用机制下。

## 本轮候选调整

现机仍是265部署，本轮没有刷写、重启、卸载或安装驱动。

IMX319标准Selection API候选从既有九组寄存器表解码模拟裁剪范围，所有寄存器表保持不变；[独立几何检查](geometry-source-check-validation.json)通过。原生数组范围由现有模式表推导，未取得Sony有效像素阵列规格证明，不能扩大为厂商规格认证。

原r1/r2候选曾在RMX1931 profile里提供后摄方向默认值，**未部署且已放弃**。当前候选仅通过标准fwnode读取方向，后摄`orientation = <1>`仅在RMX1931 DTS中；未知rotation保持未设，不直接把OEM roll值等同Linux rotation。[调整核验](device-tree-alignment-validation.json)。既有lab供电与模式profile仍存在，本次元数据调整不代表这些债务已清理。

当前r3模块构建见[构建收据](imx319-build-validation.json)：37312字节、SHA256为34f7c82a153e20273c153c41719bdb6eeb7c02ccce8cd033321f3bd402678d7a，W=1无诊断、导入符号与vermagic匹配，canonical构建树已完整恢复；r1/r2历史收据保留。离线编译及静态检查不代表新模块、DTB或跨启动已实机验收。当前启动DT没有后摄orientation属性，不能仅换模块就宣称方向已修好；后续需构建配套DTB并按当前设备状态验证。

后续优先：正式regulator/MFD供电关系与标准sensor binding、SM8150公共驱动中的通用修复、最小用户态补丁、完整源码构建与配套启动验收。后摄低照度、颜色、GUI切换、录像和其它后摄仍开放。
