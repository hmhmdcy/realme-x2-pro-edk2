# L2-L4 收敛计划：工作包、闸门与飞轮保护

整理日期：2026-11-05。

本文把 [Linux 七层适配说明](LINUX-ADAPTATION-LAYERS.md) 中的 L2/L3/L4
落成可执行工作包。目标是先收敛硬件描述、驱动边界和公共 UAPI，
**不改变当前调试飞轮的主路径**：

- 只从 L2（DTB/硬件描述）、L3（内核驱动）、L4（内核公共 UAPI）开始；
- 暂不把 L1 的 ESP/BDS/启动项改造、L5-L7 的发行版/桌面迁移混入首轮；
- 每次运行时切换只引入一个可归因变化；
- 变更有本地基线、回退路径和独立验收证据。

2026-11-05 的 L2 进展：规范源码已锁定为 k363 提交
`ba61a62293e0f6bc5838c06f2e85e033e3d702a8` 的板级 DTS，
重建 DTB 与构建记录完全一致；共享 DTSI、OS DTS、vendor 对照 DTS
也已在离线构建中通过语义验证。实机侧另有一次只删除三个 vendor
根属性的 boot 内嵌 DTB 探针，验证了入口、单变量切换和飞轮恢复。

仍未完成的是：把**源码构建的 OS DTB**实际装入固件，并把当前 boot
中的充电实验 DTB 与规范 OS DTB 分离。因此不能据此宣布
`samurai-dt-v1` 已冻结。

本文不是功能完成声明，也不替代 [硬件状态](HARDWARE-STATUS.md)、
[当前检查点](../../NEXT-SESSION.md) 和 [飞轮流程](../../FLYWHEEL.md)。

## 0. 飞轮不变量

当前飞轮依赖以下条件。任何工作包如果破坏其中一条，都不合格：

1. `boot` 分区中有一份已知可启动的 UEFI；原厂 boot image 和 GPT 备份
   可取回；
2. `logdump` 的 FAT 仍有可识别的 `\Image`，且 PE/MZ 校验通过；
3. EUD/console、`pstore`/ramoops 和 USB NCM/SSH 仍可用于观察与救援；
4. 实际运行的内核 release、`/lib/modules` 和模块构建版本匹配；
5. 当前桌面/rootfs 仍能启动，至少保留一个可用的旧接口或回退包；
6. 两边都有回退：PC 保留上一份 boot/logdump 镜像，设备上保留原厂
   boot 和 EDL 救援路径。

“L2/L3/L4 可以并行”只适用于**离线设计、源码拆分、增加兼容别名**。
运行时的三个危险动作——换 DTB、删启动保险、删旧 UAPI——必须串行。

## 1. 当前证据与待收敛点

### 1.1 L2：DTB 和硬件描述

**源锁已解决。** 仓库中的
[`linux-port/dts/sm8150-samurai.dts`](../dts/sm8150-samurai.dts) 是早期
bring-up 快照（487 行，SHA-256
`6e6c592b612712f7528841f0a3f918546e9bd5f348e3f516310b2f4145f9462c`）；
它只能作为历史快照。规范输入是
[kernel276 归档 DTS](../../reference/kernel276/sm8150-samurai.dts)，
1094 行，SHA-256
`428e20b3fe06a8b4ea85617cd2db3da9528e4edb0276647e7c7ed15c3737338b`；
该 blob 与 k363 构建提交 `ba61a622...` 中的
`arch/arm64/boot/dts/qcom/sm8150-samurai.dts` 逐字节相同。

用 k363 的精确配置
`23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed`
离线重建后得到 DTB SHA-256
`dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d`，
与 [kernel363 构建记录](../../reference/kernel363/boot-candidate-build-validation.json)
完全一致。

源码级拆分产物在
[`linux-port/dts/split-ba61`](../dts/split-ba61/)：

- shared DTSI `d119d7d9...`；
- OS DTS `d3d165f2...`；
- vendor 对照 DTS `05091604...`；
- OS DTB `f7959f8a...`，仅比规范 DTB 少三个 vendor 根属性；
- vendor DTB `dcdd74ec...`，与规范 DTB 逐字节相同。

这个 vendor 产物只是语义对照，不是 boot image 后附加的 450826 字节
stock ABL compat DTB。

本次受限探针是一个明确、一次性的例外：它没有拆源码，只把当前已部署
OS-facing DTB 的三个 vendor 根属性删除，再原位替换 boot image 内嵌
DTB。这样可以把“DTB 是否真的从这里进入 Linux”与“源码拆分是否正确”
分开验证，且不需要同时改源码、启动项或用户态。

实测入口纠正：当前 OS DTB 在 boot image 内，不在 `logdump` 的 FAT
里。只替换 `logdump\samurai.dtb` 并重启时，运行态
`/sys/firmware/fdt` 和三个 vendor 属性均保持原样；恢复 logdump 后，
改为原位替换 boot 内嵌 DTB 才观测到运行态变化。后续不要再用
`fastboot flash logdump` 来测试 OS DTB 是否生效。

2026-11-05 探针收据：

| 项目 | 结果 |
| --- | --- |
| baseline boot | `758694a1...a4acd`，100663296 B |
| OS DTB 候选 | `e3db4fa9...7850a`，只少三个 vendor 根属性 |
| boot 候选 | `66dbe234...efa23ae`，BootShim/ramdisk/其他 FV 模块不变 |
| fastboot 身份 | `msmnile`，boot `0x6000000`、类型 `raw`，只写 boot |
| 运行态 | 新 boot ID；三个 vendor 属性消失；`realme,samurai`/`qcom,sm8150` 保留 |
| 树差异 | 反编译前后只差三个 vendor 根属性；候选 vs 运行态只差 UEFI mmap/table 字段 |
| 飞轮 | SSH 约 32 秒恢复；`logdump`、798 项模块清单、Image 均未变 |

本地收据：
`E:\edk2-samurai-out\layer-adaptation-20261105\boot-dtb-inplace\runtime-result.json`。
该探针只证明运行时拆分入口和最小 boot 切换可行，不证明源码双 DTB、
调试 `bootargs` 删除、双内核兼容或不同 SKU。

另一个必须保留的边界：当前 boot 在探测前的 OS DTB
`9736b861...`（116962 B）来自充电实验链，不是 k363 官方构建 DTB
`dcdd74ec...`（114556 B）。规范 OS DTB 合并前，必须先逐项分类这些
充电实验属性；不能把实验 DTB 当作稳定 ABI。

### 1.1.1 2026-11-05 差异账本

已用
[`diff-dtb.py`](../scripts/diff-dtb.py) 对 canonical k363 DTB
`dcdd74ec...` 和探测前 boot OS DTB `9736b861...` 做只读语义比较，再用
[`dtb-diff-ledger.py`](../scripts/dtb-diff-ledger.py) 分类。工具先归一化
299 个纯 phandle 值变化和 679 个已知引用属性；剩余 **24 个语义项全部
有分类，0 个未分类**：

| 类别 | 项数 | 处置 |
| --- | ---: | --- |
| 相机 ICP | 7 | 可选 overlay，不进入 v1 公共硬件契约 |
| 充电 / USB input | 12 | 可选 overlay/固件实验输入，不进入 v1 |
| USB 控制器 linkage | 1 | 只表示 DWC3 被实验引用，不是硬件策略 |
| EUD 调试路由 | 3 | debug-only，生产 DTB 排除 |
| 调试 / 测试 bootargs | 1 | 迁移到 debug 启动项或 LoadOptions |
| vendor/compat 根属性 | 0（探测前）/ 3（当前 `e3db4fa9...`） | 只留在 vendor DTB |
| **新增公共 ABI** | **0** | canonical OS DTB 继续作为基线 |

当前 post-probe OS DTB `e3db4fa9...` 与 canonical 的 27 项差异，正好是
上面的 24 个实验项再加 3 个 vendor 根属性删除；两套账本均为 100%
分类。

把探测前链路按阶段拆开后，当前 `9736b861...` 不再是不可解释的整体：

| 阶段 | 语义变化 |
| --- | --- |
| canonical `dcdd74ec...` → integration509 `9aa3e6fc...` | 24 个实验项：ICP、EUD 路由节点、充电接线、bootargs/serial/typec 状态 |
| `9aa3e6fc...` → EUD route `d7d8a7da...` | 只改 `/soc@0/eud-off-route` 的 `status`：`disabled` → `okay` |
| `d7d8a7da...` → 5V1500 `9736b861...` | 只改 Type-C connector 两项：`op-sink-microwatt` 2.5 W → 7.5 W；`sink-pdos` `0x04019032` → `0x04019096`（5 V 500 mA → 5 V 1500 mA） |

这说明 5V1500 不是新的硬件 ABI，而是一个可以独立版本化的供电策略
参数；EUD route 也是单独的调试开关。

随后用
[`experiments/`](../dts/experiments/) 中的独立 DTSI 重建了整条实验链。
构建结果 `c582dd7c...a64f`（116843 B）与部署的 `9736b861...` 比较：
changed/added/removed 语义属性均为 0，节点差异为 0；只有部署端
`/soc@0/eud-off-route` 多一个未消费的 phandle。也就是说，当前部署 DTB
已经从源码层面解释清楚，不再是一个带黑盒补丁的二进制。

独立 profile 也分别离线构建并通过账本检查：
`charging_500ma` 15/15、`charging_5v1500` 15/15、
`camera_icp` 10/10、`eud_debug` 8/8；0 个 unclassified。它们仍不是
运行时已激活的 profile。

同时把 source-built OS DTB `f7959f8a...a3f0`（调试 `bootargs` 仍在）
装入 `boot` 候选：
候选 boot `aa93d14d...1c55`（100663296 B），源 boot 为
`758694a1...a4acd`。后续复核推翻了“只有内嵌 DTB payload 改变”的
初判：`BdsDxe` 从 110690 B 变为 114786 B，`UiApp` 有 312 字节、
149 个区间的代码差异，`PlatformSmbiosDxe` 也有 11 字节变化。因此
`aa93d14d...` 已标记为**拒绝、不得刷入**。必须从原 boot 重新做
in-place 替换，证明所有非 DTB FFS body 逐字节不变后，才能进入 G3。

该 in-place 重建已于 2026-11-05 完成：从 `758694a1...` 出发，只替换
内嵌 DTB payload，使用 EDK2 `LzmaCompress` 生成原格式的
known-size/no-EndMark LZMA 流，得到候选 boot `3e83798e...`。
独立复核结果是 `BdsDxe`、`PlatformSmbiosDxe`、`UiApp` 全部逐字节
相同；除 DTB GUID `25462cda...` 外没有 FFS body 变化，
`non_dtb_ffs_body_changes = 0`，metadata review `passed: true`。
该候选仍未刷入，且会激活 canonical OS DTB，移除当前充电/camera/
EUD 实验行为；充电长测结束前不得用它进入 G3。

可重复的构建顺序是：

1. `patch-dtb-boot-in-place.py --dump-modified-plain` 导出修改后的
   未压缩 main FV；
2. 用 EDK2 BaseTools 的 `LzmaCompress -e d 24` 压缩该文件；
3. 再用 `--compressed-main` 生成 boot 候选；
4. 最后运行 `review-boot-metadata.py`，要求 `passed: true` 且
   `non_dtb_ffs_body_changes: 0`。

不要用 Python `lzma.compress` 生成 known-size header：它输出的是
unknown-size/EOS 流，直接改 8 字节长度会被固件判为 corrupt。

收据：

- `E:\edk2-samurai-out\layer-adaptation-20261105\source-lock-ba61\deployed-dtb-difference-ledger.json`
（SHA-256 `5170ba9e...93d351`）；
- `E:\edk2-samurai-out\layer-adaptation-20261105\source-lock-ba61\current-os-dtb-difference-ledger.json`
（SHA-256 `0c9026ae...304089c`）。
- `E:\edk2-samurai-out\layer-adaptation-20261105\source-lock-ba61\eud-route-to-5v1500-semantic.json`
  （SHA-256 `c246b921...a8d3`）。
- `E:\edk2-samurai-out\layer-adaptation-20261105\experiment-dtb-build\build-result.json`
  （SHA-256 `cc2e22b5...bc25`）；
- `E:\edk2-samurai-out\layer-adaptation-20261105\experiment-dtb-build\deployed-vs-source-reconstruction.json`
  （SHA-256 `6a48a2d0...fac7`）。
- `E:\edk2-samurai-out\layer-adaptation-20261105\production-boot-candidate\result.json`
  （SHA-256 `531de2eb...39cc`）。
- `E:\edk2-samurai-out\layer-adaptation-20261105\production-boot-candidate\metadata-review-v2.json`
  （SHA-256 `af40cd11...6f3`；`passed: false`）。
- `E:\edk2-samurai-out\layer-adaptation-20261105\production-boot-candidate-inplace\result.json`
  （SHA-256 `5cef8468...92d3`）。
- `E:\edk2-samurai-out\layer-adaptation-20261105\production-boot-candidate-inplace\metadata-review.json`
  （SHA-256 `b1088a80...7581`；`passed: true`）。

这解决的是“哪些差异属于哪一层”的账本问题，不证明充电、相机或 EUD
实验已经可以进入生产 DTB。下一步必须把这些实验项变成独立、可构建的
overlay 或固件输入，再决定是否以及何时激活。

当前 [samurai DTS](../dts/sm8150-samurai.dts) 同时承担三种职责：

| 当前内容 | 位置示例 | 目标归属 |
| --- | --- | --- |
| 根 `model` / `compatible` / `chassis-type` | DTS 26-28 行 | OS-facing DTB，稳定保留 |
| `qcom,msm-id`、`qcom,board-id`、`oppo,dtsi_no` | DTS 38-40 行 | vendor/compat DTB |
| `chosen`、`stdout-path`、调试 `bootargs` | DTS 42-51 行 | 启动项/调试启动项，不属于硬件 ABI |
| `/memory` 占位 | DTS 97-109 行 | EFI memory map/运行时修补 |
| `reserved-memory` 和板级资源 | DTS 110 行起 | OS-facing DTB，作为硬件契约 |
| OS DTB 与 vendor DTB 产物 | `FdtBlob` / `FdtBlob_compat` | 分离构建、分别记录哈希 |

L2 的首轮工作不是立刻刷入新 DTB，而是先做**只读盘点**：

- 哪些属性和节点被驱动真实消费；
- 哪些只是原厂 ABL/DTBO 匹配所需；
- 哪些由 UEFI 在启动时动态修补；
- 哪些数据是每台设备的校准值，不应进入公共 DTB。

盘点结果先落在
[`samurai-dt-v1-contract.md`](../dts/samurai-dt-v1-contract.md)；
它当前是 v1 草案，完成离线拆分和双内核验证后才算冻结。

2026-11-05 已把这份盘点推进为机器可读契约：
[`samurai-dt-v1-abi.json`](../dts/samurai-dt-v1-abi.json) 绑定了 23 个
资源组、驱动消费者、UAPI 和 `reserved-memory` 规则；
[`check-dtb-contract.py`](../scripts/check-dtb-contract.py) 会拒绝稳定
属性改值、节点删除、未登记新增和实验 compatible 混入。自测中基线与
L3-02 sensor 加法候选通过，实验 profile、vendor DTB 和 UFS 改值样本
被拒绝。详见 [L2 DTB ABI 闸门](L2-DTB-ABI-GATE.md)。它只属于 G1
准入，不替代 G3 运行态。

### 1.2 L3：内核驱动和启动保险

[270 分层审计](../../reference/kernel270/LAYERING-AUDIT.md) 已经给出当前
内核的边界：

- 基线是 Linux v7.3-rc6，之后有 25 个本地提交、125 个文件改动；
- 仍带有 `clk_ignore_unused`、`pd_ignore_unused`、
  `regulator_ignore_unused` 等 bring-up 保险；
- 存在专用 `sensor-power` sysfs 和 C 内电压策略；
- 面板 GPIO6 复位仍有公共 pinctrl 与板级逻辑交叉；
- 板级 ASoC machine driver 本身是正常分层，不应因为带机型名就删除；
- 当前内核不是“换任意 stock mainline 内核即可”的状态。

L3 的首轮工作是把驱动、资源图和调试保险分类，而不是先删除参数：

| 类别 | 处理方式 |
| --- | --- |
| 通用 SoC/子系统修复 | 保持行为，整理到通用驱动/子系统路径 |
| 板级接线和资源 | 进入 DTS 或板级 driver 数据，不写死在通用驱动 |
| 私有 sysfs/调试节点 | 先保留，新增标准接口并迁移消费者后再删 |
| bring-up 参数 | 先保留，最后逐项删除；每项都有冷启动/回退证据 |
| 板级 ASoC machine driver | 保留，只要它使用标准 ASoC 接口 |

L3 的首轮 ownership 表应按以下硬件组建立：

| 驱动组 | 当前入口/证据 | 首轮安全动作 |
| --- | --- | --- |
| 显示/DSI | DRM/KMS、DSI panel、60/90 Hz 补丁、背光 class | 保持现有模式，只整理面板/背光的板级数据；不改桌面选择逻辑 |
| 存储/UFS | UFS LUN、GPT、4 KiB 逻辑扇区 | 只做只读容量/LUN/模块记录，不与 DTB 拆分同时改 |
| 输入/按键 | rmi4 触摸、PM8150 按键、evdev | 保持键值和唤醒属性；先补消费者/设备名清单 |
| USB | DWC3、configfs、CDC NCM | 先消除 `a600000.usb` 等固定名依赖，保持现有 gadget 身份 |
| Wi-Fi/蓝牙 | WCN3990、cfg80211/BlueZ、固件服务 | 先区分标准接口和板级 helper，不先改固件加载顺序 |
| 音频 | ASoC、ALSA UCM、路由 helper | 保留 machine driver；把板级路由和桌面策略分开 |
| 传感器 | SSC/FastRPC、IIO、SensorProxy、`sensor-power` | 先画清 `sensor-power` 的消费者和标准资源替代方案 |
| 充电/电池 | MP2650、BQ28Z610、`power_supply`、服务 | 保持电源策略服务；先统一只读属性，不先改充电状态机 |
| 相机 | CAMSS/CCI、V4L2/media controller、libcamera、校准 | 只整理板级数据和通用驱动边界；不把 ISP/画质工作混入 L2/L4 |
| modem/GNSS | remoteproc、QRTR/QMI、ModemManager/GeoClue | 保持服务启动顺序；先把板级 helper 和标准 UAPI 分开 |

L3-01 的交付物必须至少包含：硬件组、实际驱动/模块、通用 vs 板级、
上游 vs 本地补丁、使用的 UAPI、当前调试开关、回退镜像。没有这张表，
后续“整理驱动”很容易退化成跨层大改。

当前的文件/模块级清单见
[L3 驱动 Ownership 清单](L3-DRIVER-OWNERSHIP.md)。

### 1.3 L4：内核公共 UAPI

L4 只讨论**内核到用户态**的接口。下面有些条目其实是 L5/L6 的配置
债，单独列出是为了避免把它们误当成“内核 ABI”：

| 当前接口/硬编码 | 类型 | 处理方向 |
| --- | --- | --- |
| `/sys/devices/platform/sensor-power/state` | 私有板级 sysfs | 评估转为 `regulator`/`power-domain`/板级标准资源；过渡期保留旧节点 |
| `/sys/class/udc/a600000.usb` | 标准 UDC class，但名字写死 | 通过 `/sys/class/udc` 发现，不把控制器名写死到脚本 |
| `/sys/class/backlight/ae94000.dsi.0` | 标准 backlight class，路径含设备名 | 用 class 目录/属性发现，不把背光设备名当稳定 ABI |
| `DSI-1`、`wayland-1` | L5/L7 的运行环境名 | 从 DRM/session 环境发现，不写死到板级检查脚本 |
| `/usr/local/share/dbus-1/...ModemManager1.service` | L5/L6 发行版策略 | 迁到 init/发行版适配包，不作为通用硬件包内容 |
| `AUTOLOGIN_UID=10000` | L5/L6 用户配置 | 从本地普通账号推导，安装时只写缺失值 |
| `realme,samurai` 检测 | 稳定的 DT compatible | 保留；这是板级识别，不是私有 ioctl |
| `samurai-powerkey`、KWin DPMS | L7 桌面策略 | 留在 Plasma 适配包，不进入板级主包 |

L4 的原则是**先双栈、后迁移、最后删除**。在旧消费者还存在时删除
私有接口，会直接打断当前 rootfs/桌面调试链。

当前消费者和迁移条件见
[L4 公共 UAPI 与硬编码清单](L4-UAPI-INVENTORY.md)。

## 2. 工作包

| ID | 层 | 工作 | 运行时影响 | 闸门 |
| --- | --- | --- | --- | --- |
| L2-01 | L2 | DTB 属性/节点盘点，生成稳定、动态、vendor 三类清单 | 无 | G0/G1 |
| L2-02 | L2 | 先锁定规范 DTS 源，再拆共享 DTSI、OS DTB、vendor/compat DTB，离线构建 | 无 | G1 |
| L2-03 | L2 | 建立 `samurai-dt-v1` 清单（哈希、兼容属性、动态字段） | 无 | G1 |
| L2-04 | L2 | 将候选 DTB 装入 UEFI 并启动；只把 boot 内嵌 DTB 当作当前入口 | 刷 `boot`、重启 | G3 |
| L3-01 | L3 | 建立驱动/资源/调试保险 ownership 表 | 无 | G0/G1 |
| L3-02 | L3 | 行为保持的驱动内聚和板级资源下放 | 仅 kernel Image | G2 |
| L3-03 | L3 | 通过标准子系统暴露新接口，旧接口保留 | 仅 kernel Image | G2/G4 |
| L3-04 | L3 | 逐项删除 bring-up 参数 | 可能影响启动 | G2，最后做 |
| L3-05 | L3 | 保持 `\Image`、PE、内核 release 和模块打包可重复 | 仅 logdump | G2 |
| L4-01 | L4 | UAPI/私有接口/消费者盘点 | 无 | G0/G1 |
| L4-02 | L4 | 加标准接口或兼容别名 | 用户态可继续用旧路径 | G2/G4 |
| L4-03 | L4 | 迁移板级脚本/桌面/检查工具到标准接口 | 可能影响测试与桌面 | G4 |
| L4-04 | L4 | 删除旧 UAPI/旧 helper/旧服务名 | 会打断旧 rootfs | G4 完成后 |
| L4-05 | L4 | 建立标准接口回归矩阵 | 无 | G4 |

### 2.1 依赖关系

- L2-01 独立，可立即开始；
- L2-02 依赖 L2-01、规范 DTS 源和匹配 DTB 身份，但不依赖刷机；
- L2-04 的规范候选依赖 L2-02/L2-03 和一次完整飞轮基线；2026-11-05
  的受限探针是单变量例外，不替代这些依赖；
- L3-01 独立，可立即开始；
- L3-02 依赖 L3-01；
- L3-03 依赖 L3-02，且必须保持旧接口；
- L3-04 依赖 L3-02/L3-03 的冷启动证据；
- L4-01 独立，可立即开始；
- L4-02 依赖 L4-01；
- L4-03 依赖 L4-02 和一个可回退的旧包；
- L4-04 必须最后做，不能和 L2-04 同一次启动。

## 3. 闸门

### G0：基线和可回退性

必须记录：

- UEFI boot image；
- vendor/compat DTB；
- OS-facing DTB；
- `logdump` 镜像；
- kernel Image 与 release；
- 模块 manifest 或模块文件清单；
- rootfs 镜像/摘要；
- GPT 备份；
- 当前启动的 EUD/pstore/NCM 观测结果。

证据是本地哈希和可读回退文件，不是“我记得上次能启动”。

### G1：离线/静态闸门

- DTS 可构建、可反编译；
- 稳定属性、动态字段、vendor 字段分类完成；
- L4 接口和消费者表完成；
- 没有修改运行中的 `boot`/`logdump`；
- 文档和链接检查通过。

### G2：kernel-only 闸门

- 只替换 `logdump` 中的 `Image` 或对应 FAT 镜像；
- `\Image` 路径、PE/MZ、内核 release 和模块匹配；
- EUD/console 和 pstore 仍可用；
- USB NCM/SSH 仍可用；
- 失败可回到上一份 logdump 镜像，不需要刷 `boot`。

L3 的行为变化默认在这里验证。一次只改一个驱动行为或一个资源依赖。

### G3：boot-flash 闸门

- G0/G2 已通过；
- 旧 boot image、GPT 备份和 EDL 路径已验证；
- 只改变 DTB/启动固件相关的一个变量；
- 失败时能直接回到旧 boot image；
- 不在同一轮同时改 ESP、BDS、bootloader 和 DTB。

L2-04 只能在这个闸门执行，并且要有单独的维护窗口。

2026-11-05 已在该闸门执行一次受限探针：先记录 boot/logdump/GPT/Image/
模块基线，确认唯一 fastboot 设备、产品名和 boot 几何，只写 boot，
失败回退文件始终可用。探针没有同时改 GPT、BDS、ESP、logdump 或模块；
重启后约 32 秒恢复 USB NCM/SSH，飞轮继续。

### G4：userspace/desktop 闸门

- 旧包和旧接口仍保留；
- 新标准接口能在当前桌面/rootfs 上工作；
- 至少一个发行版/桌面包完成迁移；
- 有回退包；
- 不依赖固定 UID、固定 Wayland socket 或 `/usr/local` 覆盖。

L4-03/L4-04 只能在这里执行。L4-04 之前，旧接口不能删。

## 4. 基线快照和比较

新增只读工具：

[`flywheel-baseline.py`](../scripts/flywheel-baseline.py)

它只读取本地文件并记录 SHA-256，不访问手机、不刷写、不改变分区。

示例（路径按当前主机实际产物替换）：

```sh
python3 linux-port/scripts/flywheel-baseline.py capture \
  --out out/flywheel-baseline-20261105.json \
  --label rmx1931-current-debug \
  --artifact boot_image=/path/to/uefi-boot.img \
  --artifact compat_dtb=/path/to/FdtBlob_compat/samurai.dtb \
  --artifact os_dtb=/path/to/FdtBlob/samurai/sm8150-realme-samurai.dtb \
  --artifact logdump_image=/path/to/logdump.img \
  --artifact kernel_image=/path/to/Image \
  --artifact modules_manifest=/path/to/modules.manifest \
  --artifact rootfs_image=/path/to/rootfs.img \
  --artifact gpt_backup=/path/to/gpt-before.bin

python3 linux-port/scripts/flywheel-baseline.py check \
  out/flywheel-baseline-20261105.json \
  --artifact boot_image=/path/to/uefi-boot.img \
  --artifact compat_dtb=/path/to/FdtBlob_compat/samurai.dtb \
  --artifact os_dtb=/path/to/FdtBlob/samurai/sm8150-realme-samurai.dtb \
  --artifact logdump_image=/path/to/logdump.img \
  --artifact kernel_image=/path/to/Image \
  --artifact modules_manifest=/path/to/modules.manifest \
  --artifact rootfs_image=/path/to/rootfs.img \
  --artifact gpt_backup=/path/to/gpt-before.bin
```

`check` 只比较哈希、大小和已记录路径，不证明启动成功。它用于回答
“这次部署的 boot/DTB/kernel/rootfs 是否真的还是基线组合”，飞轮证据
仍必须由 EUD、pstore、SSH 和实际功能测试提供。

## 5. 执行顺序

### 第 0 阶段：不改运行态

并行完成：

- L2-01 DTB inventory；
- L3-01 驱动 ownership 表；
- L4-01 UAPI/消费者表；
- G0 基线快照；
- 把当前 kernel/DTB/模块/rootfs 的已知组合写进一份清单。

这一步不需要重启手机，也不应修改 `boot` 或 `logdump`。

### 第 1 阶段：L4 加法和 L3 内聚

- 先增加标准接口/别名，保留旧路径；
- 把板级资源从通用驱动中下放，行为保持不变；
- 用 G2 验证 kernel-only 变化；
- 保持 `\Image`、EUD/pstore、模块目录和 SSH 不变。

### 第 2 阶段：L2 离线拆分

- 生成共享 DTSI、OS DTB、vendor DTB；
- 比较稳定节点和属性，不刷机；
- 生成 `samurai-dt-v1` 清单；
- 先证明“新 DTB 树只少了 vendor/调试字段”，再安排 G3。

### 第 3 阶段：L2 单窗口激活

- 保留旧 boot image 和 EDL；
- 一次只换 DTB/固件的一个变量；
- 启动后先看 EUD/pstore、UFS、显示和 USB；
- 失败立即回退，不继续叠加 L3/L4 删除。

### 第 4 阶段：L4 消费者迁移和 L3 调试保险清理

- 先把板级脚本/桌面/检查工具迁移到标准接口；
- 再考虑删除旧 UAPI；
- L3 的 `clk_ignore_unused` 等按单项删除，每项单独冷启动和回退；
- 不把 L4-04 和 L3-04 放在同一次启动。

## 6. 停止规则

出现下列任一情况，停止追加改动并回到最近基线：

- 进入不了 `\Image`，或内核在 EUD 上没有新的可解释日志；
- pstore 没有生成可读的上一轮崩溃记录；
- UFS/FAT/模块 release 与预期不匹配；
- 桌面/SSH 只能靠手工重启服务恢复；
- 修改了一个接口但找不到它的消费者；
- 同一轮同时改了 DTB、驱动和用户态；
- 只能用“重建后应该会好”解释失败。

回到基线后，保留失败日志，不把“回退成功”写成“改动通过”。

## 7. 验收边界

L2/L3/L4 首轮完成时应当能说清：

- 哪些 DTB 字段是 ABI，哪些是动态/厂商字段；
- 哪些驱动还在使用私有 sysfs 或 bring-up 参数；
- 哪些 UAPI 有旧消费者，删除条件是什么；
- 每个运行时变化属于 G2、G3 还是 G4；
- 当前飞轮的 boot/DTB/kernel/rootfs 组合是否仍与基线一致。

这不等于硬件功能全部通过，也不等于所有发行版/桌面已经无适配。
它只证明分层工作已经开始，且没有把调试飞轮当作重构的试验品。

## 当前进度

| 工作 | 当前状态 | 下一步 |
| --- | --- | --- |
| L2-01 DTB 契约盘点 | v1 草案和机器可读 manifest 已落地：[samurai-dt-v1-contract.md](../dts/samurai-dt-v1-contract.md)、[samurai-dt-v1-abi.json](../dts/samurai-dt-v1-abi.json)；23 个资源组已绑定驱动消费者和 UAPI，含 PM8150L 闪光灯候选 | 继续把每个 manifest 字段映射到实际运行时检查命令；G1 检查器已通过，闪光灯仍需 G3 |
| L2-02 源码拆分 | 规范源已锁定；[共享 DTSI、OS DTS、vendor 对照 DTS](../dts/split-ba61/) 和[实验 DTSI](../dts/experiments/) 均已离线构建；三个板级相机 fragment 已本地化，重建仍为 `f7959f8a...`；实验 profile 重建出 `c582dd7c...` | 把实验 profile 接成独立运行时启动项/固件输入，再做双内核运行态矩阵 |
| L2-03 ABI 清单 | 已绑定规范源、配置、k363 DTB、当前 boot DTB、模块和运行时探针；探测前 24/24、当前 27/27 差异已分类；k270 实际 DTB → 候选为 0 值变化、12 新增节点、3 新增 CCI 属性、3 个 vendor 根属性删除；SKU 静态审计通过（零大小 `/memory` 占位、无容量属性）；机器可读 ABI 闸门已通过基线、L3-02 加法候选并拒绝实验/vendor/改值样本；见 [双内核矩阵](L2-DUAL-KERNEL-MATRIX.md) 和 [ABI 闸门](L2-DTB-ABI-GATE.md) | 用 k270/k363 两个运行态启动确认加法矩阵；再补实际 SKU 启动 |
| L2-04 DTB 激活 | 受限单变量探针已通过；`aa93d14d...` 被拒绝；`3e83798e...` 已通过离线复核，其他 FFS body 逐字节不变；L3-02 sensor-data 变体 `15f9e4d5...` 也通过 metadata review | 先完成 G2 Image，再单独排 G3；补运行态 k270/k363 和 SKU 矩阵 |
| L3-01 驱动 ownership | 文件/模块级清单已落地：[L3-DRIVER-OWNERSHIP.md](L3-DRIVER-OWNERSHIP.md) | 把每组绑定到固定 source-lock、模块哈希和部署状态 |
| L3-02 标准生命周期 | genpd/PAS proxy 方案已在真机 `#9` 否决并回退 `#5`；[补丁 0021](../patches/0021-misc-samurai-sensor-power-rproc-subdev.patch) 改为 `qcom,rproc` + `rproc_subdev`；真机 `#2` 已通过：boot `ad48e343...`、Image `edb15bd6...`、logdump `dd1a3cea...`，块设备回读一致，`start → vdd=1`、`stop → vdd=0`、SSC/SensorProxy readiness 和重启后自动冷启动均通过 | 保持旧 `state` 只读兼容；转入 G3 规范 OS DTB 激活和 k270/k363 运行态矩阵 |
| L4-01 UAPI 盘点 | 消费者清单已落地：[L4-UAPI-INVENTORY.md](L4-UAPI-INVENTORY.md) | 为每个接口补一条实际检查命令和迁移验收证据 |
| L4-02 双栈 | UDC 发现源级测试 14/14 通过（包脚本 + 开发脚本各 7 例）；旧 `a600000.usb` 仍优先兼容 | 继续加标准别名，不改旧 consumers；包构建/安装和运行态验收留到 G4 |
| G0 基线 | 已用真实 boot/DTB/kernel/rootfs/GPT 文件生成并通过 SHA 校验 | 下次切换前重新核对当前运行态身份 |

2026-11-05 的 L2 探针修改了 `boot` 的内嵌 DTB payload，但没有改
`logdump`、Image、模块、GPT、rootfs 或现有 DTS 源；旧 boot 和 GPT
备份仍在。探针成功后 SSH、USB NCM、显示、充电和睡眠抑制服务均恢复，
因此飞轮已回到原路径。规范源锁定、源码级双 DTB 和部署 DTB 差异分类
已完成离线部分；充电、相机 ICP、EUD 和调试参数也已落成独立实验
DTSI，并重建出与 `9736b861...` 语义相同的 profile。下一步是把实验
profile 接成独立运行时启动项/固件输入，再补运行态双内核和 SKU 矩阵。L3/L4
的加法和内聚可以继续；`aa93d14d...` 候选已因 `BdsDxe` 长度变化和
`UiApp` 代码差异被拒绝，不能用它进入 G3。替代候选 `3e83798e...`
已从 `758694a1...` 只替换 DTB payload 重建，并通过
`BdsDxe`/`PlatformSmbiosDxe`/`UiApp` 逐字节相同检查；k270 实际 boot
DTB 到候选的离线语义矩阵也已收敛为纯加法（0 个值变化、12 个新增
相机节点、3 个新增 CCI 属性、3 个 vendor 根属性删除）。下一步是补
k270/k363 两个运行态启动和 SKU 矩阵，再在独立 G3 窗口激活。该候选
会移除当前实验 DTB 的充电/camera/EUD 行为；若需要保留，必须先做单独
的 experiment profile。删除性动作仍须排在单独运行时窗口。
