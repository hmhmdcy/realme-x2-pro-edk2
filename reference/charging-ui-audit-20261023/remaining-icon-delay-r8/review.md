# R8 剩余图标延迟：本轮事件链与最小下一步

仅分析已完成的 R8／Image363／boot4126／正常 USB500 启动后的实体断接缓存。未采集手机、执行测试套件、构建、挂载、使用 SDK 或 Git；未改 R8、BQ 候选 B／Image501 或采集器。原件 SHA256 为 `57d98e04d5a987d4598e552779133fb4b5f492bedfe7042860517c71a79abe5e`。267 个样本、295.856 秒，确有连续 offline→online；所有时间为本轮相对秒，D-Bus 以起止时钟锚点映射，不是用户手部动作或屏幕像素的时间。

## 结论

本轮约 3 秒重接延迟主要发生在 **原 Battery 状态变成 Charging 以前**。Display 在 Battery 的 D-Bus State 之后约 3.4ms 更新；首次采样已读得原标准 Charging 后约 184ms 已出现 Display Charging。没有证据支持 UPower 固定缓存 30 秒。断线则明确存在原 0x14 平均电流保持正值的拖尾，501 的瞬时电流语义修正有针对性，但这轮不能量化它将缩短多少。

不要把“已经接电”和“电池正在净充入”合成一个真值。若需要像接线动作一样迅速的反馈，最小 UI 方向是单独显示由 LINE_POWER Online 驱动的连接标记，原 bolt／Battery Charging 继续使用真实电池状态。**不能简单用 `!OnBattery` 当连接状态**：本版本 OnBattery 同时取决于 Display 是否 Discharging，本轮断线时它与 Battery 一起晚了约 4 秒。

## 实际时序

| 事件 | 断线 | 重接 |
| --- | ---: | ---: |
| charger／ACOK uevent Offline / Online | 191.488823 | 201.754057 |
| UPower charger Online=false / true | 191.503707 | 201.761545 |
| UPower source Online=false / true | 191.403905 | 201.926208 |
| source Online=0 / 1 uevent | 191.889353 | 201.921677 |
| source 完整 CURRENT_MAX/native=500mA uevent | — | 203.151801 |
| charger 硬件 Charging uevent | — | 203.499410 |
| 首个标准 Battery 状态已变的采样区间 | 195.579420–195.601768，Discharging | 204.796576–204.814084，Charging |
| UPower Battery State | 195.617221，2=Discharging | 204.994342，1=Charging |
| UPower Display State | 195.619737，2=Discharging | 204.997747，1=Charging |
| 根 OnBattery | 195.623000，true | 201.784405，false |
| 真实 Battery change uevent | 196.515415，Discharging | 205.190108，Charging |

- source Online uevent→Display：断线 3.730384 秒、重接 3.076070 秒。ACOK uevent→Display：断线 4.130915 秒、重接 3.243690 秒。
- 从首个已经读得新标准状态的样本**末端**到 Display 为断线 17.97ms、重接 183.66ms；这是采样到事件的时间间隔，不是状态实际翻转到显示的严格上界（状态读取发生在该行区间内）。
- Battery D-Bus State→Display D-Bus State 为 2.516ms／3.405ms。未记录 Phosh icon-name／绘制提交，不认证像素延迟。
- 两次 Battery D-Bus State 均**早于**相应 Battery kernel uevent，约 898ms／196ms。不能把它们写成一条严格串行的“source→Battery uevent→Display”；UPower 的其他刷新路径已先取得新状态。
- 转换期 Battery D-Bus 属性刷新约每 1.02 秒一次，符合本轮实际快速刷新。`UpdateTime` 变化不等于 `State` 变化，本文只把正确方向的 State 当响应。

## 三个重接样本不能混成同一时刻

1. 202.750165–202.767676：source/current_max/native 与硬件输入限值均 500mA，UDC configured；但 charger `valid=0/error=-61/source_inhibit=1/budget=0/desired_enable=0`，硬件 Not charging。source getter 每次 fresh 读 PMIC；telemetry 是之前安全工作轮的结果。输入限值保留 500mA 不代表 converter 已 enable。
2. 203.775136–203.789553：安全 telemetry 已有效，budget=500mA、desired_enable=1；0x0c=-124mA、age=301ms；原标准 STATUS=Discharging，0x14=-155mA。**0x0c 不是在 203.789553 当场读取**：`sm_collect()` 先读 gauge，再设 sampled_at，最后 policy/apply。按整行采样区间和 age 估算，其 sampled_at 在约 203.474–203.489 秒，且 0x0c 读取还在它之前；这轮负值在 203.499410 的 Charging 硬件事件以前，不能据此断言之后仍然净放电。
3. 204.796576–204.814084：0x0c=+100mA、age=162ms，原 0x14=+100mA、STATUS=Charging。对应 telemetry sampled_at 约 204.635–204.653 秒，0x0c 读取在它之前。记录没有更密的独立 0x0c 样本，不能确定瞬时值领先原平均值多少，也不能把全部 3 秒归为硬件起充延迟。

source 完整 allowance 事件到 Charging Display 为 1.845946 秒，charger Charging 事件到 Display 为 1.498338 秒。其中包括安全轮调度、硬件／电流变化、gauge 采样及 UPower 快速刷新，缺函数跟踪，不能逐项相减后声称已分离各自耗时。安全检查通过前的 inhibit 不能为图标速度而跳过。

## 断线平均值拖尾与离线瞬时值缺失

确认 offline 后，192.503–192.520、193.528–193.546、194.553–194.573 秒原 Battery 仍分别读得 +70／+59／+49mA 和 Charging；195.579–195.602 秒才读得 -172mA、Discharging。这直接证明本轮原 0x14 驱动的状态没有随接电消失立即反号。

这些 offline 行里的 telemetry `valid=1/gauge_current_ua=0/flags=0` **不是实际 gauge 零电流／零 flags 读数**。`sm_collect()` 清零结构后，在 source 与 ACOK 一致离线分支即返回，没有调用 `sm_gauge_sample()`。因此没有本轮断线后有效 0x0c 首次变负时刻，不能估计或保证 501 的具体改善秒数；也不需为补证据把遥测改成离线持续读总线。

## 精确源码的通知／缓存含义

- Image363 BQ 基线 SHA `b2cd415a995cb196559c0e4981988f737c17c98486449659d168314926aec69e`，对应 ba61。`bq27xxx_battery_current_and_status()` 1860–1913 每次读 AI（本机表为 0x14）和 flags，再按 FC 优先、正负电流决定状态。STATUS 与 CURRENT_NOW getter 即时调用该函数。2128–2131 的 5 秒 general cache 刷新门**不会让电流／状态等 5 秒才读**。
- `bq27xxx_external_power_changed()` 2219–2226 是 `mod_delayed_work(..., HZ/2)`，明确 0.5 秒后取样，**不是立即 queue**。360 秒是后备工作轮；一次更新结束也会重排该后备轮。update 1915–1950 仅在 capacity／flags／last_status 改变时发 Battery changed。
- 当前 R8 的 `sm_poll()` 每 1 秒安全采样后生成离散 signature（含直接读取的原 Battery STATUS／errno）；只有 signature 改变才在释放 charger mutex 后发 charger changed。source／protection notifier 已将该工作轮用 `mod_delayed_work(...,0)` 提前，不需要另加重复的“source 变化立即 poll”。`supplied_to` 将 charger 变化送达原 BQ 的 0.5 秒回调；不处理 Battery notifier，避免回授环。没有稳定期每秒无条件 changed。
- 当前 provider 的 native allowance setter 立即 `power_supply_changed()`；PMIC/APSD/attachment 后续状态则由 `samurai_usb_poll()` 每秒 fresh 两组读取后按变化通知。getter 本身虽 fresh，但**不主动执行 charger policy 或改变通知缓存**。这可留下小于一个正常周期量级的相位等待，但无本轮函数跟踪不能把某个固定 1 秒全归给它。没有证据支持为此直接复制另一 PMIC IRQ owner／提前接受未稳定预算。
- UPower 缓存官方 v1.91.0：udev change 直接 `up_device_refresh_internal(UP_REFRESH_EVENT)`→class refresh；line-power Online 变化还以 idle 调用全部系统电池 `UP_REFRESH_LINE_POWER`，并启用一段 fast repoll。supply-battery 523–527 uncached 读 status/current_now，非 Full 且负电流覆盖为 Discharging；battery report 384–399 直接设置 state。功率估算 distrust 只清 energy-rate，不把已知 state 延迟成旧值。未缓存 `up-constants.h`，本文不凭记忆写死各 timeout 常数；实际约 1 秒刷新已在本轮事件中可见。

## 501 与最小可执行方向

冻结 B SHA `0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe` 同时把 STATUS／CURRENT_NOW 换为直接 0x0c（原厂 FFA5 接口已有依据），把真正 0x14 保留为 CURRENT_AVG；显式 samurai opt-in，默认 false，Full／错误优先级不变。它**没有**改变上述 0.5 秒回调、360 秒后备轮或一般 cache。故只有实际启用该参数，501 才改变本机语义；只换 Image、参数仍 false 则无此收益。

建议先把已冻结 501 作为**单一变量**验证正确 NOW 语义及断线拖尾，暂不把 BQ 回调 0.5 秒改为 0、降低全局 poll、增加连续广播或强制刷新 UI。本轮 UPower 已在 Battery uevent 之前取到新状态，不能证明额外通知补丁是消掉当前 3 秒的必要条件。若之后证据显示“正确瞬时 STATUS 已变而无事件导致 UI 等待”，最窄后续才是 board opt-in 下缩短 external_power_changed 的队列等待／按真实状态变化通知；仍保留标准 supply 关系和错误／Full 语义，不让 getter 产生重复通知或引入 charger↔BQ 锁环。当前未编写或启用此改动，也不承诺它可加快尚未净充入的阶段。

## 独立连接标记的可实现点与缺项

缓存 Phosh `battery-manager.c` 固定提交 a3cded46d6c6ad8f51678834cd17e95967cc0702：已有 `UpClient *upower`（36、104行），106行只取 DisplayDevice，113–120行监听 state／percentage；当前参考图标选择分支 60–74 行不读 line Online。`battery-info.c` 180–187 行将 manager icon-name 直接绑定到现有 battery widget。

最小方向是同一个 manager 内增加独立连接状态：首次枚举和设备增删时维护 LINE_POWER 的集合，监听这些设备 Online 变化并聚合 `any known Online=true`，独立 property 驱动旁边插头标记；不改现有电池 icon-name／State。初始化未知、设备移除／服务重连及读取错误必须表示未知或已知集合结果，不能失败时沿用“已接电”断言。具体 UpClient 枚举和信号 API、widget 位置／资源要对**实际发行源**核对后才写补丁。

`!OnBattery` 不足以替代此状态：UPower v1.91.0 daemon 99–102 用 Display 的 Discharging 判断 get_on_battery，828 行再与“无 AC online”相与；因此外接电已断、Battery 仍 Charging／Full 时 OnBattery 仍 false。本轮插头标记若只取它，拔线仍延至 195.623 秒。LINE_POWER Online 本轮在约 191.4–191.5 秒已离线，接回在 201.761545 秒已在线，可分别早于净电池 State 约 4.1／3.24 秒；这属于连接语义响应，**不是提前显示充电 bolt**。

实际包版本已知为 Phosh 0.57.0-r3／UPower 1.91.0-r2／Phoc 0.57.0-r1，但参考 Phosh 两文件不等同发行源逐字匹配，UPower 官方主源也未认证发行补丁。当前没有已核定的 0.57.0-r3 APKBUILD、发行补丁、完整源树及相同依赖构建缓存；这是形成可直接构建 UI 补丁前所需的最小输入，不能升级版本来代替。

逐事件／采样精简数据见 `timeline.json`，其计算脚本 `read-timeline.py` 只读已留存原件。本文没有屏幕绘制延迟、已关闭问题或 Android 实现等价的验收结论。
