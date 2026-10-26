# 19781普通充电软件 Full／再充移植规范

本目录是纯PC离线参考，不访问手机、SSH或SDK，不修改生产驱动。已直接提取固定提交的6个原厂函数体并以19781 DTS生成参数，编译执行26个Full／再充边界向量和7个原厂signed电流解码向量；ASan／UBSan通过。生成物、源文件hash、函数准确行号和实际结果见 [reference-result.json](reference-result.json)。[reference-profile.json](reference-profile.json) 是可供portable helper使用的参数；[test-reference.c](test-reference.c) 为可执行向量。

来源沿用已缓存 `realmeX2pro-X3-AndroidR-kernel-source` 提交 `23172a1571bd91156032cc9fef16284a82b63d2c`。以下简写 `charger` 指 `drivers/power/oppo/oplus_charger.c`，`gauge` 指 `drivers/power/oppo/gauge_ic/oplus_bq27541.c`，`DTS` 指 `arch/arm64/boot/dts/19781/pm8150b.dtsi`。没有重新下载整个仓库。

## 输入与单位

每次状态机输入必须来自同一轮新鲜、完整、通过保护和预算检查的样本：实际online与USB许可、电芯1/2、温度、MP2650 REG13/REG14、已有硬fault／超时、signed净电流、BOOTTIME。`max_cell_uv=max(cell1,cell2)`，不是整包除2；这是 gauge 408–432、2468–2490 的原厂语义。

**电流寄存器必须说清：** gauge 的函数名 `bq27541_get_average_current()`（1207–1233）一般读 `reg_ai`，但真实legacy FFA5分支在1590–1592将该选择器改为 `Bq28Z610_REG_TI`。已缓存原厂头 `kernel85/official-oplus_bq27541.h` 26–27行给出 `TI=0x0c`、`AI=0x14`，175行给出 `DEVICE_TYPE_BQ28Z610=0xFFA5`。本项目原有审计 `reference/kernel85/source-audit.json` 也已记录这一区别。

- 0x0C是瞬时signed current；0x14是真正AverageCurrent。当前主线 `CURRENT_NOW` 读0x14，不能直接声称它等同原厂这个Full判定输入。
- SMBus word成功值0..65535先与负的总线错误分开，再按二补码 `word>=0x8000 ? word-0x10000 : word` 解码为mA，最后乘1000为µA。**正gauge电流表示充入**。
- 原厂函数末尾返回 `-curr`，所以原厂 `icharging<0` 实际是正gauge充入；portable接口宜保留正充入，不要再取两次反。
- 本目录实际执行了原厂电流函数体，验证原始 `0x006e→OEM -110mA`、`0xffff→OEM +1mA` 等7例。传输失败必须传播；不要复制原厂读取失败后返回旧值时可能改变符号的缓存分支，也不要把失败当0mA累计11次Full。

本机扩展身份0x2719不能单靠名称当成标准2610；上述legacy选择器及报文兼容性有既有本机证据，新的0x0C用途仍需集成后以实际完整样本核对。不要因此执行解封、NVM或保护FET命令。

## 完整参数与精确比较

以下均为单芯电压，单位mV；portable实现请乘1000。表中HW Full是软件电压后备，不等于MP2650的硬件CHG_STAT Full。

| 温区 | OEM CV | SW Full严格大于 | HW后备Full大于等于 | OEM再充小于等于 | 当前band OVP大于即拒绝 |
| --- | ---: | ---: | ---: | ---: | ---: |
| cold −2..0℃ | 3980 | 3930 | 3998 | 3680 | 3990 |
| little_cold 0..5℃ | 4400 | 4350 | 4418 | 4200 | 4410 |
| cool 5..12℃ | 4400 | 4350 | 4418 | 4300 | 4410 |
| little_cool 12..16℃ | 4400 | 4350 | 4418 | 4300 | 4410 |
| normal 16..44℃ | 4400 | 4350 | 4418 | 4300 | 4410 |
| warm 44..53℃ | 4130 | 4080 | 4148 | 4030 | 4140 |

来源：DTS 281–323的CV／温区，332–337的SW门限，363–364的两种HW增量18mV；`charger` 6438–6553、5261–5304。

适配继续沿用原目标上限，例如当前继承单芯4.3625V，不能为满足OEM表抬到4.4V。再充门限建议使用 `min(OEM温区CV, 实际已采用的温区/继承CV) - offset`，offset依次为300/200/100/100/100/100mV。因而当前normal例为4.2625V，little_cold例4.1625V。这个clamp是适配选择，oracle原厂normal向量仍使用4.300V，两者必须分开标注。

HW后备门限不要擅自改成“当前CV+18mV”，那会让4样本Full提前；完整安全policy应先判OVP，因此上表HW门限均高于当前OVP，正常情况下这条后备不应越过OVP获准充电或清故障。SW门限／实际MP2650硬件Full才是当前更直接的普通路径。若继承CV低于SW门限，保留真实硬件终止作为后备，不为凑软件Full提高电压。

## 精确计数与节拍

`charger` 91–95行定义5秒周期并使用 `round_jiffies_relative` 调度。计数是每次有效周期消费一份样本；本机1秒poll不能每秒加1，也不能在唤醒后用一份样本补多个丢失周期。

SW Full只用一个共享counter（6435–6496）：

```text
if max_cell <= sw_full_limit: sw_count=0, sw_full=false
else if 0 < gauge_current_ua <= 110000:
    ++sw_count
    if sw_count > 5: sw_count=0, sw_full=true
else if gauge_current_ua <= 0:
    ++sw_count
    if sw_count > 10: sw_count=0, sw_full=true
else: sw_count=0, sw_full=false
```

因此是第6或第11个样本，不是5／10；正充入／非充入分支切换时原厂不清counter。例如5个零电流样本后一个+110mA样本就触发第6样本Full。Oracle已验证此边界。原厂也未专门在温区切换清此counter；适配若为避免跨模式拼接而清streak，应注明这是更严格的选择。

HW电压后备（6498–6553）：`max_cell>=OEM_CV+18000µV` 时 `++hw_count`，到第4样本Full，否则counter=0。真实REG13 CHG_STAT==3是独立硬件Full证据，可在完整安全样本上直接进入Full；不要用SOC100或一次current0代替。

再充（5261–5304）：Full保持期内，每份有效样本满足 `max_cell<=recharge_limit` 时 `++recharge_count`，`>5`即第6样本请求新周期，否则清counter。`short_c disable_rechg` 时原厂把计数封顶5，永不触发。源未知、采样失败、保护错误或温控暂停不应累计有利证据。

首个合格周期就计为1；以t=0、5、10…采样，第6个样本首末跨度25秒。不要把“6个5秒样本”硬解释成首次计数前必须等满30秒。相邻周期存在正常调度抖动，不能以纳秒精确 `gap>5.000s` 每次重置；portable helper应规定5秒最小消费周期、不追赶，并为真正漏采样定一个明确边界（例如超过两个周期），作为适配选择记录。

## 可编程状态机与优先级

将永久硬锁存、暂时输出模式和Full周期状态分开，建议输出 `INHIBIT_ALL / CHARGE / FULL_INPUT_ON` 三态，便于驱动避免充电脉冲。状态转移顺序：

1. 已有硬锁存／已确认真实充电周期超时始终优先，输出INHIBIT_ALL；Full、温度或USB恢复不能清旧fault。
2. 新鲜采集、全局电芯域／整包一致性、Safety/PF/REG14、TCA/OCA分类失败先处理；真正保护或总线错误仍锁存。源过渡或纯温控reason输出INHIBIT_ALL，可后续重评，但不能清旧硬fault或累计Full／再充streak。
3. 实际断开经两来源确认后结束会话；清可恢复计数。临时USB零额度／未知源不是实际断开，不能擦掉尚未完成周期的时间。
4. NORMAL且完整安全样本：真实硬件Full或SW/HW参考谓词达到门限，进入FULL_INPUT_ON，确认本轮完成并将本轮timer结束。否则继续CHARGE并累积本轮实际充电时间。
5. FULL且完整安全样本：保持CHG_EN=0；每5秒判断一次再充；达到第6份证据且无TCA/其它阻止时请求NORMAL新周期，清本轮计数并从0开始计时。不能用Full来清之前已经成立的硬超时。
6. Full期间临时源不明、温度不合适或系统休眠可转暂时INHIBIT_ALL；保留“已Full”的周期事实，待新鲜许可恢复后继续Full保持或再充判断。

原厂Full动作（5306–5319）每次Full执行 `total_time=0`，而真实time检查在4539–4559；原厂update的保护→Full→其它timer顺序见7351–7378。适配保留这项易失周期语义即可，不需要引入未经用户要求的跨boot永久到期。

## Full时保留输入，别复用安全INHIBIT

DTS 399行的 `suspend_after_full` 是注释。`charger` 4088–4099因此选择CHG_DISABLE；FULL voter 4134–4149调用turn_off_charging，后者4032–4060最后调用 `mp2650_disable_charging`。OEM MP2650的910–927行只写REG08 CHG_EN(bit4)=0。输入converter LEARN_EN(bit3)保持未暂停。

当前安全停充 `sm_stop()` 同时关CHG并置LEARN_EN（mask0x18/value0x08），适用于保护／无许可／休眠。它不能直接代表普通Full保持，否则插电满电后系统可能仍主要耗电池，再触发不必要再充。

正常Full保持应：CHG_EN=0、LEARN_EN=0，实际输入额度继续随USB许可下降或恢复；必要的限流／CV修改仍按暂停输入→写入并回读→只恢复输入的事务进行。**不能先调用当前 `sm_apply()`（它最后启用CHG）再清CHG来模拟Full，那会每次制造短暂充电脉冲。** 若从INHIBIT恢复到Full，也不能只清bit4而留下旧LEARN_EN=1。

OEM MP2650 `read_full()` 1041–1057虽然计算终止状态，结尾实际写死return0，这是原厂实现缺陷。当前Linux对REG13的已验证解释可以使用，不应为了逐字复刻把这个错误移植回来。

## TCA与OCA必须区分，但本轮不能凭TCA放行

已缓存TI SLUUA65E第27页§4.8（txt1207–1215）规定：TCA可来自SafetyAlert的OCC/COV/OTC，也可来自GaugingStatus.TC且仍是CHARGE模式；OCA则表示SafetyStatus.OC且处于CHARGE。第70页§12.1.6给出TCA bit14、OCA bit15、FC bit5。

所以必须在状态定义上区分TCA/OCA，不能把TCA alone称为“电池坏了”，也不能把它alone称为“正常充满”。当前允许查询的是SafetyStatus0051/PF0053/Operation0054/Manufacturing0057，未取得本机SafetyAlert0050和GaugingStatus0056；`SafetyStatus=0`并不排除尚未trip的SafetyAlert。没有这两份兼容性核对前，合理最小策略是：

- OCA或实际Safety/PF/MP故障：硬阻止，保持旧锁存。
- TCA：停止充电并hold，不直接宣告Full，不清锁存，不授权再充。
- 已有独立可信Full仍不能绕过TCA停充请求；后续证据完备才能区分正常TC与保护预警。

将来若补0050／0056，须先核对0x2719族返回长度／位布局，再加只读白名单和传输故障用例。不得以此为由修改保护配置、开启PF_EN或操作FET。

## 运行与证据范围

在Windows工作区运行 `python reference/charging-oem-audit-20261023/software-full/build-reference.py` 会只在本子目录生成DTS参数、抽出原厂函数并调用WSL gcc测试。所有源文件hash和准确函数行号保存在reference-result.json。

这33例证明固定OEM代码的边界与符号，不证明portable helper已经等价，也不证明实机Full／再充、温区、输入维持或低电量预充已通过。根会话和session_persistence支线负责候选合并、受影响测试及有窗口时的实际验收。
