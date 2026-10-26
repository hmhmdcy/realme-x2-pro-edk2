# PipeWire GStreamer CPU camera profile

上游PipeWire1.6.9，两个小补丁：上游延后pool回收的锁顺序修复，以及仅由进程环境 `SAMURAI_CAMERA_COPY=1` 启用的视频源复制策略。默认客户端行为保持，SHM/DMA-DRM/provider特性保留。

实机安装版本 `gst-plugin-pipewire-1.6.9-r1`；只替换该包拥有的GStreamer插件，PipeWire服务与libcamera未重启或改版。手机已有公钥验签，官方r0回退包保留，降级模拟通过。完整构建、测试、失败、限制和后续见[262记录](../../../reference/kernel262/README.md)。

常规aarch64 Alpine构建可使用本目录APKBUILD。262实际产物由隔离ARM64 SDK源码编译，再由原生APK3工具将该已核插件装入保留官方依赖/install-if的签名包；不是宣称已独立重跑完整abuild流水线。两种构建配置保留相同功能开关；来源校验见[source-lock](source-lock.json)。

复制增加CPU/内存带宽成本；30秒后端压力通过不替代长稳、功耗或GTK实屏验收。Snapshot仍采用Cairo配置，完整rootfs尚须纳入插件配方、包约束及对应启动环境。

264后续已部署[公共核心/SPA修复](../pipewire-common/README.md)，撤去Snapshot复制开关；此GStreamer插件r1仍保持，复制功能只留作默认关闭的诊断选项。实际GUI预览/快门及无复制的跨框架/多客户端验收见[264](../../../reference/kernel264/README.md)。上文服务未重启是262安装当时的事实；264更换公共库后已正常重启PW/WP。
