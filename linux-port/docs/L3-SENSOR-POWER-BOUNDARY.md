# L3-02 预检：sensor-power 的真实边界

整理日期：2026-11-05。

本文把 `sensor-power` 从“私有 sysfs”拆成可判断的驱动、资源和消费者
边界。2026-11-05 已实现方案 A 的离线加法（可选 DT 数据下放），并
完成了 `rproc_subdev` 的真机运行态验收；本文不删除
`/sys/devices/platform/sensor-power/state`，也不把当前 bring-up 行为
当成已完成的标准接口。

## 0. 运行态结论与当前目标（2026-11-05）

方案 A 之后的 genpd 实验已在真机 `#9` 上实际测试并否决：

- SLPI 能启动并到达 running；
- PAS 在 handover 时释放所有 proxy power domain，sensor rail 仍为
  `vdd=0 vddio=0`；
- `samurai-ssc` 报 `Sensor power domain did not enable`，启动失败；
- 已用 boot/logdump 分区逐字节回读校验后回退到基线 `#5`，SSC、
  SLPI/modem/adsp、加速度计和光线 readiness 均恢复。

因此，sensor rail 不是“PAS boot-time proxy PD”。当前目标是极薄板级
sequencer 注册通用 `rproc_subdev`：

```text
sensor-power
  compatible = "realme,samurai-sensor-power"
  qcom,rproc = <&remoteproc_slpi>
  vdd-supply = <&vreg_l7c_3p0>
  vddio-supply = <&vreg_l8c_1p8>
```

`prepare` 上电，`unprepare` 下电；顺序仍是 VDD → 10 ms → VDDIO 和反向
关断。`/sys/devices/platform/sensor-power/state` 只保留只读兼容视图，
不再允许用户态控制电源。实现为
[`0021-misc-samurai-sensor-power-rproc-subdev.patch`](../patches/0021-misc-samurai-sensor-power-rproc-subdev.patch)。

真机候选为 DTB `754a13b0716b97948ef855f1aedb22b5c90e2fffadcdc7113dcebab37096ab65`
、boot `ad48e3434192343b7738818fd2166787774138c87c3f7a0c04c6f611b16eb226`、
Image `edb15bd638cd4ac5ba37f5e0ddda54b304e6a0b4d73f93588435568c1ee5dcb2`
和 logdump `dd1a3cea944bda9b63537ec5f2571edfacadb54b0a3d8e25de9fcf70cebda9b3`；
metadata review `passed=true`、`non_dtb_ffs_body_changes=0`。真机已
从块设备回读两个分区，内核为 `#2`；SSC 启动/停止、重启后自动冷启动
均通过，详见 [rproc_subdev 候选](L3-02-RPROC-SUBDEV-CANDIDATE.md)。

## 1. 当前拓扑

板级节点在
[`sm8150-samurai-common.dtsi`](../dts/split-ba61/sm8150-samurai-common.dtsi)
中：

```text
sensor-power
  compatible = "realme,samurai-sensor-power"
  vdd-supply = <&vreg_l7c_3p0>      2.856–3.104 V
  vddio-supply = <&vreg_l8c_1p8>    1.800 V
  qcom,rproc = <&remoteproc_slpi>
```

驱动是 `drivers/misc/samurai-sensor-power.c`，它做三件事：

1. 用标准 regulator consumer API 取得两路电源；
2. 注册通用 `rproc_subdev`，在 prepare 按 VDD → 延时 → VDDIO 上电，
   在 unprepare 按 VDDIO → VDD 下电；
3. 在 `/sys/devices/platform/sensor-power/state` 提供只读
   `vdd=0/1 vddio=0/1` 兼容视图。

电源生命周期由 remoteproc core 的 prepare/unprepare 顺序保证；不再
需要用户态在 `state` 中写入，也不把 SLPI 的 boot-time proxy PD
误当成运行期电源。

## 2. 消费者

| 消费者 | 用法 | 约束 |
| --- | --- | --- |
| [samurai-ssc.py](../ssc/samurai-ssc.py) | 启动/停止 SLPI；sensor rail 由 `rproc_subdev` 跟随生命周期；只读断言 `vdd=1 vddio=1` / `vdd=0 vddio=0` | 不在用户态直接控制电源 |
| [native-quiesce.py](../../reference/kernel270/native-quiesce.py) | 只读断言两路电已关闭 | 可以改为标准只读接口 |
| [restart-bootloader.py](../../reference/kernel270/restart-bootloader.py) | 只读断言两路电已关闭 | 可以改为标准只读接口 |
| 板级 quiesce/重启流程 | 通过上述脚本确认 SLPI 不再持有电源 | 不能在电源仍开时重启 |

当前没有发现第三类写入者，也没有发现桌面直接写这个节点。仍应在每次
内核/服务变更时重新跑消费者搜索，不能把本次清单当作永久 ABI。

## 3. 可选的标准化阶梯

### A. 先做行为保持的 DT 数据下放（推荐）

把 C 里的 VDD/VDDIO 电压范围、延时和 load 常量变成可选 DT 属性，
驱动保留同样的默认值；旧 DTS 不写这些属性时行为完全不变。

候选属性只放在 `sensor-power` consumer 节点，不冒充 regulator core
的标准约束：

```text
realme,vdd-min-microvolt
realme,vdd-max-microvolt
realme,vddio-min-microvolt
realme,vddio-max-microvolt
realme,vddio-delay-us
realme,rail-load-microamp
```

这不是最终标准 ABI，只是把板级数字从 C 移到 L2，并让旧默认值可回退。
必须先离线编译驱动、在旧 DTS 上验证默认分支不变，再谈运行态。

### B. 用 regulator 约束替代部分硬编码（中风险）

`vreg_l7c_3p0` 和 `vreg_l8c_1p8` 已有相同的
`regulator-min/max-microvolt` 约束。可以评估删除驱动里的
`regulator_set_voltage()`，只保留 `regulator_enable/disable` 和
load/sequence。

风险：这两路电可能被其它 consumer 共享；删除 `set_voltage()` 后
实际电压可能由别的 consumer 决定。必须在 SLPI 启动/停止和冷启动
矩阵里验证，不能只做静态编译。

### C. 聚合为 power-domain / remoteproc supply（高工作量）

把“两路电 + 延时 + SLPI 生命周期”建模为 power domain，或让 SLPI
remoteproc 直接消费电源。这是最接近标准平台模型的方案，但需要改
remoteproc/驱动接口，并证明现有 `samurai-ssc.py` 的启动顺序仍成立。
在 A/B 的运行时证据完成前，不应直接跳到 C。

## 4. L3-02 首轮候选

首轮只做 A 的**加法**：

- 驱动读取可选 DT 属性，缺省值保持当前常量；
- DTS 写入当前实测/公开板级数字；
- 保留旧 sysfs 和旧消费者；
- 不改 `rproc` 锁、上下电顺序、load 调用位置和 shutdown 行为。

验收至少需要：

1. `dtc` 构建 DSP/DTS 不改变树上既有属性值；
2. 驱动编译通过，`modpost` 无新增未解析符号；
3. 旧 DTS 路径（没有新属性）仍走默认分支；
4. SLPI 启动/停止、quiesce 只读检查、重启前两路电关闭；
5. 失败时可回到原模块/DTB，不需要重装 rootfs。

### 4.1 2026-11-05 离线实现结果

方案 A 已落为
[`0018-misc-samurai-sensor-power-optional-dt-data.patch`](../patches/0018-misc-samurai-sensor-power-optional-dt-data.patch)，
SHA-256 `3248bc0e1e81f364fbf3ebf6ad2a3f50251b65bb0d83dee8e48a7275fabb7a37`。
补丁同时修改驱动和
`arch/arm64/boot/dts/qcom/sm8150-samurai.dts`。

驱动在读取任何可选属性前先填入原常量：

| 参数 | 缺省值 | 可选 DT 属性 |
| --- | ---: | --- |
| VDD 最小电压 | 2,856,000 uV | `realme,vdd-min-microvolt` |
| VDD 最大电压 | 3,104,000 uV | `realme,vdd-max-microvolt` |
| VDDIO 最小电压 | 1,800,000 uV | `realme,vddio-min-microvolt` |
| VDDIO 最大电压 | 1,800,000 uV | `realme,vddio-max-microvolt` |
| VDD → VDDIO 延时 | 10,000 us | `realme,vddio-delay-us` |
| rail load | 200,000 uA | `realme,rail-load-microamp` |

旧 DTS 不写这些属性时仍走完全相同的默认常量；属性格式错误会返回错误，
不会被静默当成缺省。上下电顺序、`rproc` 锁、手动 `state` 写入和
shutdown 行为均未改动。电压范围倒置或 load 超过 `INT_MAX` 时 probe
失败。

离线构建结果：

- 候选 OS DTB：`89604b9ce7ea1502dc3a73f1523fc48d46044166792dbbd2d5c2aa4f9d66d570`
  （114,709 B），由独立 wrapper
  `linux-port/dts/l3/sm8150-samurai-os-sensor-data.dts` 构建；相对旧
  OS DTB `f7959f8a...a3f0` 只有 6 个新增属性：
  `changed_properties=0`、节点变化 0、删除属性 0；
- 六个属性经 `fdtget` 读回分别为 `0x2b9440`、`0x2f5d00`、
  `0x1b7740`、`0x1b7740`、`0x2710`、`0x30d40`；
- 驱动用精确 k363 源树、ARM64 和 `W=1` 编译 `.ko` 通过；这里的
  `CONFIG_SAMURAI_SENSOR_POWER=m` 只是命令行临时覆盖，不写回
  `.config`。modpost 无 warning/error，vermagic 与实机 release
  预期一致；
- 候选 `.ko` SHA-256
  `d3d602165a0a8d76a4392b71f507152edc0c6e9603e04f4acd34c7457bc6eeb5`
  （77,048 B）；基线 `.ko` SHA-256
  `332d53135a82f96b056b390629f996ef0137354cef2fa78fbdb18676e8f84f2a`
  （72,312 B）；
- 新增的未解析符号只有标准的 `dev_err_probe` 和 `of_find_property`，
  没有新增私有内核接口；
- 候选构建结束后临时替换的源文件已恢复为原 SHA-256
  `2b662bfa...afbd4`。

**部署边界：** k363 的 `.config` 是
`CONFIG_SAMURAI_SENSOR_POWER=y`，所以候选 `.ko` 只用于编译、modpost
和符号检查，不是本次可安装的运行态产物；当前内核已经内建该驱动，不能
用同名模块覆盖。真正的 G2 候选是带本补丁重新构建的 `Image`，必须保留
旧 `Image`/模块集合和可回退的 `logdump` 写入路径。

完整 G2 `Image` 已用同一个精确 k363 源树和 `y` 配置构建成功，release
仍为 `7.3.0-rc6-rmx1931-samurai-k363+`；详见
[L3-02 G2 候选](L3-02-G2-CANDIDATE.md)。

本地收据：

- `E:\edk2-samurai-out\layer-adaptation-20261105\l3-sensor-power-dt\dtb-build-exact-k363\build-result.json`
  （SHA-256 `989a5522...42d1`）；
- 同目录 `os-vs-sensor-power-dt.json`
  （SHA-256 `4903a892...65b0`）；
- `E:\edk2-samurai-out\layer-adaptation-20261105\l3-sensor-power-dt\exact-k363-candidate-build.log`
  （SHA-256 `6699c9d9...2e70`）；
- 同目录 `samurai-sensor-power.exact-k363.candidate.ko`；
- 基线构建日志 `exact-k363-baseline-build.log`
  （SHA-256 `0315b232...b56a`）。

G2 候选 `Image` 和已替换 `\Image` 的 logdump 镜像已另行准备，详见
[L3-02 G2 候选](L3-02-G2-CANDIDATE.md)。候选 `Image`
SHA-256 `9ee6d800...ef17`，release 与 k363 相同，内嵌 initramfs
与原 k363 逐字节一致；尚未写入设备。

当前状态：**方案 A 已实现并通过离线 DTB/驱动编译；B/C 未改；
`rproc_subdev` 的 G2 已真机通过（含启动/停止和冷启动）**。下一步
是独立的 G3 窗口激活规范 OS DTB，并补 k270/k363、quiesce 和重启前
两路电关闭的更完整矩阵；不能把本次 sensor 运行态结果写成 DTB ABI
已冻结。
