# X2 Pro 与近机型：Linux 相机和 GNSS 的实际使用路线

2026-10-16 再次联网核对，补充[238研究](../kernel238/RELATED-LINUX-SOLUTIONS.md)。三个已授权代理只读查源码，手机操作由主线程串行完成。以下外部成功属于维护者报告，本机验收见[239记录](README.md)。

## 哪些机型值得参考

| 对象 | 查到的实际能力 | 对本机的价值 |
| --- | --- | --- |
| OnePlus 7T Pro / hotdog，SM8150 | [固定状态页](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/status.md)及[相机实测](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-09-mainline616-camera-libcamera.md)报告四摄原生采集，S5K3M5有软件ISP与应用预览；[GNSS记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-10-gnss-qmi-loc.md)只到LOC会话启停，没有真实fix。 | 最接近的CAMSS、S5K3M5、IMX471参考。本轮未发现超出238固定提交的新修复；不能把其新镜像内核版本当作新相机验收。 |
| Realme X2 Pro / samurai，Halium | [Halium #324](https://github.com/Halium/projectmanagement/issues/324)尚未勾选LXC、test_camera、test_gps；[FusinX manifest](https://github.com/FusinX/android_device_realme_samurai/blob/c64691bf3a15a7048fb3a8aa1cd3d284a7fb6db4/manifest.xml)声明camera/GNSS hwbinder HAL。 | 有同机厂商兼容路线入口，没有已完成相机/GPS的公开验收。Android HAL声明不等于本机主线Linux能够直接调用。 |
| Realme X3，SM8150 | [维护者页面](https://wiki.postmarketos.org/wiki/Realme_X3_%28realme-x3%29)标Camera未测试；[固定DTS](https://github.com/sm8150-linux-mainline/linux/blob/91911e069acbb9d38e5dcc633d454f7b1ff9bc4b/arch/arm64/boot/dts/qcom/sm8150-realme-x3.dts)未启用sensor/CCI/CAMSS端点。 | 可参考SM8150平台与MPSS组织；没有查到真实相机采集或GNSS fix方案。 |
| OPPO Reno Ace / Reno 10x Zoom | [官方板级源](https://github.com/oppo-source/Reno10X-RenoAce-10.0-kernel-source/blob/289d6118ef783a281a8ecf0378e3c560ff6976c4/msm-4.14/arch/arm64/boot/dts/19081/sm8150-camera-sensor-mtp.dtsi)可核电源、时钟和连接；有24MHz前摄、部分2.9V配置，与本机不同。 | 用于交叉查厂商资源。没有查到这两款原生Linux相机和真实GNSS fix均完成的可信记录，不能整份套DTS。 |
| OnePlus 6/6T，SDM845 | Ubuntu Touch [6 focal](https://devices.ubuntu-touch.io/device/enchilada/release/focal/)和[6T focal](https://devices.ubuntu-touch.io/device/fajita/release/focal/)标注相机/GPS可用；6的[固定设备数据](https://gitlab.com/ubports/infrastructure/devices.ubuntu-touch.io/-/blob/de838718d502068135bf771bfe22857e8ec3d128/data/devices/enchilada/releases/focal.md)说明Halium9。 | 厂商HAL路线成功参照，不能扩写为SM8150原生成功。其相机不等于本机IMX319。 |
| Surface Duo，SM8150，Droidian | [固定适配源码](https://github.com/agentsco-lab/surfaceduo-droidian/blob/7cb53ddca60590b1f44c402d1b5bfd333b44fa66/adaptation/package/build.sh#L280)记录厂商HAL定位约4m、冷启约100秒、无XTRA。 | 同SoC的GNSS成功链路：匹配vendor HAL→hwbinder→GeoClue。当前版本已去除旧keepalive重启循环。 |

## 原生相机怎样接到 Linux 应用

链路是：**传感器驱动与本机电源/复位/MCLK → V4L2 subdev/media graph → CSI/CSIPHY/CSID/CAMSS RDI → RAW → libcamera simple管线/软件ISP → 应用**。[CAMSS文档](https://docs.kernel.org/admin-guide/media/qcom_camss.html)解释媒体图与RAW接收；其文中老平台枚举不是当前SM8150支持矩阵。取得RAW不等于全部Spectra硬件ISP算法开放。

驱动、媒体图和libcamera sensor helper就绪后，通常用`cam -l`枚举，以`qcam`预览，或经GStreamer的`libcamerasrc`供应用使用，见[libcamera官方用法](https://docs.libcamera.org/master/getting-started.html)。先确认实际camera ID、支持的格式与尺寸，不能依赖易变化的`/dev/videoN`编号。曝光/增益、CFA、黑电平、颜色、裁剪和控制延迟分别验证；仅probe成功或非零像素不够。

下面只展示检查入口，不在本轮启动预览或保存图片：

```sh
media-ctl -p
cam -l
gst-inspect-1.0 libcamerasrc
```

| 本机相关器件 | 可复用的 Linux 来源 | 必须保留的本机差异 |
| --- | --- | --- |
| IMX471 前摄 | [Hotdog驱动](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0102-media-add-OnePlus-hotdog-IMX471-front-camera.patch)；主线[新增提交](https://github.com/torvalds/linux/commit/be1589e567aeea5d32d9dd7027501657787d3ad3)和[CCI错误修复](https://github.com/torvalds/linux/commit/b272a1780e8515617fed2564edccb8da8431d707)。 | 当前[主线实现](https://github.com/torvalds/linux/blob/2f2f7eeef8b0a1a9b9ca998231419873ccae8d4e/drivers/media/i2c/imx471.c)为笔记本ACPI、1928×1088单模式；不能替换本机e49的OF、电源及Quad模式。 |
| IMX319 后摄 | [主线驱动](https://github.com/torvalds/linux/blob/2f2f7eeef8b0a1a9b9ca998231419873ccae8d4e/drivers/media/i2c/imx319.c)提供寄存器和V4L2基础。 | 主线仍主要ACPI；本机235已另补OF/runtime/供电。libcamera增益按`1024/(1024-code)`，不能借用别的Sony黑电平。r15已有本机首参同步修复，光学黑场仍开放。 |
| S5K3M5 长焦 | [主线新增提交](https://github.com/torvalds/linux/commit/7d402666094ce25d2b52da679b8d7210cde01a34)及[当前驱动](https://github.com/torvalds/linux/blob/2f2f7eeef8b0a1a9b9ca998231419873ccae8d4e/drivers/media/i2c/s5k3m5.c#L1238)；Hotdog已有实采。 | 上游只接受24MHz；本机19.2MHz、CCI1/master0、reset23、MCLK3、CSIPHY3及供电不同。239已核917条初始化和4×53模式写入，应以本机OEM表接驱动框架。 |
| OV02A10 候选人像 | [主线驱动](https://github.com/torvalds/linux/blob/2f2f7eeef8b0a1a9b9ca998231419873ccae8d4e/drivers/media/i2c/ov02a10.c)，以及[endpoint/可选属性修复](https://github.com/torvalds/linux/commit/94971ba0592ca77ec99b292226a4b398763315b8)。 | 上游1600×1200、单lane、24MHz。先确认本机物理身份和OEM时序；尚不能宣称本机人像可用。 |
| S5KGW1 主摄 | 此次未找到可直接复用的主线驱动或可信原生Linux实采方案。 | 仍须处理本机C-PHY接收、模式和电源资源；别机Android能拍照不能补足这些证据。 |

## GNSS 怎样供 Linux 应用使用

**原生路线：MPSS固件 → QRTR/QMI LOC → libqmi/ModemManager Location → GeoClue/应用。** `gnss-share`可通过MM共享NMEA。已支持设备常用如下操作；这是说明，不是本轮执行记录：

```sh
mmcli -m any --location-status
mmcli -m any --location-enable-gps-nmea
mmcli -m any --location-get-gps-nmea
mmcli -m any --location-disable-gps-nmea
```

实际运行须由一个控制方管理启停，检查时间戳推进、有效fix、正CNR及真实定位事件。本机已有自定义同CID诊断和桌面辅助服务，不能再并开这些命令干扰会话。无SIM不妨碍独立卫星接收，但MM是否开放无SIM接口是另一层软件条件。

Hotdog的记录可以参考CID生命周期，不能提供零CNR修复。[Surya同CID补丁](https://github.com/woodyst/surya-pmos/blob/d7eadb03f230506140839f18a6c0ef3c43016d7e/packages/libqmi/0004-qmicli-loc-combine-loc-start-with-monitoring.patch)和[GSV补丁](https://github.com/woodyst/surya-pmos/blob/d7eadb03f230506140839f18a6c0ef3c43016d7e/packages/modemmanager/0002-shared-qmi-synthesise-missing-gsv-traces.patch)分别解决会话与报告，本机已覆盖前者；后者不能从零SNR合成真实信号。[gnss-share MM后端](https://gitlab.postmarketos.org/postmarketOS/gnss-share/-/blob/67c146475379d358ce17f2f132601ee586130bc9/internal/gnss/modemmanager.go)没有XTRA自动注入，gpsd也不能修复接收机RF初始化。

**厂商兼容路线：匹配的Android vendor GNSS HAL → Android运行环境及binder/libhybris桥 → 桌面定位服务。** Surface Duo使用[Droidian GeoClue桥](https://github.com/droidian/geoclue/blob/2f578dd7959c153fd085514cdbf20a7c71fb2aaf/src/gclue-hybris-binder.c)。这提供可行的替代研究路线，迁移仍需匹配本机内核ABI、HAL依赖和初始化；不是单拷一个`.so`或`gps.conf`。

[MM SUPL地址字节序修复](https://chromium.googlesource.com/external/gitlab.freedesktop.org/mobile-broadband/ModemManager/+/f51cc9488b94a53f411149b7cb5380c5839c3a27)在本机保存源码中已含，不重复补丁。它修辅助服务器连接，不解释本机standalone及采用辅助数据后仍原始CNR0/SEARCH。

## 本机此次得到什么

r15/r10已安装七包并验证默认运行、两次start首参数、前摄RAW/RGB回归及清理；保留后摄全零帧失败，不宣称光学/颜色已修复。S5K3M5本机模式表离线核验完成，下一颗适配优先级较高。

实际ODM `etc/gps.conf`已只读提取，逐字节等于锁定社区版本，见[本机比较](odm-gps-comparison-validation.json)。但实际GNSS库固定读`/vendor/etc/gps.conf`，尚无运行时映射或注入证据；文件存在不证明HAL采用。库内默认也不是modem当前状态。没有发现可直接部署的新RF初始化补丁；GNSS正CNR、TRACK和真实fix仍未解决。

[此次新增主来源快照收据](related-linux-source-validation.json)保存成功和失败：固定原文8项已抓取，6项GitHub API请求失败；代理独立核过对应提交/状态，不将失败当成功下载。此前Hotdog/Duo/GeoClue/gnss-share的原文收据见[238](../kernel238/related-linux-source-validation.json)。本次没有照搬别机固件、写NV或运行下载的仓库代码。
