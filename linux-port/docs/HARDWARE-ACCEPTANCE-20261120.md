# 官方稳定版镜像：实机接口验收（2026-11-20）

镜像：`samurai-stable-f2fs-partuuid.simg`
（`E:\edk2-samurai-out\standard-arm64-v731\rootfs-stable-20261119-clean\`）
系统：`postMarketOS v26.06`，Alpine v3.24 基线
内核：`7.3.1-rmx1931-samurai-v731-usbwake-otg`
设备：`192.168.0.105`（WiFi；DHCP 动态地址，**不是**历史记录的 `.106`）

结论：**系统级服务全部 healthy，传感器链路完全按发行版接口工作。**
相机与内核 GNSS 字符设备仍是缺口，属于内核层而不是发行版层。

## 一、系统状态

```
systemctl --failed            ->  (空，0 个失败单元)
```

| 服务 | 状态 |
|---|---|
| `samurai-radio` | active |
| `samurai-ssc` | active |
| `samurai-gnss-assist` | active |
| `samurai-usb-network` | active |
| `samurai-usb-recover` | active |
| `iio-sensor-proxy` | active |
| `bluetooth` / `NetworkManager` / `ModemManager` / `sshd` / `usb-signaller` | active |
| `nftables` | disabled / inactive（内核 `CONFIG_NF_TABLES=n`，已按 preset 关掉） |

remoteproc 三路全部 `running`：

```
remoteproc0 name=slpi  state=running
remoteproc1 name=modem state=running
remoteproc2 name=adsp  state=running
```

## 二、传感器：走的就是发行版推行的接口

`iio-sensor-proxy 3.9-r2` 原生链接 `libssc.so.2`，通过
`net.hadess.SensorProxy` D-Bus 暴露，**不走** `/sys/bus/iio`：

```
$ udevadm info --query=property --path=/sys/devices/virtual/misc/fastrpc-sdsp \
    | grep -E "IIO_SENSOR|ACCEL_MOUNT"
IIO_SENSOR_PROXY_TYPE=ssc-light ssc-compass ssc-accel ssc-proximity
ACCEL_MOUNT_MATRIX=-1,0,0;0,-1,0;0,0,1

$ busctl call net.hadess.SensorProxy /net/hadess/SensorProxy \
    org.freedesktop.DBus.Properties GetAll s net.hadess.SensorProxy
HasAccelerometer=b true  AccelerometerTilt="face-up"
HasAmbientLight=b true   LightLevelUnit="lux"  LightLevel=0
HasProximity=b true      ProximityNear=b false

$ monitor-sensor
Has accelerometer (orientation: undefined, tilt: face-up)
Has ambient light sensor (value: 0.000000, unit: lux)
Has proximity sensor (near: 0)
Has compass (heading: unset)
Compass heading changed: 22.92 -> 22.95 ...   (实时更新)
```

### 标签来自哪里（这是本轮纠正的关键）

`ACCEL_MOUNT_MATRIX` 的规则条件里带 `*ssc-accel*`。这个标签由
**`postmarketos-base-ui 51-r0` 的
`90-iio-sensor-proxy-proximity-sensor-enable.rules`** 提供：

```
SUBSYSTEM=="misc", KERNEL=="fastrpc-adsp*", ENV{IIO_SENSOR_PROXY_TYPE}+="ssc-accel ssc-proximity"
SUBSYSTEM=="misc", KERNEL=="fastrpc-sdsp*", ENV{IIO_SENSOR_PROXY_TYPE}+="ssc-accel ssc-proximity"
```

`iio-sensor-proxy` 自己的 `80-iio-sensor-proxy.rules` 只加
`ssc-light ssc-compass`。`90-` 排在 `99-realme-rmx1931-sensors.rules`
之前，所以条件成立。

> 早前“条件恒假 / 矩阵从未生效”的结论是**错的**：我只看了 80- 规则
> 就下了判断。实机 `udevadm` 输出直接推翻了它。仓库里的
> `99-realme-rmx1931-sensors.rules` 已恢复成实机那份
> （sha256 `b33a6148…`），未做无谓改动。

`check-rootfs.py` 现在断言：

1. 板级规则在两条 FastRPC 节点上导出竖屏矩阵；
2. 存在一条**排序在前**的规则提供 `ssc-accel` 标签（缺失即失败）。

正反两条路径都已用构造目录验证过。

### libssc 覆盖层（唯一属于“灰区”的部分）

| 路径 | 大小 | `wise_light` |
|---|---|---|
| `/usr/lib/libssc.so.2`（系统） | 133088 | 无 |
| `/usr/lib/samurai/ssc/libssc.so.2`（`samurai-libssc 1-r0`） | 160408 | 有 |

切换方式：

```
/usr/lib/systemd/system/iio-sensor-proxy.service.d/10-samurai.conf
  Environment=LIBSSC_LIGHT_DATA_TYPE=wise_light
  Environment=LD_LIBRARY_PATH=/usr/lib/samurai/ssc
```

实机验证 daemon 确实加载了覆盖库：

```
$ grep -i libssc /proc/$(pgrep -o iio-sensor-proxy)/maps | awk '{print $6}'
/usr/lib/samurai/ssc/libssc.so.2
```

原因：原厂 SLPI 把 Sensortek 光线实例发布成 `wise_light`，而
libssc 0.4.4 默认只查 `ambient_light`，枚举为空。更干净的做法是把
这个补丁并进官方 `libssc` 包（或推上游），去掉 `LD_LIBRARY_PATH`
覆盖 —— 仍在待办。

## 三、逐项硬件

| 接口 | 结果 | 证据 |
|---|---|---|
| WiFi | 正常 | `SSID TP-LINK_156D`，5180 MHz，-66 dBm |
| USB NCM | 正常 | `usb0` = `172.16.42.1/24` + `169.254.42.1/16`，carrier=1 |
| 蓝牙 | 正常 | `58:85:A2:CF:12:BE`，Powered yes |
| 传感器 | 正常 | 上表，四项能力 + 指南针实时读数 |
| 音频 | 正常 | 默认 sink `alsa_output.platform-sound.HiFi__Speaker__sink` |
| 背光 | 正常 | `/sys/class/backlight/ae94000.dsi.0` = 400 |
| 电源 | 正常 | `bq28z610-0 Battery`、`mp2650-input USB` |
| 闪光灯 | 正常 | `/sys/class/leds/white:flash` |
| 温度 | 正常 | thermal_zone0 = 29.3 °C |
| GNSS (QMI) | 可用 | `qmicli -d qrtr://0 --loc-get-operation-mode` → `standalone` |
| GNSS (`/dev/gnss`) | **缺** | 镜像内有 `gnss.ko`/`gnss-serial.ko`，但 DT 无 gnss 节点、未 `lsmod` |
| 调制解调器 | 部分 | modem running，`state: failed` + `sim slot 1: none`（未插卡） |
| 相机 | **图已建好，只差 sensor 连线** | media graph 27 个实体齐全；sensor 端 `links=0`；见下 |

### 相机

早期我用 `sysfs` 的 `v4l-subdev*` 和一次错误的 `ioctl` 布局判断“0 实体”，
那是**误报**。用正确的 `struct media_entity_desc` 布局
（`id` 在偏移 0、`name` 在偏移 4、`pads/links` 在 52、`dev` 在 60，
`MEDIA_IOC_ENUM_ENTITIES` 尺寸 256、`id |= 1<<31` 取下一个）
枚举 `/dev/media0`，实际有 **27 个实体**：

```
msm_csiphy0..3   type=0x20000 pads=2 links=2
msm_csid0..1     type=0x20000 pads=5 links=8
msm_vfe0_rdi0..2 / pix  + msm_vfe0_video0..3
msm_vfe1_rdi0..2 / pix  + msm_vfe1_video0..3
s5k3m5 8-002d    type=0x20001 pads=1 links=0
imx319 7-0010    type=0x20001 pads=1 links=0
s5kgw1 6-0010    type=0x20001 pads=1 links=0
imx471 9-0010    type=0x20001 pads=1 links=0
lc898219xi 6-0072 type=0x20003 pads=0 links=0
```

所以 kernel 的 CAMSS/csiphy/csid/vfe 注册**全部成功**，
`/dev/video0..7` 的 `VIDIOC_QUERYCAP` 也正常
（`driver=qcom-camss`，`caps=0xa5201000`）。

唯一缺的是 **sensor → csiphy 的 pad link**：4 个 sensor 实体的
`links=0`，csiphy 侧 `links=2` 只含 csid 方向。这与之前记录的
“`camss_subdev_notifier_complete()` 里 `media_create_pad_link()` 未执行”
一致 —— 属于内核 async-notifier 行为，需要重编内核并刷 `logdump`。

另外 `/dev/v4l-subdev*` 不存在是**正常的**：camss 没有调用
`v4l2_device_register_subdev_nodes()`，它只通过 media controller
暴露 subdev，不导出字符设备节点。所以不能拿“没有 v4l-subdev”
当作相机坏的证据。

## 四、这一轮真正改了什么

| 文件 | 改动 |
|---|---|
| `linux-port/docs/SSH-ROOT-CAUSE-20261120.md` | 新增：SSH 两层根因（真实 IP 变化 + fake-IP 劫持） |
| `linux-port/scripts/ssh-path-diag.py` | 新增：判定 socket `local` 是否落在 fake-IP 段；`--scan` 扫真实 IP |
| `linux-port/scripts/_wsl-samurai/extract-image-tree.sh` | 新增：`cp -a` 抽整树，保留空目录 |
| `linux-port/scripts/_wsl-samurai/repro-sshd-in-chroot.sh` | 新增：chroot 内跑 sshd 验证镜像，结束删除临时 host key |
| `linux-port/scripts/_wsl-samurai/check-rootfs.py` | 新增传感器链路双向断言 |
| `linux-port/packages/samurai-platform/99-realme-rmx1931-sensors.rules` | **恢复**为实机字节（撤销我误加的“无条件”改写） |
| `linux-port/packages/samurai-platform/APKBUILD` | sha512 回到 `7621e2d3…`（与实机一致） |

未做：重编内核、重建镜像、改 `libssc` 包归属。

## 五、下次接手

1. 相机：重编内核修 CAMSS notifier → 刷 `logdump` → 用
   `media-ctl -p` 验证 4 个 sensor 都有 link。
2. GNSS：DT 增加 `gnss` 节点或改用 QMI 后端，让标准 `gnss.ko` 绑定。
3. `libssc`：把 `wise_light` 补丁合进官方包，去掉 `LD_LIBRARY_PATH`。
4. 装机脚本里的 `.106` 全部改成“扫描后取真实地址”。
