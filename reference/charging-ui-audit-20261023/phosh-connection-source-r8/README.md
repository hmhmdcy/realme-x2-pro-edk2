# 实装 Phosh 连接标记：固定发行源与最小方案

本叶只读取留存包元数据、缓存和官方固定源；未连接手机、执行 APKBUILD／patch／构建／测试、使用 SDK、改变版本或修改运行源。上一轮时间链保留在 [冻结审计](../remaining-icon-delay-r8/review.md)，本叶只追加新取得的发行源对应关系与可实现点。

## 实物包 → 固定配方 → 校验通过的源

根会话新鲜实物元数据给出 Phosh `0.57.0-r3`、APK `c:97dba23dc382440e73c3813c9072a25099fb0d67`；UPower `1.91.0-r2`、`c:ab329cc95719eba4b967c403f5e2e034184a37d1`。运行文件 SHA256 分别为 Phosh `99b2a367e455fa6028dc97cdf29e6a53824d6316dbee2b2e011eabf31f05cf0c`、upowerd `69a01f39eadb0f14015517331c246f125c93f9a15f5416aa4c7b18c3f66e9241`。私有原件没有复制到本叶。

从这些**实际 c 字段**定位到官方 Alpine aports 固定提交，取得 [Phosh APKBUILD](https://gitlab.alpinelinux.org/alpine/aports/-/raw/97dba23dc382440e73c3813c9072a25099fb0d67/community/phosh/APKBUILD) 与 [UPower APKBUILD](https://gitlab.alpinelinux.org/alpine/aports/-/raw/ab329cc95719eba4b967c403f5e2e034184a37d1/community/upower/APKBUILD)。配方内版本／release 均匹配实物；当前 edge 页面已经是 Phosh 0.58，未采用它。

| 输入 | SHA256 | 验证 |
| --- | --- | --- |
| Phosh APKBUILD | fe029f77cabb223b729017c1938dfa46c2e9233e8f312e58656d7ac1b12152d9 | 实物 c 对应固定提交，0.57.0-r3 |
| phosh-0.57.0.tar.xz | 30cd0eb182b92846162ab57516170ca09fe8ce08ef95703ee351af7b9c2b9520 | [官方 release](https://sources.phosh.mobi/releases/phosh/phosh-0.57.0.tar.xz)，与 APKBUILD SHA512 精确相等 |
| splash-timeout-flatpak-dbus.patch | 44101593f57bf0cb805e1f6255f2ae21459282cb14864894848489114484923f | 固定 Alpine 提交，同配方 SHA512；只改 src/app-tracker.c |
| UPower APKBUILD | f811fdbf7617e4a8cb60c8b9567e28c8349ce659f439b6e4db1cbc02144fa294 | 实物 c 对应固定提交，1.91.0-r2 |
| upower-v1.91.0.tar.bz2 | 954f8ee8d1422c813615862bc6249cb9b31ace1d905fd1f06549c4e47f4ba401 | [官方 v1.91.0 archive](https://gitlab.freedesktop.org/upower/upower/-/archive/v1.91.0/upower-v1.91.0.tar.bz2)，同配方 SHA512 |
| 0001-fix-self-test-sleep-duration.patch | 943d8cd4baba501839cc461c1fe83fca262248ae4bba4bfbdf93d9b1de3c723e | 固定 Alpine 提交，同配方 SHA512；只改 src/up-self-test.c |

两份完整 tar 只缓存于私有输出目录；本叶保存配方、发行 patch 和定向源文件。`recipe-fetch-result.json`／`release-input-result.json`／`source-addendum.json` 记录 URL、长度、SHA256、配方 SHA512 和源 archive member。`release-input-result.json` 中最初请求的 `src/resources.gresource.xml` 不存在，后续已在同一校验 archive 找到真实 `src/phosh.gresources.xml`，由 addendum 独立记录，未改早期收据。

Phosh release 的 `src/battery-manager.c` SHA `6a03bf69…5122df4`、`src/battery-info.c` SHA `c0eda134…70c1f3` 与之前固定提交参考缓存**逐字一致**，且唯一发行 patch 不涉及它们。UPower 已审 daemon／device／battery／Linux udev 与 supply 各文件也与旧 v1.91.0 缓存逐字一致，唯一发行 patch 只改测试。这闭合了发行输入来源和本条源码路径；未重现发行构建，不声称由这些源独立重建出的二进制 SHA 已等于实物。

## 新补齐的精确超时常数

现在从经配方 SHA512 校验的 archive 取得 `src/up-constants.h`：UNKNOWN_TIMEOUT=1 秒，UNKNOWN_POLL_TIME=5 秒，ESTIMATE_TIMEOUT=5 秒，SHORT_TIMEOUT=30 秒，LONG_TIMEOUT=120 秒。结合 `up_device_battery_update_poll_frequency()`，line-power 变化后的快轮询是**每 1 秒，持续约 5 秒**，不是固定 30 秒事件节流；与本轮约 1.02 秒的 Battery 属性更新相符。DISTRUST_RATE_TIMEOUT=10 秒只影响功率／时间估计，不保留旧已知 State。

## 最小实现范围

只新增一个“外接电源已连接”标记，不更改 Battery State、Charging／Discharging、Full 优先级、原电池图标或 bolt 判据。可限定在现有 Phosh manager 和顶部栏：

1. `src/battery-manager.c`：复用已有 UpClient；在连接 client 后监听 `device-added`／`device-removed` 并首次异步枚举。以 object path 为键保存 LINE_POWER 设备引用，监听其 `notify::online`（以及 kind 变化时更新集合），计算是否有任一已观察的 LINE_POWER online。新增只读属性，例如 `external-power-known`／`external-power-connected`，仅真实变更时 notify。**不调用 Refresh，不访问 sysfs，不加周期 poll。**
2. `src/ui/top-panel.ui`：在原 BatteryInfo 旁加入独立 `PhoshStatusIcon`，使用现有 PhoshRevealer 控制 show-child；现有状态容器本来就支持该组合。连接标记的语义／辅助文本为“外接电源已连接”，不称“正在充电”。原 BatteryInfo 节点与 icon-name 绑定不改。
3. `src/top-panel.c`：绑定新的 template child，把 manager 的连接属性绑定到 revealer。已有 constructed 路径第698行取得 shell，可从它取得现有 battery manager。必要时加相应类型头，不新增进程或 UPower client。
4. 图形资产要在真正补丁阶段固定：可复用已核定存在的主题连接图标，或随本补丁加入一个独立插头 SVG 并登记到真实 `src/phosh.gresources.xml`。当前未认证实物 Adwaita 是否有某个指定 icon-name，不以猜测名称冒充可交付资产。

这通常只需要 manager C、top-panel C／UI，另加一个小图形资源；无需改 status-icon／status-icons-box 实现、battery-info、UPower、内核、Phoc 或公共 lib ABI。

### 当前实际 API 可用

- UPower 1.91.0 `up-client.h` 88–96 提供 `up_client_get_devices_async()`／`finish()`；returned GPtrArray 为 transfer-full 且元素带 unref free-func。
- `up-client.c` 507–531 已导出 `device-added(UpDevice*)`、`device-removed(object_path)`。added 对象在 emit 后立即被库 unref，manager 若持有它必须自行 ref；removed 的参数是路径，不能按 UpDevice 解读。
- `up-device.c` 1001、1068 的属性名为 **online／kind**；分类读 `kind==UP_DEVICE_KIND_LINE_POWER`，不是猜一个 `type` GObject 属性。112–120 将远端属性通知转发给 UpDevice。
- Phosh `battery-manager.c` 104行已有 UpClient，106–120行已有 DisplayDevice 与它的独立 state／percentage listener。此处无需改变原 `on_property_changed()` 的电池图标规则。
- `top-panel.ui` 326–330 为现有 BatteryInfo；`PhoshStatusIconsBox` 支持 PhoshRevealer 包裹 PhoshStatusIcon，且会根据 priority 排列。新图标应使用相同 16px 尺寸和明确优先级，布局不足时的显示不能由本轮日志保证。

### 最少必须处理的生命周期边界

先接设备增删信号、再枚举；按路径去重。枚举期间增删设备时应使旧快照失效，完成后只接受当前 generation，避免已移除设备被旧异步结果重新加入。异步完成需要保住 manager 生命周期／取消对象，dispose 取消并断开监听、释放 device refs；不能沿用裸指针异步回调而不处理销毁。

UPower 名称失去 owner 时，把连接结果置 unknown 并隐藏标记、清掉旧设备；owner 重建后重新枚举，不保留旧 online=true。可用现有 GLib 的 bus-name watch，具体实现无需访问 UpClient 的 private proxy。无设备／枚举失败／未知 kind 不能被包装成“确认已拔线”；此 UI 只承诺显示**UPower 已报告的连接**，不把 DBus 默认值当新的物理检测器。

这些是一个小 manager 扩展的必要边界，尚未实现或新增测试。本轮没有将其扩展成通用监视框架。

## 为什么不直接使用 !OnBattery

精确发行的 `up-daemon.c` 99–102 取 Display Discharging，828 行再与“没有在线 AC”相与后才设置 OnBattery。本轮 source／charger Online=false 在约191.4–191.5秒，OnBattery=true却直到195.623秒；简单反转它仍然晚约4秒。重接 Online=true 在201.762秒，Display Charging在204.998秒。因此连接标记可按**已收到的 Online**先反馈动作，而原 bolt 要等真实 Battery State；不把负净流伪装为净充电。

## 后续构建输入与当前限制

当前已缓存精确 release tar、发行 patch、APKBUILD 和本改动所需的原源码，来源不再阻断。Phosh APKBUILD 的 `prepare` 除 default_prepare 只替换 meson 的 `.rc` 字符串；build 使用 `abuild-meson -Db_lto=true -Dphoc_tests=disabled -Dman=true` 再完整 meson compile。因启用 LTO、且所需产物含主 shell／相关库，不应声称只编译一个 battery.o 并在线替换即可等价。

还未确认现存缓存含**相同发行依赖闭包与 aarch64/musl abuild 环境**；未安装／下载二进制依赖，也未开启 SDK。下一个实际步骤可以先按上述精确源在新 leaf 写最小 UI patch 和少量真实函数／异步边界测试，再明确批准一个隔离的原版本构建。当前没有修改、构建、安装或重启桌面，也未触碰冻结501／R8。
