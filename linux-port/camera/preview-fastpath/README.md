# Snapshot 预览绘制路径与注入库

本目录保存 `samsinkinject.so` 的源码与构建配方，作为可选兼容回退。
正式路径已下沉到
[`gst-plugins-bad` 的 `viewfinderbin`](../../packages/gst-plugins-bad/)，
启动器不再加载 `LD_PRELOAD`。

## 已确认的预览链路

Snapshot 51 的 `aperture/src/viewfinder.rs` 创建 `camerabin`、
`gtk4paintablesink` 和 `AperturePipelineTee`，实际显示路径是：

```
pipewiresrc ! ... ! camera-source
  ! vf-bin (videoconvert ! videoscale)
  ! aperture-tee (tee)
  ! queue ! gtk4paintablesink
```

`vf-bin` 的内部元素名是 `vfbin-csp`／`vfbin-videoscale`，不是
`preview-*`。camerabin 另有一条拍照预览消息管线：

```
preview-appsrc ! preview-vscale ! preview-vconv ! preview-appsink
```

它只把拍照预览 sample 通过 bus message 交给应用，**不参与取景显示**。
之前把 `preview-appsink` 当成取景 sink，所以只改它的 caps 对画面帧率
没有影响。

`gtk4paintablesink` 的 sink caps 先声明 YUY2／NV12 等 YUV 格式，BGRx
排在后面，因此默认协商会选中 YUV。GTK 随后为每一帧在 Cairo 软件
渲染器里做 YUV→RGB，1080p 实测约 5 fps。

Snapshot 还会把 sink 包进只带 ghost pad 的小 bin；实机日志里显示分支是
`queue0 -> bin0`，`bin0` 内部才是 `gtk4paintablesink`。因此只判断目标元素
自身有没有 `paintable` 属性会漏掉它。

## 实机实测（GSK cairo）

| 场景 | sink 收帧率 | GTK 绘制 |
| --- | --- | --- |
| 1920x1080 YUV（原默认） | 30 fps | 约 5 fps |
| 1920x1080 BGRx | 30 fps | 约 10–12 fps |
| 1280x720 BGRx | **30.0 fps** | **30 fps** |
| 960x540 BGRx（shim 回退路径） | **30.0 fps** | **30 fps** |

1080p BGRx 已经消除了 YUV 转换，但 Cairo 每帧还要上传/缩放 8.3 MB
纹理，仍只有约 10 fps。960x540 BGRx 降到约 2.1 MB，实测稳定 30 fps，
CPU 约占单核 19%；在 900 mA SDP 输入下仍保持电池净充电。

## 注入库行为

- 拦截 `gst_element_link_pads_full` / `gst_element_link_pads` /
  `gst_element_link` / `gst_element_link_filtered` / `gst_pad_link_full`。
- 当目标本身是 `gtk4paintablesink`，或目标 bin 的后代包含
  `gtk4paintablesink` 时，在目标前插入
  `videoconvert(dither=none) ! capsfilter(video/x-raw,format=BGRx,width=960,height=540)`。
- 当 camerabin 链接 `viewfinderbin-capsfilter -> vf-bin` 时，插入
  `videoscale(method=nearest-neighbour) ! capsfilter(width=960,height=540)`，
  并在同一入口关闭 `vf-bin` 自带的 `videoconvert ! videoscale`，避免
  重复全帧转换/缩放。
- 可选 `SAMURAI_SOURCE_WIDTH=1280` / `SAMURAI_SOURCE_HEIGHT=720`：
  拦截 Aperture 写入相机源 capsfilter 的 1920x1080 caps，改为 720p，
  让 libcamera 选择 sensor 原生 720p 模式。拍照仍使用 Aperture 的
  静态拍照模式，不受取景尺寸影响。
- 不要改 camerabin 的 `viewfinder-caps`：Aperture 的源 capsfilter 已
  固定请求 1920x1080，再要求取景链路输出 720p 会令 `decodebin3` 的
  pad 链接失败（`Pads do not have common format`），实测 0 fps。
- Snapshot 实际用 `queue.link(branch)` 和
  `videoconvert.link(paintablesink)` 连接显示分支，这两处都会落到
  `gst_element_link`；本库已在该入口识别 ghost-pad bin 并执行注入。
- 不再修改 camerabin 的 `preview-appsink`。
- 插入失败会退回原始链接，不影响应用启动。
- 默认预览为 960x540 BGRx；`SAMURAI_PREVIEW_WIDTH`／
  `SAMURAI_PREVIEW_HEIGHT` 可覆盖，设为 `0` 则保持原生尺寸。
- `SAMURAI_PREVIEW_SCALE_METHOD` 可覆盖缩放算法，默认 `0`
  （最近邻）；`1` 为双线性，画质略好但功耗余量更小。
- `SAMURAI_SOURCE_WIDTH`／`SAMURAI_SOURCE_HEIGHT` 可把源 caps 降到
  720p；正式启动器不设置。设为 `0` 或删除变量则保持原始源尺寸。
- `SAMURAI_NO_PREVIEW_CONVERT=1` 关闭注入；
  `SAMURAI_PREVIEW_DEBUG=1` 输出链接与格式诊断。

## 离线回归测试

用带 `paintable` 属性的 GstBaseSink 模拟 Snapshot 的链接路径：

```
videotestsrc ! videoconvert ! fake-paintable-sink
```

- 直接链接和 ghost-pad bin 包装两种形态都测过。
- 不加载本库：sink 协商为 `A444_16LE`。
- 加载本库：日志打印 `forced BGRx before display-bin`，sink 最终 caps
  为 `width=960,height=540,format=(string)BGRx`。

这验证了注入点、链接成功率和 caps 协商结果，不依赖 GTK/屏幕。

## 构建

目标机为 Alpine edge aarch64（GStreamer 1.28.7），用同版本容器构建：

```sh
podman run --rm --arch arm64 \
  -v "$PWD/linux-port/camera/preview-fastpath:/src:Z" -w /src \
  alpine:edge sh /src/build.sh
```

## 部署

```sh
install -Dm755 samsinkinject.so /usr/lib/samsinkinject.so
```

如确需使用回退路径，可手工以
`LD_PRELOAD=/usr/lib/samsinkinject.so` 启动 Snapshot；正式启动器不再设置。

也可在设备上以 root 执行本目录的 `install.sh`，一次安装共享库和两个
用户级启动器：

```sh
sh install.sh /home/cy122 cy122
```

## 当前状态

- 已按真实显示路径重写注入，离线回归和实机验证均通过。
- 正式配方已放入 `../../packages/samurai-snapshot-preview/`，同时携带
  WirePlumber 四摄命名和新用户默认主摄设置。
- 实机 Snapshot（2026-11-03 晚）：正式 `viewfinderbin` 路径默认源仍为
  1920x1080，显示 caps 为 `854x480 BGRx @ 30 fps`；亮度 400/2047 下
  连续 30 秒取景的电池净流为 `+21..+39 mA`，CPU 约占单核 17%。
- 本轮部署的 `samsinkinject.so` SHA256 为
  `6c9df2f043a7e93bea37f0914d0a1ed225c9ffebd9718156b4a267ff442010a3`。
- 桌面启动器和 D-Bus service 已移除 `LD_PRELOAD`；该 shim 只作为
  手工回退保留，720p 源尺寸变量是可选项。
