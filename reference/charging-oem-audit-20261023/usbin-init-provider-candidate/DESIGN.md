# R7 provider 上的最小 USBIN 初始化：冻结窄设计

目标是未来在现有 provider 中完成一次普通配置初始化，摆脱临时手动 helper；“持久”指驱动生命周期内保留状态、下一 boot 重新只读判断，并非 NVM/OTP。当前只是独立离线候选，**默认关闭 opt-in，禁止安装；生产自动采用仍须临时 helper 的实体结果**。

基线为 R7 FLOAT USB ko `7d4e0f94…c4f70`：C `b712764f…b7098`、decoder `a17caa2c…d548fd`，in-tree Y、k363、depends 空。R8 更新后 USB 未换，已有 R8 handoff 的实际 USB note `f0edb792…804b0` 保留。准确来源/完整 SHA 见 baseline.json。实际现 provider poll 是 **1000ms**，本候选保持它，不以别的版本或新 cadence 冒充当前实现。

只复制冻结 `usbin-init-core.h`（`80aa4274…f11dd9`），不修改 helper 目录；只接受 CLEAR 操作。唯一写是 `regmap_update_bits(map,0x1358,0x80,0)`。没有 CMD_APSD、PD、DWC/PHY/EUD、预算升级、charger/I2C访问、restore控制、额外 owner、timer daemon 或自动重试。

| 状态 | 行为 |
| --- | --- |
| disabled（默认 `usbin_init=0`） | 完全不读取0x1358、不排初始化步骤，原 source/budget 行为保留 |
| probe_already_zero | opt-in 时 probe 两次配置字节一致且bit7已0，仅记录零写终态，不假称本模块清过位 |
| wait_first_off | probe bit7为1；只在既有worker每1000ms新采样，不消耗60s期限。普通 suspend 只暂停；resume后用新样本继续等待，无旧off锚 |
| transaction | 首次完整新鲜七字段物理off后，`ui_start(CLEAR)`仅一次，绝对BOOTTIME期限60s；立即由冻结core重读并建立首off锚。随后沿用1000ms worker，至少两相同off样本跨度≥500ms。prewrite新读到写门≤250ms，与poll间隔不同 |
| initialized | core明确clear_verified后自动调用其零IO `ui_commit`记录采用；保存实际oldbit、pre/post、write_return等历史。没有自动恢复旧bit或下次重写 |
| timeout/error/cancelled | 保留绝对期限和历史，不rearm、不retry。真正写后unknown保留原值/错误，不能以新鲜source或resume冒认初始化成功 |

probe读取错误/两次配置不一致是初始化前终态，不阻止原provider注册。等待首次off时读错终止此功能，不拿旧数据推进。事务期间 suspend 在原lock下取消为终态，保留原deadline/error；resume不延展和重启。若事务已经成功/失败，PM不覆盖其历史。devres stop仍在释放supply前join原worker，且不持worker mutex等待。

物理off只复用冻结core的 plugin/VBUS/CCattached/stateattached 掩码；所有七字段和配置一致性、first-off锚、写前实际BOOTTIME复核、读回其它bit保持、post再附着/原始字段变化拒绝均保持。顺序读取不是电气原子快照，单次regmap操作也不能硬中断在60s内完成，这些限制不因集成消失。

新IO只在probe及原worker中，均由原mutex串行；所有power-supply getters保持零写，原 `samurai_usb_read_status/get_budget/type/get_property/set_property` 和 FLOAT decoder逐字保留。初始化错误在独立只读平台属性 `usbin_init_state` 报告，不伪造online、native额度、类型或UPower，不借此改既有 `udc_valid` 暂态规则；既有source fresh/guard/保护仍独立决定普通充电。该隔离明确表示：**source正常不等同初始化成功，初始化失败也不能被source恢复擦掉**。

复用现provider自持/native生命周期；不为新步骤增加可热卸/重复provider/try-get事务。新增内部 `native_ref_held` 只能在原生DT接线检查通过、实际 `__module_get` 后置位；新prepare在取得此证据后、首次排worker之前，持原mutex运行。无native接线或用户预设 `native_retained=true` 导致原retain跳过时，opt-in初始化零配置IO、以ENODEV终止。这个新内部证据不接收模块参数。原retain函数只增加该置位，不另拿引用。

`usbin_init` 是只读加载参数、默认false；sysfs只有状态没有arm/commit/restore写入口。当前helper未实测，所以无默认自动开启、部署或物理通过声明。根已批准窄实现，已完成新增10组/17个实际函数集成测试和私有USB ko W=1构建，结果见README；不构建Image、调用SDK或改共享树。首次构建后仅为probe双读加原mutex包围做过一次必要增量重编，最终交付只认result绑定的字节。
