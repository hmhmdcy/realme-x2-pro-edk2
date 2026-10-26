# 充电适配交接（2026-10-25）

## 当前设备与限制

本次只读观察仍在正式506启动 82d6ada4… 上运行。最近读数：测试累计 **8643/36000秒**，手机 uptime 8745秒；电量31%，两节电芯3.844/3.839V，26.2°C，电量计瞬时+74mA/平均+65mA，AUTO、charger/protection Good、fault/error均0。TCPM/native输入预算500mA，软件限值输入500mA、CC250mA、CV8.725V。实验负载duty0.3（SOC高于25%阈值）。supervisor6483/start68160、worker6484/start68170、CPU helpers6485/6486/start68240；只用现有只读 status 核验进程身份。

手机归这次36000秒试验。到期前不刷写、不重启、不切换USB、不重启充电服务或替换当前模块；否则会破坏同一启动的长测。用户无法现场拔线，物理断源/USB唤醒不能由软件模拟。用户报告 /dev/ttyeud0: No such file or directory；82d6只读复查显示EUD tty/getty/reader未就绪且没有当前EUD日志。旧getty保持禁用，不改桌面。需要EUD时先恢复并验证底层EUD路由/设备节点。

## 已完成的离线候选

- [MP2650 TCPM额度消费者](../charging-oem-audit-20261023/tcpm-charger-input-candidate/README.md)：采用 CURRENT_NOW 作为工作电流、CURRENT_MAX 作为能力上界；双快照和电芯采样后复核，物理在线/连接周期与协议态分开。38项真实函数测试、ASan/UBSan、单KO W1/Werror构建过；未安装，不构成完整PD/APSD或高功率支持。
- [ADC5/VBUS板级候选](../charging-oem-audit-20261023/tcpm-measured-vbus-board-candidate/README.md)：本板PM8150B Type-C使用同PMIC ADC@3100 channel8，processed结果是µV；8项实际缩放函数测试过。DTB只增加channel和consumer引用等3处属性，其他节点/属性精确保持。候选DTB b9ecb374… 未刷写；物理精度/时序未验。
- [PD/APSD真实5V接管](../charging-oem-audit-20261023/tcpm-apsd-handoff-candidate/measured-start/README.md)：支持off/vSafe0V和新鲜ADC证明的已连接5V sink；在启动TCPM PHY前关闭APSD/QC，并把真实PHY regulator引用转交给runtime owner。3708断言、156个PMIC故障点、8个生产PHY函数以及2个对象W1通过。full_probe_integration=false；主任务仍需接线，物理断开后的APSD新周期重建未完成。
- [PD合同退出到5V](../charging-oem-audit-20261023/tcpm-contract-shutdown-candidate/README.md)：新Request及本次SOP Accept/PS_RDY完成后，用3次实际ADC样本确认5V，随后才允许原关闭序列；6个相关对象W1零诊断，34个生产函数的ASan/UBSan/Werror控制测试通过。通用 tcpc_dev 布局不变。platform .remove 返回void，失败时无法拒绝解绑并保证devres供电继续存活；因此 high_voltage_adoption_ready=false，不能启用高压。

## 接手顺序

1. 等当前长测结束，先用原只读status确认同一boot、测试进程及最终AUTO/保护状态；不重放旧观察事务。
2. 离线整合两套候选：保留shutdown的最终join/finish次序，解决共同 qcom_pmic_typec.h 字段；在实际 pdphy_probe 与profile判断后、tcpm_register_port() 前接入APSD owner，复用唯一的 tcpm->read_vbus_uv ADC callback和真实PHY quiet ops。不要整文件互相覆盖。
3. 先解决 void remove 和prepare失败时的高压安全收尾。核实provider、IRQ、delayed work及TCPM callback的销毁顺序；未能证明时保持高压路径关闭。
4. 完整整合后只重编受影响对象并重跑合并后的生产函数测试。具备实机窗口后，验证ADC与外部表的误差/时序、已连接5V启动、真实PD Request/Accept/PS_RDY日志、9V→5V及失败退出，以及物理detach后APSD新周期。未经这些验证不能声称完整PD/QC/快充通过。
5. 插入图标仍观测到2–5秒延迟，拔出较快；用户已明确不改桌面。沿kernel/power_supply通知、IIO/Type-C事件和UI读取属性继续查实际延迟，不以桌面重编作为方案。

## 原厂与上游依据

本机Android R固定提交的Oplus charger实现继续作为温控、电池保护和保守PD/APSD交接依据。公开资料：[PM8150B SMB5 v4补丁](https://lore-kernel.gnuweeb.org/linux-pm/20260820-submit-qcom-smbx-send-v1-v4-2-818dabb2771e%40snyders.xyz/)、[维护者要求提供TCPM线上协商证据的评审](https://lists.openwall.net/linux-kernel/2026/10/19/14)、[BC1.2完成后再启动PD的TCPM讨论](https://lkml.iu.edu/hypermail/linux/kernel/2411.1/08795.html)。补丁仍处评审证据范围；不能据此宣称主线已合入或本机QC/PD兼容。
