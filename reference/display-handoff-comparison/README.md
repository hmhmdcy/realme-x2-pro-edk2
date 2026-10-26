# 一加、真我 Linux 显示交接方案对比

核查日期：2026-10-14。范围是公开原始面板驱动、设备树及作者提交/实机记录；不以Android第三方ROM的可用状态推断主线Linux行为。本轮只搜索、下载和阅读公开资料，没有修改或刷写手机。

结论：复位后重新初始化面板有公开先例，但“在EDK2 BeforeExitBootServices拉低GPIO6、保持到Linux接管”是当前Realme X2 Pro本地实现。本轮未找到其它一加/真我项目的完全相同实现。不同机型也会选择保留固件已初始化的面板状态，不能将本机策略推广为通用要求。公开资料不足以证明其它机型也有同样时长的黑屏。

| 对象与资料版本 | 实际读到的代码或记录 | 与本机方案的关系 |
|---|---|---|
| OnePlus 6：上游SOFEF00驱动，抓取的master源码 | probe以GPIOD_OUT_HIGH取得reset；prepare供电后执行复位、初始化；enable发送display-on | 同属重新初始化，但位置在Linux面板驱动，不是EDK2退出前 |
| OnePlus 6T：上游S6E3FC2X01驱动，抓取的master源码 | probe使用GPIOD_OUT_LOW，注释说明保持显示以避免闪烁；prepare仍复位和初始化，enable再发送display-on | probe阶段的策略与提前保持复位不同；也说明复位时机要逐机核对 |
| Realme X3：linux-6.12_rc7移植分支 | DTS是mdss,x3-jdi-nt36672c，reset-gpios为TLMM6/ACTIVE_LOW；对应驱动probe使用GPIOD_OUT_HIGH，prepare执行复位、初始化和DSC PPS | GPIO与极性相同，重新初始化思路相似；面板是NT36672C LCD，不能照搬SOFEF03F OLED命令 |
| OnePlus 8T：2024-06-30 v2移植提交 | 作者说明Pixelworks Iris 5在SoC与面板之间；当时缺少其重新初始化驱动，复位后无法恢复，因此省略面板reset GPIO | 是明确的反例；这是该版本的处理方案，不宣称2026所有分支仍如此 |
| OnePlus 7T Pro：独立hotdog移植项目2026-08实机记录 | 原厂OnePlus bootloader直接启动Linux；曾出现DSI/DSC噪声及白屏，完整面板重新初始化能恢复，扩大FIFO错误软件复位反而破坏CTL握手并被撤销 | 能佐证同平台存在类似故障和恢复方式；该项目没有经过EDK2，记录不能证明用了我们的固件回调，也不能证明两机根因相同 |

本机当前修改分成三个层次：固件164退出Boot Services前保持面板复位；内核158起在SM8150清理固件CTL前停旧DSI，并在163 TLMM就绪后维持复位；156起等待真实PP TX done再放行亮度。查到的其它面板驱动有prepare/enable阶段划分，但这不等于本机新增的首帧TX完成门控。在已检查的SOFEF00、S6E3FC2X01及X3 NT36672C面板驱动文件中，没有同样的显式PP TX done等待；这项文件级检查不代表对其整个DRM调用链做完了审计。

工程判断：本机方案是有实机验证的重新初始化接管方案，并且主动让交接窗口保持黑屏；它尚未实现保留固件画面的无缝接管。若后续要改善黑屏时长，需要测量显示驱动实际就绪时间，或另外研究完整继承固件的时钟、IOMMU映射和DSC/面板状态。其它机型“驱动有复位”不能证明本机所有历史显示故障的硬件根因已经厘清。

主要来源：

- [OnePlus 6 上游面板驱动](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/panel/panel-samsung-sofef00.c)：本地快照[upstream-sofef00-master.c](upstream-sofef00-master.c)，reset/prepare/probe及enable可直接核对。
- [OnePlus 6T 上游面板驱动](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/panel/panel-samsung-s6e3fc2x01.c)：本地快照[upstream-s6e3fc2x01-master.c](upstream-s6e3fc2x01-master.c)。[2022作者说明](https://lists.openwall.net/linux-kernel/2022/10/08/205)记录旧SOFEF00兼容驱动不能在复位后正确初始化6T，后续增加专用驱动。
- [Realme X3 DTS](https://github.com/sm8150-linux-mainline/linux/blob/linux-6.12_rc7/arch/arm64/boot/dts/qcom/sm8150-realme-x3.dts)、[对应NT36672C驱动](https://github.com/sm8150-linux-mainline/linux/blob/linux-6.12_rc7/drivers/gpu/drm/panel/panel-novatek-nt36672c.c)；[postmarketOS包来源](https://pkgs.postmarketos.org/package/v25.06/postmarketos/aarch64/linux-realme-x3)将该库标记为Realme X3主线分支来源。DTS中LM3697及LCD型号均有别于本机OLED。
- [OnePlus 8T v2作者说明](https://lwn.net/Articles/980163/)、[AMB655X驱动原始提交](https://marc.info/?l=devicetree&m=171977261419436&w=4)：LWN此页是邮件原文归档，采用作者内容；不把该历史提案当成当前上游支持状态。
- [OnePlus 7T Pro原生显示启动记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-03-native-display.md)、[DSI/DSC错误实机记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-17-dsi-dsc-transport-errors.md)：属于该项目作者报告，非对其硬件的独立复测。
- [本机固件164补丁](../kernel164/before-exit-panel-reset.patch)、[本机165及用户实屏验收](../kernel165/README.md)。

抓取范围与失败项见[sources.json](sources.json)。GitHub API遇到匿名限流，使用公开raw文件完成必要核查；未取得的目标文件不作为证据。本次请求上游v6.12的专用S6E3FC2X01文件路径返回404，后续抓取master专用驱动成功，因此6T的当前分析以master快照为准，不以404推断没有支持。每份下载成功的文件保留SHA256，master链接可能随后变化。
