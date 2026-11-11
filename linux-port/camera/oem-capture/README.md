# OEM 取景、4608x3456 主拍与 9280x6944 高像素

原厂 ODM 配置给出的主摄取景/拍摄参数是：

- 取景：`1440x1080`，主摄 sensor 模式约 30 fps；
- 主拍：`4608x3456`；
- 高像素：`9280x6944`，原厂 mode 0，10 fps 静态档。

Snapshot 走 PipeWire 的单流 camerabin，取景和拍照共用同一个源，因此
只能得到取景分辨率（`1440x1080`）。本目录提供一个独立的高分辨率
采集工具，直接使用 libcamera 的双流能力：

```
viewfinder 1440x1080 NV12
still      4608x3456 SGBRG10_CSI2P
```

这两个流在同一帧上同时输出，等价于原厂“预览 + 主拍”的双路配置。
高像素模式使用独立的 V4L2 mode 0 路径，原因是 Snapshot/libcamera 目前
只暴露普通源尺寸。

## 使用

Snapshot 会独占相机，先关闭它：

```sh
pkill -u cy122 -x snapshot
/usr/local/bin/samurai-oem-capture
```

高像素采集：

```sh
pkill -u cy122 -x snapshot
SAMURAI_HIGHRES=1 /usr/local/bin/samurai-oem-capture
```

输出目录为 `~/Pictures/OEM/OEM-<时间>/`：

- `preview-1440x1080.nv12`：NV12 预览帧；
- `still-4608x3456.raw`：10-bit MIPI packed Bayer，19,906,560 字节；
- `Photo from <时间>.jpeg`：设备端 C 去马赛克后的 4608x3456 JPEG；
- 高像素模式下输出 `still-9280x6944.raw`（80,550,400 字节）和
  `9280x6944` JPEG；
- 文件时间戳与拍摄时间一致。

环境变量：

- `SAMURAI_USER`：桌面用户，默认 `cy122`；
- `SAMURAI_CAMERA`：`cam` 的相机索引或稳定 ID，默认
  `/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10`（主摄 s5kgw1）；
- `SAMURAI_CAPTURE_DIR`：输出根目录。
- `SAMURAI_HIGHRES=1`：走 `9280x6944` mode 0 的 V4L2 RDI 采集；
  高像素采集要求没有活动的 Snapshot/PipeWire 相机流。

## Snapshot 快门注入

默认 Snapshot 启动器已加载 `samucaptureinject.so` 并设置
`SAMURAI_CAPTURE_ON_SHUTTER=1`。快门流程不是直接替换 Snapshot 的保存
逻辑，而是：

1. Snapshot 先正常保存一张 `1440x1080` JPEG 到
   `~/Pictures/Camera/`，产生相册条目；
2. 注入器暂扣 `picture-done`，停掉 camerabin，运行
   `samurai-oem-capture`；
3. 用原厂双流 JPEG 覆盖同一个 Camera 文件，再补发 `picture-done`；
4. 相册加载覆盖后的全分辨率文件。

因此普通主拍仍是“拍照后可浏览”的正常 Camera 目录，只是文件内容升级为
原厂 `4608x3456`：

```text
1440x1080@30 预览  +  按键快门 -> 4608x3456 JPEG
```

高像素会话：

```sh
pkill -x snapshot
SAMURAI_HIGHRES_ON_SHUTTER=1 \
  gio launch /home/cy122/.local/share/applications/org.gnome.Snapshot.desktop
```

该环境变量被注入器继承，按快门后输出 `9280x6944` JPEG。高像素拍摄需要
约数秒停流和去马赛克时间；由于 CAMSS/media graph 被重配，拍完会重开
Snapshot 以重新建立取景。照片已写入 `~/Pictures/Camera/`，重开后在相册
直接可见。

桌面也提供 `Camera (64MP OEM)` 图标；它运行
`/usr/local/bin/samurai-camera-64mp`，即上述高像素启动方式。

注入器可用以下命令交叉编译为不含 glibc 依赖的 ARM64 共享库：

```sh
./build-samucaptureinject.sh
install -m755 samucaptureinject.so /usr/local/lib/samucaptureinject.so
```

当前实机验证的 `samucaptureinject.so` SHA256 为
`4183a8a11dfbeb6bd4e13eeed08d687575c3fce73aed83ec0ef324ba392ac567`。

## RAW 还原

RAW 是 `SGBRG10_CSI2P`（GBRG Bayer），每 5 字节压缩 4 个 10-bit 像素。
设备端使用 `samurai-demosaic`（`demosaic_gw1.c`）完成解包、双线性
去马赛克、灰度世界白平衡和 gamma，再由 ImageMagick 编码 JPEG。
如果该工具不可用，也可以在主机上运行 `demosaic_gw1.py`：

```sh
python3 demosaic_gw1.py still-4608x3456.raw still-4608x3456.jpg GBRG
```

需要 Python 3、NumPy 和 Pillow。C 工具现在也接受可选尺寸：

```sh
samurai-demosaic still-9280x6944.raw still-9280x6944.ppm 9280 6944
```

原厂 `6400` 高像素模式对应 `9280x6944`，由
`0009-s5kgw1-9280x6944-highres.patch` 加入模式，并由
`0011-s5kgw1-hide-mode0-from-libcamera.patch` 对 libcamera 隐藏，避免
它抢占默认取景配置。当前设备的 CAMSS 使用原厂模块加
`patch-qcom-camss-full-width.py` 的最小二进制补丁，而不是 rebuilt
模块；原厂模块包含源码树中缺失的 `sm8150-camss-icp` 路径。

## 限制

- 手工运行 `samurai-oem-capture` 时不能有 Snapshot 活动流或其它 `cam`
  进程；通过快门注入器运行时，注入器会先停流并等待；
- Snapshot 原生照片路径仍只有 1440x1080；要得到原厂主拍必须经过
  注入器或手工命令；
- 高像素模式是 10 fps 静态档，不适合作为连续取景；
- 高像素快门需要显式设置 `SAMURAI_HIGHRES_ON_SHUTTER=1`；默认快门
  走 `4608x3456` 普通主拍；
- 该工具只负责抓取，不提供实时取景窗口；取景请先用 Snapshot；
- 普通双流与高像素路径已实测可反复切换；快门注入会在拍摄后恢复预览；
- 去马赛克是双线性算法，仅用于验证 RAW 与分辨率，画质不等同于
  原厂 ISP。
