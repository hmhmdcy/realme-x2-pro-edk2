# 当前：Linux v7.3.1 标准 ARM64 镜像已刷入并通过重启

核对日期：2026-11-06。设备当前运行
`7.3.1-rmx1931-samurai-v731`，Wi-Fi SSH 可用。详细源锁、构建命令、
实验矩阵和剩余边界见
[STANDARD-ARM64-V731](linux-port/docs/STANDARD-ARM64-V731.md)。

## 本轮完成

- Linux 正式稳定版 `v7.3.1` 已成为唯一部署基线，不再部署
  `7.3.0-rc6` bring-up 镜像；
- 源码为官方 tarball
  `fa595aad93734f829c963c2a90ef7c3673224fd7fdae7b49406e397cde2de231`
  解包后的两提交树：
  `09455be5a`（v7.3.1 baseline）和
  `824dc0a56`（samurai standard glue）；
- 内核补丁、精确配置和生产 DTS wrapper 已落入
  [`linux-port/patches/v7.3.1`](linux-port/patches/v7.3.1/)、
  [`linux-port/configs/v7.3.1`](linux-port/configs/v7.3.1/) 和
  [`linux-port/dts/v731`](linux-port/dts/v731/)；
- 最终 boot 已刷入 `boot` 分区，设备内回读哈希与候选一致；
- 三次启动均成功：首次 `a38fc278-644b-4387-97cf-f5c0c06aa541`，
  两次普通重启后分别为 `3df82213-3f55-4ab6-b6af-a8a54e73645d`、
  `9183a664-475e-46f6-b850-ad35aa99a93b`；
- `taint=0`，三路 remoteproc `running`，`sensor-power` 为
  `vdd=1 vddio=1`，UDC `configured`，DSI `On`，Wi-Fi SSH、KWin、
  plasmashell、USB 和 OpenRC 服务正常；
- 标准 `power_supply` 绑定为 `bq28z610-0` 与 `mp2650-input`，不再加载
  私有 managed-charging 模块；
- 旧 `samurai-charging` 已从所有 runlevel 移除，并在第三次启动确认不再
  尝试加载；源码安装钩子改为旧内核上的显式 opt-in，
  `samurai-platform` 5-r14 不再依赖它；
- `samurai-dt-v1-abi.json` 已改到 v7.3.1 基线，声明 MP2650 与标准
  DWC3 绑定；12 个资源全部通过契约检查。

## 当前镜像身份

| 项 | SHA-256 |
| --- | --- |
| boot | `c8a6c616f60c8ee8f314bfc9e1329c61af3eb070b0cee3724b99080ad3444eaf` |
| BdsDxe | `f3b946b1660cd444048aba7e5fe434e08a6f41d8dd11cc83f944455fea6855ac` |
| Image | `dc4c5623551824d170397cd93a01256dfc0eadb0d13b949c54e64f6e0ea61eda` |
| DTB | `3261908efb6730f43f41e9ab752b03a107ab583d451f433c7eb648760ed79ebb` |
| modules | `fc1607efc672b047318936fdada05f33a286815fac46ee6efac05291c6376bbb` |
| logdump | `31049b6c328c0ad4716189ed20854cf3839b656edb17f6fd6c60e47205fe38a4` |

产物目录：`E:\edk2-samurai-out\standard-arm64-v731\`。
当前源码 boot：
`source-final-boot\boot-eud-production-off.img`。

## 命令行边界

最终运行时命令行：

```text
console=tty0 loglevel=4 panic=15 clk_ignore_unused
```

`ignore_loglevel`、`pd_ignore_unused`、`regulator_ignore_unused` 已移除。
单独移除 `clk_ignore_unused` 实测停在 fastboot 并已回滚，因此这一项是
当前板级必要约束，不是通用默认值。后续应定位缺失的 clock consumer，
再删除该约束。

EDK2 `PlatformBm.c` 已同步为最终字符串。EDK2 GCC LTO 对命令行数组尺寸
敏感，所以源码保留历史 108-`CHAR16` 分配并用 57 个尾随空格填充；内核
忽略空格。用固定 staging 树重编旧/新源码后，BDS 审查为
`passed=true`、`printable_metadata_only`，Smbios/UiApp 逐字节相同。

## 回退

- 上一已验证 boot：
  `E:\edk2-samurai-out\standard-arm64-v731\cmdline-final\boot\boot-eud-production-off.img`
  `236360a31ce397ddceec2eca91b0a4c606d93f754ced0c19325b4c288568ec5e`；
- 更早生产回滚 boot：
  `E:\edk2-samurai-out\runtime-20261106-eud-default-off\boot\boot-eud-production-off.img`
  `8d1d6de2a3c63599080a16ded6ced1e410c9434e4e411a969e19b25ff03e690b`；
- 刷写入口为 fastboot `62bc28a1` / `msmnile`；进入 bootloader 必须使用
  设备上的 `RESTART2("bootloader")` 脚本，不能依赖 BusyBox
  `reboot bootloader`。

## 标准边界

已切到主线已有模型的接口包括 `mps,mp2650`、`bq28z610`、
`qcom,sm8150-dwc3`/`qcom,snps-dwc3`、UDC class/configfs、DRM/KMS、
backlight、remoteproc subdevice、ASoC/ALSA/UCM、evdev/input-ff 和 IIO。

保留的板级极薄部分只有 DTS 接线、sensor-power regulator 时序、
sofef03f 面板描述、AW8697 触觉板级驱动、MAX98937 与 samurai ASoC glue。
相机 ICP/CAMSS 实验、APSD/私有 USB-input、私有 managed-charging KO、
生产 EUD serial、vendor 根属性和 `samurai_diag` trace 依赖均未进入该镜像。

## 未完成

1. 当前 boot 内嵌本地测试 initramfs（含测试凭据），只能用于本机测试，
   不能作为通用发布镜像；
2. 只验证了普通重启，尚未做断电冷启动、实际 suspend/resume、90Hz 模式
   切换和长期稳定性；
3. 尚未覆盖 RAM/UFS SKU，也未做 k270 旧内核回归；
4. RPMh 日志仍有 `ret=-95` 读噪声，启动与运行健康，但根因未清；
5. 标准 ESP/BDS 回退路径、持久 UEFI 变量尚未实现；
6. 相机与受管高压充电仍是独立未来 profile，不混入当前 v1 契约。

下一轮优先顺序：先解决 `clk_ignore_unused` 对应的真实 clock consumer，
再做断电冷启动与 suspend/resume；随后把测试 initramfs 与设备私钥从
发布镜像中剥离，并实现标准 ESP/BDS 回退。
