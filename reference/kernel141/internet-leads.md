# 阶段141互联网线索与适用范围

2026-10-12，因用户询问“为何难以定位、搜索有什么线索”进行新核对。只使用作者讨论、上游项目文档/源码和芯片厂商说明来支持技术结论。

- [DPU空闲timer竞态提案，2026-09-03](https://www.mail-archive.com/dri-devel@lists.freedesktop.org/msg632873.html)：中断先清busy、随后才arm可产生挂起时timeout pending。当前源码已有同步busy/deadline处理；141两次expire时busy1，PP callback确实91–95ms才执行，不能据相似报错认定同一根因。机器人评审仅为提示，没有用其假设作为实机结论。
- [SLIMbus未提交TX回收讨论](https://lkml.iu.edu/2609.2/05810.html)，[作者验证范围说明](https://lkml.iu.edu/2610.0/02660.html)：作者说明只编译测试。139结合tx_lock和尾槽回退保留较早在途槽位，有12项实际函数注入、ASAN/UBSAN及实机恢复证据。提案本身不证明141 DOWN/NULL channel或PDR恢复根因已解决。
- [Mesa Freedreno官方缓存文档](https://docs.mesa3d.org/drivers/freedreno.html#cache-hierarchy)：CCU用于2D blit、sysmem渲染目标和GMEM resolve；支持继续核查图像回写、缓存转换、压缩布局和映射生命周期。当前搜索未获得针对本机136延迟CCU fault的已验证现成补丁。
- [MPS MP2650官方产品说明](https://www.monolithicpower.com/en/mp2650.html)：支持buck或boost及2–4串电池，充电电压/电流、输入限制和保护需要配置。不能仅因输入5V与两串电池判定无法充电。官方PDF网址本轮open失败，未把搜索缓存片段当完整数据手册阅读。具体8.725V/8.525V数值来自138设备只读寄存器和原厂源码，不由产品介绍推导。
- [Realme samurai Android内核源码](https://github.com/alextrack2013/android_kernel_realme_sm8150)：有设备专用Android参考实现，可核对硬件契约；不是这套mainline/Mesa/Phosh已通过的postmarketOS成品。当前有限搜索没有找到可直接解决本机显示、GPU和充电全部问题的已验证方案，不能扩大成“全网不存在”。

当前最具体的下一实验是增加IRQ entry/exit、CPU idle/frequency和PM事件，区分显示完成回调迟到前的硬件/CPU时序。充电下一实现须按已读设备配置接入温度、输入额度、失联行为和持续控制；芯片能力不能替代整机验证。
