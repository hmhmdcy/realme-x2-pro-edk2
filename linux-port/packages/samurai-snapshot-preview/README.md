# Snapshot 预览与相机选择修复

此包保留 Realme X2 Pro 四摄命名、新用户默认主摄设置，并提供两个可选的
`LD_PRELOAD` 兼容层：

- `samucapsinject.so`：把相机源 caps 的首选格式重排为原厂取景参数
  `1440x1080@30`；需要高刷时可切回 `1280x720@60`；
- `samsinkinject.so`：旧的 BGRx/缩放假取景回退。

`samurai-desktop` 的正式 Snapshot 启动器还会加载
[`oem-capture`](../../camera/oem-capture/) 部署的
`/usr/local/lib/samucaptureinject.so`，并把快门接到原厂
`4608x3456` 双流；设置 `SAMURAI_HIGHRES_ON_SHUTTER=1` 时改走
`9280x6944`。该库不存在时动态加载器会忽略它，Snapshot 仍可按原生
单流启动。

正式取景仍使用 [`gst-plugins-bad`](../gst-plugins-bad/) 的
`viewfinderbin`。当前 `samurai-desktop` 启动器还加载
`samucapsinject.so`、`gstjifpreload.so` 和
`samucaptureinject.so`；最后一个库负责把快门接到 OEM 主拍/64MP。

## 内容

| 路径 | 作用 |
| --- | --- |
| `/usr/lib/samsinkinject.so` | 可选的 Snapshot 预览回退，不再由正式启动器加载 |
| `/usr/lib/samucapsinject.so` | 把相机源首选 caps 改为 1440x1080@30，不重编译 Snapshot |
| `/etc/wireplumber/wireplumber.conf.d/60-samurai-camera-names.conf` | 区分主摄、超广角、长焦和前摄 |
| `/usr/share/glib-2.0/schemas/99_samurai-snapshot-camera.gschema.override` | 新用户默认选择后摄主摄 |

`samurai-desktop` 的 Snapshot 启动器和 D-Bus service 不再设置
旧的 `samsinkinject.so`。当前正式取景路径由补丁版 `viewfinderbin` 完成
`videoscale ! videoconvert ! BGRx`，相机源仍是 Aperture 选择的
首个 caps；`samucapsinject.so` 将这个顺序改为 1440x1080@30 优先。

## 取景规格（OEM 1440x1080@30）

Aperture 原先把相机源 caps 按 PipeWire 返回顺序交给 capsfilter，首项是
`640x480`。原厂 ODM 配置给出的主摄取景是 `1440x1080`，主拍是
`4608x3456`；`samucapsinject.so` 把 `1440x1080@30` 结构移到 caps
首位，其余分辨率保留。

实机结果：PipeWire/`cam` 的 1440x1080 源稳态约 30fps；Snapshot
取景正常，照片分辨率与源一致（1440x1080）。若需要 60fps 取景，
把 `SAMURAI_PREFER_SOURCE` 改为 `1280x720@60`，此时照片也会降到
1280x720。Snapshot 的 camerabin 只有单路源，取景和拍照不能同时使用
不同分辨率；4608x3456 主拍走独立的双流 RAW 采集路径，见
[`oem-capture`](../../camera/oem-capture/)。

`1440x1080` 不在 libcamera 默认的 53 个离散尺寸表里，PipeWire 只枚举
这张表，因此需要 libcamera 补丁
[`0010-camss-add-1440x1080-preview-size.patch`](../../camera/libcamera/0010-camss-add-1440x1080-preview-size.patch)
把 `Size(1440, 1080)` 加入 `rangeDiscreteSizes`。

## 原因

Snapshot 的取景链路是：

```
pipewiresrc ! ... ! vf-bin(videoconvert ! videoscale)
  ! aperture-tee ! queue ! gtk4paintablesink
```

如果手工加载该回退库，它默认做三件事，并可选择降低相机源尺寸：

1. 在 `viewfinderbin-capsfilter -> vf-bin` 之间插入
   `videoscale(method=nearest-neighbour) ! capsfilter(width=960,height=540)`，
   在 NV12 域完成取景缩放；
2. 关闭 `vf-bin` 自带的 `videoconvert ! videoscale`，避免多一次全帧拷贝；
3. 在 `gtk4paintablesink` 前插入
   `videoconvert(dither=none) ! capsfilter(format=BGRx,width=960,height=540)`。
4. 可选：设置 `SAMURAI_SOURCE_WIDTH=1280`、`SAMURAI_SOURCE_HEIGHT=720`
   时，拦截 Aperture 对相机源 `capsfilter` 的设置，把 1920x1080 源
   caps 改为 1280x720，让 libcamera 选择 sensor 原生 720p 模式。

默认源尺寸保持 1920x1080；只有显式设置源尺寸变量时才降低源 caps。
960x540 与屏幕上的取景区域匹配，缩放和转换量比 1280x720 再少约
44%，因此取景期间仍能保留 USB 净充入余量。

这里改的是 **相机源 capsfilter**，不是 camerabin 的
`viewfinder-caps`。直接设置 `viewfinder-caps=NV12,1280x720` 仍会与
Aperture 的 1080p 源 caps 冲突，`decodebin3` 报
`Pads do not have common format`，预览 0 fps；该失败方案已排除。

`gtk4paintablesink` 默认优先协商 YUV。Cairo 软件渲染器每帧把 1080p
YUY2/NV12 转成 RGB，实机只有约 5 fps。强制 960x540 BGRx 后，转换在
GStreamer 的 `videoscale`/`videoconvert` 中完成，GTK 直接绘制 RGB
纹理，实机稳定 30 fps。

WirePlumber 原本把三颗后摄都命名为 `Built-in Back Camera`，Snapshot
无法区分；规则按 `device.product.name` 覆盖名称。主摄同时设置
`priority.session = 900`。

## 环境变量

- `SAMURAI_PREVIEW_WIDTH` / `SAMURAI_PREVIEW_HEIGHT`：覆盖预览尺寸，
  默认 960x540；任一设为 `0` 保持原生尺寸。
- `SAMURAI_PREVIEW_SCALE_METHOD`：设置 GStreamer 缩放算法，默认 `0`
  （最近邻）。`1` 为双线性，画质略好但净充入余量更小。
- `SAMURAI_SOURCE_WIDTH` / `SAMURAI_SOURCE_HEIGHT`：把 1920x1080 相机源
  caps 降到指定尺寸；默认不设置，保持原始源尺寸。设为 `0` 或删除变量
  同样保持原始源尺寸。
- `SAMURAI_PREVIEW_FORMAT`：覆盖颜色格式，默认 `BGRx`。
- `SAMURAI_NO_PREVIEW_CONVERT=1`：关闭格式注入。
- `SAMURAI_PREVIEW_DEBUG=1`：输出链接、caps 和 sink 帧率。
- `SAMURAI_PREFER_SOURCE=1440x1080@30`：`samucapsinject.so` 的首选源
  caps，默认值；格式为 `宽x高@帧率`。`1280x720@60` 可切到高刷档。
- `SAMURAI_CAPS_DEBUG=1`：打印被替换的相机源 caps。

## 构建与验证

```sh
podman run --rm --arch arm64 \
  -v "$PWD:/repo:Z" \
  -w /repo/linux-port/packages/samurai-snapshot-preview \
  alpine:edge sh -c 'apk add --no-cache gcc musl-dev pkgconf gstreamer-dev &&
    gcc -shared -fPIC -O2 -Wall -Wextra -o /tmp/samucapsinject.so samucapsinject.c \
      $(pkg-config --cflags --libs gstreamer-1.0 gobject-2.0) &&
    gcc -shared -fPIC -O2 -Wall -Wextra -o /tmp/samsinkinject.so samsinkinject.c \
      $(pkg-config --cflags --libs gstreamer-1.0 gobject-2.0)'
```

安装后关闭旧 Snapshot 进程，重新打开相机应用。实机验收标准为后摄主摄
画面、sink 30 fps，且 `wpctl status` 中四个相机名称互不重复。

2026-11-03 实机：回退路径在默认源 1920x1080 下输出 960x540 BGRx，
连续 30 fps；在 SDP 900 mA 输入策略下可保留净充入。正式路径改用
`gst-plugins-bad` 的 854x480 输出，实机净流为 `+21..+39 mA`
（亮度 400/2047），空闲约 `+320..+350 mA`。可选 720p 源模式也已实测
`fmt:SGBRG10_1X10/1280x720`，但默认不启用，以保留照片源分辨率。
本轮部署的 `samsinkinject.so` SHA256 为
`6c9df2f043a7e93bea37f0914d0a1ed225c9ffebd9718156b4a267ff442010a3`。
本轮部署的 `samucapsinject.so` SHA256 为
`c778b0078143dbf2242e9a86ecbb90585dd6b42e12116ac5860fed66711cc14c`。

## 限制

该 shim 仅作为兼容回退保留，不需要重编译 Snapshot。正式路径已不依赖
`LD_PRELOAD`。可选的 1280x720 源尺寸要求内核 `s5kgw1` 暴露 OEM 720p
模式；若内核仍只有 4608x3456/2592 两个模式，源尺寸会被 VFE 缩放但
sensor 仍全分辨率读出，省电效果有限。
