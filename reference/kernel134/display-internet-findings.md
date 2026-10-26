# 阶段134：显示启动失败检索与边界

2026-10-12。实际搜索了 DPU/CTL/boot/reset/handover 与 dpu_hw_ctl_reset_control，并阅读以下原作者邮件和补丁。没有找到已证明能修复本机这次启动的现成补丁。

- [2022年 boot loader 数据路径清理提案](https://lkml.iu.edu/2202.1/09164.html)：指出启动画面路径与 Linux 新路径、IOMMU 交接可能冲突；修改 CTL_FETCH_PIPE_ACTIVE 的提案不能自动等同于本机命令模式停帧和复位成功。
- [原作者及维护者讨论](https://lkml.rescloud.iu.edu/2202.1/10016.html)：强调连续启动画面交接涉及 clocks/regulators/power domains，临时清理不是完整继承方案。需要结合本机状态和完整时序证明。
- [SDM630 missing MDSS reset 修复](https://lkml.iu.edu/2602.3/09565.html)：另一平台的 CTL reset -22 有明确缺失 reset 属性；本机为 SM8150，不能直接添加同名 reset 或套用该平台参数。

本机新证据：134初次启动 INTF1 高度2400、行号2337，关闭 autorefresh/TE 后等待超时；CTL0 reset poll 随后返回 -22，KMS失败、原生DRM缺失。132与134四个清理路径源码逐字节一致，尚未证明 USB observer 是原因。失败现场、初次完整日志和失败验核均保留。

一次原生 mipi-dsi panel bind 后，内核自行完成 msm 绑定，得到 card0/renderD128。标准 greetd 首次会话标记使普通服务 restart 进入 Phrog，随后仅保存当前 /run 标记并恢复原配置的 Phosh；配置及 launcher 未改。此恢复没有修复初次启动缺陷，不能作为永久显示修复、GPU压力或完整冷启动验收。

下一项继续记录启动交接的 reset/clock/domain 依赖和实机恢复前后差异，形成根因补丁后再做一次有界新启动验证；不重复本次 bind/会话恢复，也不添加开机重绑循环来代替修复。
