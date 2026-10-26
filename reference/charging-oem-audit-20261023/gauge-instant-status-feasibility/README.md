# BQ28Z610 STATUS使用瞬时净流：离线可行性与最小设计

**技术上可做有板级范围的STATUS瞬时净流候选，但“只改STATUS、CURRENT_NOW仍平均”不能保证双向图标都更快。** 这值得作为独立内核候选审阅，不能宣称003的4.11秒全由平均滤波造成，也不应混入当前只变EUD boot policy且保留Image363的试验。

本叶仅恢复源、锁和属性语义，未写可应用patch、编译或部署。`collect.py/source-result.json` 固定来源；`kernel-excerpts.txt`、`board-config-excerpts.txt` 保留准确行号和配置。没有设备/SSH/USB/SDK/Git动作，没有调用或建议在gauge getter中调用 `power_supply_is_supplied`。

## 已有本机/原厂依据

- 精确原Image363 SHA `15746aab…d6468` 的**内嵌IKCONFIG**，不是用当前共享.config替代：`CONFIG_BATTERY_BQ27XXX=y`、`CONFIG_BATTERY_BQ27XXX_I2C=y`、DT_UPDATES_NVM关闭。其配置抽取SHA在source-result。原native DTB `c559d2c4…c4503` 的fuel-gauge@55使用 `ti,bq28z610`。
- 固定Image关联bq27xxx核心 SHA `b2cd415a…aec69e`：bq28z610表504–523行的AI=0x14；1055行使用BQ27Z561位布局。当前1860–1913函数从同一个AI signed值同时产生CURRENT_NOW及STATUS，FC仍优先。1932行cache update也调用这条状态路径；只改get_property STATUS一处会留下通知比较仍用旧平均流的缺口。
- 原厂AndroidR同机 `oplus_bq27541.c` 1590–1592仅在legacy FFA5分支把reg_ai选择器改为头文件26–27行的TI=0x0C，AI=0x14；1207–1233的所谓get_average_current读该选择器并在API出口取负。**Linux正值=充入，不能照抄原厂这个API取负号。** FFA5是legacy接口，扩展实物身份0x2719；不因此冒认精确标准2610硅片/固件，也不扩展其它flags/MAC语义。
- TI原始SLUUA65E缓存Table12-1（文本2720–2729，正文67页）明确0x0C/0D为只读signed瞬时sense current，0x14/15为只读signed average current，均mA、每秒更新；§12.1.7/12.1.11（正文70/71页）给出Word/I2。没有给出本机平均滤波时间常数，不能把“每秒更新”理解为1秒平均窗口或4秒固定延迟。
- 精确已编R8 charger `ed2e1d4…a144c` 73–93行已经在受控gauge总线段读取0x0C，并经现有signed转换作为普通Full/再充输入。003供电在线有效样本中它产生真实负值。这比仅用相近TRM更强，支持本机这一个标准电流命令的复用；不证明断源边沿时每毫秒真实0x0C变化。

## 锁和传输审查

原bq i2c read28–62行把寄存器选择和数据读取放在同一个 `i2c_transfer` 的两个消息中，成功后返回LE16原word；不是新的MAC/NVM事务。新路径应复用这一总线方法，不通过charger遥测缓存取值。必须先把负transport errno与非负原word分开，再做 `(s16)word * 1000`；合法0xFFFF为−1mA，不能把转换后的负净流误当读取失败。

`bq27xxx_battery_update()`1951–1956持di->lock调用update_unlocked；get_property2128–2132只在可能刷新cache时持锁，**2137/2146的直接STATUS/CURRENT_NOW寄存器读取在解锁之后**。不能把“现所有电流读已由di->lock串行”写成事实。设计中的共用状态helper不应自行无条件锁di->lock，否则cache update调用会自锁；若加强直接STATUS读取串行，只在解锁后的STATUS case外围取di->lock，共用helper明确caller-held。CURRENT_NOW原分支可保持原锁政策，不能顺手重构全部gauge。

R8通知实际有charger.lock→gauge property/cache lock的调用边。新状态helper只读0x0C和已有flags/cache，不查询source、charger、ONLINE、供电者或 `power_supply_is_supplied`，故不增加gauge→charger反边。已有power_supply_changed是标准异步通知，不用同步source回调来决定正负。I2C适配器锁仍是原传输边界；本叶没有把这个审查扩大成所有MAC owner并发证明。

## A：保留CURRENT_NOW平均的最小兼容设计

范围先明确限制为本机已经匹配的ti,bq28z610标准寄存器接口，并用**显式板级opt-in**启用，默认其它gauge完全不变。现代码没有现成“STATUS只用瞬时电流”的标准开关；opt-in的DT binding/内部选项名需在真正候选时确定，不在本叶伪造一个已支持的属性。不能只靠chip名字或读到2719就全局改所有bq族。

可编程增量只有这些：

1. 增加受限状态helper：读0x0C signed净流和原flags，或接收update_unlocked已取得的有效flags。保留现FC优先；FC未置时按净流正/负/0产生Charging/Discharging/Not charging。读错返回明确errno，不用旧值或0冒充新鲜读数，不增加死区/阈值猜测。
2. 仅opt-in的 `POWER_SUPPLY_PROP_STATUS` 和 `battery_update_unlocked` 中last_status比较切到此helper，保持两处一致。其它属性、健康/Full、平均CURRENT_NOW、原工作间隔不变。
3. 继续原supplier关系和external_power_changed的0.5秒调度。**不按在线/离线直接定状态**，也不更改R8充电控制、预算或Full状态机。

这是最小兼容方向，但有两个限制：瞬时signed值在零附近可比平均值更易反复变号，不能未采样就加入人为deadband；约4秒包含至少采样/通知/用户态调度的可能贡献，源码只能证明平均值是候选环节。

更关键的是缓存UPower supply-battery523–527：非Full时，只要读取的**CURRENT_NOW仍为负**，就会把自身state覆盖为Discharging。因此：

| 实际输入组合 | STATUS瞬时方案A | CURRENT_NOW仍平均 | UPower参考实现 |
| --- | --- | --- | --- |
| 拔线后瞬时负、平均仍正、FC=0 | Discharging | 正 | 保留Discharging，可能改善该方向 |
| 插回后瞬时正、平均仍负、FC=0 | Charging | 负 | 被覆盖Discharging，仍等平均反号 |
| FC=1 | Full | 正或负 | 保留Full；不绕过原FC |

所以A可以作为有明确范围的底层优化候选，不能作为“双向图标都及时”的完整解决方案，也不能独立解决SDP100负净流。该表是已有实际函数源码的组合推导，未新跑测试，非003瞬时原件。

## B：使用已有标准CURRENT_NOW/CURRENT_AVG属性分工

原内核ABI文档 `Documentation/ABI/testing/sysfs-class-power` 41–63行已有current_avg=平均IBAT；79–96行规定current_now为未平均/未平滑的瞬时IBAT。这提供更一致的长期接口：在同一受限板级profile中CURRENT_NOW读0x0C，新增CURRENT_AVG读原0x14，STATUS用同一瞬时源且保留FC优先。平均数据仍有标准出口，不需要伪造状态。

这比A多改变一个已有属性的读值/增加一个属性；UPower参考实现直接读current_now、不读current_avg，因此可消除上述A在插回方向的自相抵消，却也会影响其功率率估计和依赖旧CURRENT_NOW平均语义的采集者。它需要显式版本、调用者核对和边沿验证，不能当成“CURRENT_NOW保持不变”的小修。此方向也没有授权本轮实现。

直接改用BatteryStatus的DSG等mode位不是已证明更小的替代：模式可有阈值/迟滞，0x2719的全部精确状态语义没有因此恢复。调低bq轮询或重复发送通知也不能让旧平均值反号，增加总线唤醒成本；原外部供电0.5秒工作已存在，当前不建议盲改它。

## 目前缺证与集成边界

003断源后R8采样安全逻辑会使gauge电流遥测无效/归零；**该0不是0x0C的离线实物原字**。因此还缺同一拔插边沿、带有效性和时间的0x0C原word与0x14/FC对照，不能拿离线清零列计算“瞬时提前了多少”。当前平均反号和State2约4.11秒也不足以分摊整个延迟。自然零附近的稳定性、FC保持、读取失败和通知age同样需未来候选范围验证，不能预承诺0秒或1秒。

因为原Image内嵌配置为built-in，A/B任一真实代码改变都需要**一致的新Image**，以及实际gauge core/I2C/header/板级开关的一致构建；不能卸载当前built-in或加重复power_supply覆盖它。若内部struct有变化，更不能仅替换gauge对象。即使其它摄像头接口未改，也须核对新产物的CONFIG/导出符号/模块接口并保留相机434等实际依赖依据，不能用原Image SHA充当新产物。

本叶建议先把A作为“单向兼容优化的设计备选”、B作为“标准属性语义的后续选择”，交根会话决定范围。当前EUD boot-only实验应继续保持Image363不变；这两个候选没有构建、安装或实体窗口，也不提高USB预算。
