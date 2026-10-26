# k363 蓝牙主机协议与最小配置增量

2026-10-23。固定源审查后，相机456明确交还CPU/内核构建资源，主线授权在原私有QCA O中实际构建两个小模块。构建与恢复已完成，未改共享 source/build，未使用SDK或手机，未构建Image、安装或加载模块。

固定内核为 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`。复用主线私有 `host-protocol-prerequisites-private.json`：Image SHA256 `15746aab…6468`、内嵌配置 `23e088a9…30ed`、模块归档均与363构建记录一致；归档相关名单仅有 `hidp.ko`。来源和脱敏事实统一见 [audit-summary.json](audit-summary.json)，具体行号、Git blob、SHA256见 [kernel-source-evidence.json](kernel-source-evidence.json)。

## CONFIG_BT_LE 的实际含义

**此固定树的 `CONFIG_BT_LE=n` 只排除 ISO socket 对象/接口，不能据此判定普通 LE MGMT、ATT、SMP 或 GATT 被编译删除。** 前期按选项名称作出的“普通LE缺失、必须新Image”推断已撤回；本轮不因此重建Image。

- `net/bluetooth/Makefile:14..18` 始终把 `mgmt.o`、`l2cap_core.o`、`l2cap_sock.o`、`smp.o`、HCI连接/事件/同步编入 `bluetooth-y`；第22行才用 BT_LE 控制 `iso.o`。
- `include/net/bluetooth/hci_core.h:1959` 的 `lmp_le_capable()` 只读控制器 LMP_LE 位；`mgmt.c:1523..1531` 的 LE 支持判定只读此能力和 HCI_LE_ENABLED。MGMT LE开关/广告代码未被 BT_LE 条件包围。
- `l2cap_sock.c:105..109` 保留用户态 ATT CID 的 LE socket，`smp.c:3370..3392` 按控制器能力建立 SMP CID。GATT由 BlueZ用户态通过这些协议承载。
- BT_LE 的实际条件出现于 `iso.o`、ISO init/recv stub，以及 MGMT ISO experimental feature入口。将该 bool 改成 y 会改变已内建的 Bluetooth核心，需要新Image；是否可用ISO还取决于控制器能力，不由配置单独证明。
- `BT_LE_L2CAP_ECRED` 只决定 `enable_ecred` 的默认值；实际代码已在，`l2cap_core.c:8043` 有 `module_param(enable_ecred,bool,0644)`。当前普通ATT测试不依赖它，不改运行参数，也不把 absent 直接当成编译缺失。

上述“ISO门控”指此开关在主机C/Kbuild路径的直接作用；Kconfig还把BT_LE用于ECRED及可选6LoWPAN的菜单依赖。本轮不新增6LoWPAN，也不为这些菜单改动Image。

现场 MGMT supported/current settings、HCI能力、BlueZ GattManager/LEAdvertisingManager 和实际服务行为仍待设备窗口读取。源审查不等于手机 GATT 已验收；UART PM r2也只修传输生命周期。

## 哪些需要 Image，哪些可单独模块

| 功能 | 此版本现状 | 最小边界 |
| --- | --- | --- |
| 普通LE发现/连接、ATT、SMP、GATT | 核心源码已编入BT；现场能力/服务待核 | 无已证实的配置增量；先做受控现场读取/测试 |
| ISO socket | BT_LE=n排除iso.o | 若明确需要，BT_LE=y涉及新Image；当前不安排 |
| ECRED/EATT | 代码在，enable_ecred默认关闭 | 先核实际参数和需求；不为选项名字重建Image |
| PAN/BNEP网络 | 原Image BT_BNEP=n且归档无bnep.ko | `CONFIG_BT_BNEP=m`，单编bnep.ko |
| BlueZ HOG输入及使用UHID的用户态HID | 原Image UHID=n且归档无uhid.ko | `CONFIG_UHID=m`，单编uhid.ko；还需真实HID对端和对应服务验收 |
| Classic HIDP | BT_HIDP=m，归档已有hidp.ko | 复用现有模块；不替代HOG的UHID输入路径 |

实际Image另核实 `HID_SUPPORT=y`、`HID=y`、`HID_GENERIC=y`、`CRC32=y`，因此两模块已有依赖均为内建。全树固定对象搜索显示 CONFIG_UHID只出现在其Makefile；CONFIG_BT_BNEP只决定BNEP目录/对象，filter条件仅在BNEP私有代码，没有共同Bluetooth/HID头文件的条件字段。此次 n→m 不要求重编原内建BT/HID或改变其结构ABI。仍须按实际原配置、固定头文件、原符号表、完整vermagic和intree标记构建验证，不能仅靠名称相同判断模块兼容。

[modules.config](modules.config)只启用 BNEP=m、UHID=m，保留两个BNEP filter为n；BT、BREDR、BT_LE、HIDP、HID、CRC32等保持。固定BNEP Kconfig的两个filter无default语句、隐式默认n；执行脚本仍显式读取并合入fragment中的两条n，合并前后按absent等价于n确认只有两项语义变化。

## BlueZ HOG 来源

复用项目已固定的BlueZ 5.87 commit `65d11edee469c24dcc8d075b8be9c040cebaaf98`。本目录补充的三个原始源文件及SHA在 [bluez-reference/manifest.json](bluez-reference/manifest.json)：

- [hog.c](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/profiles/input/hog.c)通过 `bt_hog_new_default()` 建立HOG对象，并明确HOGP要求bonding；专用不配对GATT对端测试不代替HOG验收。
- [hog-lib.c:1428](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/profiles/input/hog-lib.c#L1428)调用 `bt_uhid_new_default()`，失败时不创建HOG对象。
- [uhid.c:189..196](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/src/shared/uhid.c#L189)实际打开 `/dev/uhid`；内核 `drivers/hid/uhid.c:808..819`以misc设备/模块导出该接口。

## 两模块实际增量构建

[build-missing-modules.py](build-missing-modules.py)默认只打印计划，不调用make、不写配置。本次在456交还后使用以下显式执行入口，已保留终态收据，不能盲目重放：

```text
python3 build-missing-modules.py --execute-after-456-handoff
```

实际复用已有私有 `bluetooth-transport-20261023/source-view` 和 `O`，没有新建大O或修改源文件。校验原363 Image/config/symvers、固定相关源/头文件及当前私有配置，只改两个 n→m；olddefconfig后确认只有这两个语义差异，以 `-j1 W=1 KCFLAGS=-Werror` 构建：

```text
net/bluetooth/bnep/bnep.ko
drivers/hid/uhid.ko
```

olddefconfig用时8.593秒、modules_prepare 8.646秒、两个模块目标6.800秒，含恢复总计30.435秒，实际session 5829退出0、state terminal=true，诊断0。两模块intree=Y、完整vermagic均为 `7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64`、依赖为空；77/38个导入符号分别全部存在于原363符号表。[实际构建报告](module-build-validation.json)

| 私有产物 | 字节 | SHA256 |
| --- | --- | --- |
| `E:/edk2-samurai-out/bluetooth-host-config-20261023/bnep-k363-intree.ko` | 26696 | `b5ad9a3f3aed3ed97cf20ec656ee997550270f3ee37f4131b655020a0be5f909` |
| `E:/edk2-samurai-out/bluetooth-host-config-20261023/uhid-k363-intree.ko` | 18240 | `90694197207607ebb036157aaeab03bee5023fa68c0ccae5dd3f6de22b9cd78e` |

原私有O配置与Module.symvers逐字恢复，相关共享输入与既有PM r2原件保持；固定源/头文件Hash及Git对象等价、恢复字节核对见[构建来源收据](build-provenance.json)。开始可用空间7,452,372,992 B，结束7,450,660,864 B，保持2GiB加128MiB边界。

构建输入/导入核对使用原363 `build/Module.symvers`，1005354 B、SHA256 `0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223`。私有 `module-symvers-before-private` 是原QCA O的876446 B表，仅用于逐字恢复，不能拿它替代原363符号证明。

第一次执行在最早守卫发现WSL已自动结束、原ext4未挂载而退出1；mountpoint为空、原32GiB普通backing保持，无make/worker或配置写。主线审查284 storage后授权恢复该已知挂载，在同一WSL进程验证挂载/原件后才执行构建。失败收据保留在私有目录；没有格式化、卸载或更换backing。后续只读Hash收尾同样使用已审storage入口，无第二次构建。

源码锁只固定源码、fragment、说明和静态来源证据，不纳入本次生成的验证/来源JSON，也不包含自身，避免循环Hash。未来装包、模块加载/撤销、UHID权限和PAN/HOG业务验证由主线按实际owner与设备交接安排。本次仅编译通过，没有把它记作业务已验收，也没有相机或充电改动。
