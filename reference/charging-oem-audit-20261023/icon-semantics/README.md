# 拔插图标语义离线审计

仅在本目录执行已缓存源码的函数／最小分支；未访问设备、SDK、网络，未改candidate或main。6个组合案例和2个UPower覆盖分支通过ASan/UBSan，见 [test-result.json](test-result.json)。**这是可能的语义／平均电流延迟路径，不是本次用户所见延迟的实测根因。**

## 实际执行的源码

- 内核缓存 `kernel-bq27xxx_battery.c`：完整 `bq27xxx_battery_is_full()` 1845–1853和 `bq27xxx_battery_current_and_status()` 1860–1913。本机BQ28Z610条目1055选择BQ27Z561位布局，FC为bit5；其AI寄存器509行为0x14。
- UPower缓存 `upower-up-device-supply.c`：完整status字符串映射170–199；`upower-up-device-supply-battery.c` 523–527的实际negative-current覆盖分支。
- Phosh缓存 `phosh-battery-manager.c`：62–73行实际图标选择分支。它60行只取得device的state/percentage，106行采用UPower DisplayDevice，113–120行监听其state/percentage；该图标分支不读line-power Online。

源码原件哈希、准确行号和抽取片段哈希均在test-result.json。内核缓存来自实际source354；UPower是已缓存v1.91.0官方源，Phosh是固定提交a3cded46…参考源。本测试不证明发行包补丁／当前Phosh二进制逐字节相同。

## 已执行的语义边界

| 合成输入 | 内核Battery STATUS | UPower电池状态 | 将该state传给Phosh分支的结果 |
| --- | --- | --- | --- |
| FC=1，源已断，AI=−5mA | Full | FullyCharged | charged图标 |
| FC=1，源连接SDP100mA，AI=−5mA | Full | FullyCharged | charged图标 |
| FC=0，源已断，AI仍为+5mA；瞬时0x0C另给−200mA | Charging | Charging | charging图标 |
| FC=0，外接SDP100mA，AI=−4mA | Discharging | Discharging | 普通电量图标 |
| FC=0，源在线，AI=0 | Not charging | PendingCharge | 普通电量图标 |
| FC=0，AI=+5mA，percentage=100 | Charging | Charging | **charged**图标（Phosh自身百分比规则） |

还直接执行了UPower分支：即便输入status为Charging，单独读取的current_now<0会改为Discharging；输入status为Full则保留FullyCharged。上述函数成功读取current和flags后，FC优先于电流正负；总线读取失败时函数会返回错误，不能把无效读取当这些有效状态。

测试未执行实际UPower DisplayDevice聚合器、D-Bus发送、Phosh属性通知或屏幕绘制。表格最后一列是对给定state的实际Phosh分支计算，不是声称本次DisplayDevice或面板已经显示该值。

## 这些边界对延迟判断的意义

1. source Online变0并不强制原Battery STATUS变Discharging。FC还在时，内核／UPower可继续Full，Phosh继续charged；仅充电器事件准时并不能使该语义变化。
2. source已变0但AI平均电流仍为正，可以仍得到Charging。外部供电动作、瞬时电流和平均电流并非同一字段；这只证明一种允许的输入组合，不证明实机平均值实际滞后多久。
3. 外接电源但受SDP100mA预算限制，系统负载可能高于输入，净电流为负时显示Discharging符合真实电池功率流。**禁止用charger Online=1强写Battery Charging**，否则会掩盖净放电。
4. Phosh在Charging且百分比向下取整到100时也选charged图标，故“图标看起来没变”不能直接等同“D-Bus State没有变”。

原厂legacy FFA5的 `get_average_current` 名字容易误导：实际上1590–1592行将选择器改为0x0C瞬时电流，原厂头定义0x14才是AverageCurrent。主线当前0x14路径与原厂这个接口不同，准确证据见 [Full电流规范](../software-full/README.md)。不能为了让图标迅速变化擅自用0x0C替换所有主线平均电流语义；需要先采集实际各字段时序。

## AverageCurrent时间窗的证据边界

已定向检索缓存TI SLUUA65E完整文本。PDF67页Table12-1，`ti-manual-private.txt` 2728–2729行，将0x14/15描述为sense resistor的平均电流，**每1秒更新**；PDF71页§12.1.11仅列signed word及mA单位，没有进一步给出平均时间窗／滤波常数。因此不能从这份缓存确定“拔线后多少秒AI必定反号”。每秒更新不等于1秒平均窗，更不等于本机0x2719实测反号周期。

紧邻的2730行“15秒时间常数”明确属于 **AverageTimeToEmpty 0x16/17** 的方法，不能挪给AverageCurrent；2743–2744行的1分钟、93%／7%权重属于 **StandbyCurrent**，同样不是AI。本文不假定10秒、15秒或任意固定平均延迟，后续必须通过同窗口0x0C／0x14原值与FC／事件轨迹测得。TI原件hash及身份适用边界另见 [TCA资料清单](../tca-classifier/test-result.json)。

## 下次事件采集所需最小字段

每条原件都记MONOTONIC／BOOTTIME纳秒接收时间和序号；跨进程／主机时同时记录起止REALTIME-MONOTONIC对并检查时钟跳变。用户动作必须确实落在已确认存活的观察器窗口内。USB逻辑unconfigured不能单独当物理拔线。

| 层 | 必需原件／字段 | 能回答的问题 |
| --- | --- | --- |
| 物理／源 | 动作标记；源online、类型/APSD、CURRENT_MAX/native预算；charger ACOK/REG13；实际输入限值 | 真正源状态何时改变，还是仅数据配置改变？ |
| 原电量计 | 0x0A raw flags及FC位、0x14 raw signed AI与current_now、可选同轮0x0C瞬时signed current、Battery status/capacity、有效性和采集age | 状态尚未变化是FC/平均电流语义，还是没有取得新读数？ |
| 内核通知 | 真正原Battery change uevent，含POWER_SUPPLY_NAME、STATUS、CURRENT_NOW、CAPACITY、SEQNUM和时间；与source/charger事件分开 | 源变后何时采样／发出了Battery状态变化，而非只数charger事件？ |
| UPower | 被枚举到的实际Battery对象路径及其State/Percentage/UpdateTime/EnergyRate变化；DisplayDevice对应属性；LinePower Online与root OnBattery分别记录 | 是电池设备刷新晚，还是Display聚合／转发晚？不能只看UpdateTime认定State已变 |
| Phosh／屏幕 | 如能取得，记录实际DisplayDevice state/percentage到Phosh icon-name变化；实际屏幕画面或带时标视频 | 是已收到state但图标选择规则维持charged，还是UI通知／绘制真正晚？ |

不要在观察器中额外raw读取清故障REG14；它由charger单一所有者读取，复用缓存及age。新电量计字段应由既有安全传输所有者采集，避免插入MAC事务时与两个工作队列交叉。只需本轮状态字段，无需NV／校准或整库扫描。

报告应分开给出 source→Battery有效样本、Battery变化→真实uevent、uevent→UPower Battery、Battery→Display、Display→Phosh／屏幕。若只取得到Display，明确屏幕实际绘制延迟尚未测得；若缺真实source边沿，不把一直online的轮询事件冒认为拔插。出现FC1/AI延后等组合时标记“符合已验证语义”，只有同一实际窗口的字段和事件证据才能定位本次延迟。
