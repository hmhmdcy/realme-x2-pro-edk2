# 旧工程核实报告：`E:\Realme X2 Pro移植主线Linux`

> 2026-10-07，核实人：本次会话。被核实对象是旧的 Linux 移植工程（本工作区
> `linux-port/README.md` 已宣布弃用它，但它的补丁、配置和实机记录仍在被引用）。
> 结论按"能不能直接拿来用"分类，不按好看程度。

## 0. 结论速览

1. **旧工程是可复现的。** 它的 `0001-rmx1931-usb-bringup.patch` 能干净应用到
   Linux v7.3-rc6，重新编译出的 `sm8150-realme-x2pro.dtb` 与它留下的产物
   **sha256 逐字节相同**（`f0c3a820740b352c39fa60ba1e206b8ac2c7f4dc5b2e82ce773d4752a14adc74`，
   130263 字节）。它没有伪造构建结果。
2. **事实性内容大体准确**：设备身份（msm-id / board-id / dtsi_no）、内存保留区
   （16 处地址全部与实机一致）、按键接线、以及"主线没有启动成功"的结论。
3. **有三处会实际影响启动的错误**：UFS `vccq2` 电源、按键 pin 的 bias / 电压档位、
   ramoops 的几何参数（其中 `devinfo-size` 主线根本不支持）。
4. **文档对测试轮次的记录不完整**：README/文档只写了"前四轮主线候选 + 第五、六轮
   原机内核对照"，实际是 **6 轮主线镜像刷入测试（1/2/3/4/7/8）+ 2 轮对照（5/6）**，
   第 8 轮（va39）刷了、恢复了，但**没有写任何结果文件**。
5. **旧工程的内核不可能走 EDK2 引导**：`bringup.config` 里没有 `CONFIG_EFI` /
   `CONFIG_EFI_STUB`，而 `0002` 的入口 hack 还专门 `depends on !EFI`。
6. **顺带发现（不属于旧工程，但直接关系"移植主线"）**：EDK2 固件现在通过 EFI
   配置表交给 Linux 的 `Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb`
   实际上是**小米 9（cepheus）的设备树**——反编译出来是
   `model = "Xiaomi Mi 9"; compatible = "xiaomi,cepheus", "qcom,sm8150";`，
   还带着 cepheus 的 `simple-framebuffer@9c000000` 和 `stdout-path`。
   也就是说 samurai 的 UEFI 一直在给内核一份错误的硬件描述。

## 1. 核实方法（都可复跑）

| 手段 | 命令/脚本 | 产物 |
|---|---|---|
| 旧补丁能不能干净应用 | `git apply --check` | `APPLY_CHECK_OK` |
| 旧 DTS 能不能编译、是否可以复现 | `linux-port/scripts/test-old-dts.sh` | `f0c3a820…` == 旧产物 |
| 实机真值 | `linux-port/scripts/dump-live-dt.sh`（解包 `live-device-tree.tar`） | 见下表 |
| 交叉核对 | 读 `artifacts/*.json`、`artifacts/tests/*/transaction.json` | 见第 3 节 |

证据来源三件套，优先级从高到低：

1. `artifacts/device/20261005T074931Z/live-device-tree.tar`：**运行中 Android 的
   `/proc/device-tree` 全量转储**（ABL 合并 DTBO 后的最终树）；
2. `artifacts/device/20261005T074931Z/original-appended.dts`：`boot.img` 里
   **尾部追加的基础 DTB**反编译；
3. `artifacts/device/20261005T074931Z/dtbo-entry-0.dts`：**原厂 DTBO** 反编译
   （`qcom,board-id = <8 0>`、`oppo,dtsi_no = 19781`）。

## 2. 逐项核对表

| # | 旧工程的说法/做法 | 实机证据 | 结论 |
|---|---|---|---|
| 1 | `qcom,msm-id = <339 0x20000>`、`qcom,board-id = <0 0>`、`oppo,dtsi_no = <19781>` | `original-appended.dts` 三者完全一致（live 树的 board-id 是 8，来自 DTBO） | ✅ 准确 |
| 2 | 替换 17 个 reserved-memory 节点、新增 16 个 | 与 live 树 + 基础 DTB 逐项一致：hyp 0x85700000+0x600000、smem 0x86000000+0x200000、tz 0x86200000+**0x7500000**、mpss 0x8dc00000+0xa000000、venus 0x97c00000、slpi 0x98100000、ipa 三连 0x99500000/0x99510000/0x99515000、spss 0x99600000、cdsp 0x99700000、camera 0x9ab00000、wlan 0x9b000000、npu 0x9b180000、adsp 0x9b200000、qseecom 0xa0000000+0x1400000、cdsp_sec 0xa4c00000+0xc00000 | ✅ 准确（`tz` 从 MTP 的 0x3900000 改大是对的） |
| 3 | 删掉 MTP 的 `rmtfs_mem@0x89b00000` | live 树**没有** rmtfs 节点，该地址落在 `removed_regions`（0x86200000+0x7500000）里面 | ✅ 准确 |
| 4 | `xbl_mem@0x85e00000`（实机 xbl_aop 起点是 0x85e00000，MTP 的 0x85d00000 是错的）；大小裁成 0x120000 以避开 `aop_cmd_db@0x85f20000` | 基础 DTB 与 live 一致，均为 0x85e00000+0x140000 | ✅ 准确（裁剪是合理取舍，保留 `qcom,cmd-db` 节点） |
| 5 | **`&ufs_mem_hc { vccq2-supply = <&vreg_l7a_1p8>; }`**，注释写"live DT 用 L7A" | DTBO 明确写 `vccq2-supply = <&pm8150_s4>`，live 树解析出来也是 `soc/regulator-pm8150-s4`，即 **S4A（fixed 1.8 V，always-on）** | ❌ **错误**。mainline MTP 原本的 `vreg_s4a_1p8` 才是对的。L7A 是紧跟其后的 `&wifi { vdd-1.8-xo-supply = <&vreg_l7a_1p8>; }` 那一行，疑似看串行。该错误还传进了 `docs/hardware-status.md`（"实机 L7A VCCQ2"） |
| 6 | 音量键：`&pm8150_gpios` 6 / 7、`GPIO_ACTIVE_LOW`、`KEY_VOLUMEUP` / `KEY_VOLUMEDOWN`、`debounce-interval = <15>` | DTBO 与 live 树完全一致（另外实机还有 `linux,input-type`、`linux,can-disable`） | ✅ 准确 |
| 7 | 音量键 pin：`bias-pull-up`、`power-source = <0>` | 实机是 `bias-disable`、`power-source = <1>` | ⚠️ **不一致**（驱动接受 1，`arg >= pad->num_sources` 才是非法；功能上可能都"能用"，但不是这台机器的配置） |
| 8 | 加 `ramoops@0xb7e00000`，record/console/ftrace 各 0x40000、pmsg 0x200000 | 实机确实有 `ramoops@0xB7E00000`（4 MiB，**地址对**），但几何是 record/console/ftrace 各 **0x400**、pmsg **0x2000**，外加 1 MiB `devinfo-size` | ⚠️ 地址对、几何是自定的；`devinfo-size` 是下游专有属性，主线 `fs/pstore/ram.c` 不解析（主线只认 record/console/ftrace/pmsg/ecc） |
| 9 | `compatible = "realme,x2pro"` + 自己往 qcom.yaml / vendor-prefixes.yaml 加绑定 | 主线没有这个串；本机基础 DTB 自称 `Qualcomm Technologies, Inc. SM8150 v2 SoC` / MTP | ⚠️ 本地能用，但不是上游命名约定（新 DTS 改用 `realme,samurai`） |
| 10 | "补丁编译通过，产出 DTB" | 重编结果与产物哈希一致 | ✅ 准确 |
| 11 | "原 Android DTBO 无法应用到带符号的主线设备树（FDT_ERR_NOTFOUND）" | 与 DTBO 里引用 vendor 符号（`&pm8150_gpios` 等）的事实吻合 | ✅ 可信 |
| 12 | `docs/control-test-result.md`："当前主线配置中 `CONFIG_QCOM_WDT=m`" | `bringup.config` / `pre-va39.config` 是 **=y**；只有更早的 `pre-network.config` / `pre-entry.config` 才是 =m | ⚠️ 文档落后于最终配置（下一轮待办其实已经做掉了） |
| 13 | （文档未提）内核是否 EFI 可引导 | `bringup.config` 中**没有** `CONFIG_EFI` / `CONFIG_EFI_STUB`；`patches/0002` 的 `REALME_X2PRO_DIAGNOSTIC_ENTRY` 还 `depends on ARCH_QCOM && !EFI` | ✅ 事实成立 → 旧镜像**不可能**由 EDK2 加载，只能走 Android 启动链 |

## 3. 测试轮次：文档漏了第 7、8 轮

README 的说法是"前四轮主线候选已刷入测试……第五、六轮保留原机内核做 RAM 诊断对照"。
机器可读记录里实际是：

| 轮次 | 候选 | 内核 | 刷入 | 结果 |
|---|---|---|---|---|
| 1 | `bringup1-no-avb` | 7.3-rc6 rmx1931 | ✅ | `native_boot_confirmed = false` |
| 2 | `bringup1-avb2` | 同上 | ✅ | false |
| 3 | `bringup1-v2-raw3` | 同上 | ✅ | `round-3-boot-result.json` = false |
| 4 | `bringup-entry4-stock-v1` | 入口 hack + text_offset | ✅ | `round-4-boot-result.json` = false |
| 5 | `downstream-control5` | **原机 4.14** | ✅ | NCM 起来、没拿到日志 |
| 6 | `downstream-control6` | **原机 4.14** | ✅ | 拿到 250 KB 内核日志（对照成功） |
| 7 | `bringup-network7-stock-v1` | `7.3.0-rc6-rmx1931-netwdt1`（NCM 日志 + 内建看门狗） | ✅ | `round-7-boot-result.json` = false |
| 8 | `bringup-va39-8-stock-v1` | `7.3.0-rc6-rmx1931-va39` | ✅ `tests/20261005T113027Z-install` | **没有结果文件**；USB 快照仍只有 Android Bootloader Interface |

也就是说：**主线被盲刷了 6 次，没有一次拿到内核输出**，而 `deployment-review.json`
里第 8 轮至今还挂着 `"status": "offline candidate, not boot-tested"`（那是刷机前写的
清单，事后没人回填）。第 7、8 轮在文档里完全不存在。

## 4. 为什么这些错要紧

* **UFS 电源挂错**：`vccq2` 是 UFS 的 1.8 V IO 电源。挂到 L7A（一颗普通 LDO）而不是
  always-on 的 S4A，最坏情况是 UFS 根本不上电或初始化失败——而 UFS 恰好是这台机器
  唯一的持久存储，也是"能不能装发行版"的前提。
* **按键 pin 配置不忠实**：`bias-pull-up` 会在板子已有外部上拉的情况下再叠一层，
  `power-source = <0>` 选了另一个电压档位。前几轮既然没有日志，也就无法归因，
  不能排除是它造成的按键不稳。
* **pstore 为空不是配置问题**：`CONFIG_PSTORE_RAM=y` 是有的（ramoops 也就注册了），
  但 ramoops 只在 **oops / panic** 时落盘，**hang 不写任何东西**。前 6 轮多半是
  早期 hang，所以 pstore 永远空。这恰恰说明"没有 early console 时盲刷毫无信息量"——
  也是现在补 EUD earlycon、并用 EDK2 先开 EUD 的意义。
* **没有 EFI**：旧内核即使能跑，也接不上现在这台机器已经验证可用的 EDK2 固件引导链，
  而那条链是目前唯一"启动前就能把日志通道开好"的路径。

## 5. 可以直接继承 / 必须丢弃

**继承**（已并入新工作树）：

* reserved-memory 的 16 处数值与"删 MTP 节点再补实机节点"的写法；
* 身份三属性 `qcom,msm-id` / `qcom,board-id` / `oppo,dtsi_no`（走 Android 启动链时 ABL 要用）；
* 音量键接线（gpio 6/7、active-low、115/114、15 ms）；
* `bringup.config` 作为诊断内核配置基线（见 `linux-port/README.md` 的下一步）；
* minimal overlay 的思路与 `upstream-integration.patch` 的绑定写法。

**丢弃**：

* `&ufs_mem_hc` 的 `vccq2 = L7A`（保持 MTP 默认的 S4A）；
* 按键 pin 的 `bias-pull-up` / `power-source = <0>`（改用实机的 `bias-disable` / `<1>`）；
* `0002` 的入口 hack（`b1 primary_entry` + `text_offset 0x80000`，专为老 Android
  引导链做的实验，和 EFI stub 冲突）；
* 不含 EFI 的内核配置；
* 自定的 ramoops 几何（地址保留，几何按用途重写，并去掉 `devinfo-size`）。

## 6. 本轮据此产出的东西

| 交付 | 位置 | 校验 |
|---|---|---|
| EUD earlycon 提交 | WSL `~/x2pro-linux/linux` `e4858b30a`；补丁 `linux-port/patches/0001-tty-serial-add-Qualcomm-EUD-COM-early-console.patch` | 编译通过 |
| samurai 主线设备树 | `linux-port/dts/sm8150-samurai.dts`；补丁 `…/patches/0002-arm64-dts-qcom-add-realme-samurai-X2-Pro-bring-up-description.patch`；提交 `31491583b` | `make dtbs` 通过，DTB `1c760ec9cf74389c246e1b64a032c52910f6437dab29772371a506ead5d67b81`，94623 字节 |
| reserved-memory 核对表 | `linux-port/artifacts/reserved-memory.txt` | 21 个节点，逐项对齐实机 |
| 旧工程核实脚本 | `linux-port/scripts/{test-old-dts,install-samurai-dts,dump-live-dt,verify-samurai-dtb,collect-artifacts}.sh` | 可复跑 |

还没做（下一轮）：诊断内核 `Image`（EFI stub + `CONFIG_SERIAL_EUD_EARLYCON=y`）、
把 EDK2 的 `FdtBlob/samurai/` 从 cepheus 换成新 DTB、真机验证。
