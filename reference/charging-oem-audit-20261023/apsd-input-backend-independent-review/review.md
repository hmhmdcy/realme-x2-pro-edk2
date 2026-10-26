# R7 APSD input backend薄审：当前新增范围未见阻断

只读审查wrapper `fc7c42cf…27d7`、实际inc `ef6baeee…4ff2`和API头 `00d5659e…ee94`。没有运行入口、测试或构建，没有设备/SSH/SDK操作，也没有改候选叶。定向测试/对象构建收据尚由作者准备，本结论不替代这些收据或硬件验收。

- `rerun_once`拒绝零epoch；同值EALREADY、较小值ESTALE。新值在paused/joining判断和regmap之前记录，因此被阻止或返回transport errno也消耗，resume没有重置/补写。最大u64消耗后不能回绕重新尝试。
- `read_sample`在同input mutex中做两次新的七寄存器读取，完整tuple不等或四个物理位混合时EAGAIN；错误不发布输出、不增加serial。成功才++serial，overflow在读取前拒绝。它不使用budget.last或UDC cache，也不把present解释为sink/PD/route许可。
- 实际cache的regmap.h 1373–1376将`regmap_write_bits`转成force=true；regmap.c 3249–3282先read保留其它位，force条件不跳过_write。PMIC配置16-bit reg/8-bit val、默认REGCACHE_NONE，SPMI bus没有reg_update_bits捷径。因此成功的该RMW产生一次1341写，即使bit0原来已为1；它另有保留其它位所需read。读取失败可以零写，epoch仍消耗。不能把“一次write请求”说成已观测一次物理APSD完成或只有一次总bus事务。
- withdraw先在input锁内置joining/摘registered标志，放锁后调用同步unregister。owner的registry锁不会被worker获取，unregister的join等待callback退出时input锁已释放；之后R7 stop才置paused、清UDC有效性并同步cancel poll。probe的stop devres action在power_supply注册后加入，故LIFO下join/停poll先于psy/input存储释放；不是仅靠device/module引用假定regmap寿命。
- default apsd_backend=false；注册失败只阻断可选transport，原budget observer继续。旧get_budget/getter/setter/poll与decode逻辑保持。可选stop的joining标记不参与原budget计算。新路径没有1358/1362/PD/role/charger/预算写。

锁审查限于实际input→regmap回调和释放input锁后的owner_registry→join链。它不能认证尚未接入的PD/route/PHY/DWC所有权图。当前owner entry_gate仍对每次硬件attempt返回EOPNOTSUPP；backend注册不构成启用许可。

另有一个应保留的**跨provider instance可用性边界**：同一个input的suspend/resume保留serial和attempt epoch；全新input重probe会从serial1开始。API定义serial为registered instance域，而owner保留的once.last_read_serial没有在bus_register换ctx时显式换域。如果旧物理session没有观察detach，新ctx的初始serial可能被ESTALE拒绝；现owner对未attempted错误没有自动补读，可能等下一事件/真实detach。这是fail-closed边界，不是本inc放行重复write；本次不修改owner，也不宣称任意source重probe已经完整恢复。未来替换关闭的entry fence时需把此语义纳入真实provider生命周期契约。
