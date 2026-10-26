# 原厂动态温区最小 r6 候选

本目录独立基于已冻结 `kernel-v2` 八文件，差异仅为 [thermal-bands.patch](thermal-bands.patch) 中的三个既有文件和一个新头文件。根会话已完成[私有k363单模块编译](../../charging-management-20261023/thermal-bands-build-result.json)，W=1无warning/ABI和有效CONFIG不变，ko `10ec06fb…6297f`；[R8两文件包](../../charging-management-20261023/r8-payload-result.json)经[单次更新](../../charging-management-20261023/r8-update-result.json)实际加载。NORMAL下停充/恢复、caps、三notes、fresh保护/相机/四服务通过并已交还窗口。未做实物温界刺激，未修改 main、冻结 v1/v2、共享源码/SDK，未重建Image或重启。

候选以**一个 OEM effective band** 同时选择 CC/CV/OVP、软件 Full、电压 Full 和 recharge 参数，撤掉旧的固定外界2℃恢复状态机。没有 static∩effective 双表，也没有另一个固定2℃恢复门。继承的全局 CV 上限及250mA充电/900mA输入请求帽原样保留，实际源预算仍可进一步压低输入；不引入 PD/QC/VOOC/FFC、normal 高功率子区、相机/通话等情景功率策略。

## 原厂证据与顺序

复用已缓存官方仓库 `realmeX2pro-X3-AndroidR-kernel-source` 的固定提交 `23172a1571bd91156032cc9fef16284a82b63d2c`，源码和19781 DTS指纹见 [oracle-result.json](oracle-result.json)。温度单位是0.1℃，电流/电压转换后是µA/µV。应以本机DTS的 `-20,0,50,120,160,440,530` 为准，源码注释里残留的“-3℃/45℃”不是这台19781配置。

原厂 [oplus_charger.c](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/power/oppo/oplus_charger.c) 的关键位置：

- 4174–4267：`battery_temp_anti_shake_handle()` 用 `tbatt_status`、`tbatt_pre_shake`、不可变 `anti_shake_bound` 和可变 `limits`。方向根据当前温度相对 `pre_shake`，普通同带样本不更新它；一般移动20decic，0℃处单独移动5decic。
- 4271–4337：`oplus_chg_check_tbatt_is_good()` 先根据**上次可变边界**分带；首次 `pre_shake=999` 时先seed当前温度。只有带改变才更新 `tbatt_status`，调用CV/CC setter，再重算下一次边界并更新pre_shake。`TEMP_CNT=1`，不是额外多周期去抖。
- 7351–7361：周期先detect/get-data，再 `protection_check()` 更新温区，之后normal子区、Full/recharge。因此这些阈值消费同一 `tbatt_status`。候选同样在Full前确定一次effective band，每个poll仍受全部硬保护验证。
- 4919–4993、5096–5184：原厂接入/断开reset与init会恢复基础边界、NORMAL、pre_shake=999和Full/session状态。候选仅在既有PMIC+ACOK一致的真实detach分支清全部温区历史，临时零预算、未知源和缺失样本不能当detach。

动态边界不是统一±2℃施密特：

| 新状态 | 相对pre_shake升温后的可变边界 | 降温后的可变边界 |
|---|---|---|
| COLD | cold=-4℃，上界0℃ | cold=-2℃，上界+0.5℃ |
| LITTLE_COLD | 下界-0.5℃，上界5℃ | 下界0℃，上界7℃ |
| COOL | 下界3℃，上界12℃ | 下界5℃，上界14℃ |
| LITTLE_COOL | 下界10℃，上界16℃ | 下界12℃，上界18℃ |
| NORMAL | 所有边界恢复基础值 | 所有边界恢复基础值 |
| WARM | 下界42℃，hot=53℃ | 下界44℃，hot=55℃ |
| LOW / HIGH | LOW升温时cold仍-2℃；HIGH升温时hot=51℃ | LOW降温时cold=0℃；HIGH降温时hot仍53℃ |

方向相等时偏移全为0。首次样本会先seed pre_shake，所以不能假定每次进入冷/热都要恢复2℃。原厂通用函数的实际波动序列已在候选实现前由97断言oracle独立跑通：从NORMAL降至-0.1℃后，COLD保持至+0.4℃、+0.5℃才LITTLE_COLD；之后-0.5℃仍LITTLE_COLD、-0.6℃才COLD。44℃进入WARM后，42.0℃仍WARM、41.9℃才NORMAL，回44.0℃再入WARM。

## 有意保留的差异和保护边界

候选保留 r6 **原始温度 `<-20` 或 `>=530` 立即停止**，这一绝对门来自当前profile/适配的严格安全范围。原厂动态边界会把COLD放宽至-4℃或WARM放宽至55℃，且原厂hot比较为 `>hot`，53.0℃本身仍可WARM；候选在这些原厂可充样本上更严格停止。该差异没有被隐藏或描述成原厂完全等价。

温区状态仍按原厂通用算法更新，包括全部七个动态边界；绝对门只阻止外界充电授权，不新造固定恢复迟滞。例如effective band可能仍为WARM但raw=53.0℃，此时仍停止、Full policy_good=false；raw回52.9℃且同一动态状态允许时即可恢复。首次raw=-2.1℃后回-2.0℃也可恢复，不能被旧的固定“回到0℃”再挡住。`hold`现在只是 `raw绝对越界 || effective band不在六个可充带` 的诊断结果，不独立保存另一套恢复历史。

0℃方向窗口会改变部分低温点相对r6静态表的目标：LITTLE_COLD从正温回到-0.4℃时，原厂仍选择4.4V/芯档；受继承4.3625V/芯上限约束，候选实际目标为4.3625V，而旧静态COLD为量化后的3.975V。CC仍不超过250mA，输入仍不超过900mA及真实USB预算。此变化有同机原厂函数和DTS依据，**尚未经过实物温界验收**。WARM的4.13V目标向下量化到4.125V，COLD的3.98V向下量化到3.975V；不提高任何继承全局上限。

Full有三项既有/明确的保守适配继续保留：

1. 原厂离开WARM或COLD且 `soc!=100 && batt_full && charging_state==FULL` 时，温区检查里会立即撤FULL voter（4319–4326）。r6当前没有这一SOC输入；本补丁不伪造SOC或直接启动充电。已Full事实/cause保持，最终target和新effective band决定recharge阈值，仍需六份新鲜合格低压证据。
2. 原厂SW/HW/recharge计数按新阈值判断，并非每次跨带都无条件清零；97断言oracle实际证明同阈值跨带SW计数会延续。r6现有的**effective band改变即清未完成streak**更保守规则保留。原始温度跨44℃但effective band未变时不误清streak；真正跨带才清。五秒tick、连续性/缺样处理、手动INHIBIT不建立新Full/recharge的规则原样保留。
3. 原厂normal子区函数4432–4471有一个真实副作用：`normal_pre_shake`仍INVALID时写父层`tbatt_pre_shake`，且update_work会调用该函数；normal子区首次改变状态后才更新自己的pre_shake。独立oracle已演示此调用条件。r6未实现该normal子状态机，本候选不硬抄其初始化副作用。因此差分结论限于原厂**通用温区函数**，不声称完全重放整个OEM work循环。

## 样本、故障与手动停止

先运行完整既有验证。当前采集/MAC/I²C、保护缺失、电芯/pack数据异常、OCA、电气故障、旧timeout、TCA等非温控失败优先，不能被温区恢复掩盖，也不能靠旧温区标签允许充电。只有当前完整在线样本且验证成功或仅温度/温区OVP拒绝时，才更新动态温区并用该effective band重新执行**全部**验证。这样可正确处理LITTLE_COLD动态延伸时的原静态COLD OVP拒绝，也确保WARM动态延伸时采用更低的WARM OVP。

缺失样本/未知源冻结历史、不假装detach；原有Full streak被阻断，既有故障锁存不清。手动INHIBIT期间仍读取新鲜保护并更新温区历史，但沿用v2的Full skip：保留已Full事实、清未完成streak、不产生recharge/entered事件、不请求正常converter hold，实际CHG/输入仍停止。AUTO后重新用当前band开始新证据。真实detach清所有七个动态边界、band/pre_shake及Full/session；STOP写失败继续锁存，不能由温区变化赦免。

所有新运算在既有`c->lock`调用链内，纯内存，不增加I²C读取、设备引用、锁或广播。telemetry只新增 `thermal_band` / `band_pre_shake`；六个可充带按0…5，LOW=-1、REMOVED=-2、HIGH=6，尚未有历史时=-3。继承masked事务、源预算复核、硬故障优先、CHG保持/INHIBIT写门原样不变。

## 软件证据及交付

[test-result.json](test-result.json) 的新验证全部 `-Wall -Wextra -Werror`、ASan/UBSan通过：

- 独立实际OEM函数差分20,079连续样本、368,171断言；band/pre_shake/七边界逐样本相同，151样本输出差异仅为上述绝对stop更严格。包含0℃、44℃连续小幅波动、所有内部边界、首样本、动态外界和可复现游走。没有用另一个新helper充当oracle。
- 真实候选 `sm_step_locked()` 提取体33序列/278断言，覆盖继承Full/硬故障测试及新单band目标/OVP、raw波动不误清Full计数、首次恢复、0℃扩展目标、缺样冻结、真实detach、INHIBIT/重新AUTO和六份recharge。旧“必须先恢复2℃”测试的HIGH入口由530改为531，匹配原厂严格`>hot`；另有明确530绝对stop测试。
- 原97断言oracle没有重跑，收据字节指纹保持；冻结v2八文件仍逐件匹配原baseline。

`thermal-bands.patch` 基线是本目录 [baseline.json](baseline.json)，新依赖`thermal-bands.h`已随三个变更文件完成独立模块编译及R8加载。完整温控、实体Full/再充和图标仍未验收。
