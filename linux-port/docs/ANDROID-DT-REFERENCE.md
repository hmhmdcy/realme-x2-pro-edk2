# Android 设备树参考评估（realme X2 Pro / samurai / 项目号 19781）

> 2026-10-07。回答"安卓设备树能不能作为移植主线的参考"：**能，而且是目前最有价值的
> 硬件参考**——但它只提供"接线与时序"，不提供"主线能跑"。下面写清来源、已经用上的、
> 还能用的，以及必须注意的坑。

## 0. 结论速览

1. 本机有**下游内核源码级的设备树**，不是只有反编译产物：realme 官方 AndroidR 内核
   （4.14）里 `arch/arm64/boot/dts/19781/` 整个目录就是这个项目的设备树，其中
   `sm8150-mtp.dtsi`（1334 行）就是本机板级描述，`sm8150-mtp-overlay.dts` 是 DTBO 入口。
   **`19781` 正是本机 `oppo,dtsi_no`。**
2. 这份源码已经**离线**躺在本机（旧工程留下的 187 MB 浅克隆
   `E:\Realme X2 Pro移植主线Linux\sources\realme-downstream.git`，`git ls-tree` /
   `cat-file` 直接可读，不需要联网）。
3. 它的价值：带标签、带注释、按功能分段的**接线真相**（GPIO 号、I2C 控制器与地址、
   中断、复位脚、供电 rail、面板初始化序列）。这正好补上主线 DTS 缺的部分。
4. 它的边界：**4.14 下游私有 binding + 厂商私有驱动**，不能整段搬进主线；面板/触控/
   充电在主线要么没有驱动要么 binding 不同。DT 给不了"能跑"。

## 1. 三个来源，各有用途

| 来源 | 位置 | 用途 |
|---|---|---|
| **下游源码**（最好读） | 本地克隆 `…sources/realme-downstream.git` → `arch/arm64/boot/dts/19781/`（449 个文件） | 查接线、查时序、查供电；带注释与厂商修改记录 |
| 原厂 DTBO 反编译 | `…/artifacts/device/20261005T074931Z/dtbo-entry-0.dts` | 交叉验证源码与实机是否一致 |
| 运行中设备树 | `…/artifacts/device/20261005T074931Z/live-device-tree.tar` | 最终裁判：ABL 合并后实机真正用的树 |

已挑出关键文件复制到 [refs/19781/](../refs/19781/)（244 KB，见第 5 节）。

## 2. 已经从 Android 源拿到、并已进 samurai 主线 DTS 的

| 项 | Android 源写法 | 主线落点 | 状态 |
|---|---|---|---|
| 音量+ | `gpio_keys/vol_up`: `pm8150_gpios 6`,`GPIO_ACTIVE_LOW`,`KEY_VOLUMEUP`,`debounce 15` | `gpio-keys` + `&pm8150_gpios` pinctrl | ✅ 与源**逐字一致** |
| 音量− | `gpio_keys/vol_down`: `pm8150_gpios 7` 同上 | 同上 | ✅ |
| 按键 pin | `key_vol_up_default` / `key_vol_down_default`（`bias-disable`、`power-source = <1>`） | 同样两个 pinctrl 节点 | ✅（旧工程写的 `bias-pull-up`/`<0>` 已纠正） |
| UFS 供电 | `&ufshc_mem`: `vcc = pm8150_l10`、`vccq = pm8150_l9`、**`vccq2 = pm8150_s4`** | `vreg_l10a_2p5` / `vreg_l9a_1p2` / `vreg_s4a_1p8`（MTP 默认值） | ✅（旧工程的 L7A 是错的） |
| reserved-memory | 见 `live-device-tree.tar` 与基础 DTB | 21 个保留区 | ✅ |

> 这三项用 Android 源码独立复核了一遍，结论与之前用 DTBO/运行中树得到的一致。

## 3. 还能从 Android 源拿到、但主线**缺驱动**的部分

### 3.1 触控（Synaptics S3706）—— 接线已完全拿到

Android 源（`sm8150-mtp.dtsi` 916 行起）：

```dts
&qupv3_se17_i2c {                    // 主线对应：i2c17: i2c@c80000（sm8150.dtsi:1560）
        synaptics19081@20 {
                compatible = "synaptics-s3706";
                reg = <0x20>;
                interrupts = <122 0x00>;                 // TLMM GPIO 122
                vdd_2v8-supply = <&pm8150_l17>;          // 2.8V
                enable1v8_gpio = <&pm8150l_gpios 5 0x1>; // 1.8V 使能脚（output-low）
                irq-gpio = <&tlmm 122 0x2008>;           // 边沿触发
                reset-gpio = <&tlmm 54 0x1>;             // TLMM GPIO 54
                touchpanel,tx-rx-num = <15 34>;
                touchpanel,panel-coords = <1080 2400>;
        };
};
```

主线对应物：`i2c17` 下挂 `syna,rmi4-i2c`（主线 Synaptics RMI4 驱动）**或**新写一个
S3706 驱动；供电用 `vreg_l17a_3p0`，1.8V 使能脚要新增一个 `&pm8150l_gpios` 的
pinctrl 节点（Android 的 `enable_1v8_gpio` 就是 pm8150l GPIO5）。**能不能被主线 rmi4
认出来要试**，这是未知数。

### 3.2 面板（三星 SOFEF03F_M，1080×2400，DSC，90 Hz）

`dsi-panel-samsung-sofef03f-m-amoled-dsc-fhd-plus-90fps-cmd.dtsi`（806 行，已存）：

```
qcom,mdss-dsi-panel-type = "dsi_cmd_mode";
qcom,mdss-dsi-bpp = <24>;
qcom,mdss-dsi-reset-sequence = <1 5>, <0 10>, <1 10>;
qcom,mdss-dsi-bl-pmic-control-type = "bl_ctrl_dcs";   // 亮度走 DCS
qcom,mdss-dsi-te-pin-select = <1>;  wr-mem 0x2c/0x3c;   // TE
// 后面是几百行 init 序列（0x... 命令表）
```

主线有 msm dsi 控制器，但**没有 SOFEF03F_M 的面板驱动**；这份文件提供初始化序列、
时序、亮度方式，是写驱动的输入，不是可直接 include 的节点。

### 3.3 其它（都在 `sm8150-mtp.dtsi` 里）

| 功能 | Android 源线索 | 主线现状 |
|---|---|---|
| WiFi / BT | `wcn3990` 节点 + 供电 rails（`vreg_l7a_1p8` 等） | 主线有 wcn3990 驱动，首轮 disabled |
| 充电 / 电量 | `&pm8150b_gpios` 的 gpio1/7/12 ADC + `mp2650`/`bq27` + OPPO 私有 `oplus_chg` | 主线无对应驱动，最难的一项 |
| NFC | `sn100`（SN100T） | 主线有 nxp-nci，需要自行接 |
| 音频 | `sm8150-oppo-audio-overlay.dtsi` + TFA9874/AQT1000 | 需要 asoc 机器驱动 |

## 4. 使用限制（别踩的坑）

1. **私有 binding 不能搬**：`synaptics-s3706`、`oplus_chg`、`oppo,dtsi_no`、
   `qcom,mdss-*` 这些是下游/厂商属性，主线 schema 里不存在，照抄只会得到
   `dtbs_check` 报错和驱动不 probe。
2. **DT 给不了驱动**：面板、触控、充电的驱动在主线要么不存在要么不匹配。DT 只能提供
   "接在哪、什么电压、什么时序"，剩下的要写/适配驱动。
3. **vendor DTBO 套不到主线 DTB 上**：旧工程实测 `FDT_ERR_NOTFOUND`（标签与单元地址
   对不上）。所以主线 DTS 必须自建，Android 源只是数据来源。
4. **命名体系不同**：Android 用 `qupv3_se17_i2c`、`msm_gpio` 式 pinctrl；主线是
   `i2c17: i2c@c80000`、标准 pinctrl 子节点。搬运时必须做一次映射。
5. 有些事实不在 dts 里（regulator 默认电压、驱动内置延时），要去驱动源码或运行中树里找。

## 5. 已复制到本仓库的参考文件（`refs/19781/`）

| 文件 | 说明 |
|---|---|
| `sm8150-mtp.dtsi` | **本机板级文件（1334 行）**：按键、触控、UFS、WiFi/BT、充电、NFC、传感器 |
| `sm8150-mtp-overlay.dts` | DTBO 入口（39 行），include 上面的 dtsi 与音频 overlay |
| `dsi-panel-samsung-sofef03f-m-amoled-dsc-fhd-plus-90fps-cmd.dtsi` | 本机面板：时序 + 数百行 init 序列 |
| `sm8150-sde-display.dtsi` | 显示子系统与面板选择逻辑 |
| `sm8150-pinctrl.dtsi` / `sm8150-qupv3.dtsi` | TLMM 与外设 pin 状态、QUP 实例定义 |
| `sm8150-v2.dts` / `sm8150.dts` / `Makefile` | 基础 dts 与 DT 构建规则（本项目 build 的是 `sm8150-v2-mtp.dtb` + overlay） |

重新取用（无需联网，用旧工程留下的浅克隆）：

```bash
R="/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git"
git --git-dir="$R" ls-tree -r --name-only HEAD arch/arm64/boot/dts/19781
git --git-dir="$R" cat-file -p HEAD:arch/arm64/boot/dts/19781/sm8150-mtp.dtsi
```

参考脚本：[scripts/list-19781.sh](../scripts/list-19781.sh)、
[scripts/extract-19781.sh](../scripts/extract-19781.sh)、
[scripts/dump-android-facts.sh](../scripts/dump-android-facts.sh)。
