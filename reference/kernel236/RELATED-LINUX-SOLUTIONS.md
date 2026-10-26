# 同机与近平台 Linux 相机、GNSS 资料核对

检索日期2026-10-16。以项目源、补丁、维护者实测记录为依据；移植工程存在、引擎启动、传感器probe、实际取流和坐标fix分别记录。下列外部实测是各作者的报告，并非我们在相同硬件上独立复测。

## Realme X2 Pro 与 OPPO

X2 Pro已有[Halium项目记录#324](https://github.com/Halium/projectmanagement/issues/324)，2026年2月的清单仅勾选构建和rootfs启动，LXC、test_gps、test_camera未勾选。原链接失效，实际[Realme_RMX1931.xml](https://github.com/FusinX/samurai.halium10/blob/98de27ba33403851d83ce3ffbf6cdc0f8c419232/Realme_RMX1931.xml)指向FusinX的kernel/device/vendor三个halium-10分支。这提供厂商栈对照，不能称相机/GNSS已可用。

OPPO的[Reno10X/RenoAce官方内核源](https://github.com/oppo-source/Reno10X-RenoAce-10.0-kernel-source)可核板级连接与厂商驱动。此轮没有查到Reno Ace已完成原生Linux相机及GNSS的可信验收记录，不把Android BSP当作现成libcamera方案。本机资源仍以匹配19781原机overlay/OEM XML为准。

## 同 SM8150 的原生相机参考：OnePlus 7T Pro

[hotdog-linux-bringup，固定47087509](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/README.md)报告S5K3M5、IMX586、IMX481、IMX471经CAMSS/libcamera实采，使用Linux6.16方向内核及公开补丁。其[相机实采记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-09-mainline616-camera-libcamera.md)提供原生用户态证据，颜色/3A/更多模式仍开放；不能扩写成上游发行版开箱支持。

| 公开材料 | 本机能借鉴什么、必须重做什么 |
| --- | --- |
| [0058 S5K3M5驱动](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0058-media-i2c-add-the-samsung-s5k3m5-sensor-driver.patch) | V4L2框架/controls可参考；该模式MCLK24MHz/link602.5MHz，不能替换本机OEM19.2MHz PLL。 |
| [0063 S5K3M5板描述](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0063-arm64-dts-hotdog-describe-the-telephoto-camera.patch) | Hotdog CCI0/master0、reset28、CSIPHY0；X2Pro CCI1/master0、reset23、CSIPHY3，不复制DTS/PM8009供电。 |
| [0102 IMX471移植](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0102-media-add-OnePlus-hotdog-IMX471-front-camera.patch) | 同型号、19.2MHz，可对照模式/接口；Hotdog CCI1/master0，本机master1，保留本机已验生命周期。 |
| [0114 CAMSS失败启流回收](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0114-media-qcom-camss-unwind-failed-stream-starts.patch) | 与本机fae1逐函数比较，不能整包覆盖当前恢复逻辑。 |
| [libcamera S5K3M5 helper](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/temp/libcamera/0003-libcamera-add-Samsung-S5K3M5-sensor-data.patch)、[IMX471 helper](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/temp/libcamera/0007-libcamera-add-Sony-IMX471-sensor-data.patch) | 前者假定内核gain已表示倍率，后者为1024/(1024-code)；需要与本机control单位匹配。 |

本次所读[Torvalds IMX319](https://github.com/torvalds/linux/blob/master/drivers/media/i2c/imx319.c)及[IMX471](https://github.com/torvalds/linux/blob/master/drivers/media/i2c/imx471.c)仍仅ACPI匹配，不能仅因存在同名驱动就认为手机OF供电/接收链已完成。[CAMSS文档](https://docs.kernel.org/admin-guide/media/qcom_camss.html)描述V4L2/media graph及RAW接收；该文档的老平台列表不能当SM8150支持矩阵。应用入口见[libcamera官方用法](https://docs.libcamera.org/master/getting-started.html)：驱动/图/管线完整后才能使用cam、qcam、GStreamer libcamerasrc。

## GNSS：原生 QMI 与厂商 HAL 两条路线

Hotdog的[GNSS原始记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-10-gnss-qmi-loc.md)只证明LOC查询、同CID/proxy会话启停，未取得卫星或坐标。文中后半已纠正早期“GNSS必须先IPA”的推断：这是其打包MM路径的限制，不能泛化为RF前提。当前[状态页](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/status.md)仍将真实定位列为Partial。

近平台POCO X3/SM7150的[同CID start+monitor补丁](https://github.com/woodyst/surya-pmos/blob/d7eadb03f230506140839f18a6c0ef3c43016d7e/packages/libqmi/0004-qmicli-loc-combine-loc-start-with-monitoring.patch)把注册事件、启动和监控合在同一个LOC client，取消时完整stop；本机226已覆盖同CID，不能当新根因。[GSV补丁](https://github.com/woodyst/surya-pmos/blob/d7eadb03f230506140839f18a6c0ef3c43016d7e/packages/modemmanager/0002-shared-qmi-synthesise-missing-gsv-traces.patch)从已有有效SV/SNR补Galileo/BeiDou NMEA，SNR<=0仍留空，不能修原始零CNR。[engine unlock循环](https://github.com/woodyst/surya-pmos/blob/d7eadb03f230506140839f18a6c0ef3c43016d7e/device/services/gnss-engine-unlock.service)针对其Start GeneralError46；本机本地Start成功、221读lock=mt，症状不同，不部署该循环或机型NV操作。

同SM8150的Surface Duo有厂商栈真实fix报告：[固定源码记录](https://github.com/agentsco-lab/surfaceduo-droidian/blob/7cb53ddca60590b1f44c402d1b5bfd333b44fa66/adaptation/package/build.sh#L280)称冷启约100秒、约4m、未用XTRA。Droidian [binder](https://github.com/droidian/geoclue/blob/2f578dd7959c153fd085514cdbf20a7c71fb2aaf/src/gclue-hybris-binder.c#L196)经hwbinder获取Android GNSS HAL，[source](https://github.com/droidian/geoclue/blob/2f578dd7959c153fd085514cdbf20a7c71fb2aaf/src/gclue-hybris-source.c#L108)采用standalone/periodic/1000ms。这是厂商HAL→GeoClue，区别于本机MPSS→QRTR/QMI→libqmi/MM。

Surface Duo README的keepalive建议已过时：[e20c534修复](https://github.com/agentsco-lab/surfaceduo-droidian/commit/e20c53494c9f8c9739e86a013d2eee51d61a722c)移除了强制驻留，以免闲置退出后不断重启/重复初始化GNSS。不能照抄旧README。

Ubuntu Touch官方[OnePlus6 focal](https://devices.ubuntu-touch.io/device/enchilada/release/focal/)及[6T focal](https://devices.ubuntu-touch.io/device/fajita/release/focal/)标明GPS工作；这是Halium9、SDM845和focal版本证据，不推及noble或SM8150主线。厂商兼容路径边界见[Halium官方架构](https://docs.halium.org/en/latest/project/Planning.html)，用户入口见[UBports定位说明](https://docs.ubports.com/en/latest/userguide/dailyuse/location.html)。

## 对本机的决定

继续原生V4L2/CAMSS/libcamera路线，当前IMX319先完成RAW/回收，再用本机OEM资料准备S5K3M5的19.2MHz profile。新公开补丁用于精确比较，不覆盖现有前摄/PMIC配置。GNSS仍无正CNR/TRACK/fix；此次没有得到可直接部署的新RF、GPIO、NV或MEMSHARE修复，避免重复已过的同CID/辅助数据矩阵。
