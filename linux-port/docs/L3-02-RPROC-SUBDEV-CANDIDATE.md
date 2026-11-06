# L3-02 rproc_subdev 候选（2026-11-05）

本文记录 `sensor-power` 从 PAS/genpd 方案收敛到通用 remoteproc
生命周期后的实现。状态：**已刷入真机并通过运行态验收**。真机使用
kernel `#2`，验证了 SLPI 启动/停止、两路电顺序、SSC readiness，
以及重启后的自动冷启动。

2026-11-06 更新：该机制已进入 Linux v7.3.1 标准镜像；当前部署、
源码锁和重启收据见
[STANDARD-ARM64-V731](STANDARD-ARM64-V731.md)。

## 1. 设计

板级 `sensor-power` 仍负责两路 regulator 的板级顺序，但不再提供
电源控制 sysfs，也不挂到 PAS 的 boot-time `proxy_pds`。它通过
`qcom,rproc = <&remoteproc_slpi>` 取得通用 `struct rproc`，并注册
`struct rproc_subdev`：

- `prepare`：SLPI 启动前按 VDD → 10 ms → VDDIO 上电；
- `unprepare`：SLPI 停止后按 VDDIO → VDD 下电；
- `state`：只读的 `vdd=0/1 vddio=0/1` 兼容视图。

这样，电源和 `rproc_boot()`/`rproc_shutdown()` 是同一个生命周期，
不依赖用户态写电源节点。实现补丁：
[`0021-misc-samurai-sensor-power-rproc-subdev.patch`](../patches/0021-misc-samurai-sensor-power-rproc-subdev.patch)，
SHA-256 `dae82998aa0400e594fd537b0e895a520f61ce378271d820f6fb44174180b62c`。

## 2. 为什么否决 genpd

真机 `#9` 的 `power-domains` 版本已经启动测试：

- SLPI 能到 `running`；
- PAS 在 handover 时释放 `proxy_pds`；
- `sensor-power` 保持 `vdd=0 vddio=0`；
- SSC 报 `Sensor power domain did not enable`，启动失败。

这不是 DTB 没写对，而是 PAS proxy PD 的语义只覆盖 firmware
load/authentication 窗口，不应承担 SLPI 运行期板级供电。设备已回退
到基线 `#5`，并验证 SSC、三个 remoteproc、加速度计和光线 readiness
恢复。

## 3. 离线产物

| 产物 | SHA-256 | 大小 |
| --- | --- | ---: |
| 实验 DTB | `754a13b0716b97948ef855f1aedb22b5c90e2fffadcdc7113dcebab37096ab65` | 116,748 B |
| in-place boot | `ad48e3434192343b7738818fd2166787774138c87c3f7a0c04c6f611b16eb226` | 100,663,296 B |
| Image（r2） | `edb15bd638cd4ac5ba37f5e0ddda54b304e6a0b4d73f93588435568c1ee5dcb2` | 59,439,616 B |
| logdump（r2） | `dd1a3cea944bda9b63537ec5f2571edfacadb54b0a3d8e25de9fcf70cebda9b3` | 67,108,864 B |

构建输入：

- release：`7.3.0-rc6-rmx1931-samurai-k363+`；
- UTS version：`#2 SMP PREEMPT Thu Nov 5 22:09:57 CST 2026`；
- 基线配置：`build-hz90/.config`，VA 39/PA 48；
- initramfs source：`/tmp/initramfs.cpio.gz`，SHA-256
  `04765104e92f1cca1415669b09eafb658ff1a205f25facd347f2699dc7dc1952`；
- 新构建 initramfs payload 与基线逐字节相同；
- `vmlinux.symvers` 与基线均为 15,122 项且逐行相同；
- `rproc_add_subdev`、`rproc_remove_subdev`、`rproc_get_by_phandle`
  均为内核已导出符号。
- 补丁 `0022-misc-samurai-sensor-power-legacy-rproc-fallback.patch` 保留
  旧 DTB 的 `remoteproc` 回退；新 DTB 优先使用 `qcom,rproc`。

> `925d7f4d...` / `694e8dff...` 是加 legacy fallback 前的旧候选，
> 已被本表产物取代，不能作为回退目标。

## 4. 载体验证

- DTB 对当前 live DTB 的语义差异只有 sensor 节点的
  `remoteproc` → `qcom,rproc`，其余实验 profile 未改变；
- boot 从 `758694a1...` 基线只替换 DTB FFS；
- `changed_ffs_guids` 只有
  `25462cda-221f-47df-ac1d-259cfaa4e326`；
- `non_dtb_ffs_body_changes=0`；
- `BdsDxe`、`PlatformSmbiosDxe`、`UiApp` 逐字节相同；
- `metadata-review.json`：`passed=true`；
- logdump 由 `3e406...` 基线只替换 FAT `\Image`；`mdir` 显示
  `Image` 为新 Image，`mtype` 回读 SHA-256 相同，`fsck.fat -n` 通过。
- 真机 fastboot 只写 `boot` 和 `logdump`，分区大小分别为
  `0x6000000` / `0x4000000`，类型均为 `raw`；写入后从
  `/dev/disk/by-partlabel/{boot,logdump}` 回读的 SHA-256 分别逐字节
  等于 `ad48...` 和 `dd1a...`。

## 5. 真机运行态验收

设备序列号 `62bc28a1`、fastboot product `msmnile`。刷入后启动到：

```text
Linux samurai 7.3.0-rc6-rmx1931-samurai-k363+ #2 ... aarch64 Linux
```

启动路径：

- `samurai-sensor-power` 输出
  `SSC supplies bound to slpi lifecycle`；
- SLPI `rproc_boot()` 时输出 `sensor supplies enabled for slpi`；
- SLPI、modem、adsp 三个 remoteproc 均为 `running`；
- `/sys/devices/platform/sensor-power/state` 为 `vdd=1 vddio=1`；
- `samurai-ssc` 自动启动，`iio-sensor-proxy` 与 `tinydm` 随后启动；
  加速度计和光线 readiness 日志均包含真实测量，并完成 disable；
- USB NCM/SSH 在重启后恢复，未因 SLPI 电源生命周期变化断开。

停止路径（同一次启动内）：

- 停止 `tinydm` 与 `iio-sensor-proxy` 后停止 `samurai-ssc`；
- SLPI 变为 `offline`；
- `sensor supplies disabled after slpi stop`；
- `/sys/devices/platform/sensor-power/state` 为 `vdd=0 vddio=0`；
- `samurai-ssc stop` 返回 0，未再出现
  `Sensor power domain did not enable`。

两次重启均能重新自动启动 SSC；第二次冷启动完成时间约 70 s。最终
运行态 boot ID 为 `adbd8ef6-873f-46b7-b4fc-a87ffd5fc848`，SLPI、
modem、adsp 均为 `running`，`sensor-power` 为 `vdd=1 vddio=1`。真机
证据保存在
`E:\edk2-samurai-out\layer-adaptation-20261105\rproc-subdev-r2\`：

- `runtime-dmesg.log`：本次启动 dmesg；
- `runtime-stop.txt`：停止路径、状态和 dmesg 摘要；
- `runtime-final-dmesg.log` / `runtime-final-summary.txt`：最终回读
  boot ID、三路 remoteproc、服务状态和分区哈希；
- `runtime\samurai-ssc\`：SSC 状态、传感器 readiness 和文件服务日志；
- `logdump-rproc-subdev-r2.img`：已刷入的 logdump r2。

### 5.1 规范 OS DTB 的 G3 激活

规范 OS DTB
`b6faa45f7aabdf3d9a19e90bc566dd6da94fabd68c525e12072f8914030c1785`
已封装进 boot
`93ce2bfe5207e7cc63865a58fe637d13c345bfd14048ac7396936c6e23f30df7`
并真实启动。boot metadata review 通过，且只替换 DTB FFS。启动后
boot 分区回读哈希与候选一致，boot ID 为
`430ddbdc-f43d-4cfc-a2de-cfd8860e5f3f`。

保存的 live FDT 与候选 DTB 的语义差异只有动态 `/chosen/bootargs`，
没有硬件节点或普通属性缺失；报告 SHA-256
`15ef1317d322b44b8b2b2f3f227df10f047d23e204ac5b2f4742934586992863`。
这证明标准 `qcom,rproc` 属性在规范 DTB 中仍能驱动 SLPI 生命周期：
三路 remoteproc 为 `running`，`sensor-power` 为
`vdd=1 vddio=1`，SensorProxy 的加速度计和光线 claim 成功。

该窗口未完成完整验收：USB gadget 没有 attach，`usb0` 无载波，
Windows 看到设备挂在 EUD hub `05c6:9500` 下；重启后 SSH/USB 也未
恢复。根因是 `serial@88e0000` 仍为 `okay`，且板级 `qcom_eud_com`
probe 无条件写 `CSR_EUD_EN=1`。这不是 `qcom,rproc` 回退，也不能通过
重新加入私有 `eud-off-route` 解决。

同一 boot 还观测到 `samurai-charging` 的独立启动失败
（请求 500000 µA，实际 effective input 900000 µA）。它与
`sensor-power`/SLPI 生命周期无关，不能作为本驱动失败证据；应另开
充电控制工作包处理。

## 6. 下一步

本次只完成 L3-02 标准 `rproc_subdev` 的运行时收敛；尚未完成
`samurai-dt-v1` 冻结或全平台标准化。下一步按顺序：

1. 修复生产启动的 EUD ownership：默认关闭 EUD，或改用主线
   role-switch/`enable` 模型；私有 `eud-off-route` 和 `qcom_eud_com`
   只保留在 debug profile；
2. 恢复设备后补 USB gadget、`udc`、`usb0`、SSH 和冷/暖重启验证；
3. 将 source lock 从 `7.3.0-rc6` 迁到正式稳定版 `7.3.1`，再跑
   k270/k363 运行态矩阵和 SKU 矩阵；
4. 把 boot/logdump/部署脚本做成可重复流程，继续只允许分区级最小
   写入和块设备回读；
5. L4 旧 `state` sysfs 保留为兼容视图，待消费者迁移后再删除，并把
   充电、显示、USB、音频按同一“通用子系统 + DTB 数据 + 小 board
   glue”模板收敛。
