# Phosh完整私有包独审：待产物

当前仅完成新构建输入、配方及原版回退事实的预审，**未签通过**。公开的 `phosh-build-result.json` 是保留的首次configure失败记录；resumed build及完整运行时包终态待作者交付，不能混用旧结果。Windows对private WSL日志的只读UNC访问被拒绝，没有另启WSL、改权限或干预构建。

已核原0.57.0-r3 APKBUILD的四个Meson选项／LTO、发行patch及冻结五文件应用入口；候选使用独立r3001身份。原四包的签名／原索引身份和实机72文件一致性收据已绑定。306项private build-input layer包含两个明确不同控制摘要的同源GIR开发工具，不是手机运行环境或完整APK事务；generated feedback接口未替换原运行库。最终包仍需证明没有把这些开发输入带入四个runtime splits，并保留portalsconf精确版本install_if。

GTK检查须区分范围。真实TopPanel在instance init即访问Shell/Layout，构造还依赖LayerSurface/DragSurface的Wayland上下文；Xvfb单独不提供这些协议。原0.57源码已有 `tests/testlib-full-shell.c`／`testlib-compositor.c` 可作完整上下文入口。若只在Xvfb用真实PhoshStatusIcon/Revealer验证新增准确子树和编译资源，应明确记为子树检查，不能声称完整TopPanel已经实例化。此建议已发作者，本审未运行GTK或旧10组测试。

完整产物出现后只补受影响的同次四split元数据、实际ELF依赖／导出、模板及resource绑定，保持旧源码／收据历史。当前没有安装、重启、设备或共享源码操作。
