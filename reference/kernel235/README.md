# 235：IMX319 真实驱动、独立 P 两路供电候选与磁盘暂存

用户延期前摄纯色参照，继续推进其它适配。本轮实现并构建了真实 IMX319 OF/runtime 驱动及严格 L1P/L4P 供电模块，生成新设备树和启动包，三个模块已原子暂存到手机磁盘。**当前仍为233启动、232驱动在运行；候选未加载，未读到新的后摄ID，也未完成后摄出帧。** 完整适配goal保持active。

## 已完成与证据边界

- 在独立分析副本运行原厂XML reader，Sunny/Qtech的global 136条与1632×1224模式171条都交叉一致。原始BIN和payload保持。模式为四lane、RAW10、RGGB，LLP2080/FLL3350、初始HBLANK448/VBLANK2126。保留原厂PLL；XML的177.6MHz与30fps不自洽，不能直接作为阵列时钟。222MHz链路/209066666Hz阵列时钟是推导候选，须用真实SOF验证。[表](imx319-oem-tables.h)
- 新增独立实验regulator cell/模块，只允许P的L1=1.104V、L4=2.8V、mask0x09；Q原regulator不改。其它五路不注册、不写入，只有整芯片ENABLE只读审计会读取其使能位。未知VIN不编造、不挂dummy供应者；这仍不是完整产品供电描述。[供电源码](qcom-pm8008-imx319-lab.c)、[父状态](qcom-pm8008-imx319-lab.h)
- VSET前确认关闭，写后双字节核对；ENABLE失败及READY超时在回调内清理。fault属于父MFD生命周期，不能靠child重探测清除。全局0x0950仅接受0/1并只操作bit0；原先为1则保留。无法确认OFF/恢复全局时，只通过父独占reset句柄断言P，不释放、不脉冲、不操作Q。仅assert和status均成功才记录隔离；失败保留不确定状态且同周期不重复reset。隔离不等于恢复原寄存器，也不等于物理电压测量。[MFD](qcom-pm8008.c)
- 对真实regulator core和devres顺序复核：成功隔离后`.disable`返回0让core正常平衡引用；不改core私有计数。若I²C关闭和独立P复位同时失败，仍有未回收引用/退出WARN风险，不能宣称所有硬件失败都已封闭。
- IMX319 OF使用三路真实supply、MCLK1、reset、TITAN_TOP GDSC，managed link明确依赖实验regulator child。上电顺序为pinctrl/default、reset断言、VANA、VDIG、VIF、MCLK、reset释放；掉电反序回收并切sleep。GPIO/pinctrl返回值检查，成功enable才持有各路标志，失败disable不清标志。runtime回调不递归拿controls mutex，重复stream不重复获取/释放PM引用。原ACPI八模式及数据表保留。[驱动](imx319.c)、[补丁](imx319-rmx1931-of-runtime.patch)
- 只在已确认ID后尝试失败路径standby。运行时ID读取失败/错ID时零sensor寄存器写入，直接同步挂起回收供电。此修正避免统一清理向未确认器件写0100。370个实际power/identify/table-writer/stream C函数测试通过ASan/UBSan，覆盖308个配置写入失败位置，四个删除防护负对照均被拒绝。[传感器测试](imx319-fault-validation.json)
- PMIC实际C回调465例及三个负对照、MFD实际编排40例及两个负对照通过。host模型对I²C部分写入、持久错误、READY、GPIO/时钟/pinctrl和引用计数作API结果模拟；不代替真实kernel并发、regulator注册或硬件测量。[供电测试](lab-fault-validation.json)、[MFD测试](mfd-profile-validation.json)
- 三模块真实树内W=1零诊断、intreeY、匹配183 ABI且导入符号均存在。构建用`CONFIG_REGULATOR_QCOM_PM8008_IMX319_LAB=m`和`CONFIG_VIDEO_IMX319=m`覆盖，未伪造模块元数据。每次构建后canonical after228、原Q源码、对象与全局构建元数据都恢复。[PMIC构建](pmic-build-validation.json)、[传感器构建](imx319-build-validation.json)
- 原机两份overlay、stock base及锁定19781源码确认CCI0/master1、0x10、GPIO14/MCLK1/19.2MHz、reset30、CSIPHY1。MCLK active/sleep均6mA，reset2mA，sleep output-low；不复制前摄管脚参数、不添加无依据的lane polarity。新DTB相对真实232仅新增12个节点、改变CCI0/master1状态及P实验marker；真实camcc/GDSC/时钟/supply phandle、双向endpoint、四lane均逐项核对。[板片段](imx319-p-lab.dtsi)、[DTB核对](board-build-validation.json)
- 启动包解包证明只有内嵌FDT变化，固件代码、183 Image、logdump、shim/ramdisk/header/兼容DTB/尾保持。固件有30条既有诊断、无新诊断模板；不是整个固件零warning，也未重建完整kernel/rootfs。[启动包](build-package-validation.json)
- 已原子暂存MFD替换及lab、IMX319两个新增模块，共775ko/789相关文件，depmod/加载参数、provider先于MFD及两种modalias核对通过。旧文件、14个元数据和原配置有私有回退副本；当前加载note仍为232 MFD，未热卸P/Q、未加载候选、未重启或刷分区。[暂存](module-stage-validation.json)
- 暂存后当前boot身份、分区读回、原前摄/CAMSS/FastRPC/BT/provider加载note通过，P仍无secondary，前摄/CCI/CAMSS suspended。taint0，WARN/Oops/GPU/DSP fatal/BT重组0，三个DSP running、SensorProxy三Has真、BT关且无连接。原生收据私有保存，无场景像素或公开私人标识。[健康](final-health-validation.json)

首个DTB校验脚本误把DT标签当regulator-name，编译本身成功、校验退出；改为从已部署前摄真实vif phandle解析，并在独立r2目录通过。早期构建/模型失败和每版源保留在私有证据，不改成“首次全过”。脚本是已执行操作收据，带一次性目录与旧启动guard，不能直接重放。

## 继续执行与回退

下一步准备新的受控过渡：重新核当前身份和暂存清单，清理相机端点而保留P/Q/provider，执行一次bootloader切换，再用fresh fastboot身份/几何只刷锁定235 boot一次。建立新boot guard后先查P两路/ID/自动挂起，再做真实RAW的RAM统计，确认回收后补前摄回归。不得把旧235/233摘要当新启动证据。

回退基线是当前232 boot及`k235-module-stage/before`、原loader配置；219旧回退另行保留。回退必须核新身份，恢复三个模块路径/元数据/配置，再正常重启；不热卸存在children的MFD，不覆盖NV、校准或工厂备份。

GNSS研究修正：本树QRTR namespace只接受本地lookup观察者。MPSS可在自身namespace等待AP公告，因此“AP没有看见MEMSHARE52 lookup”不能排除固件需求；`qrtr-lookup`也不能证明MPSS发起了请求。现有trace不含服务参数，不能假称可据此得出需求结论。仅为此增加一轮内核部署价值不足；不注册伪服务、不盲分配MEMSHARE，真实正CNR/TRACK/fix继续开放。

BT历史phase5、其它后摄、SIM业务、传感器精度/PM、GPU ISP等仍见[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。前摄纯色校验保持延期，不重复追问。
