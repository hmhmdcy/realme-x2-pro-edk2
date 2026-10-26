# Realme X2 Pro 与近机型：Linux 摄像头、GNSS 可复用方案

核对日期：2026-10-16。本文补充[236资料](../kernel236/RELATED-LINUX-SOLUTIONS.md)，以项目源码、补丁及维护者实测为依据。外部机型的成功是作者报告，本机实测单列；Android厂商栈、原生Linux取流、应用预览、颜色调校和卫星fix分别判断。

## 查到了哪些机型

| 机型或实现 | 证据与实际状态 | 对 X2 Pro 的用途 |
| --- | --- | --- |
| Realme X2 Pro / samurai | [Halium #324](https://github.com/Halium/projectmanagement/issues/324)在此次重新读取时只勾选构建和rootfs启动，LXC、test_camera、test_gps未勾选；[固定manifest](https://github.com/FusinX/samurai.halium10/blob/98de27ba33403851d83ce3ffbf6cdc0f8c419232/Realme_RMX1931.xml)列出FusinX kernel/device/vendor的halium-10分支。 | 提供同机厂商兼容栈入口；没有相机或定位已验收的公开证据，不能称现成可安装修复。 |
| OPPO Reno Ace / Reno 10x Zoom | [OPPO官方Android内核源](https://github.com/oppo-source/Reno10X-RenoAce-10.0-kernel-source)，以及[Realme官方X2 Pro/X3源](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source)。 | 查CCI、GPIO、MCLK、PMIC及厂商驱动连接。此次没有找到Reno Ace原生Linux相机与真实GNSS fix均完成的可信记录；同平台不能代替本机19781板级资料。 |
| OnePlus 7T Pro / hotdog，SM8150 | [固定47087509状态页](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/status.md)报告四颗相机通过libcamera采集，整体仍Partial。[S5K3M5实测](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-09-mainline616-camera-libcamera.md)包含60帧软件ISP、曝光变化和Plasma Camera预览。 | 当前最接近的原生相机参考：S5K3M5、IMX471的驱动/helper，SM8150 CAMSS错误回收、媒体图、libcamera到应用链路。对焦/颜色/更多模式仍不能视为量产完成。 |
| OnePlus 6 / 6T，SDM845 | [Ubuntu Touch 6 focal](https://devices.ubuntu-touch.io/device/enchilada/release/focal/)及[6T focal](https://devices.ubuntu-touch.io/device/fajita/release/focal/)标注拍照和GPS工作；属于Halium 9路线。 | 厂商HAL兼容路线的成功参照。其IMX371/IMX376K/IMX519与本机不同；一加6/6T没有IMX319，不能套其传感器标定。 |
| Surface Duo，SM8150 | [Droidian适配源码](https://github.com/agentsco-lab/surfaceduo-droidian/tree/7cb53ddca60590b1f44c402d1b5bfd333b44fa66)报告使用厂商GNSS HAL取得真实fix。[GeoClue入口](https://github.com/droidian/geoclue/blob/2f578dd7959c153fd085514cdbf20a7c71fb2aaf/src/gclue-hybris-binder.c)通过hwbinder调用HAL。 | 证明SM8150在Linux桌面加厂商HAL的路径可行。其Android11 vendor与板级初始化不等于samurai，不能单拷一个.so就得到同样结果。 |
| POCO X3 / surya，SM7150 | [同CID启动并监控补丁](https://github.com/woodyst/surya-pmos/blob/d7eadb03f230506140839f18a6c0ef3c43016d7e/packages/libqmi/0004-qmicli-loc-combine-loc-start-with-monitoring.patch)及[GSV生成补丁](https://github.com/woodyst/surya-pmos/blob/d7eadb03f230506140839f18a6c0ef3c43016d7e/packages/modemmanager/0002-shared-qmi-synthesise-missing-gsv-traces.patch)。 | 前者是QMI会话生命周期参考；后者仅把已有有效卫星/SNR变成NMEA。本机226已覆盖同CID，原始零CNR不能靠补GSV解决。 |

## 原生 Linux 摄像头怎样使用

接收链是：**传感器V4L2 subdev → CCI控制及本机供电/复位/MCLK → CSI-2/CSIPHY/CSID → CAMSS RDI RAW → libcamera软件ISP与IPA → qcam、GStreamer或相机应用**。[CAMSS内核文档](https://docs.kernel.org/admin-guide/media/qcom_camss.html)解释V4L2/media graph和RAW接收；其中老平台枚举不是SM8150支持矩阵。[libcamera软件ISP上游补丁](https://patchwork.libcamera.org/patch/19834/)说明qcom-camss与simple软件管线的关系。此路径能够处理RAW，不意味着手机Spectra全部硬件ISP算法已开放。

[libcamera官方用法](https://docs.libcamera.org/master/getting-started.html)提供`cam -l`、`qcam`和GStreamer `libcamerasrc`入口。只有sensor、完整媒体链、正确gain helper和匹配调校数据均就绪，应用才能正常使用；单独出现`/dev/video*`或probe成功不足以验收。本工程继续只在RAM做场景统计，本文没有执行保存照片或显示场景的命令。

可复用的具体代码包括Hotdog的[0058 S5K3M5](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0058-media-i2c-add-the-samsung-s5k3m5-sensor-driver.patch)、[0102 IMX471](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0102-media-add-OnePlus-hotdog-IMX471-front-camera.patch)、[0114 CAMSS回收](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0114-media-qcom-camss-unwind-failed-stream-starts.patch)。本机237已按当前内核结构改写并验证回收修正。S5K3M5必须保留本机OEM 19.2MHz模式；Hotdog驱动所用24MHz、reset28、CCI0/CSIPHY0与本机不同，不能整份复制DTS或PLL。

[上游IMX319](https://github.com/torvalds/linux/blob/master/drivers/media/i2c/imx319.c)提供寄存器、模式和V4L2基础，当前读取版本面向ACPI。本机235另加OF、真实电源、runtime PM和复位时序；238进一步修正libcamera analogue gain转换：`gain=1024/(1024-code)`，8倍对应code896。不能把另一颗Sony传感器的黑电平、像素尺寸、延迟顺带复制。

本机此次已验证48帧RAW控制：约2ms/1倍→32ms/1倍→32ms/8倍→2ms/1倍，采集元数据及I²C发送请求的曝光/增益码对应变化。I²C trace是发送事件，不是ACK或寄存器读回；图像均值和噪声变化仍不足以独立证明正常光学成像。RGB也完成48帧，但queued_index1整帧为零，严格验收仍失败，未把r14候选替换默认r13。

## 相近 Sony 摄像头的黑帧历史

[pmaports MR6299对应的固定提交](https://gitlab.postmarketos.org/postmarketOS/pmaports/-/commit/250904dd1da51a8f6afdc7f7b1f7b1e60b139624)曾给IMX371/IMX376加入固定黑电平调校；[官方API diff](https://gitlab.com/api/v4/projects/8065375/repository/commits/250904dd1da51a8f6afdc7f7b1f7b1e60b139624/diff)说明该常数来自相似传感器推测。该值不适合直接移给IMX319。[后来的libcamera通用修复](https://patchwork.libcamera.org/patch/24487/)把未标定时的初始BLC从255降到16；0.6.0已有，本机0.7.2也已包含。

因此当前不是漏装这个历史补丁。对实际r14源码的公式复核发现：RAW10约63–67DN量化到8bit后，初始black0/gamma1得到RGB14–15，black16得到全零，动态降到black12后得到33–38；恰与本机q0/q1/q2的范围吻合。**这是源码与统计相符的候选解释，尚未取得同帧实际ISP参数证明。** 下一项应记录逐帧BLC/Gamma/ColourGains及参数更新时序，必要时配对同request RAW/RGB；不以暗光为由豁免，也不把非零灰底当成彩色画面正常。

## Linux GNSS 两条已知路线

1. 原生QMI：MPSS固件/QRTR → QMI LOC/libqmi → ModemManager Location → GeoClue；`gnss-share`可通过MM读取NMEA并管理共享使用。Hotdog的[原始GNSS记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-10-gnss-qmi-loc.md)仅证实LOC查询及会话启停，没有取得卫星或坐标。文末已纠正“GNSS硬件必须依赖IPA”的早期说法：那是当时打包的MM路径限制，QMI本身可独立使用。
2. 厂商兼容栈：匹配的Android vendor GNSS HAL → binder/libhybris → GeoClue或Ubuntu Touch定位服务。[Halium架构](https://docs.halium.org/en/latest/project/Planning.html)说明这种复用方式；一加6 focal和Surface Duo提供成功案例。需要匹配内核接口、Android运行环境、HAL依赖和配置，移植成本不能简化为安装普通Linux GPS软件。

[gnss-share新主仓](https://gitlab.postmarketos.org/postmarketOS/gnss-share)与旧GitLab归档应区分，[官方迁移说明](https://postmarketos.org/blog/2024/10/14/gitlab-migration/)提供来源。[此次核到的固定MM后端](https://gitlab.com/postmarketOS/gnss-share/-/blob/67c14647/internal/gnss/modemmanager.go)只设置GPS_NMEA、刷新周期、轮询GetLocation并在停止时清GPS位，没有自动下载/注入XTRA；不能把README的部分设备A-GPS或[2023议题](https://gitlab.com/postmarketOS/gnss-share/-/issues/10)的设想当作MM后端已实现功能。[gpsd官方输入说明](https://gpsd.io/gpsd.html)面向已有接收机/数据流，安装它不能修复本机原始零CNR；[旧MSM示例](https://github.com/andersson/gpsd/blob/master/driver_pds.c#L14)查找PDS 0x10/version2，与本机LOC 0x16不同。

原生控制实现可直接对照[libqmi LOC](https://github.com/linux-mobile-broadband/libqmi/blob/main/src/qmicli/qmicli-loc.c)与[MM QMI](https://github.com/linux-mobile-broadband/ModemManager/blob/main/src/mm-shared-qmi.c)。GeoClue提供桌面定位权限与消费接口；这些软件层各有职责，均不能将没有有效卫星信号的原始报告变成真实fix。

## 本机 GNSS 当前结论

238以实际vendor分区只读提取GNSS服务、配置和依赖，不执行vendor代码、不读取NV/persist、不搜星或发送新SET；两次均正常卸载，前后分区摘要一致。当前vendor属性为Android16/SDK36，ELF同时有API30实现和API36接口构建标记；不能再笼统称其Android10 vendor，标记不同本身也不能证明ABI错误。关键文件逐字节匹配[固定HyperTeam vendor](https://github.com/HyperTeam/proprietary_vendor_realme_samurai/tree/77f9b7aa9445e268d406317bf98db8d6a696a9a9/proprietary/vendor)，不扩写为全部vendor均已比对。

vendor/etc/gps.conf不存在，不等于整机遗漏；设备树把gps.conf安装到ODM。旧228所引ODM izat.conf是社区仓库资料，尚不能证明本机当前ODM配置，也不能把vendor/ODM配置差异解释成配置被更改。下一项来源核验只需当前匹配ODM的gps.conf，不重新扫描vendor或NV。

对实际liblbs_core反汇编、结合vendor izat.conf推演，其普通分支会向LOC 0x84注入地面定位/传感器辅助配置：GTP_CELL(type0,disabled)、GTP_WIFI(type3,disabled)、SAP(type1,premium)，各等同号完成指示、1000ms超时；此次没有观察Android实际发包。[固定高通IDL](https://github.com/qualcomm-linux/location-apis-qcom/blob/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948/loc_api/loc_api_v02/location_service_v02.h#L14293)给出枚举。sap.conf的SENSOR_CONTROL_MODE=2是MODEM_DEFAULT。未发现这些是本机RF/LNA供电前提的证据，不能因此追加SET或照抄其它手机NV解锁。

独立卫星接收无需SIM；无SIM可能影响MM暴露接口或辅助定位路径，需要与RF接收分开诊断。本机此前的原始卫星CNR仍无正值、未TRACK/fix，室内窗边条件仍是限制因素，但不足以单独证明根因。此次研究得到可核对的初始化链与配置来源缺口，尚没有可直接部署的新GNSS RF修复。
