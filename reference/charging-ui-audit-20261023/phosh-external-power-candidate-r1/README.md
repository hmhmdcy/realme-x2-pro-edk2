# Phosh 0.57.0-r3：独立外接电源标记候选

未部署。只在新目录生成五文件补丁并验证新增 manager 的异步边界；未构建完整 Phosh、安装 APK、连接手机、重启桌面、使用 SDK 或 Git。精确发行链复用 [固定源资料](../phosh-connection-source-r8/README.md)：实物包 c=97dba23dc382440e73c3813c9072a25099fb0d67，release tar 与发行 patch 已按该 APKBUILD SHA512 校验。

`external-power-marker.patch` 只改 `battery-manager.c`、`top-panel.c`、`top-panel.ui`、`phosh.gresources.xml`，新增一个自带 16px 插头 SVG。发行 splash patch 仅改 app-tracker，与本补丁无交叉。原 `on_property_changed()` 电池图标选择函数逐字保留，Battery State／bolt／icon-name、UPower、501 和 R8 不改。

## 行为

新增只读 `external-power-known`／`external-power-connected` 属性：

| UPower 观察结果 | known | connected／插头标记 |
| --- | ---: | ---: |
| 任一已识别 LINE_POWER Online=true | true | true／显示 |
| 本代枚举成功、至少一个 LINE_POWER、没有未知 kind、全部已识别 LINE_POWER offline | true | false／隐藏 |
| 服务无 owner、失败／尚未完成的枚举且没有已观察的 online、空集合或未知 kind | false | false／隐藏 |

这是 **UPower 已报告的连接**，不创造新的物理检测器。UpClient 在创建单个设备代理失败时会跳过该设备，API 不向调用者报告完整性计数；known 不应被解释为“证明所有物理接口都已离线”。连接为正只来自实际可用的 LINE_POWER Online 属性，不从 `!OnBattery`、电流符号、SOC 或 charger Switching 猜测。

顶部栏在电池旁显示独立插头，原电池图标不变。可访问名称为可翻译的 “External power connected”（外接电源已连接），描述与 tooltip 明示电池仍可能放电。新英文 msgid 接入原 gettext 路径，未擅自假定本机 locale 或既有中文翻译覆盖。插头使用自带 symbolic SVG，沿已有资源图标路径着色；新 revealer 的 transition-duration=0，不额外加原组件默认的400ms动画。原电池／其他状态图标动画不改。

## 生命周期与最小接入

- 仍只持一个当前 UpClient；bus-name watcher 的 AUTO_START 保留原 `up_client_new_async()` 默认会激活可用 UPower 服务的行为，避免引入“daemon尚未启动则永远无电池”的启动回归。
- 先接 client 的 device-added／device-removed，再调用实际 get_devices_async。按 object path 去重并自己持有设备引用；added 的临时引用不能借到回调之外。
- 设备增删提升 topology，取消旧快照并重新异步枚举；旧 topology／owner generation 的完成仅释放结果，不能重建已移除路径。Online／kind 属性更新只聚合，不触发额外枚举或 poll。
- 服务消失／换 owner 时先使 generation 失效、cancel、断旧信号、释放旧代理与设备集合，并将连接状态置 unknown；新 owner 用同一现有 client 字段建立新代理。保留最后电池图标，不造 Battery State；重连后仍只用真实 DisplayDevice 更新它。
- 每个异步 request 使用 GWeakRef；完成始终调用 finish 回收结果，即使 manager 已销毁也不解引用。dispose 可重复调用，取消并 unwatch，清理全部引用。属性通知可能同步触发 dispose，owner replacement 在通知返回后复查 disposed，禁止再发新请求。
- 沿 Phosh 的 UI main context 串行操作这些 GObject 状态；这不是跨线程操作 manager 的新 API。

没有 Refresh、sysfs、周期轮询或强制广播。没有新增服务／进程／UPower client 池，也不改输入预算或充电策略。

## 验证与边界

实际完整 candidate `battery-manager.c` 被直接 include 到定向 C 夹具，执行真实 GLib/GIO 的 GObject 属性通知、信号、GTask、GCancellable、GWeakRef 和引用释放；只模拟 UpClient／UpDevice 的远端边界与 bus-name watcher。10组覆盖：启动／signals先接、Online OR 与原放电图标保持、空／未知kind、移除期间旧枚举、同路径替换、枚举失败、owner变化／旧结果、销毁期间异步完成、失败不忙重试与重连、通知内dispose。ASan／UBSan／Werror通过；模拟错误日志是刻意的失败案例。未重跑旧语义套件，也不声称真实 DBus／GTK／像素时序已测。

`source-result.json` 固定五文件SHA、旧电池回调逐字保持和 XML／资源关系。核对了精确 PhoshRevealer 实现：其 GtkBin 已有内部 GtkRevealer，所以使用原 **child属性引用**，不额外向外层 GtkBin 加第二个 child。顶部栏注册 PhoshStatusIcon 类型。XML静态检查通过，但本环境没有 GTK3 开发包／Xvfb，尚未实例化完整模板。

`patch-result.json` 记录在全新私有目录重新运行候选生成器的五文件／补丁逐字比对，以及实际 `patch --dry-run` 和 apply 后全部输出SHA相等。未改原 release、旧冻结报告或发行 patch。

## 原版本隔离构建方案

现已具备精确 Phosh release、唯一发行 patch、APKBUILD 和本补丁。未来先在新的私有目录展开校验 tar，依次采用固定发行 prepare 和本补丁，再用原 0.57.0-r3 配方的 Meson 选项（包括 b_lto=true、phoc_tests=disabled、man=true）。保持原 package dependencies／subpackages，独立候选版本及回退字节需在构建前明确，不覆盖既有配方。

已有 Ubuntu 主机可运行 Meson/Ninja，但没有 abuild 或已认证的 aarch64-musl 交叉编译器；主机 GLib 2.88 的小夹具不等于目标 musl/GTK 构建。允许的缓存盘点只读取既有 rootfs 的数据库、world哈希及工具文件，不执行 chroot／SDK 工具或更改 DB/world。

实际缓存 `libcamera214-root` 不是当前 mountpoint，内有 aarch64 abuild 3.18.0_rc7-r1、GCC15.2.0-r9（ELF machine183）、musl-dev1.2.6-r5；固定配方28个 makedepends 仅发现 gettext/glib/meson/wayland 四项，仍缺24项（含 GTK3、Upower、libhandy、callaudiod 等开发包）。数据库读取前后 SHA 相同，完整缺项见 `cache-inventory-result.json`。这是可复用的**隔离副本种子**，不是已齐备的 Phosh 构建 SDK；没有直接运行它的 gcc／abuild。

未来在新的私有目录做无 hardlink 的 rootfs 副本，先核定目标依赖版本闭包，再仅在该副本补齐缺项并采用原版本配方／选项构建；不能写共享 rootfs、DB 或 world。完整产物及 split APK、依赖／ABI和回退需另行验证。不要把 single-object 结果当原 LTO 完整 shell 的可替换二进制。本轮没有开始副本构建或安装依赖。

本轮连接标记尚不能验收 Android 式响应或消除净充电建立时间；其目标仅是在 UPower 已 Online 时及时呈现独立接电事实。
