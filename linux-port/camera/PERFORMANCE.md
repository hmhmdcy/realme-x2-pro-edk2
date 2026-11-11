# 相机预览帧率实测与瓶颈定位

2026-11-03，`7.3.0-rc6-rmx1931-samurai-k363+`（taint 4608，历史 WARN/OOT）。
主摄 S5KGW1 在 4608x3456 下**全链路 30 fps**，包括 Snapshot 实际使用的
`pipewiresrc` 源。

## 结论

主摄不是「只能跑 15 fps」。此前记录的 11–15 fps 已无法复现，根因是上一次
测试遗留的僵尸采集进程：一个 `v4l2-ctl -d /dev/video7 --stream-mmap` 在
`VIDIOC_DQBUF` 上永久阻塞，持续持有 CAMSS 通道（VFE1 + 相机时钟）。清理该
进程并重启 WirePlumber 后，sensor、CSIPHY、VFE、libcamera、GStreamer、
PipeWire 全部恢复到 30 fps。

因此 sensor 模式、MIPI lane/link frequency、VFE 缩放都不需要改动。

## 分层实测

测量前先停掉 WirePlumber（否则 VFE 节点被占用，`STREAMON` 返回 EBUSY），
测完恢复。

| 层 | 方法 | 结果 |
| --- | --- | --- |
| sensor 读出 | `v4l2-ctl --stream-count --verbose`，读每帧时间戳 | 4608x3456，间隔 33.27 ms，seq 连续，**30.08 fps** |
| CAMSS VFE RDI | 同上，`csid0:1 -> vfe0_rdi0` | **30.08 fps**，19.9 MB/帧 |
| CAMSS VFE 缩放 | `csid0:4 -> vfe0_pix`，compose 640x480 | **30.06 fps** |
| libcamera | `cam -c 1 --capture=60 -s width=1920,height=1080,pixelformat=NV12` | **30.06 fps** |
| GStreamer + libcamera | `libcamerasrc ! fakesink`，720p / 1080p | **29.5 / 29.8 fps** |
| PipeWire（应用路径） | `pipewiresrc path=55 ! fakesink`，640x480 / 720p / 1080p | **30.5 / 29.8 / 29.8 fps** |
| PipeWire + 转换 | `pipewiresrc ! videoconvert ! BGRx ! fakesink` 1080p | **29.8 fps** |

## 关键实验

**1. 帧率由 sensor 决定，CAMSS 不丢帧。**

在最小 vblank（VTS 3584）下 `v4l2-ctl` 报告的帧间隔恒为 33.27 ms，序号
0..N 连续、没有跳号，说明 VFE 没有隔帧丢弃。把 `vertical_blanking`
从 128 调到 3712（VTS 7168）后，同一时间窗内交付帧数精确减半，
证明帧周期由 sensor 行时间决定。

**2. 驱动模式表与原厂逐条一致。**

本机原厂 sensormodule（`com.qti.sensormodule.sunny_s5kgw1.bin`）解析出的
mode 3 为 4608x3456 @30fps、`lineLengthPixelClock=17824`、
`frameLengthLines=3584`、`laneCount=3`、`is3Phase=1`，与
`drivers/media/i2c/s5kgw1-tables.h` 的 `s5kgw1_mode2_regs` 逐条比对
**1089 条写入、零差异**（含 0x0340/0x0342/0x0900/0x0114 及
0x0300–0x0312）。PLL 字段 `0x030e=3`、`0x0310=312`、`0x0312=2` 对应
19.2 MHz / 3 × 312 / 4 = **499.2 MHz**，与 DT 的 `link-frequencies`
完全吻合。

**3. 原厂还有更快模式，可作后续余量。**

| mode | 分辨率 | 行/帧 | 帧率 | 用途 |
| --- | --- | --- | --- | --- |
| 3 | 4608x3456 | 17824 / 3584 | 30 | 当前预览/拍照 |
| 4 | 4608x2592 | 11824 / 2704 | 60 | 视频 |
| 7 | 2304x1296 | 9344 / 1706 | 120 | 高帧率 |
| 9 | 1280x720 | 4624 / 864 | 480 | 慢动作 |

当前 30 fps 已满足预览，暂不需要移植；若后续要做 60 fps 取景或录像再补。

## 复现命令

```sh
# 1. 纯 v4l2：确认 sensor 出帧间隔
media-ctl -d /dev/media0 \
  -l '"s5kgw1 6-0010":0->"msm_csiphy0":0[1]' \
  -l '"msm_csiphy0":1->"msm_csid0":0[1]' \
  -l '"msm_csid0":1->"msm_vfe0_rdi0":0[1]'
media-ctl -d /dev/media0 \
  -V '"s5kgw1 6-0010":0[fmt:SGBRG10_1X10/4608x3456]' \
  -V '"msm_csiphy0":0[fmt:SGBRG10_1X10/4608x3456]' \
  -V '"msm_csiphy0":1[fmt:SGBRG10_1X10/4608x3456]' \
  -V '"msm_csid0":0[fmt:SGBRG10_1X10/4608x3456]' \
  -V '"msm_csid0":1[fmt:SGBRG10_1X10/4608x3456]' \
  -V '"msm_vfe0_rdi0":0[fmt:SGBRG10_1X10/4608x3456]'
v4l2-ctl -d /dev/video0 --set-fmt-video=width=4608,height=3456,pixelformat=pGAA
v4l2-ctl -d /dev/video0 --stream-mmap --stream-count=8 --stream-to=/dev/null --verbose

# 2. libcamera 自身
cam -c 1 --capture=60 -s width=1920,height=1080,pixelformat=NV12 --file=/dev/null

# 3. PipeWire 应用路径（节点号用 wpctl status 查）
pipewiresrc path=55 ! video/x-raw,width=1920,height=1080,format=NV12 ! fakesink
```

测完务必 `media-ctl -d /dev/media0 -r` 复位链路并重启 WirePlumber，且确认
没有残留的 `v4l2-ctl` / `cam` / `gst-*` 采集进程；残留会重新把预览拖到
约 15 fps。

## 预览缩放顺序与正式包

`gst-device-monitor-1.0 Video/Source` 确认四摄的 NV12 caps 已包含
1280x720，但 Snapshot/Aperture 的源 capsfilter 仍按最高 16:9 模式请求
1920x1080。第一轮修复先改缩放的顺序：

```
viewfinderbin-capsfilter
  ! videoscale(method=bilinear) ! capsfilter(1280x720)  [注入]
  ! vf-bin(videoconvert) ! aperture-tee ! queue
  ! capsfilter(BGRx,1280x720)                            [注入]
  ! gtk4paintablesink
```

先在 NV12 域缩到 720p，再让 `vf-bin` 转成 BGRx，避免原来的
“1080p NV12→1080p BGRx→720p BGRx”顺序。

2026-11-03 18:23 实机验证：取景 caps 为
`video/x-raw,width=1280,height=720,format=BGRx,framerate=30/1`；
启动约 5 秒后连续两个 5 秒窗口均为 `30.1 fps`。此前尝试把
camerabin 的 `viewfinder-caps` 设为 1280x720 NV12，会与 Aperture
固定的 1920x1080 源 caps 冲突，`decodebin3` pad 链接报
`Pads do not have common format`，预览 0 fps，已放弃该方案。

相关文件和四摄命名、默认主摄设置已进入
[`samurai-snapshot-preview`](../packages/samurai-snapshot-preview/) 包。

## 第二轮：USB 900 mA 与可选 720p sensor 模式

第一轮只把显示纹理降到 720p，sensor 仍以 4608×3456 读出，取景负载
约 800 mA；电脑 SDP 500 mA 下电池净流约 `-300 mA`。第二轮先尝试
把 OEM `s5kgw1` 的 1280×720/30 fps 模式接入内核：

```
source capsfilter -> 1280x720
sensor            -> SGBRG10_1X10/1280x720
viewfinder sink   -> BGRx 1280x720 @ 30 fps
```

该模式可以正常出图，源 caps 会变成 1280×720。但它对整机取景功耗的
改善有限，而且会把源分辨率降到 720p；因此默认启动器不启用源尺寸
覆盖，只保留显示/取景分支的 720p BGRx。拍照和录像仍使用原始
1920×1080 源 caps。720p 源模式保留为可选路径（设置
`SAMURAI_SOURCE_WIDTH=1280 SAMURAI_SOURCE_HEIGHT=720`）。

真正解决 USB 掉电的是 SDP 900 mA 输入策略：只对确认的 SDP 生效，
把输入上限从 500 mA 提到 USB 3.x/板级 900 mA。

同一电脑 USB 口、同一根线的实测（2026-11-03 晚复测）：

| 场景 | 输入上限 | 电池净流 |
| --- | --- | --- |
| 空闲 | 900 mA (SDP boost) | 约 +330…+350 mA |
| 1920×1080 源 / 1280×720 BGRx 取景 | 900 mA (SDP boost) | 约 -80…-90 mA |
| 1920×1080 源 / 960×540 BGRx 最近邻取景 | 900 mA (SDP boost) | +18…+33 mA |
| 1920×1080 源 / 960×540 BGRx 双线性取景 | 900 mA (SDP boost) | +8…+21 mA |
| 1920×1080 源 / 854×480 BGRx `viewfinderbin` | 900 mA (SDP boost) | +21…+39 mA |

900 mA 只对确认的 SDP 生效，DCP/CDP/PD/未知来源不变；这是 USB 3.x
下行端口和本机 OEM 输入档位的上限，不表示所有 500 mA USB 2.0 端口
都能提供 900 mA。若主机端口限流，应写
`/sys/module/samurai_mp2650/parameters/sdp_boost_ua = 0`。

取景 30 秒期间未出现 USB 断开、reset 或 over-current 日志；输入仍为
5 V，`input_current_limit=900000`。余量只有几十 mA，高亮度屏幕或额外
负载仍可能抵消净充入。

## 第三轮：960×540 最近邻与无重编译收敛

第二轮之后复测发现：1920×1080 源 + 1280×720 BGRx 取景在
`vf-bin(videoconvert ! videoscale)` 仍保留内置转换/缩放时，CPU 约占
单核 37%，整机仍净放电约 80–90 mA。单纯 900 mA SDP 输入不足以覆盖
这条 720p 显示路径。

最终采用 `samsinkinject.so` 的运行时管线优化，不重编译 Snapshot：

1. 在 `viewfinderbin-capsfilter -> vf-bin` 前插入
   `videoscale(method=nearest-neighbour) ! capsfilter(960x540)`，
   在 NV12 域完成缩放；
2. 关闭 `vf-bin` 内置的 `videoconvert ! videoscale`，避免重复全帧处理；
3. 在 `gtk4paintablesink` 前插入
   `videoconvert(dither=none) ! capsfilter(BGRx,960x540)`。

结果：预览 sink 连续 `30.0–30.2 fps`，CPU 从约 37% 降到约 19–22%；
亮度 400/2047 下电池净流 `+18…+33 mA`。相机源仍是 Aperture 选择的
1920×1080，拍照/录像分辨率不因 960×540 取景而降低。

`SAMURAI_PREVIEW_WIDTH=1280 SAMURAI_PREVIEW_HEIGHT=720
SAMURAI_PREVIEW_SCALE_METHOD=1` 可切回 720p 双线性画质，但在当前
900 mA 端口上没有可靠的净充电余量。GL 路径已试，主摄画面变绿，
不能作为无重编译替代方案。

## 原厂 Android 对照

本地原厂 `X20Pro_F14` ODM 镜像的 `/etc/camera/config/oplus_camera_config`
显示：

- `com.oplus.preview.format.nv12 = 0`
- `com.oplus.preview.support.nv12 = 0`
- 人像预览仅单独声明 `1440x1080`

即默认主取景没有额外强制一条应用侧 NV12 覆盖路径。`camera.qcom.so`
还包含 `GetPreviewDimension`、`org.quic.camera.streamTypePresent.preview`、
`Display DS4/DS16` 缩放配置和 `Preview/Video cbw` 带宽记录，说明
原厂把取景尺寸、VFE/display scaler 和输出带宽交给 Camera HAL 与显示
合成路径处理，而不是由 Android 应用线程把 1080p YUV 逐帧转成 RGB。

本机主线栈没有可用的 V4L2 M2M 转换节点，GL 取景仍是绿屏，因此当前
可行的等价落点是 GStreamer `viewfinderbin`：先缩放 NV12，再转 BGRx。

## 第四轮：viewfinderbin 底层下沉

原厂 ODM `oplus_camera_config` 默认关闭额外的 NV12 预览格式覆盖；
Android Camera HAL 把 NV12 流交给显示合成路径，缩放和上屏不在应用
CPU 线程里逐帧做 1080p YUV→RGB。本机主线栈没有可用的 V4L2 M2M
转换节点，GL 取景仍是绿屏，因此把同样的“先缩放、后转换”策略放进
GStreamer 的 `viewfinderbin`：

```text
videoscale(1080p NV12 -> 854x480 NV12)
  ! videoconvert(dither=none, 854x480 BGRx)
  ! gtk4paintablesink
```

补丁位于
[`../packages/gst-plugins-bad/`](../packages/gst-plugins-bad/)。
正式启动器已经移除 `LD_PRELOAD=/usr/lib/samsinkinject.so`。后续的
`samucapsinject.so` 只负责相机源 caps 首选顺序，不参与显示缩放；
相机源与拍照分辨率的取舍见下一节。

2026-11-03 实机：

- `GDK_DEBUG=frames` 连续输出 `interval=33.3`，即 30 fps；
- `Snapshot` 进程约占单核 17%；
- 亮度 400/2047、SDP 900 mA 下电池净流 `+21…+39 mA`；
- 30 秒内无 USB 断开、reset 或 over-current；
- 插件日志确认 `viewfinder output 854x480 BGRx, scale method 0`。

冷启动后再次从桌面启动器复测：启动器环境无 `LD_PRELOAD`，插件哈希保持
`be94e9dda771c0d0c7de12873ce3877a8af45b33ef0cb2c3fe956b7328d81e12`，
24 秒取景电池净流 `+10..+31 mA`，900 mA 输入上限保持不变。
同步系统级启动项后（2026-11-03 22:09）再从桌面启动器复测：进程环境只有
`GSK_RENDERER=cairo` 和 `GDK_DISABLE=gl,vulkan,offload`，没有
`LD_PRELOAD`；亮度 400/2047、24 秒取景净流 `+16..+29 mA`，电量 93%→94%。

## 第五轮：720p60 取景

> 2026-11-04 起默认取景改为原厂 `1440x1080@30`；本节保留为可选高刷档，
> 只有显式设置 `SAMURAI_PREFER_SOURCE=1280x720@60` 时才启用。

`s5kgw1` 的 1280×720 模式（`line_length=4624`, `frame_length=6912`）
已加入模块，`cam` 和 PipeWire 源均实测 60.0–60.2 fps，无丢帧。Snapshot
的 Aperture 会把相机源 caps 的首项 `640x480` 交给 capsfilter，导致主摄
落到 30 fps；`samucapsinject.so` 将 `1280x720@60` 结构移到首位，保留
其余分辨率和 `MAXIMUM_RATE=30` 未改动的应用逻辑。

实机结果：`A5 IPE frame completed` 约 59–60 fps，桌面启动器环境包含

```text
LD_PRELOAD=/usr/lib/samucapsinject.so
SAMURAI_PREFER_SOURCE=1280x720@60
```

当前代价是 Snapshot 拍照沿用取景源的 1280×720。`camerabin` 的拍照分支
不会在 `start-capture` 前完成从 720p 到 1080p 的源 caps 重协商；已验证
运行时延迟 400 ms、切换 caps 仍只能得到 720p 照片。若必须同时保留
1080p 照片，需要在 Aperture/Snapshot 中为取景与拍照建立分开的源配置，
或重编译用户态应用；仅靠 `LD_PRELOAD` 无法可靠完成。

### 为什么不需要重编译 Snapshot

| 层 | 是否改动 | 具体 |
| --- | --- | --- |
| Snapshot 源码/二进制 | 否 | 设备 `/usr/bin/snapshot` 仍是 `snapshot-51.0-r0` 的原文件（2026-09-18，SHA256 `92f7e594…a8f3`） |
| GStreamer `camerabin` | 是 | 用补丁版 `libgstcamerabin.so` 替换发行包同名插件（SHA256 `be94e9dd…1e12`） |
| 桌面/D-Bus 启动项 | 是 | `Exec=/usr/bin/env GSK_RENDERER=cairo GDK_DISABLE=gl,vulkan,offload /usr/bin/snapshot` |

边界：这条路径不能改 Snapshot 自己的 `gtk4paintablesink` 协商逻辑，但凡是
落在 GStreamer 元素内部的行为，都可以靠替换插件或启动器环境完成。若要
修改应用插入的 `vf-bin` 结构、换 sink，或改变 `viewfinder-caps` 的协商
方式，仍然必须改 Snapshot 源码。

2026-11-03 交付检查发现系统级
`/usr/share/applications/org.gnome.Snapshot.desktop` 与
`/usr/share/dbus-1/services/org.gnome.Snapshot.service` 仍保留旧
`LD_PRELOAD`，只是被用户级同名文件覆盖，桌面实际启动不受影响。现已把
两份系统级文件同步为无 `LD_PRELOAD` 版本，避免用户级文件丢失后回落到
shim。`snapshot` 包本身未重打包，重装该包后需要重新覆盖这两个文件。

## 原厂取景与主拍参数落地（2026-11-04）

原厂 ODM `oplus_camera_config` / `oplus_camera_aps_config` 给出的主摄参数：

| 项目 | 原厂值 |
| --- | --- |
| 后摄/前摄人像预览 | `1440x1080` |
| APS `ispOutWidth/Height` | `1440x1080` |
| `masterPictureWidth/Height` | `4608x3456` |
| 高像素 | `9280x6944`（`name=6400`，`yuv=1`） |
| 高像素 MFNR | `4640x3472` |

`com.oplus.default.sensor.size.scale = 4x3x4x3x4x3`，主摄默认 4:3；
主摄 4608x3456 sensor mode 的 VTS 对应 30.06fps。因此原厂普通取景是
**1440x1080@30**，不是 60fps。60/120/240 的 tag 属于视频 HFR。

### 64MP 高像素模式（mode 0）

原厂 sensormodule 的 `resolutionData[0]` 是完整 64MP 模式：

| 项目 | 原厂 mode 0 |
| --- | --- |
| 输出 | `9280x6944` |
| Bayer / binning | `GBRG`，`1x1`（无 binning） |
| 帧率 | 10 fps |
| line/frame length | `20112` / `9472` |
| lane | 3-lane C-PHY |
| remosaic | `HWRemosaic`，`QUADCFA` |
| crop | `(0,0)/9280x6944` |
| PLL 关键值 | `0x030e=3`、`0x0310=240`、`0x0312=1` |

它与普通模式使用的 PLL/时序不同，不能只把 4608 改成 9280。RAW10 单帧
为 80,550,400 字节；10 fps 对应约 805 MB/s 的 RDI 写出带宽。原厂
`yuv=1` 表示 Android HAL 最终交付 YUV，但 sensor 模式本身仍是全阵列
Bayer，因此 Linux 侧仍需 RAW 解包和去马赛克。

2026-11-04 已把 mode 0 接入当前主线内核并实机验证：

- `0009-s5kgw1-9280x6944-highres.patch` 加入原厂 mode 0 的 1088 条
  寄存器、`9280x6944` 模式项和 `768 MHz` link-frequency 菜单项；
- `0011-s5kgw1-hide-mode0-from-libcamera.patch` 把 mode 0 从
  `enum_frame_size` 隐藏，避免 libcamera 把 `9280x6944` 当成默认最大
  分辨率；显式 V4L2 请求仍可选择 mode 0；
- `0010-camss-full-width-rdi.patch` 把 CSIPHY、CSID、ISPIF、VFE 和
  video 节点的 `8191` 宽度上限提升到 `16383`，供 RAW RDI 使用。当前
  设备改用原厂 CAMSS 模块的最小二进制补丁，因为 rebuilt 模块缺少
  原厂运行路径中的 `sm8150-camss-icp` 支持；
- `samurai-demosaic` 已改为接受可选宽高参数，可处理
  `9280x6944`（输入约 77 MiB，PPM 约 184 MiB）。

直接采集 mode 0：

```sh
SAMURAI_HIGHRES=1 /usr/local/bin/samurai-oem-capture
```

输出 `still-9280x6944.raw` 和 `Photo from <时间>.jpeg`。实机
`VIDIOC_DQBUF` 收到 80,550,400 字节，C 去马赛克约 0.84 秒，
ImageMagick JPEG 为 `9280x6944`；sensor 彩条和暗房间实景均已跑通。
暗房间画面偏黑是当时关灯导致的曝光场景，不是 mode0 空帧。

稳定组合为高像素 sensor `06f81218…4fce9` 加原厂 CAMSS 二进制补丁
`a976230f…8e47`。已验证普通 `1440x1080 + 4608x3456` 双流、高像素采集、
再次普通双流、再次高像素采集均可重复；Snapshot 预览仍为
`1440x1080@30`（GDK 帧间隔 33.3 ms）。

高像素模式仍是 10 fps 的静态拍摄档，不适合当作预览。默认 Snapshot
启动器已通过 `samucaptureinject.so` 把快门接到 `4608x3456` 双流：先让
Snapshot 正常生成 `~/Pictures/Camera` 文件与相册条目，再用 OEM JPEG
覆盖同一文件并补发 `picture-done`，因此相册加载的是全分辨率照片。
设置 `SAMURAI_HIGHRES_ON_SHUTTER=1` 后同一注入器输出 `9280x6944`；
由于高像素会重配 CAMSS/media graph，拍完自动重启 Snapshot 重新建立
`1440x1080@30` 预览，照片仍在 Camera 目录中可浏览。libcamera 侧仍不把
`9280x6944` 作为普通离散尺寸暴露，因此不能用 `cam` 的流角色选择它。

### 1440x1080 预览

`cam` 直接请求 1440x1080 可以成功，说明 sensor/CAMSS/VFE 支持；失败点在
PipeWire：SPA libcamera 插件只枚举 `StreamFormats::sizes()` 的离散表，
而 libcamera 默认 53 个候选尺寸里没有 1440x1080，所以 PipeWire 报
`no more input formats`。

补丁
[`libcamera/0010-camss-add-1440x1080-preview-size.patch`](libcamera/0010-camss-add-1440x1080-preview-size.patch)
把 `Size(1440, 1080)` 加入 `src/libcamera/stream.cpp` 的
`rangeDiscreteSizes`。本轮先在设备上对已安装的
`/usr/lib/libcamera.so.0.7.2` 做了等价二进制替换（偏移 `0x223398`，
`1440x900` → `1440x1080`），原文件备份在
`/root/libcamera.so.0.7.2.orig-a21fcedd`。替换后 PipeWire 枚举和
Snapshot 协商都出现 1440x1080。

启动器改为：

```
LD_PRELOAD=/usr/lib/samucapsinject.so
SAMURAI_PREFER_SOURCE=1440x1080@30
```

实机：

- PipeWire 1440x1080 NV12 稳态约 30fps；
- Snapshot 取景正常，照片为 `1440x1080`；
- 720p60 仍保留为可选档（`SAMURAI_PREFER_SOURCE=1280x720@60`）。

### 4608x3456 主拍双流

libcamera 的 camss-vfe 支持同时配置一路 processed + 一路 raw：

```
cam --camera=4 --capture=1 \
  -s role=viewfinder,width=1440,height=1080,pixelformat=NV12 \
  -s role=raw,width=4608,height=3456,pixelformat=SRGGB10_CSI2P \
  --file=/tmp/cap-#.bin
```

实测同一帧输出：

- `cam0-stream0`：1440x1080 NV12，2,332,800 字节；
- `cam0-stream1`：4608x3456 SGBRG10_CSI2P RAW10，19,906,560 字节。

RAW 解包后确认是 4608x3456 Bayer；用双线性去马赛克可还原
4608x3456 彩色图，说明原厂主拍分辨率在 sensor/CAMSS 层已经可用。
工具与解包脚本见
[`oem-capture/`](oem-capture/)。

### 限制

- Snapshot/camerabin 只有一路源，拍照沿用取景 caps；内置拍照仍是
  1440x1080。要同时“1440x1080 预览 + 4608x3456 主拍”，需要双流
  camera 应用或修改 PipeWire/SPA 暴露第二路 raw。
- VFE PIX 的 processed NV12 不能稳定输出 4608x3456；`3200x2400`
  因 A5 IPE 吞吐只有亚 1fps，`3840x2160` 也不到 2fps。高分辨率必须走
  RAW RDI，不能把 4608x3456 直接塞进当前 preview 源。
- 9280x6944 需要 sensor mode0 和 RAW RDI 宽度支持，当前未接入。
- 本轮 USB 充电未恢复（TCPM `current_max=0`），相机测试期间电量
  77%→69%；长时间高分辨率采集前需先恢复充电。

## 仍未完成

- **GPU / GL 仍不可用。** 主摄绿屏 + GPU fault 未解决，不能重新启用
  GL 或 Vulkan 渲染路径。
- **竖屏比例仍受限。** 节点支持多档缩放尺寸，但任意宽高（例如
  1080x1440）不保证被接受；应用应请求标准 16:9/4:3 尺寸。

## 60fps 取景与 90Hz 显示（离线准备）

原厂 sensor 模式表里 720p 的最小 VTS 是 864 行，6912 行对应
60.06fps；`0007` 的 720p 模式已改为 6912 行，30fps 由 VBLANK
恢复。离线模块 `s5kgw1.ko`（SHA256 `c6189a49…3614`，
vermagic `…-k363+`）已核对 720p/4624/6912 结构，尚未加载。
90Hz 面板只差 `B7`/`0x60` 两个寄存器值，补丁与构建结果见
[`../docs/DISPLAY-90HZ.md`](../docs/DISPLAY-90HZ.md)；内核实际位于
`logdump` FAT，已构建出可刷写镜像（SHA256 `24a2e988…9ac58`，
原 initramfs 已核对嵌入），等人在场再做重启验证。

## 应用侧实测（2026-11-03 晚）

点亮并解锁后直接测 `snapshot` 本身，用 `GDK_DEBUG=frames` 输出每一帧：

| 场景 | 结果 |
| --- | --- |
| 面板刷新率 / GTK frame clock（无视频窗口） | 60 Hz，59.9 fps |
| Snapshot 预览窗口 | 每帧 `frame_end` 约 190–205 ms → **约 5 fps** |
| 静态 1920x1080 BGRx 纹理重复重绘（不更新内容） | 59.3 fps |
| 静态 1920x1080 NV12 纹理重复重绘（不更新内容） | 约 5 fps |
| 实机 1920x1080 BGRx（每帧更新） | sink 30 fps / GTK 约 10–12 fps |
| 实机 1280x720 BGRx（每帧更新） | sink 30.0 fps / GTK 30 fps |
| 实机 960x540 BGRx（shim 回退路径） | sink 30.0 fps / GTK 30 fps |
| 实机 854x480 BGRx（`viewfinderbin`，当前默认） | **sink 30.0 fps / GTK 30 fps** |

因此传感器/CAMSS/PipeWire 侧的 30 fps 没有传导到应用：卡顿发生在应用侧。

**真正上屏的是 `gtk4paintablesink`。** Snapshot 51 的显示路径为：

```
pipewiresrc ! ... ! vf-bin(videoconvert ! videoscale) !
    aperture-tee ! queue ! gtk4paintablesink
```

`preview-appsrc ! preview-vscale ! preview-vconv ! preview-appsink`
是 camerabin 的拍照预览消息管线，只把 sample 通过 bus message 交给
应用，不参与取景显示。之前修改 `preview-appsink` 的 caps 没有效果，
原因是改错了分支。

`gtk4paintablesink` 的 caps 顺序把 YUY2／NV12 等 YUV 格式排在 BGRx
前面，默认协商后 GTK 每帧在 Cairo 软件渲染器里做 YUV→RGB，1080p
约 5 fps。改 BGRx 后 1080p 提到约 10–12 fps，但 Cairo 每帧还要上传／
缩放 8.3 MB 纹理；降到 1280x720 BGRx 后稳定 30 fps，`frame_end`
约 2–20 ms。

### 新组件：`preview-fastpath/`

正式修复由补丁版 `gst-plugins-bad` 的 `viewfinderbin` 完成：
`videoscale → videoconvert → capsfilter(BGRx,854x480)`。`preview-fastpath/`
中的 `samsinkinject.so` 仅保留为可选兼容回退，启动器不再加载。

### 环境注意事项

- 设备电池只有个位数百分比，USB 口只给 500 mA，系统会因低电量**干净关机**
  （不是内核崩溃；`logbookd` 里是正常的 SIGTERM 关机序列）。本轮在 8%
  下完成了约 15 秒短测；长时间测试前必须接足够功率的充电器。
- 重启后若 `samurai-ssc` 启动失败，`greetd` 会被依赖阻塞，需要
  `rc-service greetd start --nodeps` 才能起桌面。
- 会话解锁：`gdbus ... org.gnome.ScreenSaver.SetActive false` 只亮屏，
  还需要 `loginctl unlock-session <seat0 的 cy122 会话>` 才会真正解锁。
- `xdg-desktop-portal` 偶发卡住 `OpenPipeWireRemote`，表现为相机一直转圈；
  重启 `xdg-desktop-portal` 后恢复。
