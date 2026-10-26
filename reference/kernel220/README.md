# 220：切换模式后的曝光元数据

2026-10-16，手机仍为已验证的boot219/e49模块/完整r6/config-r1，当前实验参数N。新USB邻居与当前启动身份已核对，建立k220-baseline guard；49条当前相机payload、媒体图/休眠与三DSP检查通过。[基线](baseline-validation.json)。

标准客户端当前只暴露Contrast/Gamma，手动曝光API仍开放。分别取36帧2MP与4MP RGB，仅采集元数据和DelayedControls数值，不映射或保存像素。4MP元数据与本模式行时长吻合；2MP的1290行应换算约17057.85µs，却报10117µs。72组元数据都符合缓存的4MP行时长。[根因](metadata-root-cause-validation.json)、[2MP](exposure-metadata-r6-1920x1088-validation.json)、[4MP](exposure-metadata-r6-2296x1728-validation.json)。这不代替实际曝光延迟/光度标定。

源码显示IPA init先缓存sensorInfo，configure只更新控制范围，未刷新模式时序。候选通过IPAConfigInfo传入当前sensorInfo，并在每次配置时更新曝光换算，拒绝零速率/行长。[三文件补丁](libcamera-refresh-sensor-timing.patch)、[源码锁](candidate-source-validation.json)。参考[原始元数据实现](https://lists.libcamera.org/pipermail/libcamera-devel/2025-March/049410.html)与[其它IPA的逐次传递方式](https://lists.libcamera.org/pipermail/libcamera-devel/2024-December/047902.html)，没有复制其它镜头标定。

完整r7/r2已构建并部署，保留全部原管线与子包。使用原214完整对象缓存和官方abuild build/rootpkg/index阶段；原214目录先快照保护，终态后恢复，候选完整源/对象另存。最初宿主沿chroot绝对软链接找不到源码归档，在编译前退出并恢复了原目录；实际缓存归档SHA512正确，已恢复已有候选继续。[原失败](initial-build-preflight-failure-validation.json)。首次打包还因旧子包目录残留失败；移开候选pkg目录、复用完成的44目标构建重新封装，未重编译或丢弃原目录。[打包失败记录](initial-packaging-failure-validation.json)。

关灯/室内窗边条件保持，无闪光灯、外部照明、场景图片或定位坐标公开。GNSS真实fix、后置四摄及其余全外设目标继续active；旧[219验收](../kernel219/README.md)保持。

## 部署与回归

13包签名与34个ARM64 ELF核对通过，5IPA与r7核心内嵌公钥匹配，原Qt/Python/GStreamer等完整功能保持。[产物](forward-package-artifact-validation.json)、[运行与IPA验签](host-runtime-qa-validation.json)。原214完整目录2254个文件/链接已恢复，候选完整源/对象保留，原密钥复用，没有生成或上传私钥。

候选线程模式的2MP/4MP/实验16MP各36帧、强制独立IPA进程的2MP/4MP各36帧通过；独立进程由临时ipa.force_isolation配置启用，并实际观察到隔离日志。没有去掉或破坏签名来触发隔离。[独立进程2MP](exposure-metadata-candidate-isolated-1920x1088-validation.json)、[独立进程4MP](exposure-metadata-candidate-isolated-2296x1728-validation.json)。

七组件统一升级为r7/config-r2，944包中的937无关记录保持，49条payload核对通过，原七个r6/r1包及world/repo/配置保留，原生降级模拟通过，未执行本轮完整降级往返。[原生事务](r7-package-install-validation.json)。仅重载WirePlumber，桌面/PipeWire身份保持。

默认系统库下2MP/4MP/实验16MP各36帧通过，新修复共验证288帧。所有样本与本模式行时长计算的差小于1µs，是整数微秒量化范围，不是实际曝光精度/延迟标定。三模式的阵列时序/PLL和内核模块没有更改。

| 2MP最后一帧 | 元数据 | 当前模式计算值 |
| --- | ---: | ---: |
| r6，1290行 | 10117µs | 17057.85µs |
| 已装r7，1290行 | 17057µs | 17057.85µs |

[已装2MP](exposure-metadata-system-r7-1920x1088-validation.json)、[4MP](exposure-metadata-system-r7-2296x1728-validation.json)、[实验16MP](exposure-metadata-system-r7-4608x3456-validation.json)。所有试验只读帧元数据和数值控制，没有映射/保存图像；媒体图/格式/控制均恢复。

默认GStreamer另取六帧通过。[标准API](standard-gstreamer-validation.json)。首次包装器因继承探针路径的匹配字符串被误改，在取流前退出；已校验并复用同一探针后修正路径，保留[前置失败](gst-preflight-failure-validation.json)。

[最终健康](final-health-validation.json)：三DSP running，前摄/CCI/CAMSS休眠、两前摄电源零用户/关闭、时钟/本域票释放，参数N/图案0，GNSS空闲、BT关闭无连接，taint与五类fault0，NV/非相机程序保持。[146成员私人归档](final-evidence-validation.json)逐一哈希核对，指纹/场景/坐标不公开。

配方与部署锁已整合，[整合收据](package-integration-validation.json)。尚未验收标准手动曝光API、真实曝光延迟、CFA/几何/颜色/正常光照画质、后置四摄与GPU ISP。GNSS真实fix、蜂窝真实业务及其余[全硬件目标](../../linux-port/docs/HARDWARE-STATUS.md)继续active。
