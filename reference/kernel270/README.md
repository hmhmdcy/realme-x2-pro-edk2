# 270：恢复相机实测与第二颗后摄适配（进行中）

后续实景复测：用户确认调整正常照明、无遮挡场景后，两后摄各36帧及JPEG再次通过；长焦原图已能辨认真实场景，明显欠曝且噪点重，画质不验收。24组同request RAW/RGB中，2ms RAW均值65.79；32ms均值93.22/std16.79/max145，显示曝光和空间响应。本次没有改软件，旧暗场证据保留；下文“仍近黑电平”描述调整前场景。[光学核看](scene-r2-optical-review.json)、[配对](paired-scene-r2-validation.json)、[JPEG](rear-jpeg-scene-r2-validation.json)、[回收健康](scene-r2-health-validation.json)。分层与升级维护判断见[审计](LAYERING-AUDIT.md)。

2026-10-18。当前目标是继续摄像头适配，明确多颗后摄与骁龙硬件 ISP 的真实支持范围；完整目标未完成。本目录的当前事务只允许在核对其状态后续作，不能重放已完成的安装、启动、刷写或拍摄动作。

## 当前部署与最新结论

boot270已实际刷写并逐字读回，Image183不变，774模块/961包；270新guard及现机状态以[检查点](../../NEXT-SESSION.md)和[实际绑定](postboot-hardware-validation.json)为准。S5K3M5已过chip-ID与RAW/RGB采集，三摄14段192帧交替/中断/重开通过。两后摄可生成JPEG，但长焦真实样本仍是暗场，光学成像未验收；物理sensor彩条正确，24组RAW/RGB曝光统计仍近黑电平。[回归](three-camera-regression-validation.json)、[两后摄JPEG](two-rear-jpeg-validation.json)、[彩条](telephoto-bars-validation.json)、[曝光](telephoto-paired-validation.json)。

以下准备段按部署前阶段解释；本轮已部署，不可重复切换。

## 当前已取得的新证据

- 同269启动下，标准 `cam` 对 IMX319 后摄连续采集24帧，序号0—23；关闭后双sensor suspended、四路camera电源disabled/users0，新增warning/Oops/GPU/modem/fatal均0、taint0。[实测](native-rear-validation.json)。
- Snapshot通过实际观察到的桌面/AT-SPI控件激活，前摄快门、切换后摄、后摄快门、正常quit均通过，新增fault0，电源/时钟正常回收，没有强杀。两张本轮GUI JPEG已按哈希分块取回私人目录；IMX319样本可见真实场景，但图像方向、低照度、颜色和成像质量仍待校准。这不证明之前的modem watchdog已修复。[GUI](snapshot-gui-r1-validation.json)、[私人样本传输验证](gui-photo-collection-validation.json)。

## S5K3M5长焦候选

已从旧240候选移除lab PMIC子设备搜索、供应者驱动名检查、专用compatible和传感器内部固定电压设置。标准 `samsung,s5k3m5` 根据19.2/24MHz输入时钟选择寄存器配置；本机电源、GPIO23、MCLK3/GPIO16、CCI1/master0/0x2d和CSIPHY3由静态DTS提供。P L2/L6由公共PM8008/regulator管理，AF actuator保持独立，未新增运行时OF补节点。

917条初始化及53条模式3寄存器来自之前独立核对的本机OEM资料；首个候选仅提供2104×1560，723.2MHz link仍是待实测的PLL候选，不能把离线值当物理测量。原24MHz模式保留，尚未在24MHz设备回归。

[源核对](telephoto-source-validation.json)、[本机接线核对](telephoto-board-source-validation.json)、[匹配现机模块](current-module-build-validation.json)、[设备树](telephoto-board-build-validation.json)、[实际供电函数882个API故障模型](telephoto-power-validation.json)。模型不等于内核并发或硬件故障注入。

第一次匹配模块构建缺CCI共同目标，被modpost正确拒绝；第二次误请求不存在的独立CCI-I2C目标，失败资料保留。第三次共同构建实际v4l2-cci和sensor成功，W=1零诊断；现机CCI与该构建逐字一致，无需替换。原canonical源码/配置/Image均恢复。首轮DT schema拒绝未描述的power-domains，已在标准sensor binding补充必要属性，四类schema通过；未通过删掉实际资源规避检查。

## 部署事务

新S5K3M5模块已安装但未加载，模块数773→774，其余773模块逐字不变，APK数据库保持。只更新DTB的boot270已构建并核对：固件代码、BootShim、Android镜像头、ramdisk、compat DTB和分区尾保持，Image183/logdump不变。板级新增10节点，既有节点只改变CCI1/master0的status；现有前后摄及其它外设属性语义保持。

[暂存](module-stage-validation.json)、[boot候选](build-package-validation.json)、[回退](rollback-validation.json)。原boot267和手机/PC两份模块事务回退保持。私人输出在 `E:/edk2-samurai-out/kernel270`，匹配候选源码位于WSL `camera270-kernel` / `samurai-multicamera270`；旧269完整内核构建保持。

本段记录的是启动切换准备状态；后续须查看本目录quiesce/flash/postboot收据和根检查点判断实际设备状态。不要仅凭本段猜测是否已刷写。当前host.py只绑定切换前269启动，重启后必须独立核对并建立新的guard。

## 多摄与ISP的未完成范围

当前IMX471前摄、IMX319后摄及S5K3M5长焦均已真实绑定/采集。S5K3M5的chip ID、RAW/RGB、彩条和JPEG编码已验证，但真实光学场景仍近黑电平，新启动三摄GUI与AF尚待验收；S5KGW1主摄和候选人像sensor未完成，不用厂商库文件名证明本机sensor已识别。多个实体后摄的切换、并发、AF和录像均未验收。

当前链路是sensor→CSIPHY/CSID/VFE RDI→RAW→libcamera CPU software ISP；使用了骁龙相机采集硬件，不等于接通Spectra硬件去马赛克、降噪、HDR等图像处理。GPU软件ISP仍有既有故障，亦不是Spectra。上游CAMSS/OPE工作仅作参考，不能从其它SoC的补丁推断SM8150支持。


## 主摄后续输入

本机Sunny/Qtech S5KGW1各10个模式和51条初始化已通过边界解析和两种独立schema视图交叉核验，保留11条突发写入及真实uint32向量。没有主摄硬件操作，不能把数据解析当成支持。[数据](gw1-metadata-validation.json)、[交叉核对](gw1-crosscheck-validation.json)。
