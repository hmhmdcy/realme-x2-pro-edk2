# 显示接管资料与本机判断

2026-10-10查阅主线源码与维护者原始讨论。当前实际源码基线是
Linux v7.3-rc6+a90ee4305c4a5df72c11b31dacfdc76e00fcf78a。

[2021年Bjorn/Dmitry的原始清理方案及评审](https://lists.openwall.net/linux-kernel/2021/05/12/3502)
描述了引导器遗留CTL数据路径与新显示路径冲突，提出清空各LM图层、刷新CTL后启动。
评审明确要求验证command mode。这为本次LM清理顺序提供线索，不能直接当本机验证。

[2022年CTL_FETCH_ACTIVE讨论](https://lkml.iu.edu/hypermail/linux/kernel/2202.2/01145.html)
限制方案于支持该特性的DPU，并讨论video和command触发的区别。本机DPU5.0.1的
set_active_fetch_pipes能力仅在本地源码core>=7时注册，不能使用单纯FETCH_ACTIVE清零。

[主线Qualcomm SMMU源码](https://github.com/torvalds/linux/blob/master/drivers/iommu/arm/arm-smmu/arm-smmu-qcom.c)
为sm8150-mdss匹配identity默认域。实际msm_kms_init_vm通过iommu_attach_device换为
paging域。本机旧故障地址在保留的物理splash区域，故障在原生面板首次启用前出现。
结合CTL0的真实CMD标志和非零LM图层，推断遗留取数在域切换后访问旧物理地址。

最终本机实现先停止遗留DSI INTF1自动刷新，按旧高度有界等待帧结束，再关闭TE。
只对sm8150-dpu、CMD_TOP bit17且有旧图层/fetch的CTL执行有界复位，解除INTF/DSC/
merge3d、清空LM并刷新/提交，最后再复位以取消等待TE的空kickoff，随后才切IOMMU。
前三版逐步暴露暖重启、去掉start和未结束旧帧的失败，均归档；#68两次自动启动
完整日志与18次显示循环决定最终本机结果。仍保留SMMU；其它板、video-mode、
无缝保留splash、实际冷断电与休眠不在已验范围。

下一项GPU参考：主线SM8150 HDK使用板级签名zap路径，详见
[主线板级DTS](https://code.googlesource.com/linux/torvalds/linux/+/10dd1a736d557e310a77117832874729a0175d57/arch/arm64/boot/dts/qcom/sm8150-hdk.dts)。
[OnePlus hotdog固件仓库](https://github.com/sm8150-linux-mainline/firmware-oneplus-hotdog)
仅作命名/布局参考；本机固件来自自己的vendor只读提取，不能拿其它手机的签名blob替代。

后续清单的Wi-Fi总线按实际sm8150.dtsi的wifi@18800000与ath10k/snoc.c的
qcom,wcn3990-wifi platform匹配更正为SNOC；节点仍disabled，没有启动或流量验收。
