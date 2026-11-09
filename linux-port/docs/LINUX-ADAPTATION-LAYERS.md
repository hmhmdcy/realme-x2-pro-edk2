# 从“能启动”到“可安装平台”：RMX1931 的 Linux 七层适配、标准 ESP 与 DTB ABI

整理日期：2026-11-05。

适用范围：realme X2 Pro（RMX1931 / RMX1931CN），代号 **samurai**，高通
SM8150-AC。本文讨论的是工程分层和迁移方向，不是某一次部署的验收收据；
当前功能、部署组合、回退依据仍以
[硬件状态](HARDWARE-STATUS.md) 和 [当前检查点](../../NEXT-SESSION.md) 为准。

## 0. 结论

把手机做成“像 PC 或电视盒子”的设备，不是把手机里的每个器件都变成
PCIe 设备，而是把板级差异收敛到少数稳定层，让上层只依赖公共接口：

1. **硬件适配可以分成七层**：引导固件、硬件描述、内核驱动、内核公共
   UAPI、板级用户态、发行版集成、桌面策略。换桌面时只应改最后一层；
   换发行版时主要改板级用户态和发行版集成，不应重做 DTB 或驱动。
2. **`logdump` 可以变成标准 ESP，但不需要重新分区、移动或调整大小**。
   需要改的是 GPT 分区项的类型 GUID，以及其上的启动文件布局；当前
   64 MiB、4 KiB 逻辑扇区的 FAT16 内容可以保留。改 GPT 元数据仍有
   启动风险，必须备份 GPT 和分区内容，并保留 9008/EDL 救援路径。
3. **DTB 固定成固件 ABI 的关键不是冻结整棵二进制树**，而是冻结根
   `compatible`、稳定的设备节点/属性、`reserved-memory` 等硬件契约；
   `/memory`、`/chosen` 和启动参数属于启动时动态信息。把 ABL 使用的
   `qcom,msm-id`、`qcom,board-id`、`oppo,dtsi_no` 和调试 `bootargs`
   从面向上层的 DTB 中拆出去，放进单独的 vendor/compat DTB。
4. **同型号最小改动路线**是：一份 UEFI/引导 bundle + 一份稳定的
   DTB + 按需生成的发行版 rootfs。内存和 UFS 容量不得写死在 DTB 或
   固定大小的 rootfs 镜像中；当前按 119,033,245,696 字节
   `userdata` 制作的镜像不能直接当作所有 X2 Pro 的通用安装镜像。
5. **板级包和桌面包必须分开**。`samurai-platform` 现在同时包含
   OpenRC、硬件服务、USB、音频 UCM 等内容；Plasma 的电源键桥接、
   KWin/KScreen 策略属于桌面层。先拆包，再谈“换桌面不用适配”。
6. **现状距离目标还有明确缺口**：当前上游 Linux 没有 `samurai` 板级
   DTS，当前 pmaports 主线没有 samurai 设备包；UEFI 变量仍不是持久
   存储；当前 BDS 扫描任意 FAT 的 `\Image`，不是标准 ESP 启动；
   rootfs 仍有固定容量镜像。这些是工程工作，不应被“UEFI 能启动”
   这一条掩盖。
7. **2026-11-05 已完成一次受限的 L2 运行时探针**：从当前 OS-facing
   DTB 只移除 `qcom,msm-id`、`qcom,board-id`、`oppo,dtsi_no`
   三个根属性，原位替换 `boot` image 内嵌 DTB 后成功启动。该实验证明
   “先拆 vendor 身份、保留硬件契约”可以在一次单变量切换内完成。
   随后又锁定 k363 规范 DTS，并完成共享 DTSI、OS DTS 和 vendor 对照
   DTS 的离线构建；vendor DTB 与 k363 原始构建逐字节相同。随后完成
   了部署 DTB 的只读差异账本：24 个探测前语义项和 27 个当前语义项
   全部有分类，0 个被提升为新的公共 ABI。当前仍未完成的是把实验项
   迁成独立 overlay、把源码构建的 OS DTB 装入固件，以及双内核/SKU
   矩阵，因此不等于 `samurai-dt-v1` 已冻结。

## 1. 手机为什么不像 PC

PC 的硬件通常通过 PCIe、USB、ACPI、UEFI 等可枚举接口被发现。操作系统
可以只依赖这些公共接口，不必知道主板上的每一根 GPIO、每一路 regulator
和每一个时钟。

手机不是这样：

- SoC 内部有大量非可枚举的控制器，板级连接分散在 I2C、SPI、GPIO、
  SPMI、clock、regulator、IOMMU、remoteproc 和保留内存中；
- 启动链由 XBL/ABL、签名固件和 Android boot image 约束；
- 显示、触摸、摄像头、传感器、充电、modem/DSP 的校准和固件常常是
  机型或批次相关；
- 许多外设没有“插上就被发现”的机制，必须由设备树准确描述。

所以“手机适配 Linux”不是把 Linux 移植到手机上，而是为一块嵌入式板卡
补齐**硬件描述、驱动、标准用户态入口和发行版集成**。UEFI 只统一了
启动交接，不会自动补齐驱动，也不会自动让摄像头或 modem 工作。

“同型号轻松安装”和“换发行版/桌面无需额外适配”是同一件事的两面：
把机型差异限制在低层，把上层依赖限制在稳定接口。

## 2. 七层模型

这不是 Linux 官方规定的层数，而是本项目采用的工程划分。它可以用来判断
“某个改动应该放在哪里”，也可以用来解释为什么换桌面不应该重刷固件。

| 层 | 解决的问题 | RMX1931 的对应物 | 不应放在这里 |
| --- | --- | --- | --- |
| **L1 引导固件** | 从上电到把控制权交给操作系统；提供 DTB、命令行、内存图和启动设备 | XBL/ABL、BootShim、EDK2/UEFI、BDS、EFI 启动项、ESP | 桌面配置、发行版包管理器 |
| **L2 硬件描述** | 告诉内核板上有哪些器件、如何连接、哪些内存不能碰 | `sm8150-samurai.dts`、DTB、`reserved-memory`、regulator/GPIO/pinctrl | 用户选择、桌面策略、可变启动参数 |
| **L3 内核驱动** | 让具体控制器工作，并接入 Linux 子系统 | UFS、MDSS/DSI、DWC3、WCN3990、SPMI/PMIC、GPIO、I2C、CAMSS、音频、充电驱动 | 某个 compositor 的配置 |
| **L4 内核公共 UAPI** | 给用户态稳定、可替换的接口 | DRM/KMS、evdev、ALSA/PCM、V4L2、IIO、power_supply、cfg80211、rfkill、tty、configfs | 私有 ioctl、某个桌面专用的设备节点 |
| **L5 板级用户态** | 把公共 UAPI 组织成这台机器可用的服务 | udev 规则、ALSA UCM、firmware 文件、NetworkManager/ModemManager 配置、USB gadget、传感器/振动/充电辅助服务 | KWin/PowerDevil 策略、Phosh/Phoc 配置 |
| **L6 发行版集成** | 让一个发行版能安装、启动、升级和回退 | APK/DEB/RPM 包、init 脚本或 systemd unit、initramfs、安装器、启动项更新 | 板级寄存器、桌面快捷键 |
| **L7 桌面与会话** | 把标准接口映射成具体的桌面体验 | Plasma/Phosh/GNOME/Sway、KWin/KScreen、portal、锁屏、亮度与电源键策略 | 通用 udev 规则、内核 workaround |

从下到上的依赖关系应当是：

```text
L7  桌面 / 应用
       ↑ 只用标准协议和公共 D-Bus/文件接口
L6  发行版：包、init、安装、升级
       ↑ 消费板级包和内核包
L5  板级用户态：firmware、udev、UCM、服务
       ↑ 只用 L4 的公共接口
L4  内核公共 UAPI
       ↑ 由驱动实现
L3  内核驱动
       ↑ 由 DTB/ACPI 描述硬件
L2  硬件描述：DTB、reserved-memory、资源图
       ↑ 由固件交给内核
L1  引导固件：ABL、BootShim、UEFI、ESP
       ↑
      SoC / 板卡
```

### 2.1 判断改动属于哪一层

| 改动 | 应该主要改哪里 | 说明 |
| --- | --- | --- |
| 换 Plasma、Phosh、GNOME 或 Sway | L7，必要时加 L5 的通用服务 | 不应改 UEFI、DTB 或内核驱动 |
| 换 Alpine/Nura、Debian、Arch 等发行版 | L5 的打包和 L6 的 init/安装适配 | 硬件公共接口应保持不变 |
| 升级内核 | L3/L5，配合 L2 的兼容性验证 | 新内核应能启动旧 DTB；不能反过来假设旧内核支持新属性 |
| 增加一个可选传感器属性 | L2，加 L3 的驱动识别 | 新属性缺失时旧内核应保持原行为 |
| 修正面板时序 | L2/L3；L7 只选择已上报的模式 | 不要在桌面里写私有寄存器 |
| 修正电源键短按行为 | 先判断是内核 input 问题还是桌面策略；通常 L7 | 当前 Plasma 的电源键桥接就是 L7 的临时策略 |
| 支持 6/8/12 GiB 内存 SKU | L1 的内存图 + L5 的运行时识别 | 不要把 RAM 大小写死到 DTB |
| 支持 64/128/256 GB 存储 SKU | L1/L5 的容量发现；L6 安装器 | 不要用固定 `userdata` 大小的 rootfs 镜像冒充通用镜像 |

### 2.2 两条边界规则

1. **上层不能反向依赖下层实现细节。** 桌面不应读取板级脚本的私有
   状态文件，发行版不应依赖某个内核私有 ioctl，板级包也不应知道当前
   用户是谁。
2. **机型差异尽量下沉，策略差异尽量上浮。** 面板时序、GPIO、供电、
   reserved-memory 属于 L2/L3；是否自动旋转、电源键是关屏还是关机，
   属于 L7。

## 3. 本机资料：公开规格、上游状态和项目证据

### 3.1 硬件规格（公开资料 + 项目补充）

下表把公开资料和本机记录放在一起；带“项目资料”的条目不是厂商规格页
的承诺。任何条目都不等于本项目已经逐项验证。具体批次、地区和售后
换件可能不同，最终以设备实际枚举和原厂资料为准。

| 项目 | 公开规格 | 对本项目的意义 |
| --- | --- | --- |
| 型号 / 代号 | realme X2 Pro，RMX1931 / RMX1931CN；代号 **samurai**（项目/原厂资料） | 设备树根节点应使用稳定的 `realme,samurai` compatible |
| SoC | Qualcomm SM8150-AC Snapdragon 855+，7 nm；1×2.96 GHz + 3×2.42 GHz + 4×1.8 GHz Kryo 485，Adreno 640（AC 后缀来自项目资料） | SM8150 公共 SoC 支持不等同于 samurai 板级支持 |
| PMIC | PM8150 / PM8150L / PM8150B（项目资料） | 供电、GPIO、RTC、按键和充电链路的板级描述来源 |
| RAM | LPDDR4X，6/8/12 GB 版本 | 内存容量应由固件/运行时识别，不应按 SKU 各写一份 DTB |
| 存储 | 64 GB UFS 2.1；128/256 GB UFS 3.0；无 microSD | UFS 代际按 SKU 不同；驱动器通常自动协商，但必须逐 SKU 验证 |
| 屏幕 | 6.5 英寸 Super AMOLED，1080×2400，90 Hz，峰值 1000 nit | 60/90 Hz 是面板能力，桌面只选择 DRM 已上报的模式 |
| 电池 / 充电 | 等效 4000 mAh；50 W SuperVOOC（10 V / 5 A） | 充电策略、温度和电流限制属于 L3/L5，不应由桌面猜测 |
| 后摄 | 64 MP GW1 主摄 + 13 MP 长焦 + 8 MP 115° 广角 + 2 MP 景深 | 相机涉及 sensor、CSI、CAMSS、ISP、libcamera 和校准，不能只看 DTB |
| 前摄 | 16 MP | 与后摄分开验收 |
| 接口 | USB Type-C、3.5 mm 耳机；公开规格页只写 Type-C，GSMArena 标注 USB 2.0 | 不要把 SoC 支持的更高 USB 速率当成整机 USB 版本 |
| 无线 | Wi-Fi 5（802.11ac）、Bluetooth 5、NFC；GPS/北斗/Galileo 双频 | 无线/定位需要固件、MAC 地址、校准和标准用户态服务 |
| 传感器 | 屏下指纹、光线、距离、磁力、陀螺仪、加速度 | 指纹和部分传感器不是“DTB 一写就有” |

主要公开来源：

- [realme X2 Pro 官方欧盟规格页](https://www.realme.com/eu/realme-x2-pro/specs)：
  其中明确列出 `RAM 6GB/8GB/12GB`、`UFS 2.1 ROM 64GB`、
  `UFS 3.0 ROM 128GB/256GB`、6.5 英寸 1080×2400 90 Hz、4000 mAh、
  50 W 和四摄组合。
- [GSMArena X2 Pro 页面](https://www.gsmarena.com/realme_x2_pro-9904.php)：
  交叉核对 6.5 英寸 1080×2400 90 Hz、4000 mAh、50 W、四摄，以及
  **USB Type-C 2.0**。

> 重要修正：项目 README 原来把存储笼统写成“UFS 3.0”。64 GB SKU 是
> UFS 2.1，128/256 GB SKU 是 UFS 3.0；不能用一个容量/速度结论覆盖所有
> 同型号手机。

### 3.2 2026-11-05 的上游与发行版状态

| 范围 | 本次核对结果 | 能说明什么 |
| --- | --- | --- |
| Linux SoC 支持 | `torvalds/linux` master（核对提交 `05441d697f7f`，2026-11-03）已有 `sm8150.dtsi`，以及 HDK、MTP、Surface Duo、Sony Kumano 等 SM8150 板级文件 | SM8150 的公共 SoC 基础存在，但 samurai 不是上游板级设备 |
| Linux 板级支持 | 当前 `Documentation/devicetree/bindings/arm/qcom.yaml` 和 `arch/arm64/boot/dts/qcom/` 没有 `realme,samurai` / `sm8150-samurai.dts` | 当前项目的 samurai DTS 是项目维护的 out-of-tree 支持 |
| postmarketOS 包 | 当前 pmaports `main`（提交 `31482d7d5233`，2026-11-04）没有 samurai/RMX1931 设备目录；搜索到的 realme 条目不是本机 | 不能声称“官方 pmOS 直接安装”；项目 rootfs 和安装链仍需自维护 |
| 项目内核 | [270 分层审计](../../reference/kernel270/LAYERING-AUDIT.md) 记录其基线为 Linux v7.3-rc6 后有 25 个提交、125 个文件改动 | “基于主线”不等于“可换任意主线内核”；驱动和修复仍需随内核维护 |
| UEFI | 能启动、枚举 UFS、显示 framebuffer 文本；按键和部分设备仍有缺口 | UEFI 已经解决了引导入口，不自动解决 Linux 驱动完整性 |
| UEFI 变量 | 当前没有持久变量存储；启动项不能假设跨重启保留 | PC 式 Boot Manager 需要持久变量，或者必须依赖可移动介质回退路径 |
| rootfs | [当前 F2FS 方案](ROOTFS-F2FS-IMAGE.md) 使用固定 `userdata` 容量镜像 | 只适用于一个已验证容量，不是所有同型号手机的通用安装介质 |
| 软件包 | `samurai-platform` 仍混合 OpenRC、硬件服务、USB、音频等；Plasma 电源键在 `samurai-desktop` | 换桌面/发行版仍可能碰到板级包边界问题 |

上游源码核对入口：

- [Linux qcom binding](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/devicetree/bindings/arm/qcom.yaml?h=master)
- [Linux qcom DTS 目录](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/boot/dts/qcom?h=master)
- [Linux SM8150 SoC DTSI](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/boot/dts/qcom/sm8150.dtsi?h=master)
- [当前 pmaports 仓库](https://gitlab.postmarketos.org/postmarketOS/pmaports)

这里的“没有”只针对本次核对的提交和路径；不能据此否定私人 fork、尚未
合并的补丁或其它镜像，也不能据此宣称某个功能一定不可用。

### 3.3 项目内部证据

本机细节以这些文件为准，不应从公开规格反推：

- [samurai DTS](../dts/sm8150-samurai.dts)：根节点 `compatible`、vendor
  匹配属性、`chosen/bootargs`、`reserved-memory` 和已接入的外设；
- [20-linux-boot.md](20-linux-boot.md)：`logdump` 的当前使用方式、
  FAT16、4 KiB 逻辑扇区和 BDS 扫描 `\Image` 的历史；
- [19-loadoptions.md](19-loadoptions.md)：EFI LoadOptions 是 UTF-16，
  非空命令行会覆盖 `/chosen/bootargs`；
- [EDK2-KERNEL-EMBED.md](EDK2-KERNEL-EMBED.md)：`DtPlatformDxe` 通过
  EFI 配置表发布固件 DTB 的路径；
- [HARDWARE-STATUS.md](HARDWARE-STATUS.md)：已经证明的能力和明确的
  未验收项；
- [DESKTOP-PORTABILITY.md](DESKTOP-PORTABILITY.md) 与
  [PLASMA-MOBILE.md](PLASMA-MOBILE.md)：板级接口和 Plasma 适配的边界；
- [ROOTFS-F2FS-IMAGE.md](ROOTFS-F2FS-IMAGE.md)：固定容量 rootfs 镜像
  的历史和限制；
- [samurai-platform APKBUILD](../packages/samurai-platform/APKBUILD) 与
  [samurai-desktop APKBUILD](../packages/samurai-desktop/APKBUILD)：当前
  包边界还没有完成目标分层。

状态标签建议在后续文档中统一使用：

| 标签 | 含义 |
| --- | --- |
| **公开规格** | 厂商或独立公开规格页可以确认，未在本机逐项复测 |
| **上游** | 当前上游 Linux/pmaports/UEFI 源树中存在 |
| **项目实现** | 项目源码或固件中已有实现，但未必在本次启动中部署 |
| **实机验证** | 有本机启动、日志或用户反馈作为证据，且范围有限定 |

## 4. 当前启动链和目标启动链

### 4.1 当前链

当前不是“ABL 直接读 ESP”：

```text
上电
  → XBL/ABL
  → boot 分区的 Android boot image
       = BootShim + EDK2/UEFI FD + 追加的 vendor/compat DTB
  → BootShim 把 UEFI FD 搬到运行地址并跳转
  → UEFI DtPlatformDxe 把 mainline DTB 放进 EFI 配置表
  → BDS 扫描 FAT，找到 \Image，校验 PE/MZ，注册并直接启动
  → Linux EFI stub 取得 DTB 和 LoadOptions
  → kernel + initramfs → rootfs
```

当前实现的几个事实：

- ABL 不支持 `fastboot boot`，UEFI/boot image 必须写入 `boot` 分区；
- 引导镜像布局不能随意改：BootShim、gzip 的 UEFI FD 和追加的
  compat DTB 都有历史验证约束；
- Linux 内核现在放在 `logdump` 的 FAT 中，而不是 ESP；
- BDS 会扫描所有 FAT，并把根目录的 `\Image` 当成内核。它还会检查
  `MZ`/PE 头，避免把错误分区当成内核；
- UEFI 配置表提供 mainline DTB，`/chosen/bootargs` 和 LoadOptions
  同时存在；EFI 命令行非空时会覆盖 DTB 的 bootargs；
- `/memory` 不是唯一的内存来源：UEFI 启动时 Linux 会结合 EFI memory
  map，设备树的 `/memory` 可以保留占位；
- 当前没有持久 UEFI 变量存储，BDS 的启动项不能假设跨重启保留。
- 当前 Linux 实际使用的 OS DTB 来自 `boot` image 内的固件 DTB，
  不是 `logdump` FAT 里的 `samurai.dtb`。2026-11-05 已实测：只替换
  `logdump\samurai.dtb` 并重启，运行态 `/sys/firmware/fdt` 不变；
  因此后续 DTB 生效性测试必须检查并更新 boot 内嵌 DTB。

### 4.2 目标链

目标是让 ABL 仍然只负责启动 UEFI，而 UEFI 之后走标准的 EFI 启动约定：

```text
上电
  → XBL/ABL
  → boot 分区中的 UEFI（仍由项目写入一次）
  → UEFI 识别 GPT 类型为 ESP 的分区
  → 有持久启动项时按启动项启动
     没有时由固件尝试 \EFI\BOOT\BOOTAA64.EFI 回退路径
  → EFI loader / Linux EFI stub
  → kernel + initrd + 启动命令行（由启动项或 loader 配置提供）
  → rootfs（userdata 或专用分区）
```

注意：

- **ESP 不会取代 ABL。** ABL 仍然需要 `boot` 分区中的 UEFI；ESP 是
  UEFI 之后的操作系统启动介质。
- **ESP 类型改变本身不会让当前 BDS 自动变成标准启动器。** 当前 BDS
  仍可能继续扫描 `\Image`；必须另外修改 BDS 或在 ESP 中放一个标准
  EFI loader。
- **持久 UEFI 变量是 PC 式启动体验的必要条件之一。** 没有它，可以
  让固件显式扫描 `\EFI\BOOT\BOOTAA64.EFI`，但不能假设用户创建的
  启动项在重启后还存在。UEFI 规范里的 removable-media 回退路径不能
  直接证明“固定磁盘 ESP 一定会被自动尝试”，这必须由本机固件实现并
  实机验证。

### 4.3 建议保留的兼容路径

迁移期间不要删除当前可以启动的路径。建议同时保留：

1. 当前 `\Image` 直接启动路径，作为救援/回归入口；
2. 标准 ESP 的 `\EFI\BOOT\BOOTAA64.EFI` 回退路径；
3. 一个明确标注为“debug”的启动项，保留 `earlycon`/EUD 和详细日志；
4. 一个不含调试参数的 production 启动项；
5. 从 `boot` 分区回退到原厂 boot image 的流程。

## 5. 把 `logdump` 变成标准 ESP

### 5.1 先给出直接答案

**要把 `logdump` 变成标准 ESP，需要改 GPT 的分区类型 GUID，但不需要
重新划分分区、移动起始 LBA、改变大小或重新格式化已有 FAT。**

当前 `logdump` 在本机记录中的形式是：

| 属性 | 当前值 |
| --- | --- |
| 分区名 | `logdump` |
| 索引 | 32（只适用于当前记录的分区表，不能硬编码到别的机器） |
| 大小 | 64 MiB |
| 逻辑扇区 | 4096 字节 |
| 文件系统 | FAT16 |
| 当前类型 GUID | `5AF80809-AABB-4943-9168-CDFC38742598` |
| 标准 ESP 类型 GUID | `C12A7328-F81F-11D2-BA4B-00A0C93EC93B` |

UEFI 的 GPT 规范把 `C12A7328-F81F-11D2-BA4B-00A0C93EC93B` 定义为
EFI System Partition，见
[UEFI 2.10 GPT 章节](https://uefi.org/specs/UEFI/2.10/05_GUID_Partition_Table_Format.html)。
分区名只是标签，不是类型；`logdump` 这个名字可以暂时保留，也可以后续
改成 8.3 友好的名字，但改名不是成为 ESP 的必要条件。

### 5.2 哪些操作必须做，哪些不必做

| 操作 | 是否必须 | 是否改变分区布局/数据 |
| --- | --- | --- |
| 把 GPT 类型 GUID 改成 ESP GUID | **必须** | 只改 GPT 元数据，不改起始/大小 |
| 保留或重新制作 FAT 文件系统 | 当前已有 FAT16，**通常不必重做** | 重做会清空内容 |
| 放入 `\EFI\BOOT\BOOTAA64.EFI` 或建立持久启动项 | **必须**，否则只有“类型是 ESP”没有标准启动内容 | 只增加文件/启动项 |
| 把分区移动到新的 LBA | 不必 | 重分区风险高 |
| 扩大/缩小 64 MiB 分区 | 不是最小改动；空间不足时另行规划 | 涉及相邻分区和数据，风险高 |
| 重新格式化整个分区 | 不必 | 会清空当前内核/DTB/救援文件 |
| 修改分区唯一 GUID | 不必 | 可能影响现有引用，除非有明确迁移方案 |

所以“改类型 GUID”是比“重新分区”小得多的操作，但它仍然是**修改启动
相关元数据**，不是零风险操作：

- 写入 GPT 时掉电、写坏主/备份 GPT、选错磁盘/分区号，都可能让设备
  无法按原方式启动；
- 某些固件/工具可能按分区名、类型或缓存枚举，改完后要重新验证；
- 当前 `fastboot flash logdump` 走的是分区名，类型改变后是否仍能按原
  alias 写入，必须实机验证，不能凭规范推断；
- 如果以后恢复原厂 GPT，原厂刷机包可能重新写 GPT，届时会覆盖这个
  类型字段。

### 5.3 FAT16、4 KiB 和 64 MiB 的限制

UEFI 2.10 的媒体访问章节要求固件支持 FAT32、FAT16 和 FAT12 变体，
具体使用哪一种由介质大小决定，见
[UEFI 2.10 Media Access](https://uefi.org/specs/UEFI/2.10/13_Protocols_Media_Access.html)。
因此“类型 GUID + FAT16”在规范上不等于无效 ESP；真正的限制是目标
固件和发行版安装工具是否都接受这种组合。

本项目要特别注意：

- 这台机器的 UFS 逻辑扇区是 4096 字节；不要用默认 512 字节假设的
  工具去计算 LBA；
- 64 MiB 对“一个内核 + 一个 initramfs + 一个 DTB”可能够用，但对
  多个内核、完整发行版 `/boot`、大型 initramfs 或 UKI 往往太小；
- FAT32 在 64 MiB、4 KiB 逻辑扇区下可能受到簇数下限限制，不能
  想当然地把 `mkfs.vfat -F 32` 当成更标准；
- 如果以后要 PC 式多内核/多发行版启动，更合理的方案是使用更大的
  ESP，或把 `/boot` 放在 rootfs 上，只让 ESP 承载 loader/DTB。
  扩大 ESP 属于另一个分区规划任务，不应混在“最小 ESP 转换”里。

### 5.4 推荐的安全步骤

以下命令是模板，不是可以照抄的设备操作。先把 `$DISK`、`$PARTNUM`、
`$BACKUP` 解析成当前设备的真实值；不要假设它一定是分区 32。

```sh
# 0. 记录当前设备、GPT 和分区内容；确认电池、USB 和救援路径
lsblk -o NAME,PATH,SIZE,LOG-SEC,PARTTYPE,PARTLABEL,FSTYPE
sgdisk --print "$DISK"

# 1. 保存 GPT（主表和备份表）和 logdump 内容
sgdisk --backup="$BACKUP/gpt-before.bin" "$DISK"
dd if=/dev/block/by-name/logdump of="$BACKUP/logdump-before.img" \
  bs=4M status=progress
sync

# 2. 只改类型 GUID；PARTNUM 必须从第 0 步读出
sgdisk --typecode="${PARTNUM}:C12A7328-F81F-11D2-BA4B-00A0C93EC93B" "$DISK"
sgdisk --verify "$DISK"

# 3. 让内核重新读取分区表；若分区仍被挂载，先卸载或重启
partx -u "$DISK"
blkid -p /dev/block/by-name/logdump
```

操作前还要确认：

- `logdump` 没有正在被 Android 或 Linux 挂载；
- 没有把 `/dev/block/by-name/logdump`（分区）误当成 `$DISK`（整块
  UFS 逻辑单元）；
- `sgdisk` 看到的逻辑扇区大小是 4096，而不是 512；
- 有 9008/EDL 或原厂 boot 镜像回退路径，而不仅是“能进 fastboot”。

改完后依次验证：

1. `sgdisk --print` 中类型 GUID 已是 `C12A...`，起始/结束 LBA 未变；
2. `blkid` 仍能识别 FAT；
3. 当前 BDS 的旧启动路径仍能启动一次；
4. `fastboot flash logdump` 或等价救援写入路径仍可用；
5. 在改 BDS/启动文件前，不要先格式化或清空内容。

### 5.5 变成 ESP 之后还差什么

只改类型 GUID 的产物是“类型正确的 ESP”，还不是“PC 式启动链”。至少还要：

1. 在 ESP 中放入一个 AArch64 EFI 应用，通常使用回退路径
   `\EFI\BOOT\BOOTAA64.EFI`；
2. 或者建立持久 UEFI 启动项，让固件直接启动该应用；
3. 让 BDS 按 ESP 类型/路径查找，而不是继续扫描任意 FAT 的
   `\Image`；
4. 让启动项携带 UTF-16 命令行，或由 EFI loader 读取自己的配置文件；
5. 妥善处理没有持久 UEFI 变量的情况，保留回退路径；
6. 让内核、initramfs、DTB 和 rootfs 的更新不再要求重刷 `boot` 分区。

第 3、5 项目前是固件工作，不是分区操作。`\EFI\BOOT\BOOTAA64.EFI`
的回退文件名来自 UEFI 启动管理器规范，见
[UEFI 2.10 Boot Manager](https://uefi.org/specs/UEFI/2.10/03_Boot_Manager.html)。
固定磁盘是否在没有 NVRAM 启动项时自动尝试这个路径，仍取决于固件
策略；本项目需要在自己的 BDS 中明确实现，而不能只改分区类型。

## 6. 把 DTB 固定成固件 ABI

### 6.1 先区分两种“ABI”

DTB 涉及两层兼容性：

1. **Linux 的 DT binding ABI**：设备树属性、节点和驱动匹配规则。
   新内核应当能启动旧设备树；增加可选属性不能让旧属性改变含义；
   真正不兼容的变化要换 `compatible`，见
   [Linux DT ABI 文档](https://docs.kernel.org/devicetree/bindings/ABI.html)。
2. **项目自己的平台契约**：本项目的 UEFI 固定发布哪一棵 DTB、哪些
   字段允许固件在启动时修补、哪些字段由启动项提供、版本如何记录。

UEFI 配置表只是把 DTB 交给内核的通道，不是 ABI 本身。所谓
`samurai-dt-v1` 应该是项目发布的兼容性标签/清单，不是随便发明一个
内核不认识的 DT 属性。

### 6.2 当前 DTB 中混在一起的内容

当前 [samurai DTS](../dts/sm8150-samurai.dts) 同时包含：

> 注意：这个仓库文件是早期 bring-up 快照，不是当前内核树的完整源。
> 它与规范
> [kernel276 DTS](../../reference/kernel276/sm8150-samurai.dts) 相差 607 行，
> 只能用于历史对照。规范源、构建配置和源码级拆分已经记录在
> [DTB 源锁](../dts/source-lock.json) 与
> [`split-ba61`](../dts/split-ba61/)；不要再把本文件当作部署输入。

2026-11-05 已锁定 k363 提交 `ba61a622...` 的板级 DTS，并用
`Image363-extracted.config` 重建出与构建记录相同的 DTB
`dcdd74ec...`。源码级拆分目录为
[`split-ba61`](../dts/split-ba61/)：vendor 对照 DTB 逐字节复用规范
DTB，OS DTB 只少三个 vendor 根属性。运行时探针则另外验证了 boot
内嵌 DTB 的实际入口；当前 boot 的输入仍是充电实验 DTB `9736b861...`，
因此在 v1 冻结前必须把这些实验差异迁出稳定 OS 描述。

- 面向上游的根身份：

  ```dts
  model = "Realme X2 Pro (RMX1931CN)";
  compatible = "realme,samurai", "qcom,sm8150";
  chassis-type = "handset";
  ```

- 只有原厂 ABL/DTBO 匹配才需要的 vendor 身份：

  ```dts
  qcom,msm-id = <339 0x20000>;
  qcom,board-id = <0 0>;
  oppo,dtsi_no = <19781>;
  ```

- 启动策略：

  ```dts
  chosen {
      bootargs = "earlycon=... console=tty0 ...";
  };
  ```

- 硬件契约：`reserved-memory`、regulator、GPIO、pinctrl、面板、触控等。

这些内容生命周期不同，不应该全都冻结进同一个“ABI”：

- `compatible`、设备节点和 `reserved-memory` 是硬件/驱动契约；
- `qcom,msm-id`、`qcom,board-id`、`oppo,dtsi_no` 是原厂引导链的匹配
  元数据，不是 Linux 使用的板级 ABI；
- `/chosen/bootargs` 是启动策略，且 EFI LoadOptions 非空时会被覆盖；
- `/memory` 可能是占位，EFI 启动时内存来自 UEFI memory map；
- 序列号、MAC、摄像头校准、电池参数属于运行时/校准数据，不应从
  DTB 里伪造。

### 6.3 推荐的 DTB 拆分

目标不是只维护一个巨大的 DTB，而是把“给内核的”和“给原厂引导链的”
分开。推荐的文件关系如下（名称是工程建议，可按实际构建脚本调整）：

```text
sm8150-samurai.dtsi
    共享的 SoC/板级硬件描述（regulator、GPIO、pinctrl、UFS、DSI、
    触控、传感器、reserved-memory 等）

sm8150-samurai.dts
    OS-facing mainline DTB：
      - model / compatible / chassis-type
      - 硬件节点
      - 不含 qcom,msm-id / qcom,board-id / oppo,dtsi_no
      - 不含生产 bootargs（debug 使用单独启动项）

sm8150-samurai-vendor.dts
    ABL/DTBO compat DTB：
      - include 同一份共享硬件描述
      - 加 qcom,msm-id / qcom,board-id / oppo,dtsi_no
      - 仅在原厂链需要时保留兼容 bootargs
```

映射到当前项目：

- `FdtBlob/samurai/*.dtb` 对应 OS-facing mainline DTB；
- `FdtBlob_compat/samurai.dtb` 对应追加到 boot image 的 vendor/compat
  DTB；
- 不要把 vendor DTB 放进 OS-facing 位置，也不要把 OS DTB 当成 ABL
  的 compat DTB；
- 拆分前先保留当前能启动的两份产物和哈希，拆分后逐项比较，而不是
  直接覆盖。

一个最小的 OS-facing 根节点应当类似：

```dts
/ {
    model = "Realme X2 Pro (RMX1931)";
    compatible = "realme,samurai", "qcom,sm8150";
    chassis-type = "handset";
};
```

上面不出现 vendor 匹配属性，也不默认出现 `bootargs`。如果旧版内核
或救援路径确实需要某个兼容属性，应把它作为明确的兼容项，而不是重新
混回主 DTB。

### 6.4 动态字段和白名单

建议把 UEFI 对 DTB 的修改限制在明确白名单：

| 字段 | 允许固件修改？ | 说明 |
| --- | --- | --- |
| `/memory` | 可以，或保留占位 | EFI 启动时 RAM 描述可来自 UEFI memory map；不要把固定大小当作 ABI |
| `/chosen` | 可以 | 启动参数、initrd、控制台选择属于启动策略，不是硬件描述 |
| `reserved-memory` | 原则上不应静默修改 | 它必须与固件内存图和 carveout 一致；任何修改都要单独验证并记录 |
| 设备 `reg`、中断、时钟、regulator、GPIO、pinctrl | 不应静默修改 | 这些是硬件契约；改变会影响驱动绑定和上电顺序 |
| 设备 `compatible` | 不应静默修改 | 它决定驱动匹配；不兼容变更应新版本/新 compatible |
| 序列号、MAC、校准 | 不写入 DTB | 由固件、NV、校准包或标准用户态服务提供 |

`dtb=` 命令行可以覆盖固件 DTB，但它会绕过固件在启动时加入的运行时
信息，只适合调试或固件无法提供 DTB 的最后手段；Linux EFI stub 文档
对此有明确说明：
[EFI stub: dtb=](https://docs.kernel.org/admin-guide/efi-stub.html#the-dtb-option)。

### 6.5 版本化：`samurai-dt-v1`

建议在发布清单中冻结一个标签，例如 `samurai-dt-v1`，但不要把它当成
未登记的私有 DT 属性。清单至少记录：

```json
{
  "board": "realme,samurai",
  "board_id": 19781,
  "dt_abi": "samurai-dt-v1",
  "dtb_sha256": "<发布 DTB 的哈希>",
  "firmware_build": "<UEFI/固件构建标识>",
  "kernel_release": "<配套内核>",
  "boot_entry": {
    "command_line": "<生产命令行>",
    "debug_command_line": "<可选调试命令行>"
  },
  "esp": {
    "partuuid": "<目标 ESP 的 PARTUUID>",
    "fallback_path": "\\EFI\\BOOT\\BOOTAA64.EFI"
  },
  "validated_variants": [
    "8GB/128GB-UFS3.0"
  ]
}
```

上面的值只是字段示例，不是当前设备的事实。清单的作用是让“固件、DTB、
内核、启动项和 rootfs”有可核对的组合，而不是让用户猜。

兼容规则：

1. **只做加法**：新增属性时，缺失该属性的旧内核仍保持原行为；
2. **不改语义**：已有属性的单位和含义不能暗中改变；
3. **不重命名稳定节点**：确实需要不兼容变化时，新增 `compatible`
   或新板级文件，并提升 ABI 标签；
4. **不把启动策略放到硬件 ABI**：生产 cmdline 由启动项管理，调试
   cmdline 放在独立启动项；
5. **不把 `/sys/firmware/fdt` 当成源 DTB 哈希**：它是启动后经过
   UEFI/EFI stub 修补的树，和源码 DTB 不会逐字节相同。

### 6.6 实际冻结步骤

1. **先产出 vendor/compat DTB**：保留当前 ABL 需要的
   `msm-id`/`board-id`/`dtsi_no`，确保原厂链仍能匹配；
2. **再产出 OS-facing DTB**：从同一份共享硬件描述生成，移除 vendor
   匹配属性，移除生产 `bootargs`；
   这一步必须在新启动项/LoadOptions 已经验证之后再做，不能先把当前
   唯一可用的命令行删掉；
3. **分别构建、分别记录哈希**：不要把两个产物互相覆盖；
4. **做静态检查**：用 `dtc` 反编译、检查根 `compatible`、检查
   `reserved-memory`，并尽可能做 `make dtbs_check`；
5. **做启动矩阵**：至少用当前内核和下一个内核版本各启动一次；验证
   面板、触控、UFS、USB、Wi-Fi/蓝牙、音频、传感器、充电等已支持项；
6. **检查启动后差异**：比较源 DTB 和 `/sys/firmware/fdt` 的稳定节点，
   只允许 `/memory`、`/chosen` 和已记录的白名单变化；
7. **发布清单并冻结**：把 DTB、固件、内核和启动项绑定到
   `samurai-dt-v1`；之后只做兼容性加法。

2026-11-05 的最小验证结果：

- baseline boot：`758694a1...a4acd`；
- 候选 OS DTB：`e3db4fa9...7850a`，只比输入少三个 vendor 根属性；
- 候选 boot：`66dbe234...efa23ae`，BootShim、ramdisk、其余 FV/FFS
  模块逐字节不变，只有 DTB payload 及其派生字段改变；
- 只写 `boot`，约 32 秒后 USB NCM/SSH、显示、充电和睡眠抑制服务
  恢复；
- 运行态三个 vendor 属性均消失，`realme,samurai` 和 `qcom,sm8150`
  保留；`logdump` 与 798 项模块清单哈希不变；
- 反编译前后 DTB 只差三个 vendor 根属性；候选与运行态只差 UEFI
  mmap/table 五个动态字段。

源码级离线结果（未刷入）：

- k363 规范 DTS：`428e20b3...338b`；
- k363 精确配置重建 DTB：`dcdd74ec...2c8d`，与构建记录一致；
- OS DTB：`f7959f8a...a3f0`，仅少三个 vendor 根属性；
- vendor 对照 DTB：与规范 DTB 逐字节相同。

当前 boot 的探测前 OS DTB `9736b861...`（116962 B）来自充电实验链，
不同于 k363 规范构建的 `dcdd74ec...`（114556 B）；合并前必须逐项
分类其新增属性和节点。2026-11-05 已完成只读差异账本：归一化
299 个纯 phandle 值变化和 679 个引用属性后，探测前 DTB 的 24 个
语义项全部分类，当前 `e3db4fa9...` 的 27 项也全部分类；其中 0 项
被提升为新的公共 ABI。分类结果为相机 ICP 7 项、充电/USB input
12 项、USB 控制器 linkage 1 项、EUD 调试 3 项、调试 bootargs 1 项，
vendor 根属性只在
vendor DTB。

随后把这些实验项写成独立 DTSI，离线重建出
`c582dd7c...a64f`。与部署的 `9736b861...` 比较，changed/added/
removed 语义属性均为 0，节点差异为 0；只有部署端
`/soc@0/eud-off-route` 多一个未消费的 phandle。这样当前部署 DTB 已
能从源码解释，不再需要把它当作不可复现的黑盒。

本地收据在
`E:\edk2-samurai-out\layer-adaptation-20261105\boot-dtb-inplace\runtime-result.json`。
未完成项是：把四类实验 profile 接成独立启动项/固件输入、把源码
构建的 OS DTB 装入 boot、删除或外置调试 `bootargs`、双内核矩阵和
同型号多 SKU 矩阵。

验收时至少确认：

- `/proc/device-tree/compatible` 包含稳定的
  `realme,samurai` 和 `qcom,sm8150`；
- OS-facing DTB 中没有 `qcom,msm-id`、`qcom,board-id`、
  `oppo,dtsi_no`；
- 没有把生产 `earlycon`/调试 console 作为唯一启动路径；
- `/memory` 大小与 UEFI memory map 一致；
- `reserved-memory` 与 UEFI 内存图没有重叠冲突；
- 同一 DTB 能配合同一启动项启动至少两个相邻内核版本；
- 换发行版/桌面不需要重新生成 DTB。

## 7. 同型号手机的最小改动安装

### 7.1 一次性操作和可重复操作

把安装分成两类，用户就不需要每换一次系统都重新做高风险操作：

| 类别 | 内容 | 频率 |
| --- | --- | --- |
| 一次性设备准备 | 解锁 bootloader、刷入 UEFI boot image、设置 ESP 类型、保留 GPT/分区备份 | 每台手机一次 |
| 可重复系统安装 | 放置/更新内核、initramfs、DTB、rootfs、启动项 | 每次发行版/桌面/内核更新 |

这也是“像 PC”的实际含义：固件和板级契约不变，换发行版主要是安装
rootfs 和配置启动项，而不是重新逆向硬件。

### 7.2 同型号 bundle 应该包含什么

建议一个可发布的同型号 bundle 至少包含：

```text
boot/uefi-boot.img          BootShim + UEFI FD + vendor/compat DTB
dtb/samurai.dtb             OS-facing DTB
metadata/manifest.json      设备、哈希、ABI、支持矩阵
rootfs/rootfs.tar.zst       可选，按发行版生成
rootfs/initramfs           可选，或由发行版生成
boot/entries/               production/debug 启动项模板
recovery.md                 回退和 9008/EDL 说明
```

不要把以下内容放进“通用镜像”：

- 固定 119,033,245,696 字节的 `userdata` 镜像；
- 别人的序列号、MAC、Wi-Fi 密码、SSH 私钥或相机校准；
- 未获授权再分发的高通/realme 原厂固件；
- 当前用户的 UID、Wayland socket 名称或桌面配置。

设备固件和厂商 DXE 应通过“用户自备原厂包/提取脚本”获得，或者在
许可证允许时单独发布；不要把“能下载一个 bin”误当成“可以公开再分发”。

### 7.3 为什么必须用 tarball/安装器而不是固定镜像

同型号至少有：

- 6/8/12 GB RAM；
- 64 GB UFS 2.1、128/256 GB UFS 3.0；
- 不同地区/批次，可能还有面板、触控、摄像头模组差异。

当前 [F2FS rootfs 文档](ROOTFS-F2FS-IMAGE.md) 明确说明，已有镜像展开
容量来自一个 119,033,245,696 字节的 `userdata`，是“该机容量的定制
镜像”。把它刷到 64 GB 或不同分区的同型号手机上，容量和 GPT 条件就
不成立。

目标安装器应当：

1. 通过 GPT 分区名/PARTUUID 找到目标分区，而不是写死 `/dev/sde32`；
2. 读取块设备容量，确认 rootfs 至少能容纳解包后的文件；
3. 解包 rootfs tarball，或调用发行版自己的安装器；
4. 把内核、DTB、initramfs 和启动项放到该发行版约定的位置；
5. 在首次启动前检查 ESP 类型、fallback loader 和回退入口；
6. 保留“清空 Android/保留 Android”两条明确路线，不默认替用户做
   破坏性决定。

在安装器成熟前，可以发布“按容量生成”的镜像；但要在文件名和清单里
写清适用容量和校验值，不能叫“X2 Pro 通用镜像”。

### 7.4 同型号差异的运行时识别

建议把可变的容量信息留给运行时：

- RAM 大小从 UEFI memory map / 内核启动日志确认；
- UFS 容量、LUN 数和逻辑扇区从块设备确认；
- 根 `compatible` 用于板级识别，不要用 `model` 字符串做程序分支；
- 面板/触控/摄像头若确有条码差异，用内核枚举出的 ID 或单独的
  calibration 包选择，不要把每个批次硬编码成多个完整 DTB；
- 序列号和 MAC 从固件/NV 获取，不写进 DTB。

当前项目的实际证据主要来自 8 GiB 机型。6/12 GiB 和 64 GB UFS 2.1
SKU 在宣称“支持所有同型号”之前必须单独验证；尤其是 UEFI 的内存图
分支、UFS 初始化/容量和安装器容量边界。

### 7.5 包边界目标

当前 `samurai-platform` 和 `samurai-desktop` 已经做了部分拆分，但
还不是完全按发行版/桌面解耦。目标可以按职责拆成：

| 目标包 | 内容 | 依赖/备注 |
| --- | --- | --- |
| `samurai-hardware` | udev 规则、firmware 文件清单、ALSA UCM、modprobe、板级校准、OS DTB | 尽量 `noarch`；不包含 init/桌面策略 |
| `samurai-kernel` | 内核 Image、模块、initramfs 生成钩子、内核版本约束 | 与发行版内核 ABI 绑定；不能假装跨发行版二进制通用 |
| `samurai-services-openrc` | OpenRC init、runlevel、conf.d | 只负责 OpenRC 适配 |
| `samurai-services-systemd` | systemd unit、tmpfiles、udev 集成 | 只负责 systemd 适配 |
| `samurai-charging` | 充电模块、电源策略服务、温度/电流限制接口 | 当前已有独立包，不应塞回通用硬件包 |
| `samurai-desktop-plasma` | KWin/KScreen/PowerDevil 桥接、tinydm 配置 | Plasma 专属 |
| `samurai-desktop-phosh` | Phoc/greetd/输出管理相关配置 | Phosh 专属；历史保留 |
| `samurai-recovery` | 救援启动项、回退脚本、诊断工具 | 可选，不应依赖桌面 |

当前需要注意的具体问题：

- `samurai-platform` 依赖 OpenRC、`sleep-inhibitor` 等，已经带有
  发行版/init 选择；
- 它安装 `/usr/local/share/dbus-1/system-services/...ModemManager1.service`
  来阻止 D-Bus 自动激活。这是本机 OpenRC 单实例策略，不应成为
  所有发行版的通用硬件规则；
- `samurai-powerkey`、KWin 的 DPMS 处理属于 Plasma/KWin，不是板级
  硬件支持；
- `samurai-refresh` 是 Phoc/wlroots 历史工具，不应进入板级主包。

拆包后，换发行版只需要提供新的 `samurai-services-*` 包装同一组
硬件接口；换桌面只需要安装不同的 `samurai-desktop-*`。

### 7.6 从 L2/L3/L4 开始收敛时如何不打断调试飞轮

可以从 L2、L3、L4 开始，但要把每一层拆成两类工作：

- **契约冻结、源码拆分、加公共别名**：不改变当前启动路径，可以并行做；
- **替换运行时 DTB、删除调试参数、删除旧 UAPI**：会改变启动或用户态
  行为，必须有单独窗口和回退。

当前调试飞轮依赖以下不变量：

1. `boot` 分区中有一份已知可启动的 UEFI，且原厂 boot image/GPT 可回退；
2. `logdump` 的 FAT 和 `\Image` 路径仍然有效；
3. EUD/console、`pstore`/ramoops 和 USB NCM/SSH 仍可用；
4. 内核 release、模块目录和 `/lib/modules` 匹配；
5. 每次只引入一个可归因的硬件行为变化。

按这个边界，建议这样安排：

| 工作 | 对飞轮的影响 | 建议 |
| --- | --- | --- |
| L2a：锁定实际 DTS 源，盘点稳定属性、动态属性和 vendor 属性，生成 `samurai-dt-v1` 清单 | 几乎没有，只读/离线 | 已完成 k363 源锁；见 [source-lock.json](../dts/source-lock.json) |
| L2b：在锁定的规范源上拆成共享 DTSI、OS DTB 和 vendor 对照 DTB，离线构建并比较 | 不影响当前启动 | 已完成离线构建、差异账本、独立实验 DTSI 和语义身份重建；下一步接运行时启动项/固件输入 |
| L2c：把新 DTB 装进 UEFI 并实际启动 | 需要刷 `boot` 并重启；本次单变量探针约 32 秒恢复 SSH，飞轮只暂停一个启动周期 | 完整源拆分仍需单独维护窗口；保留旧 boot image |
| L3a：驱动内部整理、增加标准子系统接入，保持现有 DTB 和调试参数 | 只改 `logdump` 中的内核，飞轮仍可工作 | 优先做 |
| L3b：删除 `clk_ignore_unused`、`pd_ignore_unused` 等启动保险 | 可能直接打断启动，且不一定能进 fastboot | 一次只删一个，逐项回退 |
| L4a：新增标准 UAPI/兼容别名，旧私有接口暂时保留 | 通常不影响现有桌面 | 优先做双栈 |
| L4b：删除旧 sysfs、旧 helper 或旧服务名 | 会打断现有 rootfs/桌面调试路径 | 等所有消费者迁移并验收后再做 |
| L1/ESP/BDS/启动项改造 | 会影响“能否进入内核”，不是单纯接口收敛 | 不要和 L2/L3/L4 首轮混在一起 |

截至 2026-11-05，L2 的源码构建候选 `aa93d14d...` 因 `BdsDxe` 长度变化
和 `UiApp` 代码差异被拒绝，不能用于 L2c。这个结论不推翻并行规则，反而
说明离线闸门必须挡住“看起来只换 DTB、实际还重建了其他 FFS 模块”的
候选。替代候选 `3e83798e...` 已从原 boot `758694a1...` 仅替换 DTB
payload，`BdsDxe`/`PlatformSmbiosDxe`/`UiApp` 均逐字节相同，
`non_dtb_ffs_body_changes = 0`，metadata review 通过；但它仍未刷入，
而且会移除当前充电/camera/EUD 实验行为。L2a/L2b、L3a 和 L4a 可以
继续；补完运行态双内核/SKU 矩阵，并确认充电长测结束或取得维护窗口
后，才进入一次单变量 G3 启动窗口。届时飞轮只暂停一个启动周期，不会
因 L2/L3/L4 的离线收敛设计而被打断。

推荐的执行顺序是：

1. **先做基线清单和只读检查**：记录 boot image、compat DTB、OS DTB、
   `logdump` 镜像、内核 release、模块、rootfs 和 GPT 的哈希/身份；
2. **L4 先做加法**：保留旧接口，新增标准接口/别名，让当前桌面先继续
   工作；
3. **L2 做契约冻结和离线拆分**：不刷 boot，只比较 DTB 树和启动矩阵；
4. **L3 做内核内聚**：保持 `\Image`、EUD/pstore、模块匹配和调试开关，
   每次只改一类驱动；
5. **L2 选一个窗口切换 DTB**：旧 boot image 和 EDL 救援在手，失败就
   回退，不把“新 DTB + 新 BDS + 新 ESP”叠在一起；2026-11-05 已用
   只删三个 vendor 根属性的探针走通一次，但不要重复刷同一候选；
6. **最后删除旧 UAPI/调试参数**：每删一个都按“删除前可启动、删除后
   可回退”的方式验收。

这样，L2/L3/L4 **可以同时开始收敛设计**，但运行时的三个切换点要分开：
L2 的 DTB 激活、L3 的启动保险清理、L4 的旧接口删除。L3 的内核迭代
本来就在飞轮的主路径上；L2 的源码拆分和 L4 的加法不会打断它；真正
需要暂停飞轮的是 L2 实际刷 boot，以及 L3/L4 中会改变启动或现有桌面
行为的删除性改动。本次最小 L2 探针已证明：只要不同时改 `logdump`、
`Image`、模块、GPT 或调试参数，刷一次 boot 只暂停一个启动周期，
USB SSH 恢复后飞轮即可继续；这不构成跳过源锁和完整启动矩阵的理由。

具体工作包、依赖关系、G0-G4 闸门和基线命令见
[L2-L4 收敛计划](LAYER-CONVERGENCE-PLAN.md)。

## 换发行版、换桌面时应该依赖什么

### 公共接口矩阵

| 能力 | 板级应暴露的公共接口 | 桌面/发行版如何使用 |
| --- | --- | --- |
| 显示与刷新率 | DRM/KMS connector、mode、backlight class | compositor 选择 60/90 Hz、DPMS；不要写面板寄存器 |
| 触摸/按键 | evdev/input、`KEY_POWER`、`KEY_VOLUME*` | libinput、桌面快捷键；电源键策略属于桌面 |
| 亮度 | `/sys/class/backlight` 或 DRM 标准属性 | 桌面通过标准 helper/portal 控制 |
| 音频 | ALSA PCM、UCM、jack/route | PulseAudio/PipeWire；板级提供 UCM，不绑定某个桌面 |
| USB 网络/存储 | USB gadget/configfs、标准 net device/block device | NetworkManager、udhcpc、SSH；不要在桌面里写 gadget 细节 |
| Wi-Fi | cfg80211/mac80211、rfkill、NetworkManager | 标准网络栈 |
| 蓝牙 | BlueZ、HCI/UART 固件、rfkill | BlueZ 和桌面蓝牙面板 |
| 蜂窝 | QRTR/QMI、WWAN、ModemManager | ModemManager、Calls/Chatty；桌面只是客户端 |
| 定位 | GNSS/GeoClue/ModemManager | 位置服务；不要在桌面里直接解析 QMI |
| 传感器 | IIO、iio-sensor-proxy D-Bus | compositor 读取方向/亮度，不直接读板级私有文件 |
| 振动 | input/ff 或 feedbackd 公共接口 | 桌面触发 `feedbackd`，不依赖 AW8697 私有寄存器 |
| 充电/电池 | `power_supply` class、thermal | UPower/桌面读取；板级服务执行策略，不让桌面猜电流 |
| 相机 | V4L2/media controller/libcamera/PipeWire | 相机应用或 PipeWire 客户端；不依赖某个桌面 |
| 会话/门户 | logind/elogind、portal D-Bus | 各桌面自己的 portal 后端 |

### 换发行版时会发生什么

在 L1-L4 稳定的前提下，换发行版主要需要：

- 重新编译/安装适配该发行版内核版本的模块；
- 用该发行版的 init 系统包装板级服务；
- 用该发行版的包管理器安装 firmware、udev 规则、UCM 和 DTB；
- 适配安装器、initramfs、启动项和升级/回滚；
- 重新验证该发行版的内核是否包含本项目依赖的补丁。

不需要也不应该：

- 为发行版重新生成一份“Debian DTB”或“Arch DTB”；
- 把桌面配置文件塞进固件；
- 在 `/usr/local` 里覆盖发行版文件；
- 假设任意发行版的 stock kernel 都自动包含相机、充电或显示补丁。

当前项目已经指出这一点：[270 分层审计](../../reference/kernel270/LAYERING-AUDIT.md)
明确说，不能直接换无补丁主线内核并保留全部既有功能。

### 换桌面时会发生什么

在板级包正确分层的前提下，换桌面主要改 L7：

- Plasma：KWin/KScreen/PowerDevil、KAuth 背光 helper、KGlobalAccel；
- Phosh：Phoc/wlroots 输出管理、greetd、portal；
- GNOME：Mutter、gnome-settings-daemon、portal；
- Sway/wlroots：output-management、brightnessctl、标准 portal。

板级包只提供：

- DRM/KMS 已上报的 60/90 Hz 模式；
- evdev 键值和触摸；
- 背光 class；
- UCM/音频路由；
- 传感器、振动、GNSS、modem、充电等标准服务。

当前 Plasma 的 `samurai-powerkey` 是一个典型例子：它解决 KWin 6.8.2
的 PowerDevil 电源键竞争，属于桌面适配，不是“这块屏幕/这个按键的
通用硬件驱动”。如果换到 Phosh/Sway，不应要求安装它。

### “无需额外适配”的现实定义

实际可实现的目标不是“任何发行版、任何桌面，零配置启动所有硬件”，
而是：

> 换发行版时，不需要重新逆向硬件、重写 DTB 或修改内核驱动；只需要
> 重新打包、配置 init/安装器，并验证该发行版的内核/固件版本。
>
> 换桌面时，不需要改固件、DTB 或板级服务；只需要安装该桌面的
> compositor、portal、音频和电源策略适配。

这已经足以接近 PC/电视盒子的体验。剩下的“零工作”取决于上游驱动
是否完整、厂商固件是否可分发、发行版是否愿意维护该机型包。

## 风险、非目标和当前不能承诺的事

- **改 GPT 不是零风险。** 只改类型 GUID 比重新分区小，但仍然修改
  启动元数据；没有 GPT/内容备份和 EDL 救援，不应操作。
- **标准 ESP 不是驱动支持。** 即使启动链完全标准，摄像头、modem、
  指纹、传感器校准等仍需要内核和用户态工作。
- **当前没有持久 UEFI 变量。** PC 式 Boot Manager 需要变量存储，
  或必须依赖回退路径；这两者不能混为一谈。
- **64 MiB ESP 不是通用发行版 `/boot`。** 多内核、UKI、大 initramfs
  可能放不下；扩展 ESP 应另做分区规划。
- **当前 rootfs 不是通用镜像。** 固定容量 F2FS 镜像只验证了一个
  `userdata` 尺寸；同型号不同容量必须用 tarball/安装器或按容量生成。
- **没有上游 samurai 板级支持。** 不能承诺 stock mainline、任意
  pmaports 分支或任意发行版开箱即用。
- **厂商固件有再分发限制。** 同型号安装包不能让用户绕过原厂固件
  获取/许可条件。
- **ACPI 不是 Linux 的主路径。** 本项目的 Linux 主要使用 DT；
  ACPI/DSDT 是 Windows-on-ARM 等另一条路径，不能用来替代 Linux DTB。
- **功能列表不能由驱动注册推断。** 注册了 IIO、V4L2 或 power_supply
  不等于拍照、录像、通话、快充或长稳已经验收。

## 分层验收清单

### L1 引导固件

- [ ] 冷启动能稳定进入 UEFI，不依赖临时 USB 主机；
- [ ] boot image 的 BootShim/UEFI/compat DTB 布局可复现；
- [ ] GPT 中目标分区类型为 ESP，起始/大小未变；
- [ ] `\EFI\BOOT\BOOTAA64.EFI` 回退路径可用；
- [ ] 没有持久变量时仍有确定的回退启动；
- [ ] 原厂 boot image 和 GPT 备份可恢复；
- [ ] 改类型后 `fastboot flash logdump`/救援写入路径仍可用。

### L2 硬件描述

- [x] 运行态 OS DTB 根 `compatible` 为 `realme,samurai`, `qcom,sm8150`
  （2026-11-05 探针）；
- [x] 运行态和源码构建的 OS DTB 均不含
  `qcom,msm-id`/`qcom,board-id`/`oppo,dtsi_no`；
- [ ] 生产 DTB 不含唯一的调试 `bootargs`；
- [ ] `/memory` 与 UEFI memory map 一致；
- [ ] `reserved-memory` 与 UEFI 内存图无冲突；
- [x] 本次输入 DTB 与 `/sys/firmware/fdt` 的稳定节点差异可解释；
- [ ] 同一 DTB 至少配两个相邻内核版本启动通过。

### L3-L4 驱动和公共接口

- [ ] 显示通过 DRM/KMS 枚举，60/90 Hz 可选；
- [ ] 触摸和按键在 `evtest`/libinput 中可见；
- [ ] 音频通过 ALSA/UCM 播放和录音；
- [ ] UFS 全部 LUN 和 GPT 可见；
- [ ] USB gadget/NCM、Wi-Fi、蓝牙使用标准栈；
- [ ] 传感器通过 IIO/iio-sensor-proxy；
- [ ] 充电/电池通过 power_supply；
- [ ] 相机通过 V4L2/libcamera 的可测路径；
- [ ] 没有新的私有 ioctl 被桌面直接依赖。

### L5-L6 板级和发行版

- [ ] `samurai-hardware` 不含 init/桌面专属文件；
- [ ] 至少一个 init 适配包可安装/卸载/幂等启动；
- [ ] rootfs 可用 tarball 或安装器安装到不同容量；
- [ ] 内核/DTB/启动项更新不需要重刷 boot；
- [ ] 升级失败可以回退；
- [ ] 不依赖固定用户名、固定 Wayland socket 或固定 `/usr/local`。

### L7 桌面

- [ ] Plasma Mobile 能在不改板级包的情况下启动；
- [ ] 至少再安装一个不同桌面/合成器，使用同一 DRM/input/audio 接口；
- [ ] 桌面专属修复只出现在 `samurai-desktop-*`；
- [ ] 电源键、亮度、旋转、音频、portal 分别在目标桌面内验收；
- [ ] 移除 Plasma 桥接后，板级硬件仍可由标准接口使用。

### 同型号兼容

- [ ] 8 GiB 当前机型启动通过；
- [ ] 至少验证 6 GiB 和 12 GiB 的内存图/启动（如果确实要宣称支持）；
- [ ] 至少验证 64 GB UFS 2.1 和 128/256 GB UFS 3.0 的容量边界；
- [ ] 安装器不会因固定 `userdata` 大小失败；
- [ ] 面板/触控/摄像头批次差异有识别或明确的支持范围。

## 资料来源与核对记录

核对日期：2026-11-05。

| 资料 | 用途 |
| --- | --- |
| [realme X2 Pro 官方欧盟规格页](https://www.realme.com/eu/realme-x2-pro/specs) | RAM、UFS 分 SKU、屏幕、电池、相机、接口 |
| [GSMArena X2 Pro](https://www.gsmarena.com/realme_x2_pro-9904.php) | USB Type-C 2.0、屏幕/电池/相机交叉核对 |
| [Linux qcom binding](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/devicetree/bindings/arm/qcom.yaml?h=master) | 核对当前上游是否包含 samurai compatible |
| [Linux qcom DTS 目录](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/boot/dts/qcom?h=master) | 核对是否有 `sm8150-samurai.dts` |
| [Linux DT ABI](https://docs.kernel.org/devicetree/bindings/ABI.html) | 稳定 binding、增加属性、兼容性变更规则 |
| [Linux arm64 booting](https://docs.kernel.org/arch/arm64/booting.html) | DTB 传递和启动约定 |
| [Linux EFI stub](https://docs.kernel.org/admin-guide/efi-stub.html) | `dtb=` 覆盖和运行时修复信息的限制 |
| [UEFI 2.10 GPT](https://uefi.org/specs/UEFI/2.10/05_GUID_Partition_Table_Format.html) | ESP 类型 GUID `C12A7328-F81F-11D2-BA4B-00A0C93EC93B` |
| [UEFI 2.10 Media Access](https://uefi.org/specs/UEFI/2.10/13_Protocols_Media_Access.html) | FAT12/16/32 和系统分区文件系统要求 |
| [UEFI 2.10 Boot Manager](https://uefi.org/specs/UEFI/2.10/03_Boot_Manager.html) | `BOOTAA64.EFI` 回退启动约定 |
| [当前 pmaports](https://gitlab.postmarketos.org/postmarketOS/pmaports) | 核对是否已有 samurai 设备包 |
| [samurai DTS](../dts/sm8150-samurai.dts) | 本机根节点、vendor 属性、bootargs、reserved-memory |
| [20-linux-boot.md](20-linux-boot.md) | `logdump` 64 MiB/FAT16/4K 和 BDS `\Image` 历史 |
| [19-loadoptions.md](19-loadoptions.md) | LoadOptions 是 UTF-16，非空命令行覆盖 DTB bootargs |
| [EDK2-KERNEL-EMBED.md](EDK2-KERNEL-EMBED.md) | EFI 配置表发布 DTB |
| [HARDWARE-STATUS.md](HARDWARE-STATUS.md) | 功能能力与未验收范围 |
| [DESKTOP-PORTABILITY.md](DESKTOP-PORTABILITY.md) | 板级/桌面接口边界 |
| [PLASMA-MOBILE.md](PLASMA-MOBILE.md) | Plasma 专属电源键、亮度和会话经验 |
| [ROOTFS-F2FS-IMAGE.md](ROOTFS-F2FS-IMAGE.md) | 固定 `userdata` 容量镜像的限制 |
| [270 分层审计](../../reference/kernel270/LAYERING-AUDIT.md) | 项目内核/驱动/用户态尚未上游和对发行版维护成本的审计 |

公开页面可能更新；本表中的“当前”只对应上述核对日期和已记录的提交。
任何“支持所有同型号”“任意发行版可用”“标准 ESP 零风险”的结论，
都必须在相应实机矩阵和安装器验收完成后才能写出。
