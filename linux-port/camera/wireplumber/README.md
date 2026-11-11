# 相机应用唯一命名

WirePlumber 的 `monitors/libcamera/name-node.lua` 会把所有
`api.libcamera.location=back` 的节点命名为 `Built-in Back Camera`。
Realme X2 Pro 有三颗后摄，因此 GNOME Snapshot 的相机菜单会出现三个无法区分
的同名条目。

`60-samurai-camera-names.conf` 在 `monitor.libcamera.rules` 中按
`device.product.name` 覆盖 `node.description`：

| sensor | 名称 |
| --- | --- |
| `s5kgw1` | `Built-in Back Camera (Main)` |
| `imx319` | `Built-in Back Camera (Ultra Wide)` |
| `s5k3m5` | `Built-in Back Camera (Telephoto)` |

主摄同时设置 `priority.session = 900`，使 PipeWire 设备和 Snapshot 的
默认枚举顺序都以主摄优先，避免应用启动时先看到前摄。

安装到设备：

```sh
sh ./install.sh
```

重启当前桌面的 WirePlumber 后重新打开相机应用。默认相机可通过 Snapshot 的
`last-camera-id` 设置指向主摄：

```sh
gsettings set org.gnome.Snapshot last-camera-id "'Built-in Back Camera (Main)'"
```

验证：

```sh
gst-device-monitor-1.0 Video/Source 2>/dev/null |
	grep -E 'node.description|device.product.name'
```

预期四个节点分别为前摄、主摄、超广角、长焦，名称不再重复。该配置只影响
PipeWire/WirePlumber 暴露给应用的名称，不修改内核、libcamera 驱动或图像处理。

## 打包状态

该文件已进入
[`samurai-snapshot-preview`](../../packages/samurai-snapshot-preview/)
配方，安装到 `/etc/wireplumber/wireplumber.conf.d/`，并依赖
`wireplumber`。因此不需要改动仍停留在历史 r27 的
`samurai-camera-config` 版本链，也不会影响设备上已实装的 config r28
或未安装的 r29 候选。

同一包还安装 Snapshot 默认主摄的 GSettings override，并在安装后重新
编译 schema。

文件 SHA-512：
`8aa97b74457e5d97a894ccb146c7b1d8b67713d9e0d25cea1a69ccd84e6ce70b80d1f02522e9dfdad75b7096e759049b338fd5ff78203f0cf84ab1324e882e36`
