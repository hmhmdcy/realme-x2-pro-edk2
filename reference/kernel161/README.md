# 161：空 RMR 列表不再关闭 SMMU 客户端的候选

160用户把剩余白屏花屏定位到edk2画面消失后、Linux命令行出现前。158已解决已测唤醒闪屏并把Phosh启动提前至约20秒，但仍不能验收整体显示BUG。

本机采用DT启动，没有ACPI IORT RMR条目。当前arm_smmu_rmr_install_bypass_smr在列表为空时仍设置sCR0.CLIENTPD，再由后续reset恢复；这种中断可能影响仍在取帧的固件显示。161在空列表时直接返回，非空RMR和正常reset保持，不开启全局DMA bypass。[候选补丁](skip-empty-rmr.patch)

实际从内核文件提取函数编译测试：空列表的两种初始客户端状态不读写MMIO；无SID条目、单SID、多条目、已有引用、找不到SME等非空场景与旧函数完全相同。7项普通和ASAN/UBSAN通过，旧函数作为负对照在空列表检查失败。[真实函数验证](actual-function-test-validation.json)

完整W=1、Image/模块/DTB构建和FAT检查通过，770模块中768字节完全一致，2个仅GNU build-ID不同，模块132兼容复用。只刷logdump161，实际新boot自动进入桌面。[构建](build-package-validation.json)、[模块兼容](module-compatibility-validation.json)

该次实机启动没有KMS/DSI/DPU/GPU错误，但出现1个WCD934x efuse状态读取WARN，ret=-22、taint512；SLIMbus DMA prepare失败累计917条，Phosh24.04秒。27.47秒采样中计数稳定，不能据此验收新启动。候选与音频故障的因果关系未证明；实体白屏效果也未观察。候选拒收并保留现场。[失败运行验证](runtime-validation.json)、[启动顺序](startup-order-validation.json)

162按新161启动身份完成正常停机和F2FS冻结，只刷回独立的原始158 logdump。新158自动桌面、Phosh20.24秒、全boot关键错误和音频DMA prepare均0、taint0。SMMU源码已恢复，161补丁不进入后续候选；其余14个显示文件、配置和其它源码改动保持。[源码恢复](source-restoration-validation.json)、[回退记录](../kernel162/README.md)

私人161启动档案SHA256：`0e26fec7e028a9af61dd80d5896e026f070d51f288ab071bfe3fd649ed42f67f`。测试通过只证明所测代码分支，不代表硬件根因或整体显示BUG已修复。

一手依据：[内核现有RMR流程](https://kernel.googlesource.com/pub/scm/linux/kernel/git/jack/linux-fs/+/4b84a4c8d40dfbfe1becec13a6e373e871e103e9/drivers/iommu/arm/arm-smmu/arm-smmu.c)、[RMR设计讨论](https://lists.infradead.org/pipermail/linux-arm-kernel/2021-May/655944.html)、[Qualcomm继承固件SMR讨论](https://lkml.rescloud.iu.edu/2010.2/02561.html)。这些来源解释代码行为，不能替代本机实体画面验收。“preserved 0 boot mappings”只指ACPI RMR数量，不能推断DT Qualcomm路径没有继承SMR。
