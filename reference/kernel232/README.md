# 232：后摄 PM8008 复位和依赖候选已构建

按用户要求搁置前摄纯色参照测试，转向后摄共同阻塞。新增独立 P/Q reset provider，并给 PM8008 MFD 增加独占 reset backend、持久 supplier link、解绑状态检查和 P 身份探测。原 GPIO ASIS 与195地址迁移失败回收保持。未知 VIN 没有填写，P实验模式不创建任何MFD子设备。[源代码](qcom-pm8008.c)、[复位控制器](reset-realme-rmx1931-pm8008.c)、[契约及边界](RESET-CONTRACT.md)

两个真实树内模块已完成匹配7.3.0-rc6 ABI的 W=1 编译，零诊断、导入符号均存在、intree=Y。主机执行实际候选函数：双backend地址路径60例、supplier状态8例、GPIO缓存失败/顺序14例、P清理10例、probe入口边界5例，共97例，ASan/UBSan通过；删除解绑、状态有效性、child门控的三个负对照均失败。[构建](module-build-validation.json)、[故障测试](host-tests-validation.json)

设备树从实际部署219源生成，保守版保持P disabled，实验版仅启用P身份阶段；相对当前DTB只有旧hog移除、新provider/P节点、Q的reset引用及必要phandle变化。625个显式引用经过检查，未改相机、传感器或其它供电参数。[设备树核查](board-build-validation.json)

实验启动镜像已打包为私人232的 `boot-partition-k232-pmic-identity.img`，96MiB。完整解包核对固件代码不变、仅内嵌DTB改变，Image183/logdump183、头部、兼容DTB、ramdisk和尾部保持；构建后的源码及原有生成产物已恢复。[镜像核查](build-package-validation.json)

**当前没有安装候选模块、没有刷写或重启，后摄仍未出图。** 最新实机检查仍为boot230、taint0、五类故障0、三个DSP running、SensorProxy三Has真，旧Q已绑定、前摄休眠/双轨关闭，GPS关闭、BT关闭，用户无SIM。[新鲜实机检查](preflight-validation.json)

下一步先以新鲜设备身份暂存模块和加载前实验参数，保留现有MFD与boot219回退，再受控切换并验收P身份、Q/前摄和依赖清理。97例主机检查不代表硬件供电、Linux原生解绑或后摄功能已经通过。完整外设goal继续active。
