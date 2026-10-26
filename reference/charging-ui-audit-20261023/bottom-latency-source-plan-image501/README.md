# 充电延迟：底层通知链与最小下一步

按用户要求，Phosh包独审／GTK／新增桌面提示分支已停止，保持未部署。本叶只分析底层及其现有标准事件消费者，不改Phosh、UPower、冻结501或R8，不新增采集／测试／设备动作。旧报告的UI建议仅为历史，不再作为本轮方案。

结论：目前可精确指出并可单独消除的固定软件等待，是BQ的 `external_power_changed()` 延后0.5秒；它不是已证明的全部约3秒根因。source识别的1秒poll由根会话定向核原厂IRQ接入，本线不另写IRQ或缩poll实现。R8的source notifier已经立即排工作，notification已经在apply后读REG13和实际Battery STATUS，不能重复提出这些已完成改动。

## 旧363真实attach有三个不同阶段

| 记录 | 相对秒 | 可证明含义 |
| --- | ---: | --- |
| ACOK／charger Online uevent | 201.754057 | 物理输入出现，不等于安全预算已可用或净充入 |
| source Online事件，无CURRENT_MAX | 201.921677 | source可在线而充电额度尚不可读 |
| fresh顺序getter已见source/native/hw500 | 202.750165–202.767676 | 此时telemetry仍是此前valid0/error−61/budget0/desired0，不是本次getter已执行policy |
| 完整source CURRENT_MAX500事件 | 203.151801 | 有了完整源额度的事件证据 |
| converter Charging事件 | 203.499410 | 硬件已进入充电切换状态；不是电池净电流一定为正 |
| 首次标准Battery已Charging的采样区间 | 204.796576–204.814084 | 旧0x14终于为+100mA，原标准状态相应变化 |
| Battery／Display D-Bus Charging | 204.994342／204.997747 | Display仅比Battery晚3.4ms |
| Battery kernel Charging uevent | 205.190108 | 反而晚于D-Bus，不能写成唯一串行响应链 |

source Online→Display约3.076秒；完整额度事件→Display约1.846秒；converter Charging→Display约1.498秒。这些差值包含硬件／gauge更新、工作队列、I2C和consumer刷新，不能当成已分离的各函数耗时。

203.789一行的0x0c−124mA来自age301ms的旧安全样本：sampled_at约203.474–203.489，gauge读取还早于sampled_at，且在203.499 converter事件以前。因此既不能把负值当成203.789仍未起充，也不能断言全部等待已证明是硬件启动。204.814行0x0c+100mA的sampled_at约204.635–204.653；两者之间没有更密的独立瞬时读数。501已启用0x0c，但新001没有观测到off边沿，不能用主观改善或无edge窗口认证attach／detach提速。

## 实际函数、等待与通知

- R7 `samurai_usb_get_budget()` 每次读两组七寄存器，必须一致并通过原sink／错误／APSD条件；SDP仍必须原生UDC额度。`samurai_usb_poll()` 固定1000ms、只有离散状态变化才changed；DWC `vbus_draw_work` 设置额度的setter本来就立即changed。fresh getter不更新poll的last状态，也不执行MP policy。根会话负责真实IRQ来源，不能为更快而接受未完成检测或旧额度。
- R8 `sm_supply_changed()` 对input/protection已有 `mod_delayed_work(...,0)`；`sm_poll()` 每轮安全采集→完整policy／Full／fault处理→apply→notification。`sm_notification_locked()` 已在写后读取REG13及原BQ标准STATUS／errno，然后解锁才changed。保留当前signature，稳定期不加无条件广播，不让getter发通知。
- `sm_collect()` 在线时两次访问保护provider的PRESENT／HEALTH，每次各做五个MAC查询，再有一次0071电芯查询。共11次匹配OEM的1–1.5ms query等待，名义11–16.5ms，另有真实bus／调度耗时；没有2秒或5秒的attach计数门。Full的5秒采样／6或11样本是Full／再充算法，不是首次普通起充必须等待的计数。保护数据每次fresh读取，不能删查询或缓存Good来追速度。
- `sm_apply()` 不含软件sleep／debounce。目标一致直接返回；有离散变化才停输入、逐项写并回读，再启用CHG。必须保留双限流、CC/CV、继承配置、fault／失败stop语义。不能根据converter Charging把净负流提前报成Charging。
- `config.supplied_to` 由实际gauge父设备发现的Battery名字建立。BQ `external_power_changed()` 仍是 `mod_delayed_work(system_percpu_wq,&di->work,HZ/2)`：每次最终supplier通知后再等0.5秒，后到的通知可以继续后移这个期限。360秒是后备工作轮，不是plug事件延时。5秒一般cache门不缓存STATUS/NOW；getter解锁后每次直接读实际current／flags。
- 内核power-supply changed工作先处理supplied_to回调，再PSY notifier，最后kobject uevent。因此UEVENT时间不是worker最早入队时间，也不能把UEVENT后的差值全归为队列等待。
- 匹配本机UPower1.91.0-r2的源码：udev change直接 `UP_REFRESH_EVENT`；line Online变化经idle刷新Battery并进入1秒fastpoll，持续5秒。class refresh uncached读status／current_now；负净流仍优先Discharging。已知State没有固定30秒门，10秒distrust针对rate而非把State强留旧值。本轮实际约1.02秒更新且D-Bus State早于BQ事件，吻合其它刷新路径已工作。

## 建议的最小底层改动，尚未写代码

只在现已启用且严格匹配Samurai/BQ28的instant profile里，把BQ external-power回调的排队延时从 `HZ/2` 改为0；其它chip及非opt-in路径继续原0.5秒。

```c
unsigned long delay = bq27xxx_samurai_instant(di) ? 0 : HZ / 2;
mod_delayed_work(system_percpu_wq, &di->work, delay);
```

仍异步排原worker，不在notifier内做I2C，不改Full／电流符号／cache／后备poll或阈值，不额外加入轮询和广播。R8 post-step signature在发现真实0x0c状态变化后，现有supplier关系即可更早推进Battery changed。source不具备完整安全预算、硬件／gauge尚未变号时，此改动只能如实报告旧状态，不能加快物理充入。

锁序保持：charger持c.lock调用BQ getter；BQ工作持di.lock只排自己的changed；power-supply回调只排工作，不同步反调charger；MP notifier只认input／protection，忽略Battery，故没有新c↔di回授或锁反向。生命周期仍用原worker的remove／cancel顺序，不扩大硬件写范围。

这能移除明确的0.5秒通知去抖，并避免同一串通知重复延后；**不等于实测可减少0.5秒，更不保证3秒全消失**。已知旧attach在最后一段被UPower fastpoll抢先，可能收益只落在某个相位。后续仅需实际原函数定向验证opt-in队列0／非opt-in原值、通知合并／运行中重排、真实状态改变才changed、Full／错误不被伪造；没有要求重跑旧大矩阵。本轮未执行这些测试或构建。

下一次合法边沿应把“source预算何时真正ready、REG08成功enable／REG13状态、post-step读取的0x0c标准STATUS及通知入队”区分记录，不能只靠telemetry age反推完整apply耗时。是否需要这种新采集由根会话统一窗口，本文不创建观察进程，也不操作设备。
