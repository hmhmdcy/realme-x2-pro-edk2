# MP2650 冷启动 probe 依赖与软降级审阅（R16）

日期：2026-10-28  
范围：只读审阅 `reference/charging-management-20261023/samurai-mp2650.c`
（SHA-256 `986e16af8289deedcbf2885211c5cd407ca2c0aff2692ca4bc7fdbfa3a6a458e`）、
R9/R15 快照、`samurai-usb-input.c`、`samurai-gauge-protection.c`、
`MP2650-BIND-RCA-R15.md` 和已有上游/绑定资料。未改设备、源码或构建。

## 结论

**可以先用一个很小的“软依赖”改动让 `mps,mp2650` 节点在冷启动时稳定绑定，
但只建议先绑定为 shadow。** 不应把缺失 input/protection/Type-C/battery PSY
直接解释成“可以已绑定后安全控制”。当前 `samurai-mp2650.c` 是 10-23 的旧
shadow 版本；它没有 `typec` 字段，也没有 `sm_typec_supply()`。用户提到的
“Type-C supply 硬 defer”来自后续 R9/R15 快照（`trial-517-r9-status-precharge`
第 724、860-865 行），不是这个文件本身。

推荐最小策略：

1. 保留 MP2650 I2C 探测和“继承配置只读验收”为不可降级的硬前提。
2. 第一阶段只把 `samurai-usb-input`、`samurai-gauge-protection` 和
   Type-C TCPM PSY 当作“shadow 可选”；probe 记录 `missing` 并保持
   `control=0`。gauge 和 battery PSY 暂保留硬依赖。
3. battery PSY 不是普通可选 supplier：`config.supplied_to` 在 PSY 注册时
   固化，事后无法优雅补上。若确实要软绑定，只能接受暂时失去通知桥，
   或在 battery 出现后显式 unregister/re-register `mp2650-input`；两种
   方案都不如保留 battery 硬依赖简单。
4. 竞争问题不要靠“先加载 managed 就会赢”：`mps,mp2650` 同时被
   generic `mp2650` 和本驱动匹配，必须用 `driver_override`（首选），
   或在启动脚本中先移除 generic、再加载 managed。仅增加 OF compatible
   不能解决竞争。

另有一个与本文件相关的阻塞前提：`samurai-mp2650.c:108-112`、`139-145`
和 `ONLINE` getter 把 REG13 bit1 当成 online。按 MPS 定义，bit1=1 表示
**power not good**。即使 probe 改为 shadow 成功，power good 时也会得到
`source_inhibit` 或 `online=0`。因此软依赖补丁必须和 REG13 极性修正同批
完成，否则“绑定成功”不会产生稳定采样。

## 1. 当前实际 probe 依赖

### 1.1 本文件（shadow 版）

`samurai-mp2650.c:544-641`：

| 位置 | 依赖 | 当前失败行为 | 是否应硬 defer |
|---|---|---|---|
| `552-560` | machine compatible、I2C、OEM MAC opt-in | 非 defer | 是，板型/协议错了必须拒绝 |
| `569-571` | `samurai-usb-input` 或 DT `input-supply` | `sm_named_supply()` 返回 `-EPROBE_DEFER` | 建议：**否**，shadow 可先无 input 绑定 |
| `572-577` | `samurai-gauge-protection` 或 DT `protection-supply` | 同上 | 建议：**否**；但 `control=1` 时仍必须为真 |
| `580-586` | `battery-gauge` 节点 -> gauge I2C client | 无节点 `-EINVAL`；无 client `-EPROBE_DEFER` | 建议：**保留硬依赖**（没有 gauge 就没有安全采样；节点缺失是 DT bug，不该静默） |
| `589-595` | gauge 地址/功能/非 NVM 更新、device link | `-EOPNOTSUPP`/`-ENOMEM` | 保留硬失败 |
| `596-603` | `sm_preconditions()`、REG04 读取 | 失败直接拒绝 | 保留硬失败 |
| `611-618` | 按 gauge parent 找 battery PSY | 找不到 `-EPROBE_DEFER` | 建议：**第一阶段保留硬依赖**；battery 是 `supplied_to` 通知桥的必要 consumer，错过注册无法优雅补接 |
| `622-627` | battery 类型/parent 校验、supplied_to | 不匹配 `-ENODEV` | 建议保留硬失败；若必须软降级，只能接受无通知桥，或两阶段重注册 |

`sm_named_supply()` 本身（`455-480`）还会：

- `power_supply_get_by_name()` 找不到就立即 `-EPROBE_DEFER`；
- 取 provider 模块引用；
- 添加 `DL_FLAG_AUTOREMOVE_CONSUMER` device link。

这适合真正必需的 supplier；对可选观察者则会把一次加载顺序变成整个
charger probe 的失败。

### 1.2 R9/R15 快照新增的 Type-C 硬依赖

`integration-20261026/trial-517-r9-status-precharge/source-snapshot/.../samurai-mp2650.c`：

- `724-748`：`sm_typec_supply()`；如果 DT 声明了 `typec-supply` 但
  reference 暂时找不到，返回 `-EPROBE_DEFER`。
- `860-865`：`c->typec = sm_typec_supply(...)`；`control=1` 且无 Type-C
  supply 时返回 `-EINVAL`。

这意味着冷启动顺序必须是：

`gauge -> bq27xxx battery -> samurai-usb-input -> TCPM source PSY -> protection -> managed probe`

而 `samurai-usb-input` 自己又依赖 PM8150B regmap 和（可选的）DWC3 UDC
预算；任何一环晚到都会让 managed probe defer。

## 2. 最小安全改动设计

### 2.1 把 probe 拆成“核心硬依赖”和“运行期可选项”

建议新增一个明确的 probe 阶段状态，不要用 `NULL` 隐式表示“没准备好”：

```c
struct sm_charger {
    ...
    bool input_ready;
    bool protection_ready;
    bool typec_ready;
    bool battery_ready;
    bool core_bound;
};
```

核心 probe 只做：

1. 板型、I2C、gauge 节点/地址/功能检查；
2. `sm_preconditions()` 和 REG04 读取；
3. 注册 `mp2650-input` power_supply；
4. 启动周期采样。

可选依赖在 `sm_try_bind_optional()` 中按顺序尝试：

```c
static int sm_try_optional_supply(struct device *dev, const char *name,
                                  struct power_supply **out)
{
    struct power_supply *psy;
    int ret;

    psy = power_supply_get_by_name(name);
    if (!psy)
        return -ENODEV;           /* 不是 -EPROBE_DEFER */
    ret = devm_add_action_or_reset(dev, sm_put_supply, psy);
    if (ret)
        return ret;
    *out = psy;
    return 0;
}
```

注意：这段示意只适用于**已经确定可降级**的 provider。不要直接把
`sm_named_supply()` 的语义全局改掉，因为 DT 里显式引用的 supplier
应该继续遵循 `devm_power_supply_get_by_reference()` 的 defer 语义。

### 2.2 `runtime_board=1` 下的两种模式

建议把模块参数从单一 `control` 扩展为“请求模式 + 实际模式”：

```c
enum sm_mode {
    SM_MODE_SHADOW,
    SM_MODE_CONTROL,
};

static enum sm_mode requested_mode = SM_MODE_SHADOW;
static enum sm_mode active_mode = SM_MODE_SHADOW;
```

但当前文件用 bool `control`，最小补丁可以保留它，只增加：

```c
static bool control_degraded;
```

规则：

- probe 开始时 `active_mode = control ? CONTROL : SHADOW`；
- 若 `control=1` 但缺 protection、input、Type-C 或 battery 通知桥：
  - **不建议自动降级为 control**；
  - 应把 `active_mode` 降为 SHADOW，设置 `control_degraded=true`，
    并在 telemetry/sysfs 中显示 `requested=control actual=shadow`；
  - 或者更严格：`control=1` 缺 protection 时返回 `-EINVAL`，
    只有 `control=0` 才允许先绑定再等可选 provider。

推荐更保守的版本：

```c
bool degraded = false;

if (control && (!c->input || !c->protection || !c->typec))
    degraded = true;

if (degraded)
    dev_warn(dev, "optional suppliers missing; binding shadow only\n");
```

之后所有 `if (control)` 写路径都改为：

```c
if (sm_can_control(c))
    sm_apply(...);
```

其中：

```c
static inline bool sm_can_control(const struct sm_charger *c)
{
    return control && !c->control_degraded &&
           c->input && c->protection && c->typec && c->battery;
}
```

这样即使 probe 完成，缺失 provider 时也不会误写充电寄存器。

### 2.3 可选 provider 的补绑定

不要用 probe 的 `-EPROBE_DEFER` 来轮询可选 provider。建议：

1. 保留现有 `power_supply_reg_notifier()`；
2. 在 notifier 里同时匹配 input/protection/battery/typec 的 `PSY_EVENT_PROP_CHANGED`；
3. 每次事件只调用 `sm_try_bind_optional()`，成功后 `mod_delayed_work(..., 0)`；
4. 如果 notifier 注册失败，probe 可以成功，但 telemetry 标记
   `optional_watch=0`，不要因此让整个 charger 消失。

伪代码：

```c
static int sm_try_bind_optional(struct sm_charger *c)
{
    if (!c->input)
        c->input = sm_get_optional_supply(c->dev, "samurai-usb-input");
    if (!c->protection)
        c->protection = sm_get_optional_supply(c->dev, "samurai-gauge-protection");
    if (!c->battery)
        sm_find_battery_psy(c);
    if (!c->typec)
        c->typec = sm_get_optional_reference(c->dev, "typec-supply");

    c->control_degraded = control &&
        (!c->input || !c->protection || !c->typec || !c->battery);
    return sm_can_collect(c) ? 0 : -EAGAIN;
}
```

`sm_can_collect()` 至少要求：

- `c->input` 非空且 `ONLINE` 可读；
- `c->input` 的 `CURRENT_MAX` 可读且为正；
- gauge 采样成功；
- REG14 故障读取成功；
- protection 缺失时：`protection_ok=false`，不得当作 Good。

### 2.4 `samurai-gauge-protection` 也可软降级

`samurai-gauge-protection.c:110-157` 当前在 probe 中：

- gauge 节点/client 缺失：`-EPROBE_DEFER`；
- 首次保护 MAC 读取失败：`dev_err_probe()` 直接失败；
- 成功后注册 `samurai-gauge-protection` PSY。

它是**观察者**，但当前 managed charger 的 `control=1` 把它当硬依赖。
建议：

- protection 模块自己的 probe 保持“gauge 已存在才注册”；
- 不要把 protection 模块的 defer 传染给 managed；
- managed 的 `protection_ok` 只能是三态：`ready+Good`、`ready+not Good`、
  `unavailable`；`unavailable` 绝不能显示 Good；
- `control=1` 时仍建议要求 protection ready，否则只允许 shadow。

## 3. 与 generic `mp2650` 的竞争

### 3.1 竞争根因

`MP2650-BIND-RCA-R15.md` 已证实：

- 真机节点 compatible 是 `mps,mp2650`；
- I2C `of_alias_from_compatible()` 使 `client->name == "mp2650"`；
- generic `mp2650_charger.c` 同时匹配 OF `mps,mp2650` 和 I2C `mp2650`；
- managed 的 `sm_match` 当前只匹配 `realme,samurai-mp2650-managed`，
  `sm_ids` 才是 `"mp2650"`。

因此：

- 仅加载 managed，generic 仍可能先占住设备；
- 仅补 `mps,mp2650` 到 OF 表，两个驱动仍会竞争；
- 手动 `bind` 时若 probe defer，driver core 会显示 `-EAGAIN`，而设备
  不会绑定；
- `driver_override` 是最小且可验证的排他手段。

### 3.2 推荐竞争策略（从最小到长期）

**A. 服务/安装顺序（不改驱动，首选）**

在加载 managed 之前：

```text
printf '%s\n' 0-005c > /sys/bus/i2c/drivers/mp2650/unbind 2>/dev/null || true
printf '%s\n' samurai-mp2650 > /sys/bus/i2c/devices/0-005c/driver_override
insmod .../samurai-mp2650.ko runtime_board=1 control=1
printf '%s\n' 0-005c > /sys/bus/i2c/drivers/samurai-mp2650/bind
```

验证必须看链接，而不是只看 exit code：

```text
readlink -f /sys/bus/i2c/devices/0-005c/driver
test -L /sys/bus/i2c/drivers/samurai-mp2650/0-005c
```

`driver_override` 要在 unbind 之前写，避免 generic 在窗口内被 autoprobe
重新匹配。若内核没有暴露该文件，最小替代是 `rmmod mp2650`（前提：没有
其它 consumer）再加载 managed。

**B. 补 OF compatible（需重编，仍要 A 的排他）**

```c
static const struct of_device_id sm_match[] = {
    { .compatible = "realme,samurai-mp2650-managed" },
    { .compatible = "mps,mp2650" },
    { }
};
```

优点：冷启动时 OF match 直接命中，不依赖 legacy `i2c:mp2650` 别名。  
风险：generic 也匹配同一 compatible；如果两者都 built-in/已加载，
仍然是谁先 probe 谁赢。不能只做这一项。

**C. 从构建中移除 generic**

如果该板永远不应使用 generic `mp2650_charger`，最干净是：

- 不构建 `CONFIG_CHARGER_MP2650`，或
- 在板级 initramfs/模块黑名单中排除它。

但这会改变完整系统的模块集合，风险高于 `driver_override`；只应在确认
没有其它设备使用 generic 后采用。

## 4. 具体补丁思路

### P0：先修 probe 依赖，不碰策略

当前文件可直接按以下顺序改：

1. REG13：`ONLINE` 只取 input PSY；需要 power-good 时使用
   `!(reg13 & 0x02)`；`REG13` getter 不得用 bit1 反推 online。
2. `sm_named_supply()` 增加 `bool required` 参数：
   - `required=true`：保持现有 `-EPROBE_DEFER`、module ref、device link；
   - `required=false`：miss 返回 `NULL`，不创建 link。
3. `569-577`：
   - `runtime_board` 下先尝试 optional；
   - 若 `control && !protection`，不直接 `-EINVAL`，而是标记
     `control_degraded=true`，降为 shadow。
4. `611-618`、`622-627`：
   - 第一阶段保留 battery PSY 硬依赖，避免失去 bq27xxx 的即时状态通知；
   - 若必须软绑定，则先以 `config.supplied_to=NULL` 注册 shadow PSY，
     并在 battery 出现后 unregister/re-register；必须接受 UAPI 短暂消失，
     且 `active_control=1` 前必须重新建立 `supplied_to`。
5. `sm_notification_locked()`：
   - `c->battery` 为空时 `battery_error=-ENODATA`，
     `battery_status=UNKNOWN`，不能假装 Full/Charging。
6. `sm_supply_changed()`：
   - 加入 battery/typec 变化；
   - 对可选 provider 的首次出现调用补绑定函数。
7. `sm_collect()`：
   - 在任何 `power_supply_get_property(c->input, ...)` 前检查
     `c->input != NULL`；缺失时设置 `source_inhibit=true` 并返回
     `-ENODATA`。否则“input 可选”会直接变成空指针崩溃。

### P1：R9/R15 的 Type-C 路径

在 R9/R15 快照上：

1. `sm_typec_supply()` 的 `devm_power_supply_get_by_reference()` 失败：
   - DT **显式**声明了 `typec-supply`：保留 defer（说明硬件拓扑错误）；
   - `runtime_board` 下按名字/路径探测：miss 返回 `NULL`，标记
     `typec_ready=false`。
2. `control && !c->typec`：
   - 不建议 `-EINVAL` 阻塞 probe；
   - 降为 shadow，telemetry 明确 `typec=missing`。
3. `sm_input_budget()`：
   - 无 `c->typec` 时只使用 physical input 的 `CURRENT_MAX`，
     shadow 可继续采样；
   - control 必须要求 typec ready，否则 `sm_can_control()` 返回 false。

### P2：冷启动的“已绑定但未就绪”

建议 telemetry 增加：

```text
requested_control=%d active_control=%d degraded=%d
input=%d protection=%d typec=%d battery=%d
```

这样服务不会把“probe 成功”误判为“控制已可用”。

## 5. 风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| 把“绑定”误当“可控制” | 缺 protection/Type-C 时先绑定，若仍允许 `control=1`，可能在没有独立保护确认时写充电器 | 引入 `sm_can_control()`；缺任一安全 provider 强制 shadow |
| 可选 provider 晚到但永不重试 | 如果只在 probe 查一次，input/typec 后到时仍不可用 | notifier + 有限重探；不要用无限 probe defer 轮询 |
| battery 通知桥缺失 | `supplied_to` 不能事后添加；bq27xxx 可能等 360 s 周期，桌面显示旧状态 | 第一阶段保留 battery 硬依赖；软绑定必须两阶段重注册或明确接受降级 |
| input 可选但未加 NULL guard | `sm_collect()` 会解引用空 PSY | 在 `sm_collect()` 入口先把缺失 input 变成 `source_inhibit`，不进入 policy/control |
| generic 抢回设备 | unbind 后 autoprobe 可能立刻绑定 generic | 先写 `driver_override`，再 unbind；验证 driver 目录链接 |
| `driver_override` 不可用 | 内核未启用该属性 | 临时 `rmmod mp2650`；长期用构建排除 |
| 两个 driver 都匹配 `mps,mp2650` | 仅补 OF 表不会消除竞争 | 保留排他脚本；或从构建移除 generic |
| 可选 supplier 的 device link | 失败 probe 会删除 `AUTOREMOVE_CONSUMER` link；不要为可选 provider 建立强 link | 只在 provider 真正 ready 后建 link |
| probe 成功后缺 gauge | 没有 gauge 就无法安全判断温度/单体电压 | gauge 节点/client 保持硬依赖，不降级 |
| shadow 也读 MAC | `sm_gauge_sample()` 会发 0x0071；某些固件对 MAC 访问敏感 | 保留现有 opt-in/失败不写策略；不要把 MAC 失败当充电器故障以外的控制许可 |

## 6. 建议的最小落地顺序

1. **先做安装/绑定排他**：`driver_override` + unbind generic + bind managed。
   这一步不改代码，能先验证“冷启动是否能稳定绑定”。
2. **再做 shadow 软依赖**：input/protection/battery/typec 缺失不阻塞
   `mp2650-input` 注册；只允许 `control=0`。
3. **最后放开 control**：只有所有安全 provider 都在线且 telemetry
   显示 `active_control=1` 时，才允许写充电寄存器。

不要先做“自动降级后仍 control”：这会绕过保护链，且比 probe defer
更难从现场状态判断是否真的安全。

## 7. 验收要点

冷启动后至少检查：

```text
readlink -f /sys/bus/i2c/devices/0-005c/driver
cat /sys/bus/i2c/devices/0-005c/driver_override
ls -l /sys/bus/i2c/drivers/samurai-mp2650/0-005c
cat /sys/class/power_supply/mp2650-input/telemetry
dmesg | grep -E 'samurai-mp2650|mp2650|defer|probe'
```

预期：

- `0-005c/driver` 指向 `samurai-mp2650`；
- generic `mp2650` 不再是当前 driver；
- telemetry 显示 `valid=0` 或 `source_inhibit=1` 时，`desired_enable=0`；
- 缺失 protection/typec 时显示 `active_control=0`，绝不显示
  `protection_ok=1`；
- 只有在所有 provider 到位后，`active_control=1` 和 `desired_enable=1`
  才允许同时出现。

## 8. 证据边界

- 本文件结论基于源码静态审阅和已有 `MP2650-BIND-RCA-R15.md`，未访问
  手机，未验证冷启动时序。
- `mps,mp2650` 的 generic/managed 竞争已由 RCA 和真实 sysfs 现象支持；
  具体哪个驱动先 probe 仍取决于启动顺序。
- “软降级后 shadow 可稳定采样”是设计建议，不是已验证事实；必须先做
  冷启动只读验证，再考虑 control。
