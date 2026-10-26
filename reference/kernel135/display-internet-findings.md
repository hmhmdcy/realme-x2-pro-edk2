# MDSS 首次显示交接检索（2026-10-12）

已实际搜索 SM8150/DPU/CTL_SW_RESET/autorefresh/handover，阅读 Linux 主线源码和原厂固定提交。此前阶段134的继承 INTF 停帧和 CTL reset -22 仍为待修故障，不能用面板重新绑定恢复作为永久修复。

一手来源：

- [Linux MDSS 初始化](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/msm/msm_mdss.c)：可选 reset 在 MDSS 初始化前执行 assert、20ms、deassert；本地134源码同样已有此路径。
- [实际 SM8150 显示时钟提供者](https://github.com/torvalds/linux/blob/master/drivers/clk/qcom/dispcc-sm8250.c)：共同驱动匹配 qcom,sm8150-dispcc，CORE_BCR 的映射为0x2000。SM8150/SM8250 两份本地 header 的 CORE_BCR 均为0，实际 DT 提供者 #reset-cells=1。
- [显示通用绑定](https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/display/msm/mdss-common.yaml)：允许一个 MDSS_CORE reset。实际前后板 DT 的 SM8150 MDSS schema 均零诊断。
- [SDM630 missing MDSS reset 修复](https://lkml.iu.edu/2602.3/09565.html)：另一平台的失败/修复提供方向，不能据此证明本机相同根因；本轮依据本机 provider、header、完整 DT 和 native probe 形成候选。
- 原厂 [固定源码提交](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/tree/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6)：已下载 sde_hw_ctl/intf/encoder_phys_cmd/encoder/catalog 固定文件，核对 reset poll 和 override；未使用猜测寄存器或额外硬复位绕过。

本轮只增加 `&mdss { resets = <&dispcc DISP_CC_MDSS_CORE_BCR>; };`。完整909节点仅这一属性变化，原134源码、Image、DTB和模块保留；UEFI其余执行模块逐字节保持，候选实际部署记录见 boot-package-validation 与私有 flash-validation。软件版本仍134，设备树候选阶段135。搜索与静态检查不能替代首次启动或长期稳定验收；GPU131迟发CCU故障独立未修。
