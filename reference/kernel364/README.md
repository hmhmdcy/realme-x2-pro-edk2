# 364：精确 HFI ready 已应用，IOMMU 回收通过，固件引用故障定位

363在原厂ELF入口的12场景执行中确认：成功路径写响应1，失败写2，早期失败可能保持0。现有356启动代码会在任何非零值退出等待，并允许3后立刻发送SYS_INIT；这可能在明确初始化成功之前交命令。

本候选将轮询终止条件改为1/2/超时，只在1后发送SYS_INIT，保留原500ms计时、错误传播及清理。实际`camss_a5_start()`函数体的ASan/UBSan对照：旧版在`0→3→1`及持续3场景提前发送命令；新版等待1，持续3/0或过期则不发命令，2和命令失败按错误清理，已有资源时拒绝重启。8组修后检查通过，旧正常1及显式2行为保持。[补丁](exact-hfi-ready.patch)、[回归](start-regression-validation.json)。平台、电源、MMIO轮询和清理提供者是桩，没有替代真实A5启动证明。

363启动验证后，已在维护树应用为`4b5849db2cddf90e2961b55065fc1f3deb42762d`，随后诊断提交`1947eb706d0650c1515b44fc7c1d70c6077a6256`单独检查实时固件引用。核心、临时boot/memory模块在k363构建树中W=1/-Werror通过，没有更换已安装CAMSS模块或默认配置。

新内核的实际SMMU实验映射5MiB／1280页，核对并全部解除映射；组中只有实验设备，没有启动A5。模块与动态节点全部移除，taint0，无OF/IOMMU新故障。[内存实验](memory-runtime-r1-validation.json)。因此357框架引用修正已经进入实际Image并能正常回收实验节点。

第一次boot实验在资源初始化返回-22；第二次添加精确引用诊断后确认`of_parse_phandle(memory-region,0)`为空，返回-ENXIO，两次A5均未启动。原因是356通过overlay的`__overlay__`根给已有预留节点增加phandle，离线fdtoverlay允许，而当前内核实时overlay跳过已有节点的phandle伪属性。[诊断](live-reference-diagnosis.json)、[首份失败](boot-runtime-r1-validation.json)、[精确诊断](boot-runtime-r2-validation.json)。两次17路ICP/BPS/IPE时钟归零、CAMSS休眠、临时固件/模块/节点全部释放，taint0。没有放宽5MiB/no-map/独占资源检查，也没有把这次早期失败归因于HFI等待条件。

365将SoC资源和Realme固件预留区关联写入静态DT，366把DT装入实际EDK2固件卷后再测。尚无真实完整HFI或IPE图像会话，离线ELF指令执行和桩回归不能替代它们。
