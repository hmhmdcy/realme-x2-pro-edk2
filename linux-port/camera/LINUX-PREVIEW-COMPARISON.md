# 其他 Linux 手机的相机预览路径对照

整理日期：2026-11-03。以下只用于判断 Linux 侧通常把负载放在哪一层，不把
Android Camera HAL 或厂商私有流水线直接搬到本机。
文中链接均于 2026-11-03 逐条取回原文核对，引用只覆盖对应段落；无法在
原文中直接读到的结论不写入本文。

## 公开实现中的共同点

- **libcamera 负责传感器/ISP 和格式输出。** libcamera 的 pipeline model 把
  色彩空间转换、裁剪和缩放作为流水线阶段；具体由 CPU、GPU 或硬件 ISP
  实现，由设备 pipeline handler 决定。  
  <https://docs.libcamera.org/master/public-api/camera-model.html>
- **有 GPU 时优先把 debayer/缩放/上屏放到 GPU。** libcamera 的
  `software_isp/debayer_egl` 配合 dmabuf import，在 Fairphone 5 主摄上
  把 Snapshot 取景时 WirePlumber/PipeWire 的 CPU 占用从约 39% 降到约
  13%，Pixel 3a 同场景从约 59% 降到约 17%；DMABuf import 失败时仍回退
  CPU，改进明显变小（Fairphone 5 副摄约 63%→53%）。  
  <https://lists.libcamera.org/pipermail/libcamera-devel/2026-June/059622.html>
- **应用侧优先使用 GPU/DMABuf sink。** `gtk4paintablesink` 可生成 GL
  texture（需以 wayland/x11glx/x11egl 之一编译），并在 GTK 4.14+ 支持
  直接渲染 DMABuf；纯 Cairo/CPU 路径则需要先把 YUV 转成 RGB。  
  <https://gstreamer.freedesktop.org/documentation/gtk4/index.html>
- **低端设备会明确退回 GLES/有限分辨率。** Megapixels 在 PinePhone 上
  依赖 GLES 预览；GTK 4.18 移除 GLES 2.0 后性能明显下降，其应用页面提示
  可用 Flatpak 包或仍存在的 GTK3 分支。  
  <https://linuxphoneapps.org/apps/me.gapixels.megapixels/>
- **全分辨率 CPU debayer 不可行。** Librem 5 的公开讨论明确指出全分辨率
  对 CPU 过重，debayer/缩放至少要放在 GPU，否则帧率和自动对焦都会失去
  意义。  
  <https://lists.libcamera.org/pipermail/libcamera-devel/2022-November/035587.html>

## 与 Android 原厂的边界

原厂 ODM 配置把主预览的额外 NV12 覆盖关闭，由 Camera HAL 和显示合成器
处理尺寸/带宽；这可以作为“转换不要放在应用主线程”的证据，但不能据此
照搬 Android 的 Camera HAL、gralloc 或 SurfaceFlinger。

## 本机采用的 Linux 路径

本机主线栈已确认：

- CAMSS/VFE 可输出 NV12 30 fps；
- 没有可用的 V4L2 M2M 转换节点；
- GL/DMABuf 取景仍为绿屏，不能直接使用其他 Linux 手机的 GPU sink 路径。

因此当前采用 GStreamer `viewfinderbin` 的 CPU 路径，但把顺序改为：

```text
NV12 1080p -> videoscale -> NV12 854x480
  -> videoconvert(dither=none) -> BGRx 854x480 -> gtk4paintablesink
```

这避免了“1080p YUV 先转 RGB、再缩放 RGB”，并只在 NV12 域做一次缩放。
实测 30 fps、单核约 17%、USB 900 mA 下取景净充 `+21..+39 mA`。这不是
Android HAL 的移植，而是 Linux 栈内 GStreamer 插件层的收敛；后续若修复
GL/DMABuf 或启用 libcamera GPU SoftISP，可把这一段替换为 GPU 路径。
