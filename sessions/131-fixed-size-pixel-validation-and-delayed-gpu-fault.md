# 阶段131：真实离屏尺寸对照与仍存在的迟发GPU故障

2026-10-12，goal active。当前仍为#129内核及已增量部署的rootfs130功能，未刷分区、未擦userdata。阶段130的BlueZ扫描/启动验收不等同于配对传输，Wi-Fi/摄像头/其它15组边界保持。

复测只运行旧失败的`build:use-vbo=true`一个场景，UID10000、20秒墙钟/10秒CPU/768MiB地址空间上界，随后30秒观察迟发故障。签名原版glmark2-2023.01-r1实际FD640/Mesa26.2.4输出预期`0xffa7a7a7`与实际`0xffa5a5a5`，RGB各差2，验证失败但进程退出0；此轮无新增GPU fault，桌面PID保持。归档36个成员逐项SHA通过，不能以exit0代替像素验收。

官方[CanvasGeneric源码](https://github.com/glmark2/glmark2/blob/2023.01/src/canvas-generic.cpp)、[Wayland后端](https://github.com/glmark2/glmark2/blob/2023.01/src/native-state-wayland.cpp)与[验证场景](https://github.com/glmark2/glmark2/blob/2023.01/src/scene-build.cpp)表明，验证参考要求800×600，而合成器最大化尺寸被用于离屏FBO和投影。采用官方2023.01源码固定SHA的归档及15个签名Alpine包，只在手机/tmp提取SDK，不安装/升级软件包。相同公共对象编译出两个完整Wayland/GLES后端程序，共用原APK资产，horse模型逐字节一致；两版均加相同只读FBO诊断，只改变离屏验证时的width/height选择，不改阈值、模型、着色器、参考像素或驱动，不指定软件渲染/全局Mesa调试。

实机对照结果：

| 项目 | 原版尺寸对照 | 修正版尺寸对照 |
|---|---|---|
| 原生Wayland窗口 | 1080×2259 | 1080×2259 |
| 查询到的实际FBO与Canvas | 1080×2259 | 800×600 |
| 同一build场景像素验证 | Failure，RGB各差2 | Success，原阈值保持 |
| 退出码 | 0 | 0 |
| 随后30秒CCU READ TRANSLATION事件 | 0 | **2**，退出后1.993秒及2.737秒，两个不同IOVA |
| 桌面PID/taint | 保持/0 | 保持/0 |

因此该场景的像素误判与FBO尺寸关系已经实测证明，但GPU驱动故障未修复，GPU整体验收失败。停止后续GPU负载，没有重跑旧33场景、重放、GPU复位、桌面重启或刷内核。修正版成功日志不输出精确成功像素值，未编造其RGBA值；此结果也不能推断旧25项都通过。

新364,548字节devcoredump已私有保存；对照归档59个成员及构建归档21个成员逐项SHA通过，package-db/NV6/source4/vendor1检查通过。复用已验证Mesa26.2.4 crashdec离线解码成功：7 BO、fault不在所列BO、TTBR匹配、1个零页表项、无VM历史；估计命令停点在CP_SMMU_TABLE_UPDATE/CP_MEM_WRITE与CP_EVENT_WRITE/CP_WAIT_REG_MEM之间。估计停点及不完整BO列表不能证明释放后访问或根因。E118解码卷已卸载。

首次WSL下载索引SSL EOF及PowerShell并行下载EOF保留；curl重试与索引大小检查后SDK通过设备apk verify。首次构建在源码空行匹配断言失败，第二次链接缺少transitive库搜索，分别修正匹配与rpath-link；复用已编译且源码与固定上游归档逐字节一致的67个公共对象，原失败日志保留。readelf只使用SDK自己的动态库路径；GPU测试进程无该环境与RPATH/RUNPATH。首版验证器误按单个fault事件断言失败，检查完整时间线后改为两条翻译事件及一条ring诊断，未删日志。

长期GPU故障已留档，下一项转充电观测。新核对当前#129源码、配置与对象：此前#87的3次ADC重试/ENODATA修正已经包含，驱动仍仅get_property且无配置写/充电控制；下一实际步骤是本机QUP1/0x5c受守卫的临时绑定和标准power_supply事件验证，不能直接宣称充电管理可用。最新完整镜像仍rootfs130，稳定115/118/126/128/129回退保持。

充电实际追加：首次SCP复制的Windows二进制无执行位，在任何临时绑定前PermissionError失败，原目录保留；固定SHA通过后仅给工具执行权限，新r2目录测试。当前129已有正确驱动，8次标准uevent均非空且ONLINE=1/STATUS=Full，5次电压4.550–4.650V、4次电流162.500–256.250mA，另3/4次属性读ENODATA且未使整份事件丢失。11个配置寄存器前后保持、busy所有权拒绝/属性0444、包数据库保持、无新增GPU故障，临时客户端已移除。16成员SHA验证通过；输入ADC数值仍无外部校准，不是充电控制/快充或持久绑定验收。下一项推进只读观测持久DT接入，保持保护链/预算与控制待办。
