# RMX1931 桌面配置候选 3-r1

此目录对应 pmaports `device/testing/samurai-desktop` 的完整候选配方。`greetd.confd` 通过 OpenRC 标准 `rc_need` 让设备桌面等待 dbus 和 iio-sensor-proxy；SSC 服务继续管理自己的固件及 radio 依赖。撤掉原来桌面先于 radio 的相反顺序，避免构成依赖环。

这次没有修改 Phosh、Snapshot 代码。手机已单独更新 `/etc/conf.d/greetd` 并成功重建 OpenRC 依赖缓存；下一次整机启动的顺序仍需实测。候选尚未构建或安装为 APK。

既有 Snapshot Cairo／禁用 GL、Vulkan、offload 的启动回退保持。它是尚未解决的 GPU 限制，不能宣称默认图形路径已正常。旋转安装矩阵见 [samurai-platform](../samurai-platform/README.md)，当前验证见 [269](../../../reference/kernel269/README.md)。
