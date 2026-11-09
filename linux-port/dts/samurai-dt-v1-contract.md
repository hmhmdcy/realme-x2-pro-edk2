# samurai-dt-v1：RMX1931 的 DTB 契约

整理日期：2026-11-06。

这是项目级的 DTB 兼容契约，不是上游 Linux binding，也不是已经通过
全部硬件验收的最终 ABI。2026-11-06 起，Linux v7.3.1 的 OS-facing
基线是 [`v731/sm8150-samurai.dts`](v731/sm8150-samurai.dts)，已在本机
连续两次启动；机器可读源身份见
[`v731/source-lock.json`](v731/source-lock.json)。下面保留的早期
bring-up 与 k363 说明只作为迁移历史；新代码和验收应以 v7.3.1 契约及
[`samurai-dt-v1-abi.json`](samurai-dt-v1-abi.json) 为准。

总说明见 [Linux 七层适配说明](../docs/LINUX-ADAPTATION-LAYERS.md)，工作包
和闸门见 [L2-L4 收敛计划](../docs/LAYER-CONVERGENCE-PLAN.md)。

## 1. 产物边界

### 1.1 当前源身份

仓库中的 [`sm8150-samurai.dts`](sm8150-samurai.dts) 是 487 行的早期
bring-up 快照，只能作为历史。规范输入是
[`reference/kernel276/sm8150-samurai.dts`](../../reference/kernel276/sm8150-samurai.dts)，
1094 行，SHA-256
`428e20b3fe06a8b4ea85617cd2db3da9528e4edb0276647e7c7ed15c3737338b`；
它与 k363 内核构建提交
`ba61a62293e0f6bc5838c06f2e85e033e3d702a8` 中的
`arch/arm64/boot/dts/qcom/sm8150-samurai.dts` 逐字节相同。

机器可读的源身份、仓库快照差异和拆分前顺序见
[`source-lock.json`](source-lock.json)。用 k363 精确配置重建的 DTB 与
`reference/kernel363/boot-candidate-build-validation.json` 完全一致；
源码级拆分见 [`split-ba61/`](split-ba61/)。

项目当前有两个不同用途的 DTB：

| 产物 | 用途 | 不能做什么 |
| --- | --- | --- |
| `FdtBlob/samurai/*.dtb` | OS-facing mainline DTB，由 UEFI 配置表交给 Linux | 不放入原厂 ABL/DTBO 匹配属性；不默认放入生产启动参数 |
| `FdtBlob_compat/samurai.dtb` | 追加到 boot image，供原厂 ABL/DTBO 兼容链使用 | 不直接当作 Linux 的硬件 ABI |

同名或同一份源码构建的两个产物不能互换。拆分前后必须分别记录哈希，
不能只比较文件名。

2026-11-05 实测确认：当前 Linux 使用的 OS-facing DTB 在 `boot` image
内，不是 `logdump` FAT 里的 `samurai.dtb`。只替换 logdump 中的 DTB
并重启时，运行态 `/sys/firmware/fdt` 不变；该副本不能作为当前 DTB
生效性实验的入口。后续必须从 boot image 的固件/DTB 容器提取输入，
或直接校验内嵌 payload。

## 2. 稳定的硬件契约

以下内容在 `samurai-dt-v1` 中视为兼容性敏感项。新增可选属性可以，但
不能悄悄改变已有属性的单位、语义或资源拓扑。

### 2.1 根身份

当前根节点：

```dts
model = "Realme X2 Pro (RMX1931CN)";
compatible = "realme,samurai", "qcom,sm8150";
chassis-type = "handset";
```

规则：

- `realme,samurai` 是板级识别字符串，必须稳定；
- `qcom,sm8150` 是 SoC fallback，必须保留；
- `model` 是描述性字段，不能作为程序分支的唯一依据；
- `chassis-type` 可以保留，但不能替代板级 `compatible`；
- 不应为了版本号新增一个未登记的私有 DT 属性。

### 2.2 设备资源

下列资源属于硬件契约，驱动、UAPI 和用户态服务都依赖其存在或语义：

- 设备节点的 `reg`、`interrupts`、`interrupt-parent`；
- `clocks`、`power-domains`、`resets`；
- `*-supply` regulator 和 GPIO/pinctrl；
- UFS、DSI、触摸、燃料计、音频、USB 等设备的总线和地址；
- `reserved-memory` 中的固件/远程处理器 carveout 及其 `no-map` 属性。

当前源文件中可核对的例子：

| 例子 | 位置 |
| --- | --- |
| BQ28Z610 燃料计 | `i2c15`，DTS 约 358 行 |
| Synaptics RMI4 触摸 | `i2c17`，约 366 行 |
| Samsung `sofef03f-m` 面板 | `mdss_dsi0`，约 435 行 |
| 触摸 VIO 1.8 V 使能 | `vreg_touch_1p8`，约 54-63 行 |
| UFS/PMIC/固件保留区 | `reserved-memory`，约 110 行起 |

这些节点可以增加可选属性，但不能在没有新 `compatible` 或明确迁移方案
的情况下重命名或删除。

USB DWC3 节点使用主线的 `tx-fifo-resize` 布尔属性。它由
`snps,dwc3-common.yaml` 定义、由 DWC3 core 的标准 device-property
路径读取，用于动态分配 TX FIFO；它不改变 `reg`、PHY、角色或 UAPI，
已列入 `allowed_additive_properties`，并通过 4 MiB 双向 NCM 长测。

`sensor-power` 当前使用 `qcom,rproc = <&remoteproc_slpi>`，由板级
sequencer 注册通用 `rproc_subdev`：`prepare` 按 VDD → 10 ms → VDDIO
上电，`unprepare` 反向关断。它不再把 sensor rail 表达成 PAS proxy
power domain，也不由 `state` sysfs 控制电源；`state` 仅保留只读兼容
视图。此前的六个 `realme,vdd-*`/`realme,vddio-*`/`realme,rail-*`
属性属于已被取代的 L3-02-A 实验，不是当前稳定 binding。

### 2.3 `reserved-memory`

`reserved-memory` 必须与设备固件实际 carveout 和 UEFI 内存图一致。
它不是“可选性能参数”：

- 不应由发行版或桌面修改；
- UEFI 修复只能做已验证的动态内存补齐，不能静默改变硬件 carveout；
- 改变任何区域的大小、基址或 `no-map` 属性，都需要新的 DTB 版本和
  冷启动/恢复验证；
- 变量名、区域用途和固件证据应记录在发布清单中。

## 3. 动态字段

以下字段是启动策略或运行时信息，不是稳定的硬件 ABI：

| 字段 | 归属 | 规则 |
| --- | --- | --- |
| `/memory` | UEFI memory map/启动器 | 可以是占位；不能把固定 RAM 大小写进契约 |
| `/chosen/bootargs` | 启动项/调试启动项 | 生产命令行走 LoadOptions 或 loader 配置；不能把 `earlycon`/EUD 当唯一路径 |
| `/chosen/stdout-path` | 启动策略 | 调试控制台选择，不是板级硬件身份 |
| `/chosen/initrd-*` | bootloader/EFI loader | 由启动项和 initramfs 管理 |
| 固件临时修补属性 | UEFI/EFI stub | 必须记录在允许修补的白名单中 |

当前 DTS 的 `chosen/bootargs` 和 `/memory` 占位是 bring-up 现状，不是
最终生产契约。迁移顺序应是：先把命令行放入 LoadOptions/启动项并验证，
再从 OS-facing DTB 删除；不能反过来先删最后一个可用命令行。

## 4. vendor/compat 字段

以下属性只服务于原厂 ABL/DTBO/Android 兼容链：

```dts
qcom,msm-id = <339 0x20000>;
qcom,board-id = <0 0>;
oppo,dtsi_no = <19781>;
```

它们不是 Linux 的板级 ABI，不能作为用户态判断机型的依据。拆分规则：

1. 先构建 vendor/compat DTB，保留这些属性和原厂链需要的兼容字段；
2. 再构建 OS-facing DTB，移除 vendor 属性；
3. 两份 DTB 分别记录 SHA-256 和构建输入；
4. 不能用“同一份源码”作为两份产物相同的理由；
5. 如果原厂链确实需要 `chosen/bootargs`，只保留在 vendor/compat 产物，
   不把它扩大到 OS-facing DTB。

### 4.1 2026-11-05 受限实机探针

本次只验证“vendor 根属性可以从 OS-facing DTB 移走”，不是完整源拆分：

| 项目 | 结果 |
| --- | --- |
| 删除字段 | `qcom,msm-id`、`qcom,board-id`、`oppo,dtsi_no` |
| 候选 DTB | SHA-256 `e3db4fa94ae722f5dac4c363190d7a710621e75c42e3d58c2c3e38da7ba7850a` |
| 候选 boot | SHA-256 `66dbe2348b36a4de68429fc05929920c1c396b335537cc28a17cfbaa7efa23ae` |
| 离线差异 | 只改 DTB payload 及派生的 kernel size/id；BootShim、ramdisk、其他 FV/FFS 不变 |
| 运行态 | 三个 vendor 属性消失；`realme,samurai`、`qcom,sm8150` 和 `chassis-type` 保留 |
| 语义差异 | 反编译前后仅三个根属性；候选与运行态仅 UEFI mmap/table 动态字段 |
| 飞轮 | boot 单次写入；SSH 约 32 秒恢复；logdump、798 项模块清单和 Image 未变 |

本地收据：
`E:\edk2-samurai-out\layer-adaptation-20261105\boot-dtb-inplace\runtime-result.json`。
该探针没有证明规范源码拆分、调试 `bootargs` 删除、双内核兼容或 SKU
矩阵；`samurai-dt-v1` 仍保持草案。

随后完成的离线源拆分给出：

- 共享 DTSI：`sm8150-samurai-common.dtsi`；
- 板级相机 fragment：`imx319.dtsi`、`s5k3m5-samurai.dtsi`、
  `s5kgw1-samurai.dtsi` 已收进 split 目录，不依赖构建机的内核树；
- OS DTS/DTB：只移除三个 vendor 根属性，DTB SHA-256
  `f7959f8a0f8bd3b89dcd67db2f1362b746cc3c4b43f403edbf6fa5347143a3f0`；
- vendor 对照 DTS/DTB：重建结果与规范 DTB
  `dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d`
  逐字节相同。

这不是当前 boot 中正在使用的 DTB。探测前 boot 内嵌 OS DTB 是充电
实验链的 `9736b861...`，必须与规范 k363 DTB 的差异逐项分类后才能冻结。

### 4.2 部署 DTB 差异账本

2026-11-05 已完成只读分类。比较对象是：

- canonical k363 OS DTB：`dcdd74ec...2c8d`；
- 探测前 boot OS DTB：`9736b861...f9352`（充电实验链）；
- 当前 post-probe OS DTB：`e3db4fa9...7850a`（只比探测前少三个 vendor
  根属性）。

归一化 299 个纯 phandle 值变化和 679 个引用属性后，探测前 DTB 的
24 个语义项、当前 DTB 的 27 个语义项均完成分类，0 个未分类：

| 类别 | 探测前项数 | 当前项数 | 结论 |
| --- | ---: | ---: | --- |
| 相机 ICP | 7 | 7 | 可选 overlay，不进入 v1 |
| 充电 / USB input | 12 | 12 | 可选 overlay/固件输入，不进入 v1 |
| USB 控制器 linkage | 1 | 1 | link-only，不构成硬件策略 |
| EUD 调试路由 | 3 | 3 | debug-only，生产 DTB 排除 |
| 调试 / 测试 bootargs | 1 | 1 | 移到 debug 启动项/LoadOptions |
| vendor/compat 根属性 | 0 | 3 | 只留在 vendor DTB |
| **新增公共 ABI** | **0** | **0** | canonical 基线不变 |

账本收据：

- `E:\edk2-samurai-out\layer-adaptation-20261105\source-lock-ba61\deployed-dtb-difference-ledger.json`
（SHA-256 `5170ba9e...93d351`）；
- `E:\edk2-samurai-out\layer-adaptation-20261105\source-lock-ba61\current-os-dtb-difference-ledger.json`
（SHA-256 `0c9026ae...304089c`）。

`9736b861...` 的来源链已拆成三个可解释的阶段：

| 阶段 | 语义变化 |
| --- | --- |
| canonical → `9aa3e6fc...` | 24 个实验项：ICP、EUD route、充电接线、debug bootargs 和 serial/typec 状态 |
| `9aa3e6fc...` → `d7d8a7da...` | 只把 `/soc@0/eud-off-route` 的 `status` 从 `disabled` 改为 `okay` |
| `d7d8a7da...` → `9736b861...` | 只把 connector `op-sink-microwatt` 从 2.5 W 改为 7.5 W，`sink-pdos` 从 `0x04019032` 改为 `0x04019096`（5 V 500 mA → 5 V 1500 mA） |

因此 5V1500 和 EUD route 都可以作为独立策略输入，不需要变成公共
硬件 ABI。

这些策略已落在 [`experiments/`](experiments/) 的独立 DTSI 中。用锁定
k363 源码离线重建得到 `c582dd7c...a64f`（116843 B）；与部署的
`9736b861...` 比较，changed/added/removed 语义属性均为 0，节点差异
为 0。唯一差异是部署端 `/soc@0/eud-off-route` 多一个未消费的 phandle，
属于 linkage-only，不是硬件属性变化。该结果证明源码级语义身份，不证明
字节相同，也不证明已经激活。

独立 profile 也已分别编译并通过账本检查：charging 500 mA 15/15、
charging 5V1500 15/15、camera ICP 10/10、EUD debug 8/8；均无
unclassified。它们仍只是离线构建产物，没有进入启动链。

source-built OS DTB `f7959f8a...a3f0`（调试 `bootargs` 仍在）已装入
离线 boot candidate
`aa93d14d...1c55`。相对 `758694a1...a4acd`，离线检查只改变内嵌
DTB payload；但后续复核发现 `BdsDxe` 长度从 110690 B 变为 114786 B，
`UiApp` 有 312 字节、149 个区间的代码差异，`PlatformSmbiosDxe` 也有
11 字节变化。因此该候选**已拒绝、不得刷入**。下一步必须用
`patch-dtb-boot-in-place.py` 从原 boot 只替换 DTB payload，并证明所有
非 DTB FFS body 逐字节不变。

2026-11-05 后续已完成该重建：从 `758694a1...` 出发，用 EDK2
`LzmaCompress` 的 known-size/no-EndMark LZMA 流只替换 DTB payload，
得到 `3e83798e...`。独立复核确认 `BdsDxe`、`PlatformSmbiosDxe`、
`UiApp` 逐字节相同，除 DTB GUID `25462cda...` 外没有 FFS body 变化，
`non_dtb_ffs_body_changes = 0`，metadata review 通过。该候选仍未刷入；
它会激活 canonical OS DTB，并移除当前 boot 中的充电/camera/EUD 实验项。
如果需要保留这些运行时行为，必须另做 experiment profile，不能把
canonical 激活和实验激活混为一次改动。

相机 ICP userspace、受管高压充电和调试项仍保持独立 profile。标准
V4L2/CAMSS 的四个 RAW sensor 与 CCI/PM8008 接线已进入当前 manifest；
任何新增公共 ABI 仍必须另有驱动消费者、双内核和实机验收证据。

## 5. 兼容性规则

遵循 Linux DT ABI 的加法原则：

1. 新增属性时，旧内核没有该属性时仍保持原行为；
2. 不改变已有属性的单位、范围和资源语义；
3. 不重命名稳定节点；不兼容变化使用新 `compatible` 或新板级文件；
4. 不把校准数据、序列号、MAC 写入公共 DTB；
5. 不把桌面/发行版策略写入 DTB；
6. `samurai-dt-v1` 是发布清单标签，不是未登记的 DT 属性。

发布清单至少应包含：

- OS DTB 和 vendor/compat DTB 的 SHA-256；
- 构建它的 DTS/DTSI 源版本；
- 根 `compatible`；
- 允许动态修补的字段；
- 已验证的 UEFI/内核/模块组合；
- 未验证的 SKU、外设和功能。

### 5.1 机器可读 ABI 闸门

上面的规则已经落成机器可读 manifest：
[`samurai-dt-v1-abi.json`](samurai-dt-v1-abi.json)。它绑定 24 个资源组
（UFS、显示、触摸、音量键、燃料计、充电、振动、音频、sensor-power、
USB、Type-C，以及两个 CCI、CAMSS、PM8150L 闪光灯、四个 sensor、
镜头和两个 PM8008），
列出稳定属性、驱动消费者和 UAPI，并固定
`reserved-memory` 的直接子节点与关键字段。

离线检查器：

```sh
python3 linux-port/scripts/check-dtb-contract.py \
  --manifest linux-port/dts/samurai-dt-v1-abi.json \
  --baseline /path/to/os-dtb-baseline.dtb \
  --candidate /path/to/os-dtb-candidate.dtb \
  --output /path/to/contract-report.json
```

它接受 manifest 明确列出的加法、phandle 重编号和 `/chosen`/`/memory`
动态字段；拒绝删节点、稳定属性改值、未登记的新增，以及 vendor 根属性
或实验 compatible 混入 OS DTB。六个 sensor-power 属性只作为已拒绝的
L3-02-A 历史加法保留，当前目标 binding 使用 `qcom,rproc` 和通用
remoteproc 生命周期。

2026-11-05 的离线自测结果见 [L2 DTB ABI 闸门](../docs/L2-DTB-ABI-GATE.md)：
基线 `f7959f8a...` 和 L3-02 候选 `89604b9c...` 通过；
实验 profile `c582dd7c...`、vendor DTB `dcdd74ec...` 和故意改动
UFS `lanes-per-direction` 的样本均被拒绝。这只是 G1 准入，不是运行态
ABI 冻结。

## 6. 验收矩阵

### 6.1 离线

- [x] `dtc` 能构建 OS DTB 和 vendor 对照 DTB；
- [x] 反编译后根 `model`/`compatible`/`chassis-type` 正确；
- [x] 运行时探针的 OS DTB 不含 `qcom,msm-id`、`qcom,board-id`、
  `oppo,dtsi_no`；源码构建的 OS DTB 也已验证；
- [ ] OS DTB 不含唯一的调试 `bootargs`；
- [x] 源码构建的稳定设备节点/属性与拆分前逐项一致；
- [x] 源码构建的 `reserved-memory` 基址、大小和 `no-map` 未变；
- [x] vendor 对照 DTB 保留三个匹配属性；stock ABL compat DTB 仍是
  独立的 450826 字节固件输入。
- [x] 部署 DTB 与 canonical DTB 的差异已分类，探测前 24/24、当前
  27/27，0 个未分类，0 个新增公共 ABI。
- [x] 独立实验 DTSI 离线重建 DTB `c582dd7c...a64f`，与部署的
  `9736b861...` 语义属性差异为 0，仅有一个未消费 phandle 差异。
- [x] `samurai-dt-v1-abi.json` 的 24 个资源组、24 个保留内存子节点
  和允许加法清单通过离线检查器；已知实验/vendor/改值样本按预期被拒绝。
- [x] PM8150L flash/V4L2 候选 `b244b3f1...` 的语义差异为 controller
  `status=okay`、新增 `led-0` 和 S5KGW1 标准 `flash-leds` 链接；
  `qcom,rproc` 的 phandle 重编号归一化后目标不变；24 资源 contract
  和自测通过；
- [x] boot `5b4dd487...` 与 thin-private FAT `1f4bbb30...` 已由运行中的 Linux
  通过 `/dev/sde11`、`/dev/sde32` 成对写入并回读；没有使用 fastboot；
- [x] 最终 Image `f8d89621...` 删除两个 MAX98937 和一个 AW8697 的
  自定义 `status`；boot `5b4dd487...` 和 DTB `b244b3f1...` 不变；
- [x] 同一 boot 周期内 LED class、`white:flash` 媒体实体、V4L2 flash
  控制、200 mA torch、S5KGW1 开灯 RAW 亮度提升和清理后 faults 0 均通过；
- [x] 两次普通重启后 boot/FAT/DTB/777 模块哈希不变，完整 runtime gate、
  三处 status 删除、标准 ALSA/input/ff、四路 RAW、Wi‑Fi/NCM/SSH 和
  taint 0 通过。
- [ ] 一次 `loginctl` + 直接 sysfs RTC alarm 的 suspend 尝试未恢复设备；
  该结果不计为 suspend/resume 通过，需物理唤醒后用 `rtcwake` 复测。
- [ ] 拔除外部供电后的物理按键冷启动、重复冷启动和闪光灯长时间热升
  仍未验收；普通重启不能替代冷启动。

### 6.2 启动后

- [x] `/proc/device-tree/compatible` 包含 `realme,samurai` 和
  `qcom,sm8150`；
- [x] 本次输入 DTB 与 `/sys/firmware/fdt` 的稳定节点一致，差异只在
  `/memory`、`/chosen` 和已记录的白名单；
- [x] UFS、显示、触摸、USB、音频、传感器、PM8008、CCI、CAMSS 和
  四个 camera sensor 在同一启动周期内绑定；
- [x] 四路 camera 分别产生两张完整、非全零且帧间有变化的私有 RAW；
- [ ] EUD/console 和 pstore 仍可用；
- [x] USB NCM/SSH 仍可用；
- [x] 失败时可回到上一份 boot image/DTB，不依赖重装 rootfs；
  本次回退文件已保留，但尚未触发回刷。

### 6.3 兼容性

- [ ] 同一 OS DTB 能配合同一启动项启动至少两个相邻内核版本；
- [ ] 新增可选属性不会让旧内核改变原有行为；
- [ ] 换发行版或桌面不需要重新生成 DTB；
- [ ] 6/8/12 GiB 和不同 UFS 容量的差异由运行时/固件处理，而不是
      按 SKU 复制多份完整 DTB。

## 7. 当前状态

本文件目前绑定 Linux v7.3.1 单机运行态，但尚未冻结，尚未完成：

- 规范 v7.3.1 源、配置、两段源码补丁和最小 boot 收据已锁定；
  camera 标准路径已进入 DTB 契约，并在最终 camera boot 的三个启动周期
  完成四路 RAW 验收；
- 机器可读 ABI manifest、检查器和自测已落地；`samurai-dt-v1` 当前为
  `flash_led_v4l2_runtime_verified_ordinary_reboot_cold_boot_pending`，
  flash/V4L2 已在真机和普通重启后验收，但仍不能写成多 SKU 或冷启动
  已冻结；
- k270 实际 boot DTB `429db1fa...` 到候选 `f7959f8a...` 的离线语义
  矩阵为 0 个值变化、12 个新增相机节点、3 个新增 CCI 属性、3 个
  vendor 根属性删除；这是加法兼容证据，不是运行态启动证据，详见
  [双内核矩阵](../docs/L2-DUAL-KERNEL-MATRIX.md)；
- 候选 `/memory@80000000` 的 `reg` 是零大小占位，静态审计没有发现
  `userdata` 或容量属性；这只能证明 DTB 没有写死 RAM/存储容量，不能
  替代 6/8/12 GiB、64/128/256 GB 的实际启动；
- L3-02 的旧候选取代链已退出当前部署；最终 sensor-power 生命周期为
  通用 remoteproc prepare/unprepare subdevice；
- 生产 DTS wrapper 删除调试 `bootargs`；当前 UEFI LoadOptions 只保留
  经逐项删除实验后的 `console=tty0 loglevel=4 panic=15 clk_ignore_unused`；
- `samurai-dt-v1` 已绑定最终 v7.3.1 Image、DTB、modules、BDS 和候选
  boot 产物 SHA-256；
- 离线 k270/k363 DTB 语义矩阵已完成，但两个内核都尚未用候选 DTB
  实际启动；同型号多 SKU 的启动矩阵也尚未完成。

在断电冷启动、k270/k363 运行态启动、SKU 矩阵以及 G3 实装完成之前，
不应把本契约标记为“已冻结”。最终 boot 的三次启动和四路 camera RAW
通过不替代这些矩阵。
