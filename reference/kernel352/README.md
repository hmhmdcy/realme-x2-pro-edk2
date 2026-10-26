# 352：移植 LTM 逆 Gamma，取得原厂 ICP 固件并核实队列 ABI

2026-10-20。上一轮351属于实质进展：完整原厂LTM/CCM树与原HAL开关已恢复。本轮继续推进后级ISP硬件路径，新增可移植逆Gamma计算、原厂ICP固件及实际固件函数的接口证据。完整目标保持active；没有部署新驱动或改变相机默认。

新增通用 `libipa/ltm_inverse_gamma.{h,cpp}`：64个IFE green基节点（10bit）转为LTM13的64段逆Gamma（14bit基值/有符号14bit差值）。使用独立结果类型，避免与同为64段的IFE Gamma混淆。先重建4096个量化前向值，再按原厂“相同误差取最早索引”规则寻找65个逆向节点，保留平段、非单调输入的行为；没有使用依赖实现的负数右移。尚未接入IPA或硬件。

主机/AArch64以C++17、O2、Wall/Wextra/Werror各检查31项8060字节零差，包含实际原厂IFE green表、线性/反向/平段/端点/突变/非单调及非法输入，NULL和错误输入不会改写输出。参考仅在私有目录编译固定版本原`InverseGamma`、`Pack1D64EntryUnsignedHLUT`和数值辅助函数；缓存命中/未命中输出一致。[数值检查](inverse-gamma-validation.json)。未将参考源码一致性称为实际HAL指令一致性。

首版在非单调/突变案例出现625字节差异，原厂正常曲线未差。原因是原packer会对负差值显式置符号位，超出通常有符号14bit范围时也保留这一规则，普通掩码回绕不等价。已修正前向和逆向打包并重跑相关数值检查；[首份失败](inverse-gamma-r1-validation.json)及两架构原输出保留，没有删除或改称通过。

优先搜索可复用方案，找到CAMSS维护者的[ICP/BPS/IPE原型固定分支](https://kernel.googlesource.com/pub/scm/linux/kernel/git/bod/linux/+/ebd1e440443121d18f730ab2aeea5586a754f36f)。只获取9个相关源/构建文件，共67434字节，没有克隆另一份内核。该提交Makefile引用的`camss-icp-hfi.c`和`camss-bps-cmd.c`在同一目录树不存在，IPE未加入Makefile，所取源中五项IPE会话调用缺定义；不能直接当可构建部署的完整驱动。[固定源](upstream-sources.json)、[复用评估](icp-reuse-assessment.json)。这些结论限定该提交，不推断所有其它树都没有可用实现。

从已有Realme原厂内核镜像固定提交只读取10个SM8150 DT/A5/HFI文件，共131227字节，保留GPL来源。目标使用A5；其FW_VERSION/INIT/共享区/QTBL等CSR偏移与上述X1E80100原型不同。原型使用MDT/PAS加载，不能直接套到旧A5 ELF加载路径。[目标源码清单](oem-icp-sources.json)。SoC资源与HFI后端应独立适配，不改动既有传感器模式/个体调校以绕过差异。

手机只读ro/noload/noexec挂载vendor，定点取得`firmware/CAMERA_ICP.elf`（3630392字节）；普通Linux firmware两个明确候选未找到，未重复读取HAL/大调校包。已卸载并移除临时挂载点，没有读取NV/OTP/EEPROM/persist、没有改安装文件/模块或重启。[本次提取](icp-firmware-collection.json)。固件完整字节只私存kernel352，不镜像。

实际固件是ELF32 little-endian ARM/ET_EXEC，entry0，三个LOAD段位于IOVA0、0x140000、0x340000，运行跨度3686400字节，适配原厂5MiB固件窗口；包含需初始化的零填充/BSS空间。当前DT未观察到camera/icp命名的reserved-memory节点，这不等于不能动态分配。后续还需落实ICP SMMU流、固定固件IOVA及共享/图像缓冲区映射，尚未在手机加载/启动该固件。

固件保留符号，已定位并在ARM Thumb模拟器中执行完整`HFI_QueueGetQHdr`（0x1a971..0x1aa10）。30次查询/1758条原始指令，覆盖三个队列的全部排列及未知ID。确认表头24字节、队列头956字节，按type低字节查找，固定956步进；首字段偏移60，start124、type188、qsize252。固件把qsize按word消费，再乘4决定映射长度；不能照旧注释当byte。[实际固件ABI](firmware-queue-validation.json)。

该函数从固件虚拟CSR0xe0010058读取QTBL指针；这是离线可控寄存器页，不是主机物理MMIO访问。仅对48次tryMemMapping和30次成功assert调用作桩，真正IOMMU映射/固件启动/图像处理未被验证。没有把函数执行结果冒充整固件已运行。

本轮用户空间数值工具可构建；板级DT、主线框架、SoC模块及传感器均未改。SDK/private/camss352-math只有小工具，无work bind；没有相机采集/安装/固件启动worker。当前部署继续沿用349最后观察的338/r27/r22＋344私有默认，350～352新增调校数学尚未安装。下一步353据原厂A5接口补HFI队列、ELF加载/映射后端，再连接IPE会话与libcamera m2m；不能用CPU近似替代并宣称完整硬件IPE适配完成。LTM核心/ADRC、前摄后级矩阵及Gamma仍需组合，AE表/防频闪/传感器限幅、更多模式、光学、多摄几何同步和连续AF仍待。
