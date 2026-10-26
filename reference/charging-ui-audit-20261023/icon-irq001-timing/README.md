# IRQ001 相对时序与底层观察范围

[analysis.json](analysis.json)只保存相对采集开始的时刻、统计及原件SHA；没有boot UUID、endpoint、token或REALTIME锚点。原274份样本、84条kernel事件、DBus原件均未修改。完整物理周期仍为未通过，终态是300.808秒deadline；identity保持，monitor无错误，原DBus child按清理流程退出。没有屏幕像素或整机时延验收。

双online均为0的5份样本分成1/2/2三段，区间分别是145.395–145.418、149.490–150.527和155.649–156.698秒。没有连续3份且首末跨度至少2秒，因此原检测器未确认offline，不能进入完整重接周期。最后ACOK off/on事件接收间约2.205秒，DBus两个LinePower同时off的估算重叠约2.19秒；**不能把最长样本首末跨度1.025秒写成实际断电总时长，也不能反推用户没有拔线**。没有sample gap或None。8个读取错误均是源字段ENODATA：5份off的native limit、3份刚on且Unknown时的current_max；6份telemetry为-61，fault/latched/stop_error始终0，硬件输入限值274份均500mA。

| 最后一次接回证据 | 相对秒 |
| --- | ---: |
| ACOK online uevent接收 | 156.997 |
| source online、Unknown/native100mA | 157.099 |
| native500mA事件 | 157.208 |
| SDP、预算500mA事件 | 157.838 |
| sysfs样本已converter Charging，Battery仍Discharging/-16mA | 158.737–158.762 |
| converter Charging uevent接收 | 159.143 |
| Battery Charging uevent接收，瞬时+23mA、平均-41mA | 159.173 |
| Display明确State1及charging IconName | **估159.184** |

三次source online→Display目标Charging估算分别2.101、2.100、2.084秒。这里选的是明确State1与`battery-full-charging-symbolic`，不是任意first State。它支持用户“约2–5秒”的约两秒落在source接回至Battery/DBus目标变更这段；最后Battery事件至Display约11毫秒，没有额外几秒DBus停滞的证据。uevent是接收线程时间，样本是顺序读取括号，DBus是起止锚点映射估算；它们都不是电气边沿、IRQ断言或屏幕呈现时间。起止offset只变化约1微秒，但不能排除期间相互抵消的墙钟跳变或毫秒级接收排队。

实际#502 BQ源SHA为`00140777…5439b`，build收据与实际Image绑定；它已将native外供回调等待改为0，STATUS/current_now读取0x0c净流并保留FC优先，current_avg保留0x14。本次平均电流直到168.217–168.233秒样本才转正，不能拿它解释此前已经完成的Charging变更。缓存TI SLUUA65E §12.1/Table12-1明确Current0x0c和AverageCurrent0x14每秒更新；这是该芯片资料，不能变成定制2719固件的实测相位或固定延迟承诺。

charger10ec对应精确R8源`ed2e1d4d…a144c`和core`df9caed5…ed4e8`。source/protection事件已经立即排队；完整安全采样、预算/温区/Full策略、apply及写后REG13/Battery通知在同一个work内。常规1000ms是后续观察间隔，没有“安全采样后强等一整轮才enable”的固定sleep。USB观察器仍要求稳定APSD/有效native预算；0.74秒源分类段不能靠charger短poll旁路。158.74样本看到converter Charging并不等于当时刚写enable；其后约0.41秒至Battery事件也不能认定是可删的硬件等待。

有依据评估**仅真实offline→online后250ms、约3秒BOOTTIME硬截止的短观察候选**，但尚未证明实际收益。它可缩短硬件REG13/真实0x0c状态变化至下一轮观察的剩余等待，理论上相对1秒观察最多约省0.75秒；不能消除APSD或gauge本身的每秒更新。优先250ms而非200ms，没有证据值得为50ms分辨率再加25%频率。每完整step有两次保护属性各5MAC，加1个0071，共11MAC；4Hz为44MAC/s，仅现有锁内请求sleep合计44–66ms/s，尚未计I2C传输和调度。三秒窗相对1Hz多9次完整step、99MAC和99–148.5ms请求sleep，未知/断电早退可能更少。这是有成本的短期评估，不是长期250ms轮询建议。

候选必须保持全安全step、真实净流语义、1–1.5ms OEM MAC等待、BOOTTIME5秒Full/再充门和真实timeout。初始online/unknown不造offline，重复notifier或同窗flap不延后deadline，期满回1000ms，不补跑积压。本叶只记录审查建议；未修改运行源码、桌面或冻结候选，未访问设备、构建或重跑旧测试。
