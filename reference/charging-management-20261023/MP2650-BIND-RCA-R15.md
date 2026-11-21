# R15 MP2650 真机未绑定根因与最小修复

日期：2026-10-28  
范围：只读检查 `samurai-mp2650` 源码、KO、I2C core、R15 安装流程和真机现象；未访问手机、未改设备。

## 结论

根因不是单一模块 alias，而是 **匹配问题与 probe defer 问题叠加**：

1. 真机 `0-005c` 的 OF compatible 是 `mps,mp2650`，uevent 为
   `MODALIAS=of:NchargerT(null)Cmps,mp2650`。
2. 该节点的 I2C client 名称由 `of_alias_from_compatible()` 取 compatible
   `,` 后部分生成，因此 `client->name == "mp2650"`。
3. `samurai-mp2650` 的 I2C ID 表确为 `{ "mp2650" }`，KO 也确有
   `alias=i2c:mp2650`。所以 I2C legacy match 本身可以命中；缺 OF match
   并不表示完全无法显式绑定。
4. 但同名的 generic `mp2650` 驱动也匹配该 client。I2C core 在设备
   unbound 后会尝试所有已注册驱动；只要 generic 仍 loaded，它就可能先
   重新占住 `0-005c`。
5. `bind_store()` 只在
   `driver_match_device(drv, dev)` 为真时调用 `device_driver_attach()`。
   若 `device_driver_attach()` 返回 `-EAGAIN`（由 probe 的
   `-EPROBE_DEFER` 转换）或设备已有 driver（`-EBUSY`），实际绑定失败。
   因此“echo 返回 0 但 `/sys/bus/i2c/drivers/samurai-mp2650` 无链接、
   dmesg 无 probe 日志”等价于 **match 通过/未通过后 attach 失败，并非 probe
   成功**。
6. `runtime_board=1` 只跳过 DT telemetry 属性检查，不会放宽 I2C/OF match。
   它仍要求按名字取得 `samurai-usb-input`、`samurai-gauge-protection`；
   `control=1` 还要求真实 Type-C supply。任一缺失都会让 probe 返回
   `-EPROBE_DEFER`，手动 bind 表现为 rc 非零或“看似无动作”。
7. `sm_named_supply()` / `sm_typec_supply()` / gauge 路径创建的
   `device_link` 都带 `DL_FLAG_AUTOREMOVE_CONSUMER`；失败 probe 的
   `device_links_no_driver()` 会删除这些链路。它们可能造成一次 probe
   失败，但不是“永远不再调 probe”的根因。真正需要修的是匹配顺序和
   defer 依赖，而不是盲目删掉所有 link。

## 证据

### 模块

- R15 原 KO：`samurai-mp2650.ko`
  - SHA-256：`dbe445cfef6e095f8d028034f0fbba9231484b6510ab6f60354c6ff55e9c23d1`
  - aliases：
    - `of:N*T*Crealme,samurai-mp2650-managedC*`
    - `of:N*T*Crealme,samurai-mp2650-managed`
    - `i2c:mp2650`
- 新 KO：
  - SHA-256：`0f5f7f212711d304cf0e674580db9e5bc6d1f0521a4d22b711267ec1ce2e292e`
  - aliases 与 R15 原 KO 相同。

因此别名差异不是新 KO 独有回归；R15 原 KO 在当前 boot 也无法 fresh bind，
进一步指向运行期匹配/依赖状态，而不是本 patch 新增 alias。

### 匹配代码

- `drivers/i2c/i2c-core-of.c:of_i2c_get_board_info()`
  - `of_alias_from_compatible()` 取 `mps,mp2650` 的后半部分，
    得到 `info->type = "mp2650"`。
- `drivers/i2c/i2c-core-base.c:i2c_device_match()`
  - 先 `i2c_of_match_device()`，再 `i2c_match_id()`。
- `drivers/i2c/i2c-core-base.c:i2c_match_id()`
  - 比较 `client->name` 与 ID 表 name，故 `i2c:mp2650` 可 match。
- `drivers/base/bus.c:bind_store()`
  - 需 `driver_match_device()` 为真，再调用 `device_driver_attach()`。
- `drivers/base/dd.c:device_driver_attach()`
  - `-EPROBE_DEFER` 被转换为 `-EAGAIN`；设备已占用返回 `-EBUSY`。

### 驱动

- `samurai-mp2650.c`
  - `.name = "samurai-mp2650"`
  - `.of_match_table = { "realme,samurai-mp2650-managed" }`
  - `.id_table = { "mp2650" }`
  - `sm_probe()` 首先检查 machine compatible 和 `client->addr == 0x5c`。
  - `runtime_board=1` 时：
    - `sm_named_supply(..., "samurai-usb-input")`
    - `sm_named_supply(..., "samurai-gauge-protection")`
    - `sm_typec_supply()` 需 DT `typec-supply`
  - gauge 路径还有 `of_find_i2c_device_by_node()`、
    battery PSY 查找和多个 `-EPROBE_DEFER`。
- generic `mp2650_charger.c`
  - `.name = "mp2650"`
  - OF 表含 `mps,mp2650`
  - I2C ID 表含 `mp2650`
  - 因此它会与 managed 驱动竞争同一 `0-005c`。

### R15 安装流程

证据脚本：
`/mnt/e/edk2-samurai-out/charging-management-20261023/r15-evidence-20261027/r15-mincap-install-20261027-055713/samurai-charging`

关键顺序：

```python
if driver == 'mp2650':
    live.bind('mp2650', 'unbind')
else:
    assert driver == 'samurai-mp2650'
load_module(meta, 'samurai-mp2650', ['runtime_board=1', 'control=1'])
assert (live.CLIENT / 'driver').resolve().name == 'samurai-mp2650'
```

这段流程证明 R15 成功路径依赖 **先卸掉 generic，再加载/绑定 managed**，
且最后显式检查 `0-005c/driver` 链接。单写 unbind、不阻止 generic
`drivers_probe`/autoprobe，可能让 generic 立刻抢回设备。

## 最小可落地修复

### 方案 A：不改 KO，修安装/命令流程（立即可用）

适用于当前已部署的 `0f5f...` 或 `dbe445...` KO。

```bash
# 仅示意，必须由 root 在设备上执行；本次未访问手机
cd /sys/bus/i2c/devices/0-005c

# 1. 明确清掉旧 driver，并阻止 generic 抢先
printf '%s\n' 0-005c > /sys/bus/i2c/drivers/mp2650/unbind 2>/dev/null || true

# 2. 让该设备只能匹配 managed 驱动
printf '%s\n' samurai-mp2650 > driver_override

# 3. 加载/确认 managed 模块
insmod /lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko \
    runtime_board=1 control=1

# 4. 显式触发一次 attach，然后检查真实链接
printf '%s\n' 0-005c > /sys/bus/i2c/drivers/samurai-mp2650/bind
readlink -f /sys/bus/i2c/devices/0-005c/driver
test -L /sys/bus/i2c/drivers/samurai-mp2650/0-005c
```

关键点：

- `driver_override` 必须在 generic 仍 loaded 时先写，避免 unbind 后 generic
  被 autoprobe 重新匹配。
- 不要只看 `echo` 退出码；必须检查
  `/sys/bus/i2c/devices/0-005c/driver` 和 driver 目录下的设备链接。
- 若 `driver_override` 不存在，说明当前内核未启用 I2C bus 的
  `driver_override`，只能先临时 `rmmod mp2650`，再加载 managed 并显式 bind。
- 安装脚本应把“unbind generic、写 override、insmod managed、bind、
  验证链接”作为原子顺序，失败时回滚 generic。

这是**首选的最小运行期修复**：不需要重编模块，也不改动通用 I2C core。

### 方案 B：补 OF compatible，重编 KO（长期最稳）

在 `samurai-mp2650.c` 的匹配表中增加实际 DT compatible：

```c
static const struct of_device_id sm_match[] = {
    { .compatible = "realme,samurai-mp2650-managed" },
    { .compatible = "mps,mp2650" },
    { }
};
```

该修改会生成：

```text
alias=of:N*T*Cmps,mp2650
```

并让 OF match 在设备创建或驱动注册时直接命中。

但仅补 OF alias **仍不够**：

- generic `mp2650` 也匹配 `mps,mp2650`，两个驱动仍可能竞争；
- 必须保证 managed 优先，或在服务启动时卸掉 generic；
- probe 仍可能因 `runtime_board` 依赖缺失而 defer。

因此方案 B 必须与方案 A 的“先卸 generic / 验证链接”流程配套。

### 方案 C：去掉 runtime_board 对旧 client state 的硬依赖（若必须改驱动）

如果继续出现 probe defer，建议将 `runtime_board` 路径改为：

1. `samurai-usb-input` 不存在时，不要整体返回 `-EPROBE_DEFER`；
   记录 `input = NULL`，让 probe 先完成基本 charger/PSY 注册。
2. `samurai-gauge-protection` 改为可选：无 protection 时只注册基础
   `mp2650-input`，并把 `control` 自动降级为 shadow，禁止写充电寄存器。
3. 不要为可选 supplier 添加 `DL_FLAG_AUTOREMOVE_CONSUMER` 的强链路；
   只有在真实 consumer 已成功注册后才建立 link。
4. gauge 的 `of_find_i2c_device_by_node()` / battery PSY 查找失败，
   应记录明确错误，而不是让一个可选展示桥阻塞整个充电驱动 probe。

这类修改需要重编 KO，而且会改变安全策略；因此不是第一优先级。

## 为什么不应只改 id_table

`i2c:mp2650` 已经存在且可匹配。只重复添加
`{ "mp2650" }` 不会解决：

- 当前 boot 中 generic 已占用设备；
- OF compatible 是 `mps,mp2650` 而 managed 的 OF 表不认；
- probe 因 supplier/PSY 依赖返回 defer；
- 手动 bind 失败但退出码被误读。

因此不要以“再补一条 id_table”作为修复。

## 是否需要重编

- 方案 A：**不需要重编**，只改服务/安装脚本或运行期命令。
- 方案 B：**需要重编**，因为 OF 表和 module alias 编译进 KO。
- 方案 C：**需要重编**，因为 probe 流程改变。

## 验收顺序

1. 记录 binding 前：
   - `/sys/bus/i2c/devices/0-005c/name`
   - `/sys/bus/i2c/devices/0-005c/modalias`
   - `/sys/bus/i2c/devices/0-005c/driver`
   - `/sys/bus/i2c/drivers/samurai-mp2650/0-005c`
2. 写 `driver_override` 后确认内容为 `samurai-mp2650`。
3. `insmod runtime_board=1 control=1` 后确认模块 loaded。
4. 显式 bind 后确认：
   - `/sys/bus/i2c/devices/0-005c/driver` 指向 `samurai-mp2650`
   - driver 目录下存在 `0-005c` 链接
   - dmesg 出现 `offline candidate bound in control mode`
   - `/sys/class/power_supply/mp2650-input` 存在
5. 最后再启动 `/usr/sbin/samurai-charging start`，确认 `driver` 不为
   `None`，且 `mp2650-input` 可读写。

## 备注

- 当前工作树 `sm8150-samurai.dts` 写的是
  `realme,samurai-mp2650-managed`，与真机实际 `mps,mp2650` 不一致。
  这可能是启动 DTB 与源码树不同步；部署前应确认实际 DTB，而不是仅看源码。
- 不要在没有 `driver_override` 或未卸载 generic 的情况下，把
  “unbind 后无链接”误判为 managed 驱动代码崩溃；先看
  `0-005c/driver` 和 `dmesg | grep -E 'samurai-mp2650|mp2650|probe'`。
