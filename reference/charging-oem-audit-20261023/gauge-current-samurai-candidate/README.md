# 本机 gauge 瞬时 CURRENT_NOW / STATUS 默认关闭候选 B

本候选只改变显式启用的本机 gauge 电流属性：`CURRENT_NOW` 与 `STATUS` 都读取已经在本机 R8 使用的 signed 0x0c；标准 `CURRENT_AVG` 提供原 signed 0x14。默认不开启，未安装，未构建 Image；不是本轮保留 Image363 的 EUD boot 变量，也不声称已改善实体图标延迟或解决 SDP100 负净流。

## 精确范围与来源

完整候选 `bq27xxx_battery.c` 与 `samurai-current.patch` 只涉及一个原有 C 文件，无 header、DT、配置或 R8 文件变化。基线为 Image363 关联 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8` 的 bq core SHA `b2cd415a995cb196559c0e4981988f737c17c98486449659d168314926aec69e`，与固定 source354 原件相同。来源/寄存器证据详见相邻 `gauge-instant-status-feasibility` 的冻结收据及行号切片。

原 native DTB 的机器 compatible 为 `realme,samurai`，gauge 节点为 `ti,bq28z610`；原 Image 内嵌配置的 core/I2C 均 built-in。R8 精确 charger 源 SHA `ed2e1d4d96ea4f2d55b514288b0e8da1d731864d385944d02a105d41b03a144c` 已直接读取本机 0x0c。原厂同机 bq 驱动及 TI SLUUA65E 对这个只读 signed mA 命令提供相符依据。扩展身份 0x2719 不是精确 2610 型号证明，本候选不据此扩展 flags/MAC/NVM 语义。

## 启用门与属性行为

必须同时满足：只读参数 `samurai_instant_current=true`、原 `di->chip==BQ28Z610`、实际 native machine compatible `realme,samurai`、实际 gauge OF node compatible `ti,bq28z610`。参数只表示 opt-in，不自报型号。现 built-in profile 的未来参数形式为 `bq27xxx_battery.samurai_instant_current=1`；本叶没有修改或应用任何 bootargs。

- 默认参数 false，原 AI 读取、原属性数组与数目保持，CURRENT_AVG 不对外广告；直接请求未支持 AVG 仍返回 `-EINVAL`。短路门不会新增 OF 查询。
- 满足全部门时才选择独立的本机属性数组：原数组为逐项不变的前缀，只追加 CURRENT_AVG。不修改共享原数组。
- 原 current/status 共用函数 1920 行仅替换初次读取来源，后续原逻辑保留：先区分负 transport errno，再将合法 word 转为 `(s16)*1000`；FC 优先，非 FC 时正/负/零分别为 Charging/Discharging/Not charging。合法 0xffff 仍是 -1mA。
- cache update 1999 行仍调用同一个真实函数，所以 last_status 比较和 power_supply_changed 通知一起采用新来源；不是只替换直接 STATUS getter。
- 新 AVG helper 1891 行读取原 AI 0x14，signed 转换和 errno 保留。没有按外接在线强写状态，没有平均/瞬时相互回退、阈值、死区或新轮询周期。

## 锁、调用者与用户态影响

共用 helper 不加锁。原 update 在 `di->lock` 下调用；原 get_property 2195 行只为 cache refresh 临时持锁，2205/2214 行的直接 STATUS/NOW 读取在原解锁后。I2C 仍使用原 bus.read 两消息传输。没有查询 source/charger/ONLINE 或 `power_supply_is_supplied`，因此没有新增 gauge→charger 反向锁边。没有把本测试称为全部总线并发证明。

`caller-audit.json` 核对三个 core 调用点、精确 R8 入口/服务及框架；`supplement-callers.json` 补全固定 source354 全树所有 71 个包含 CURRENT_NOW enum 的 C 文件。两处直接 literal get_property 调用均在 charger-manager.c 751/1570 行，分别代理属性、检查可用性。动态属性转发、该驱动是否实际绑定以及任意外部用户程序不能由静态枚举认证；sysfs/hwmon 仍是通用用户入口，hwmon 已区分 current_input/NOW 和 current_average/AVG。

精确 R8 普通 Full/再充/保护策略自己读取 0x0c，不消费 bq CURRENT_NOW；其持 charger.lock 的通知路径读取 Battery STATUS，本改动不增加反向查询。R8 自己的 CURRENT_NOW case 属于 mp2650-input ADC。R8 control-trial.py 121 行只记录 bq current_now，不据其作控制；其 81 行旧注释“mainline current_now 为 0x14”对默认路径仍成立，未来启用后需按新 profile 解释，冻结 R8 源未修改。图标捕获 worker 也只记录此属性，历史抓取不能重新标为瞬时值。

缓存官方 UPower v1.91.0 supply-battery.c 492/503 行把 current_now 用于功率率，523–527 行在非 Full 且 current_now<0 时判 Discharging，未读取 current_avg。因此 B 保持它读取的 NOW 和 STATUS 同源，避免仅 STATUS 瞬时而 NOW 仍平均的相抵消；但功率率及由此推导的估计时间可能更易波动。Phosh 参考实现只消费 DisplayDevice state/percentage。当前设备的精确用户态版本与真实影响仍需后续取证，不能把缓存实现当当前二进制鉴定。

## 已完成验证与边界

`test-result.json`：6 组、9 个从完整候选抽取的实际函数；硬件/OF/调度边界 fake，ASan/UBSan/Werror 通过。默认路径与原未改函数作 36 个实际差分：signed 边界、I/O 错误、FC、布局与相同寄存器读取；另测全部 gate、属性可见性、瞬时/平均异号、零/FC、flags/cache 错误及实际 update 通知不递归加锁。未重跑原充电/保护大套。

`build-result.json`：私有 source-view/O，仅 W=1 编译 `drivers/power/supply/bq27xxx_battery.o`，无诊断；原共享 C/header/i2c/Makefile/config/Module.symvers 核对未变，启用 CONFIG 赋值相同。没有链接 Image 或 ko，没有设备、SSH、USB、SDK 或 Git 动作。

原 Image 是 built-in，实现若未来采用需要一致的新 Image，并核实际模块 ABI/相机依赖，不能热卸或加重复 power_supply。现阶段只交独立离线候选。003 的约 4.11s 包含采样、缓存、通知和用户态环节的可能贡献，断源后 R8 无效/归零 telemetry 不是瞬时 0x0c 原 word；尚缺同边沿有效原 word/0x14/FC 对照、自然零附近稳定性和实体收益。此候选不承诺固定延迟，不提高 USB 预算，SDP100 下实际净放电仍应显示 Discharging。

`result.json` 和 `delivery.json` 绑定最终源、patch、调用者审查、实际函数测试及对象构建收据；冻结后不再修改本叶字节。
