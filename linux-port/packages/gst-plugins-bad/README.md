# GStreamer viewfinderbin 预览下沉

此配方在 Alpine `gst-plugins-bad 1.28.7-r0` 基础上递增到 `r1`，只修改
`gst/camerabin2/gstviewfinderbin.c`。它把取景链路从：

```text
videoconvert(1080p YUV -> 1080p RGB) ! videoscale -> paintablesink
```

改为：

```text
videoscale(1080p NV12 -> 854x480 NV12)
  ! videoconvert(dither=none, 854x480 BGRx) ! paintablesink
```

因此缩放发生在 YUV 域，GTK/Cairo 只接收可直接上屏的 BGRx 纹理。
2026-11-03 实机结果：

- 后摄主摄预览连续 `30 fps`；
- `Snapshot` 进程约占单核 17%；
- 亮度 400/2047、SDP 900 mA 时电池净流 `+21..+39 mA`；
- 不再需要 Snapshot 启动器设置 `LD_PRELOAD`；
- 拍照/录像仍由 Aperture 使用 1920x1080 源，不受取景尺寸影响。

冷启动复测：插件仍为 SHA256
`be94e9dda771c0d0c7de12873ce3877a8af45b33ef0cb2c3fe956b7328d81e12`，
桌面启动器环境无 `LD_PRELOAD`，24 秒取景净流 `+10..+31 mA`。

## 可调参数

- `SAMURAI_VIEWFINDER_WIDTH` / `SAMURAI_VIEWFINDER_HEIGHT`：默认
  `854x480`。
- `SAMURAI_VIEWFINDER_FORMAT`：默认 `BGRx`。
- `SAMURAI_VIEWFINDER_SCALE_METHOD`：默认 `0`（最近邻）。`1` 为双线性，
  画质略好但功耗余量更小。

## 原厂参考

原厂 ODM `oplus_camera_config` 的
`com.oplus.preview.format.nv12` 和 `com.oplus.preview.support.nv12`
均为 `0`；Android Camera HAL 将 NV12 输出交给显示合成路径处理，
不在应用 CPU 线程逐帧做 1080p YUV→RGB。本机主线栈没有可用的 V4L2
M2M 转换节点，GL 取景仍为绿屏，因此当前把缩放/转换固定在 GStreamer
预览插件层，并降低输出到屏幕实际需要的 854x480。

## 构建

```sh
cd linux-port
abuild -r
```

离线原型构建与设备验证记录见
[`../../camera/PERFORMANCE.md`](../../camera/PERFORMANCE.md)。

