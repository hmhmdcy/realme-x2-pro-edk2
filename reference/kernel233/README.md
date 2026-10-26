# 233：后摄 PM8008 依赖已部署并完成原生暖/冷循环

232候选已在新启动233实际部署。仅刷boot，启动分区读回匹配 `45f398f2…`；Image183、logdump183、persist/NV保持。新MFD `f633467f…` 与reset provider `2223f337…` 的实际加载note匹配磁盘文件、intree=Y，实验参数在加载前生效。[新启动验收](runtime-validation.json)、[最终健康](final-health-validation.json)

**P、Q、provider均已绑定，P的0x0100身份通过，P没有secondary dummy、MFD或regulator子设备。后置四摄仍未出图。** 这是后摄共同复位/地址阻塞的实际进展，未知VIN没有填入；实验P保持身份阶段，不把供电/摄像头功能写作完成。

安装前新鲜身份、旧MFD加载note及原磁盘文件核对一致，保存旧模块和14项元数据。options/softdep先安装，两个ko随后原子替换、depmod，再用现场kmod的query-only模式确认provider→带参数MFD顺序；旧195 MFD始终保留运行到重启。暂存异常路径已改为独立临时文件、状态日志失败不阻挡恢复，并执行三种实际I/O函数故障测试。[暂存](module-stage-validation.json)、[I/O故障](atomic-recovery-validation.json)

清理保留旧Q/MFD/regulator，仅释放前摄端点；显示、音频、三DSP及网络正常清理，taint0。只执行一次Linux→bootloader，一次新鲜fastboot身份/几何核验后刷boot，一次reboot。最终console回执未收到，未重发；由fresh fastboot及新Linux身份闭合。USB刚启动时没有Up接口，等待接口实际出现后重新发现邻居，严格原公钥连接；未重启或重刷补救观察等待。[清理](quiesce-validation.json)、[刷写](flash-validation.json)

原生逐设备测试均通过：[循环与GPIO跟踪](pmic-cycles-validation.json)。

- Q单设备unbind自动先拆P，provider保持绑定；Q重绑后P自动重新探测身份。七路Q输出的关闭状态、用户0和电压逐项保持，没有冷迁址日志。
- provider设备unbind自动拆P/Q；跟踪输出为P0、P0、Q0。重绑时为P0、Q0、Q1、P0、P1，完成一次Q地址8→4迁移后才释放P。GPIO事件是软件操作跟踪，不能称管脚电压物理读回。
- 不用rmmod代替managed设备解绑。P无children按父设备归属核对。前摄sensor和WirePlumber已恢复，桌面/PipeWire身份保持，无恢复性补绑、无taint或五类故障增量，跟踪实例已删除。

冷循环后前摄系统r13/r8再次取得RAW/RGB各6帧，均非全零；所有图/格式/控制及runtime PM恢复，未保存场景照片、未加照明。RAW均值117.739–120.819，RGB均值26.6843–70.8944；不据此宣称AE收敛或颜色准确，纯色参照测试按用户延期。[RAW](raw-front-regression-validation.json)、[RGB](rgb-front-regression-validation.json)

最终taint0、五类fault0、三个DSP running、SensorProxy三Has真；自动真实readiness为加速度69条/光线10条。773ko/787相关文件、944包、相机e49/fae1及r13/r8、FastRPC2abde保持。Q七路全部关闭/用户0，GPS0/Signalsfalse/rate30、无新辅助注入，BT关闭/无连接，用户无SIM。

接受的实验源码与部署锁在[PMIC源码目录](../../linux-port/camera/pmic/README.md)；canonical after228仍保留，完整供电绑定、后摄sensor驱动/模式、GNSS正CNR、BT phase5及其余外设仍开放。完整goal active。
