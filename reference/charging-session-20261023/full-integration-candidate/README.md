# 完整软件Full候选：仅离线，未部署

2026-10-23。从当前生产9d9对应源码复制，[baseline.json](baseline.json)固定七个实际来源SHA。生产C为`986e16af…458e`、core为`f9ffc2d3…0af3`；本轮未修改主目录、手机、SDK或共享kernel。此目录可交根会话审核并进行私有真实k363 in-tree模块增量构建。

候选[源码](samurai-mp2650.c)、[核心](mp2650-core.h)、[状态机](oem-full-cycle.h)、[通知字段](charging-notify.h)和[完整小补丁](full-integration.patch)已经落盘。补丁只改变这四个文件，其余原厂profile、cycle、gauge transport/protocol均逐字节保留；`git apply --check --ignore-space-change`已在独立baseline副本通过。没有重放原厂init、修改安全计时/终止/NTC、提高继承CV、写FET/NVM或扩充MAC白名单。

实际行为：

- 原gauge segment锁内增加0x0c读取，按signed瞬时净电流解码；仍需MAC0071及全份采样成功，并通过末尾双源/预算一致性复读，才标记fresh有效。任一word/MAC失败整份不参与Full计数。0x14平均电流不冒充OEM 0x0c语义。
- 软件Full继续严格5秒最小计数、正充入≤110mA第6次、非充入第11次、共享counter；温区门限与六次再充复用原厂。正常缺样/UNKNOWN/温区变化中断streak，缺观测≥10秒不catch-up。独立真实REG13硬件Full是已发生的完成事件，因此不等待软件tick，避免同时限值改变走普通充电使能路径。
- Full处理先于本轮周期累积；新第6样本恰在36000秒可结束尚未超时周期。已经成立的`cycle.timed_out`仍在validation之前优先检查，Full/AUTO均不能抹掉。真正再充事件以当前BOOTTIME开启新周期，不带入上一Full样本间隔；真实detach正常停充、清周期/Full且不制造新锁存。
- 新`sm_apply_charge_hold()`第一硬件动作仅清CHG。稳定Full不产生任何写入；配置/输入预算变化时先安全暂停，再更新并校验两路输入限值及必要CC/CV/预充配置，最后只解除输入抑制，所有分支绝不写CHG_EN=1。每个错误走`sm_stop()`，主错误和停错误分别保留，不回滚到更大旧预算。
- 正常Full的`target.enable=0`表示期望CHG关闭；`hold_requested=1`表示正常Full请求，`full_holding=1`只在本次专用保持事务成功后声明converter正常/CHG关闭。异常或显式inhibit使用既有双抑制stop，影子模式不会假称实际full_holding。
- TCA原bit14保留，新`SM_POLICY_REASON_GAUGE_CHARGE_STOP/-EAGAIN`在真实fault/OCA/timeout及全局数据域/一致性检查之后给出；即时停充，自动请求仍保留，但不当Full、不清旧latch、不授权再充。旧fault、MAC错误或stop失败仍锁存。候选没有增加0050/0056分类，也未把TCA暂停计时与已完成周期混为一谈。
- 原1秒保护/供应器通知调度保持；新增Full/hold/TCA字段只是离散通知状态，ADC/age/session噪声仍不触发每秒广播。实际battery STATUS仍由gauge的净电流/FC给出，不将软件Full强写为gauge事实。

[测试结果](test-result.json)使用实际候选函数抽取和真实头文件，ASan/UBSan全部通过：

| 范围 | 证据 |
| --- | --- |
| Full事务 | 14条序列/97断言；全部8个实际写点逐一失败，主/停errno分别保留，全写日志无CHG=1；稳定Full零写入，两输入下降均更新 |
| 实际gauge采集函数 | 7条序列/20断言；0x0c与其它word/MAC同segment，逐word/MAC失败均解锁且不标fresh；加入Linux `current`宏模拟避免局部同名冲突 |
| 实际候选step | 19条序列/111断言；冷热/OVP恢复、MAC/stop失败、旧fault、真实detach、36000秒新Full边界、既有timeout拒绝Full/TCA、硬件Full非tick预算下降、真实再充起点、TCA/OCA/全局域优先级 |
| 软件Full组件 | 16条序列/251断言，含六温区再充、5秒节拍、缺采样及TCA拒绝 |
| 独立OEM差分 | 52项直接比较固定原厂真实提取函数及signed解码 |
| 既有核心回归 | 6016策略、113事务、8锁存序列原用例通过 |

测试harness的CHECK只求值一次，避免失败注入或状态转换被断言宏重放；提取的step与本目录`candidate-step.inc`一致。完整函数、头文件、测试源码和基线SHA均保存在结果，未把host测试称为kernel编译或实机通过。根会话随后仍须真实in-tree W=1编译及按实际改动验证加载/Full/再充，不运行本目录脚本直接替换手机。

部署前还须同步两处用户态兼容（本候选未修改用户态）：`samurai-charging.py request()`当前只容忍源未知，若启动时恰遇安全TCA -EAGAIN会进入异常inhibit，需精确容忍无latch/stop_error的gauge_charge_stop并保留AUTO；`charging-health.py`把`desired_enable=0`归为inhibited、把任何session下降当回退，新正常Full保持和新周期必须按明确状态归类，不能继续套旧单调attach时间审计。TCA正常终止分类/仅hold时是否暂停而不完成周期，需结合另行只读0050/0056及工厂2719兼容证据审核；当前保守停充不擅自解释TC。
