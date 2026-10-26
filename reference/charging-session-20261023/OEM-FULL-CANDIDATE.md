# 原厂软件Full／温区再充离线候选

2026-10-23。独占目录内完成，未修改主生产9d9，不访问手机、SSH、SDK或共享kernel；不新增跨boot持久化daemon。

[oem-full-cycle.h](oem-full-cycle.h)实现实际可移植状态机，只返回状态和动作意图，不读写寄存器、不提高CV、不关闭硬件termination/safety/NTC。原厂固定来源、逐函数提取指纹及官方手册分类见独立[OEM规范/参考实现](../charging-oem-audit-20261023/software-full/reference-result.json)。

准确复用的行为：

| 项目 | 候选行为 |
| --- | --- |
| 采样节拍 | BOOTTIME最小5秒，首个合格样本即计1，禁止catch-up补造样本；1秒driver轮询也只能每5秒累积一次 |
| 软件Full电压 | 冷区严格大于3.930V、0–44℃各区严格大于4.350V、暖区严格大于4.080V；使用两芯最大值 |
| 软件Full电流 | 真正gauge净电流，正值为充入。`0<current<=110mA`第6个合格样本；`current<=0`第11个合格样本。两分支共享counter，切正负不清counter |
| 电压后备Full | 大于等于原厂温区CV+18mV，第4个样本。没有降低成当前实际CV+18mV，更不能绕过当前温区OVP |
| 硬件终止 | 已验证REG13 CHG_STAT3可在合格5秒tick内建立Full；保留真正硬件termination、安全计时、NTC作为兜底 |
| 再充 | Full后最大电芯连续6个合格样本低于或等于门限。冷区CV−300mV，微冷CV−200mV，其它CV−100mV；不得跨短路禁止再充状态直接使能 |
| 旧fault／timeout | 输入仍须无旧锁存、无timeout、MAC保护完整良好、完整策略有效；helper不清任何外部fault/latch/time字段 |
| TCA/OCA | TCA默认停止hold，不能单独作为Full/允许再充/清fault证据；OCA拒绝；FC bit5本身也不声明Full |
| 正常Full | 输出`hold_charge_only`；正常充满只停CHG，保持输入converter/USB预算。异常条件输出`stop_all`，优先于其它输出 |

严格电流来源不能混淆：原厂`bq27541_get_average_current()`命名是average，但FFA5分支将`cmd_addr.reg_ai`映射到`Bq28Z610_REG_TI=0x0c`，这是瞬时signed电流；函数随后取负转成OEM充入为负的约定。`0x14`才是真正AverageCurrent，当前主线`current_now`实际读0x14；候选复用原厂语义需要在同一fresh gauge采集中读取0x0c，不能拿输入电流、设置上限或缓存平均电流冒充。`sm_oem_gauge_current_ua()`已验证0x8000/0xffff等有符号边界。

明确适配选择（不冒称逐字复刻）：

- 缺少有效观测达两个周期（≥10秒）、显式错误/UNKNOWN/保护无效，以及温区变化，均清当前连续计数；逻辑Full仍保留，实际操作保持停止。原厂本体没有显式清温区切换的静态counter；此处更保守地防止跨门限累假连续样本。5.01秒正常调度抖动允许，单次迟到不制造多份样本。
- 再充门限先用`min(当前实际量化CV, 原厂该区CV)`，再减300/200/100mV，绝不为对齐原厂把当前CV抬高。默认当前正常区4.3625V对应再充4.2625V；冷区3.975V→3.675V、微冷4.3625V→4.1625V、暖区4.125V→4.025V。软件Full门限保持原厂值，没有主动降低为更容易通过的数值。
- 已知1秒fresh观测在两个5秒tick间推翻电压/电流条件时立即清streak；不会选择性忽略已知不合格样本。短路禁止再充出现时清再充counter，解除后需重新积累六次。
- TCA在官方资料中既可能由正常TC也可能由SafetyAlert OCC/COV/OTC触发；现有SafetyStatus0051/PF为0不足以证明Alert0050/GaugingStatus0056。工厂2719还需核对协议，因此本候选不擅加MAC命令或把TCA等同正常Full。TCA不授权重充；也不把输入flags永久改写。

验证：

- [候选定向测试](oem-full-test-result.json)：16条序列、251个断言，ASan/UBSan通过；包括6/11共享计数、4样本后备、六温区再充、lower-CV限制、1秒poll/5.01秒抖动/长gap、未知源/错误/旧fault/timeout、TCA+FC+硬件Full拒绝、真实断源及反向时钟。
- [52项独立差分](oem-differential-result.json)：直接调用另一子代理从OEM源码抽取的真实函数，在原厂名义CV输入下比较六区SW边界/110mA边界、HW18mV边界、再充门限/禁止重充及7个signed解码，ASan/UBSan通过。此项刻意不混同上述更保守适配差异，也不授权当前OVP不允许的电压后备输入。

根会话审核后最小接入：

1. 在`sm_charger`增加一个`sm_oem_full_state`，只在probe初始化；真实双源断开可重置，UNKNOWN不能伪装为detach。
2. 在已有锁住gauge总线的完整采集中加入0x0c读取，失败即整份样本无效；最大电芯由当次校验MAC0071取得，REG13 Full来自当次独立源状态，不能用SOC/UPower图标当输入。把实际量化并受继承上限的`target.cell_uv`交给helper。
3. 保留完整电气/温控/总线/原厂会话保护检查在先。异常直接`stop_all`，不因逻辑Full清除旧latch或超时；TCA分类需要根单独审核，当前core返回TCA错误时不能仅为了helper把错误mask掉。所有安全数据不齐时本helper仅给停止，不做周期重置。
4. 正常Full新增独立事务路径，不能把`sm_stop()`的CHG+输入双抑制当作普通Full。该路径还必须依据当前真实USB allowance更新/校验两个输入限值，使Full期间源预算变化也不保留过大的旧输入上限；不得先调用会重新使能CHG的普通`sm_apply()`再每秒清CHG。最终只关CHG、输入保持正常，任何失败转既有安全stop并锁存。
5. `full/entered_full/recharge`与现有周期计时显式衔接：合格正常Full期间归零本轮；真正再充开始新周期；已有超时不重置。不要仅因helper内部保存了逻辑Full就让未知/坏样本重置10小时限制。
6. 新helper及交易函数均先做真实`sm_step_locked`整合定向测试，再增量构建受影响模块。待根会话审核后才部署，与摄像头会话协调窗口。离线差分不等于实物低压预充、软件终止／温区再充验收。
