# 人为INHIBIT期间Full计数与原厂timer条件

纯只读源码审查；未改冻结候选8文件、生产9d9、手机或SDK。被审查的候选 `full-integration-candidate/samurai-mp2650.c` SHA为 `06e92aa75a3c65382169d786295b9e2808b5499feaf27bbb22b12fccca561f09`，其 `charge-cycle.h` 为 `1ad3e8a4cdb4fa2dabc979c58265ff76efb2074a54dbc54ce811ca2485c42782`。原厂仍为固定提交23172a15…的 `oplus_charger.c`，SHA `6cfb97b4367afe25094f3f342db4c9cce7982a22708371bc08ac6ed8bc9aa2d4`。

## 结论

**原厂上层没有阻止人为停充期间的新软件Full／再充计数。候选应明确收敛这一点，而不要假设原厂caller已有 `mmi_chg/chging_on` 门控。**

候选167–270行中，197–213行构造Full样本并调用helper时没有 `auto_requested` 条件；仅240–245行在真正写寄存器前检查AUTO。因此手动INHIBIT而源仍接入、单芯高于SW门限、净电流非充入的11份有效样本，可形成新的logical_full；已Full时也能累计再充并丢失Full事实，只是末尾AUTO门挡住了当次真正充电。

建议手动INHIBIT时：保留已确认Full/cause，清未完成的SW/HW/recharge streak，不建立新Full或发出再充转移；继续采集原始遥测、源变化和真正保护错误。重新AUTO后用新鲜样本重新计数，不能接续人为停充期间的证据。真实detach仍应独立重置周期；旧硬fault/timeout保持优先。

这是一项有意比原厂严格的适配，不应写成“原厂已有相同门控”。

## 原厂准确调用链

下列行号均为 `drivers/power/oppo/oplus_charger.c`：

| 层 | 准确位置 | 实际条件 |
| --- | --- | --- |
| 周期caller | 7351–7378 | 7357仅判断 `charger_exist`，随后7359保护检查、7361 Full检查；不检查mmi_chg/chging_on |
| Full上层 | 6703–6791 | 可因VOOC/FFC/无线状态返回，但没有mmi_chg/chging_on前置条件；6754–6755按真实硬件Full、已FULL状态或SW Full分支 |
| SW Full开关 | 6679–6698 | 只检查DTS `check_batt_full_by_sw` 布尔，再调用SW/HW后备 |
| SW计数 | 6438–6496 | charger不存在则清；其余按温区、电压和电流计数，没有mmi_chg/chging_on/充电使能判定 |
| 再充计数 | 5261–5304 | 按电压和short-c禁止规则；无mmi_chg门控，触发后5302调用FULL voter start |
| 普通启动函数 | 3996–4024 | 4001–4002确有mmi_chg=0即return；它只约束这个函数，不能当Full状态机门控 |
| 用户MMI停充 | 482–524 | 493–501设置mmi_chg=0并调用turn_off_charging；未清Full计数或total_time |
| UI显示门控 | 6111–6115、6144–6149 | UI Full／Charging分支另要求mmi_chg及stop_chg；不能把UI条件误读成底层Full计数条件 |

另一个不能照搬的细节：再充调用 `oplus_chg_voter_charging_start(FULL)`，4108虽然调用了上述普通启动函数，但随后4111–4115的FULL case仍在 `allow_reading` 时直接 `charger_unsuspend/charging_enable`，**没有再检查mmi_chg**。因此不能声称原厂所有再充硬件路径都被mmi门挡住。当前候选最终 `auto_requested` 写门应保留。

## 建议接入注意事项

不能简单把Full样本的 `policy_good=false` 当作手动INHIBIT，随后不改现有错误处理。候选215–218行会把helper的stop_all转成 `-ENODATA`，这可能造成不必要fault latch。更直接的候选思路是：

```text
if not auto_requested:
    clear only full_state SW/HW/recharge streak
    retain full_state.full and cause
    do not call the transition-counting helper
    expose no new entered_full or recharge event
    keep final hardware INHIBIT and actual error collection
else:
    normal fresh Full/recharge evaluation
```

如果继续使用helper，宜增加明确的operator-paused输入／输出，不要把暂停伪装成坏采集或物理拔线。已经建立的Full事实在暂停中保持；原始REG13硬件Full仍可作为遥测显示，但不要让用户停充期间的新SW计数结束本轮。如何接纳暂停时新观察到的真实硬件Full应与软件streak分开决定，不能用一个AUTO布尔吞掉全部真实遥测。

至少补以下受影响回归：无Full→INHIBIT高压/非充入11样本仍非Full；5个SW合格样本→INHIBIT→AUTO不能借第6份直接Full；已Full→INHIBIT低压6样本仍Full且不recharge；AUTO恢复后需新一轮再充证据；这三条期间已有硬fault/超时不能丢失。

## 原厂total_time的真实累计条件

**原厂timer并非严格“只累计实际充电时间”。** 之前规范里建议按实际充电段累计，是适配选择，不能拿它当原厂源码事实。

`oplus_chg_other_thing()` 6925–6947行的唯一正常累计门是 `charger_exist`。没有检查mmi_chg、chging_on、CHG_EN、净电流或TCA。其时钟取自6915–6922行 `local_clock()`，并非BOOTTIME；不能承诺它把真实系统休眠时间完整计入。

当total_time=0时，记录start_chg_time并立即加5；否则设为 `5 + current_local_clock_seconds - start_chg_time`。调试module参数非0可以覆盖计时，通常应关闭。周期间隔采用5秒round_jiffies，并非每次只固定加5，除了首份样本。

| 条件 | 原厂timer真实行为 |
| --- | --- |
| 源连接且普通充电中 | 按local_clock跨度累计；满36000由4539–4559判超时 |
| 正常Full | Full action5306–5319每周期先清total_time=0；同周期末other_thing又置5。因此稳定Full的**完整周期末通常是5秒**，并非持续字段0 |
| 温控异常 | protection_check5666–5668每次坏温度都调用BATTTEMP voter stop；4159–4163每次清total_time=0；周期末再置5。恢复后从最近一次重置附近继续，旧未完成充电累计被丢弃，非严格pause |
| 充电输入异常 | VCHG voter4151–4157同样清0，周期末再置5 |
| 人为MMI禁止／stop_chg禁止 | 停充入口没有清/暂停total_time；源还在则继续累计。若SW Full随后成立才进入Full的每周期清0/置5行为 |
| TCA停止请求 | 此原厂主充电文件没有TCA专属timer分支；除非Full或其它voter清零，否则源还在就累计。不能推断电量计FET停充会自动暂停此timer |
| 真MAX_CHGING_TIME voter | 4165–4167只停充，不清total_time；到上限保持，不能用恢复AUTO擅自清旧超时 |
| 真实连接／拔线variables_reset | 4919–4963在连接状态重置路径清total_time、Full计数和状态；该行为不能套给一次USB配置额度波动 |

候选当前 `charge-cycle.h` 仍以attach anchor和Full重置为核心，接口没有AUTO/charging-active输入，因此它也不能自称“已经排除了人为INHIBIT／TCA hold时间”；有Full时可避免整次接线10小时到期，但尚不是严格活动充电段计时。

若后续选择更精确的活动段累计，应以已确认控制输出／源许可和状态决定暂停累计，保留已经积累的未完成周期，不能以暂停当成Full归零。净电流<0本身不能定义“未在尝试充电”，因为系统负载可能高于输入且控制器仍处于充电阶段；需要与已验证CHG_EN/INHIBIT、AUTO和Full状态结合。此处只给审查建议，没有修改冻结候选。
