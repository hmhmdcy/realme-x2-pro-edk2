# L3-02 G2 candidate: sensor-power optional DT data

整理日期：2026-11-05。

这是 L3-02 方案 A 的离线 G2 历史候选。它只保留为 0018 的构建证据，
不是已部署状态；现行 `0021` `rproc_subdev` 真机结果见
[L3-02 rproc_subdev 候选](L3-02-RPROC-SUBDEV-CANDIDATE.md)。

## 0. 运行态结论（2026-11-05）

该方案的 genpd 后继实验已在真机 `#9` 上否决：SLPI 能启动，但 PAS
在 handover 时释放 proxy PD，`sensor-power` 仍为 `vdd=0 vddio=0`，
SSC 随即失败。设备已完整回退到基线 `#5`，回退 boot/logdump 的
块设备回读哈希均通过。当前替代方案见 `0021` 的 `rproc_subdev`：
电源跟随通用 remoteproc prepare/unprepare，而不是 PAS boot-time
proxy power domain。下面的 0018 产物只保留为历史离线证据。

## 1. 内容

- 源码：source-lock 的精确 k363 提交
  `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`；
- 补丁：
  [`0018-misc-samurai-sensor-power-optional-dt-data.patch`](../patches/0018-misc-samurai-sensor-power-optional-dt-data.patch)；
- 精确配置：`23e088a9...30ed`，与 k363 配置逐项一致；
- 唯一配置改写：`CONFIG_INITRAMFS_SOURCE` 从缺失的
  `/mnt/samurai-full282/input-initramfs363` 指向从 k363 `vmlinux`
  提取的原始 gzip initramfs；
- 内建驱动：`CONFIG_SAMURAI_SENSOR_POWER=y`，没有改成模块；
- 构建期间临时应用补丁，构建结束后源文件恢复为原 SHA-256
  `2b662bfa...afbd4`。

## 2. 产物

| 产物 | SHA-256 | 大小 |
| --- | --- | ---: |
| `Image-sensor-power-k363` | `9ee6d800468235c32761896f00c1ec7b352ab4aaa877dd9e5a425e566241ef17` | 59,243,008 B |
| `logdump-sensor-power-k363.img` | `008104d0ec55b4fa929fd08480b4eb12e8c3ffee3ffb877ceed244752967020f` | 67,108,864 B |
| `k363-initramfs.cpio.gz` | `12fbc52d5f4cbea7dcda53eb1b043b54f30e727ad7a62b63db79f8322925ae3a` | 15,063,641 B |
| `System.map-sensor-power-k363` | `e830330646f92b282513a2340bd60229f8c70670b28593b9030b71c364e12878` | 9,008,412 B |

产物目录：
`E:\edk2-samurai-out\layer-adaptation-20261105\l3-sensor-power-dt\g2-image-candidate\`。

对照基线：

- 原 k363 Image：`15746aab...d6468`，59,243,008 B；
- 原 logdump 镜像：`1869c02f...5a83`，67,108,864 B
  （`kernel363/logdump-k363-candidate-private.img`）；
- 原 initramfs gzip payload：`12fbc52d...ae3a`；
- 原运行 DTB：`dcdd74ec...2c8d`。

构建日志：
`exact-k363-image-build.log`，SHA-256
`b199c5e3371ab61a1a66ba09e3f0d3e3b67fb955b371de7bdde852722d23a3e2`。

## 3. 已验证

- `Image` release 为 `7.3.0-rc6-rmx1931-samurai-k363+`，与部署链
  release 一致；
- `Image` 文件类型为 ARM64 Linux boot executable；
- 新构建的 initramfs payload 与原 k363 payload 逐字节相同
  （`cmp=0`、SHA-256 相同）；
- 新配置与原 k363 配置的有效项差异只有 `CONFIG_INITRAMFS_SOURCE`
  的构建路径；
- `Image` 中包含新驱动字符串
  `realme,vdd-min-microvolt`；
- 新 `vmlinux.symvers` 与基线 `Module.symvers` 中的 15,097 个
  `vmlinux` 导出符号逐项相同，排序后 SHA-256 都是
  `c3a41b1e...4861`；补丁没有增加或删除导出内核 ABI；
- 候选 logdump 镜像中 `\Image` 为 `9ee6d800...ef17`；
- 候选 logdump 镜像中的 `\samurai.dtb` 仍为
  `dcdd74ec...2c8d`；
- FAT 内容仍只有 `Image` 和 `samurai.dtb`，剩余空间未变化；
- 精确 k363 驱动编译和 modpost 已通过；`.ko` 只作编译证据，因为
  `CONFIG_SAMURAI_SENSOR_POWER=y`。

## 4. G2 部署前置

必须在一个明确的维护窗口执行，不与其他层改动合并：

1. 记录当前 boot ID、release、boot/logdump/GPT 哈希；
2. 读回当前 logdump 的 `\Image`，确认它仍是
   `15746aab...d6468`；
3. 保留当前 logdump 镜像、原厂 boot image 和 EDL 路径；
4. 只写 logdump，不写 boot、GPT、DTB 或模块；
5. 重启后检查 EUD/pstore、USB NCM/SSH、UFS、显示和
   `/sys/devices/platform/sensor-power/state`；
6. 通过 sensor-power 手动状态切换验证 SLPI offline 时的
   VDD → delay → VDDIO 和反向关断；
7. 再跑 quiesce/重启前两路电关闭检查；
8. 任一项失败立即恢复到基线 logdump，不继续叠加 DTB 或 UAPI 改动。

## 5. 边界

该候选不改变当前 boot 内嵌 DTB。当前 DTB 没有六个可选
`realme,*` 属性时，驱动走原默认值，因此本次 G2 只验证“解析器存在但
不改变默认行为”。六个属性的实际 DT 激活是
`89604b9c...d570` DTB 候选，属于单独的 G3 窗口。

## 6. 可选的 G3 DTB 载体

为后续单独 G3 窗口准备的 boot 候选：

- 源 boot：`758694a1...a4acd`；
- 新内嵌 DTB：`89604b9c...d570`；
- boot 候选：
  `15f9e4d568b9785c10b98eb36a00b061068f6c911c9b64446783f634a713443f`；
- `changed_ffs_guids` 只有 DTB GUID
  `25462cda-221f-47df-ac1d-259cfaa4e326`；
- `non_dtb_ffs_body_changes=0`，`BdsDxe`、`PlatformSmbiosDxe`、
  `UiApp` 全部逐字节相同；
- metadata review `passed=true`。

收据：
`E:\edk2-samurai-out\layer-adaptation-20261105\production-boot-candidate-l3-sensor\`。

该 boot 候选仍未刷入，并且会移除当前实验 DTB 的充电 5V1500、
camera ICP、EUD route 和实验 bootargs；不能与 G2 Image 写入同一次
维护动作。必须先完成 G2，再单独决定是否保留/迁移这些实验项后再进
G3。

当前状态：**已被 0021/`#2` 真机验收取代，不再作为刷入候选**。
