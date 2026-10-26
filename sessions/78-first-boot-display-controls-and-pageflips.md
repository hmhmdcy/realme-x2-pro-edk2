# Session78：相同镜像的首次显示接管对照与页面翻转

日期：2026-10-10。证据在 reference/kernel78；本轮没有内核/固件部署，也没有分区写入。
手机保留 session77 的只读 BQ28Z610 DT 和 #76 Image/config/logdump。

## 当前结果

相同镜像连续三次重启均未出现 DSI worker 错误。第三次在未请求开关屏的情况下，
完成600次双缓冲页面翻转及对应彩条/纯白 CRC；末次约669秒状态检查仍为0错误、taint0。
session77 的两次失败仍是有效证据，本轮的成功不能证明间歇性首次接管故障已修复。

当前 boot_id=e1a36cea-f401-41f2-bd1a-1eedf1282e96。电量计报告电池包8.645V、
温度29.7°C、电流0、SOC100%、Not charging。充电控制未接入，状态标签不是安全验收。
本轮未访问充电器、快充MCU、OTG或电量计配置/NVM；未做充电或热压力试验。

## 1. 相同镜像的启动对照

三次均通过真实 F1 回执进入 fastboot，独立核对 serial=62bc28a1、product=msmnile，
只执行 reboot。一次早期 COM14 被动读取35秒，发送0帧，最终释放；另外两次未运行
早期 COM 读取。NCM/SSH/SCP保持可用。传输中的断开错误与成功回执分别保留。

| 启动 | boot_id | 接管前 INTF1 行数 | 旧帧停滞 | 保存日志中的 DSI 错误 |
|---|---|---|---|---|
| fresh | 7ccf5e4b-7cd9-424f-b91c-d3bf5f529f57 | 0x960，等于2400 | 无 | 0 |
| late | 931c82bf-e465-47db-b800-a7a26cef50b0 | 0 | 无 | 0 |
| repeat / 当前 | e1a36cea-f401-41f2-bd1a-1eedf1282e96 | 0x57b，帧内 | 有；CTL复位确认 | 0，含两轮刷新后的完整日志 |

第三次同时出现旧帧停滞和正常刷新，说明旧帧超时不是本轮已证实的充分故障条件。
只读 DT 增量、早期串口读取时机和正常/异常首次启动之间的因果关系仍未确定。
不能据此认定电量计导致下溢，也不能只延长超时就宣称修复。

设备端重新核对 PARTNAME=boot/logdump，并回读当前内容：

| 产物 | SHA256 |
|---|---|
| boot，前6680576字节 | 3fbbd0eecf7e793f97920d55bd9ec2a30329d6e53edb307200160a23e1de923e |
| logdump，全67108864字节 | 607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0 |

两者与 session77 相同。Android/用户数据/GPT未写；镜像、专有固件、SSH身份保留在本地。

## 2. 无开关屏的实际刷新验证

先从 session73 的 kms-smoke 派生 kms-refresh，去掉显式 CRTC disable，直接恢复
原 CRTC。600次 DIRTYFB、10.076917秒中591次CRC与请求图案一致，另外9次恰好处于
每60次重写活动缓冲区的边界。其余590个非边界样本全部匹配。活动缓冲区重写造成
过渡帧混合是依据时点的推断；该探针不承担双缓冲正确性验收。

随后用 kms-pageflip 建立两个预先填充、翻转期间不修改的缓冲区，交替彩条/纯白，
每次等待 DRM_EVENT_FLIP_COMPLETE，并从CRC队列确认目标图案：

- 600个完成事件、600次目标图案确认，耗时20.035491秒。
- 总计1199条CRC，全部对应两个完整图案之一，没有未知的混合CRC。
- 彩条69961448/60af15f5，纯白25e11871/25e11871。
- 完成事件和确认CRC序号严格递增，原 CRTC 直接恢复，缓冲区释放。
- 两轮之前/之后 DSI worker均0；面板enable日志均1，未发生新增prepare/enable。

这验证第三次首次启动状态下的数字数据流及翻转完成，不代替用户对实际屏幕的光学
观察，也不覆盖90Hz、冷断电、休眠或长期压力。session75光学验收仍单独保留。

## 3. 驱动与寄存器审查

从驱动自带 debugfs kms 取得 session77 开关屏恢复状态、三次首次启动及刷新后的
寄存器快照，没有使用 /dev/mem 访问或写入寄存器。kms-diff.json 是跨启动对照，
包含动态计数和正常继承配置差异，不能把每个差异都当成故障原因。本轮没有取得
新启动的故障快照，无法用这些成功样本证明候选复位方案有效。

实际 DT compatible 是 qcom,dsi-phy-7nm-8150，编译 CONFIG_DRM_MSM_DSI_7NM_PHY=y，
10nm PHY关闭，匹配 DSI_PHY_7NM_QUIRK_V4_0。初期查看了10nm实现，确认实际绑定后
改为审查7nm实现；未依据10nm实现修改内核。7nm驱动与当前源码HEAD原样一致，
SHA及实际源码HEAD见 phy-binding-validation.json。源码HEAD是本地EUD提交，
不是可直接当作Torvalds上游提交的标识；不要沿用摘要中未经核对的上游SHA。

已有 INTF TE/autorefresh停机、CTL双复位和 IOMMU切换保护继续保留。主线7nm实现
在probe保存PLL状态，首次PHY复位后恢复；完整开关屏也保存/恢复PLL。仍需进一步
比较故障时的控制器、FIFO原始状态、PLL/DSC及路由状态，不能只凭 status=c 反推全部寄存器。

参考 [DPU关闭bootloader路径的维护者讨论](https://lkml.iu.edu/hypermail/linux/kernel/2202.2/01145.html)
及 [MDSS复位时机讨论](https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2203.0/01490.html)：
它们涉及启动配置及clock/PHY一致性，支持继续审查接管顺序，但不是本机故障根因的证明。
尤其不能在子设备probe之后直接追加整块MDSS复位而忽略已注册的clock/PHY状态。

## 4. 证据和限制

六份日志解压后逐字节SHA与设备端对应；分类器检查未匹配到 Oops、panic、
SMMU context fault 或 GENI I2C错误。session77基线194条worker匹配行包含177条
status消息及17条限速提示，两种计数在 hardware-validation.json 中分开记录。

不存在 /dev/disk/by-partlabel 的一次查询失败后，采用实际 sysfs PARTNAME核对。
初版日志分类器误把 debug/ramoops 子串当作 BUG/Oops，改成词边界后重新核验；
不以这个误报判定设备故障。工具读源码时的引用/范围错误已修正，未改变设备状态。

下一步在首次启动故障重现时，先保存 kms/state/clk_summary及完整日志再做恢复；
必要时加入只记录FIFO原始位和首次接管状态的受限内核诊断。保持已验证电量计读取，
充电控制继续遵守 session76 的温控、输入预算、终止、超时、失联和NVM安全边界。
全硬件目标保持active，首次接管故障仍开放。
