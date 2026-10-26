# USBIN003之后：净放电语义与SDP100预算

**当前没有依据把“无charging图标”修成强制Charging，也没有依据把SDP100改写为500。** 003已证明在这次同口断接中1358bit7成功c0→40，但它单独不足以让该电脑路径获得CDP或native500。下一步应收敛USB数据路径/合法配置权限，继续调电池图标或反复清该位不能补足该权限。

本叶仅分析冻结抓取 `usbin-init-r8-003/fetch-1792764030744355505` 的状态语义和旧预算证据，不重算事件时序；时序由UI代理独审。`audit.py/result.json` 绑定实际原件SHA，不访问设备/SSH/USB/SDK/Git，也不改当前文件或已冻候选。没有重跑旧语义矩阵或500试验。

## 精确R8来源与本次状态

本次引用R8私有实际编译输入：`/home/cy122/charging-management-20261023/thermal-bands-candidate/source-view/drivers/power/supply/samurai-mp2650.c`，SHA `ed2e1d4d96ea4f2d55b514288b0e8da1d731864d385944d02a105d41b03a144c`，匹配原build receipt，ko SHA `10ec06fb…fa6297f`。当前public main/kernel-v2文件已经是不同字节，不能冒认它们就是实装R8；本目录 `r8-status-excerpts.txt` 从该精确编译输入摘录并保留原行号。

**正式公开入口没有映射错误**：[R8 source integration](../../charging-session-20261023/r8-source-integration/README.md) 的 `source-manifest.json` 指定charger origin为 `thermal-bands-candidate/samurai-mp2650.c`；origin、整合包 `kernel-sources/drivers/power/supply/samurai-mp2650.c` 与上述私有实际编译源三者逐字相同，均27477字节/ed2e…a144c。入口manifest SHA `66f794d7…1def87`、delivery `9e08f86e…04878a` 已绑定到本叶结果。旧kernel-v2只作未变依赖/历史，入口README原已写明该边界；前述“不能替代”不表示正式R8入口缺失或错误。

在helper明确clear_verified、raw1358=40、source/ACOK均online且遥测valid/age≤2500ms的**50条**原样本（0-based312–361）中：

| 字段 | 原件值 |
| --- | --- |
| PMIC七字段 | 01/01/10/08/23/29/06，APSD完成、SDP result1 |
| native / source有效预算 / MP2650实际IIN设置 | 全为100000µA |
| MP2650 CC / CV设置 | 250000µA / 8725000µV |
| MP2650状态 / Battery状态 | Charging / Discharging |
| Battery current_now（主线AI路径） | −45000至−20000µA，全负 |
| 独立gauge瞬时电流遥测 | −133000至−7000µA，全负 |
| desired_enable / protection_ok | 1 / 1 |
| fault / latched / thermal_inhibit / logical_full | 全0 |

这些是状态分布，未另算source→DBus或屏幕延迟。capture最后仍是clear_verified的历史状态；后续commit/终态由根另外管理，不从本抓取补造。用户电脑外部直连、无外置hub的说明，也不否定此前主机已读到手机内部EUD hub。

## 为什么两个Charging/Discharging可以同时成立

精确R8 424–438行的 `mp2650-input` STATUS读取REG13的ONLINE/CHG_STAT：它表示转换器状态；510–517行将此supply注册为USB，非Battery。286–288行注释也明确不能从CHG_EN/开关状态推断净电池充电。683–704行只把外部供电通知送给真实gauge的标准回调，没有覆盖其STATUS。

主线bq缓存 `bq27xxx_battery_current_and_status` 1860–1913行用自身FC和signed 0x14 AverageCurrent决定Battery STATUS；本机选定FC布局和0x14路径已有 [离线语义实际函数审计](../icon-semantics/README.md)。原厂名字为get_average_current的legacy实现实际选0x0C，R8遥测也有独立0x0C瞬时净电流，二者不能混当相同滤波值。本次两种净电流都负，更不能归结为“只剩平均值滞后”。这不说明具体滤波时长，已有TI缓存没有给出该时间窗。

缓存UPower v1.91.0 battery523–527行在非Full且current_now<0时保留/改为Discharging。daemon292–308行仅在Battery composite状态UNKNOWN时才借AC在线推断Charging，不覆盖已知Discharging；828–829行的root OnBattery则另结合AC在线。这允许“外接电源在线、OnBattery为false、Battery/Display净放电”同时成立。

缓存Phosh分支60–73行只以DisplayDevice state/percentage选择charging/charged或普通电量图标，没有按line Online强制charging。故负净电流的普通电量图标符合这套源码语义；这是说明允许行为，不是当前Phosh二进制逐字匹配/屏幕渲染的独立证明。UI代理负责本次真实DBus与屏幕方向结论。本次没有找出该分支需要底层状态造假的bug。若产品以后要另外显示“已插电但净放电”，那是独立外部供电提示，不应改Battery为Charging。

UI代理的独立003审查另记录：重接后line Online=true、root OnBattery=false，但Battery/Display没有State1，净Battery仍Discharging；这与上述“供电在线与净电流状态不同”一致。其原件/时序结果在 `charging-ui-audit-20261023/usbin-init-r8-003-review/`，本叶不重算或代签那些延迟。UI的重接后51条含过渡样本，本叶50条是额外限定bit已清且source/ACOK/遥测新鲜有效的子集，两者不是相互冲突的样本数。

## 为什么清位不会自动把100变500

1358bit7是原厂普通检测初始化项，不是USB配置或电流授权寄存器；本次helper没有预算写。R7 FLOAT provider只在真实SDP/FLOAT且online时使用native DWC额度，完成的SDP分类本身没有“自动500”许可。有效CDP则走独立1500分支，不被native100取min；这不是当前SDP100案例。

实际Image363 composite.c1037–1059在SET_CONFIGURATION后把配置MaxPower传给vbus_draw，2632–2649恢复时使用已配置功耗或未配置默认≤100。gadget3156–3178只记录该软件额度并排work，core2177–2188把mA×1000传给provider。它们不是ADC测量，也不因PMIC检测SDP就把配置请求改成500。已知配置被恢复为100的基线下，正常配置回调仍100是预期行为。

**003本抓取没有读当前configfs MaxPower、UDC状态或主机完整ConfigurationDescriptor。** 因此只能直接证明实际native与有效预算均100，不能从这批数据断言当前bMaxPower是哪个字节、host曾读过500描述符或拒绝500。CC设置250mA是充电电流上限，不能绕过输入100mA令电池实际吸入250mA；系统负载与转换损耗可使净电池电流为负，本批净放电已直接测到。

## 已否证与仍缺证

已否证的是“只清bit7并同口普通重接就足以变CDP/500”，以及把这段持续净放电简单当成“gauge未通知/UPower必然卡旧Charging”。本次source/ACOK恢复、bit清除成功和保护无锁存已有实物证据，不能再把“helper没写到/窗口太短”当003失败原因。此范围没有重新否定其余原厂初始化或不同源模式。

原单次500试验 [冻结审计](../usb500-r7-trial-audit/README.md) 已有55个device样本持续addressed/native100、完整host683轮4781GET无查询错误，500阶段在已校准时钟范围内只见port7 absent/reset，未见Status5。它证明没有取得native500，**不证明功率拒绝**。主机collector当时没读完整标准ConfigurationDescriptor，Windows历史也无同时失败事件。不能以absence代替“EUD功率拒绝已证”。

此前实际EUD Node原件说明bus-powered、port7向主机声明removable，且100配置NCM在内部port7。这使USB2每口1 unit load的限制成为有依据的待检因素；没有父hub描述符硬件来源、完整配置功耗/实际device status证据，不能擅改self-powered或猜strap。墙充有图标是用户实际观察，不能从该观察推算这次电脑口也应有CDP许可。

## 下一最小底层方案

当前没有证据充分、可立即实装的“预算计算bug修复”。最小下一变量是已有 [boot-only EUD-off R2](../eud-boot-policy-r2/README.md)：检验首次gadget启动前关闭EUD、消除COM producer后是否改变内部hub数据路径，而非再叠加runtime APSD owner或重做同一500请求。R2已按真实完整CSR字限定允许集合；它仍未部署，CSR0/无producer/数据旁路/host接受均未实证。

可离线先完成的具体包是：把冻结R2 PlatformBm补丁、COM disabled及去eud console/earlycon的原native DTB，与将要生成的实际firmware全输入/链接收据逐项绑定；保持原Image363字节、panel handoff及相机ABI；独审arm/BeforeEBS/readback失败收据和fastboot回退来源。现候选完整carrier源链/产物绑定不能被“callback静态测过”代替。本叶只给该收敛方案，未构建firmware、Image或部署包。

若后续另行批准实体窗口，第一步仍用现合法100配置，只确认真实boot回调CSR0、Linux无COM/earlycon再启生产者、主机实际父端口/数据拓扑改变并能稳定配置。**这一步本身仍不应期待native自动500**；无EUD也不改变仍为100的gadget配置请求。本轮不安排500复测。只有将来基于不同且已确认的拓扑、完整实际描述符与合法SET_CONFIGURATION证据，才能单独决定后续授权验证；失败应保留100与真实净电池状态。

并行可离线准备一个纯标准ConfigurationDescriptor解析/只读GET收据规范，用于将来分别读取父EUD hub与NCM child的bmAttributes/bMaxPower/实际GetStatus，严格区分已读原字节与本地MaxPower。它补的是上次未读字段，不能自己产生500许可；本叶未添加或运行USB IOCTL。已冻DEVICE同步恢复候选只针对本地PM恢复错误，同样不解决USB功率授权，不应混成这个预算修复。
