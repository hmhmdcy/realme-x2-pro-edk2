# 237：IMX319 首批真实 RAW 与 CAMSS 失败回收修正

2026-10-16。沿用236启动、235 boot，未重启或刷分区。**IMX319已取得6帧1632×1224 RAW10**，前摄4MP RAW及CPU RGB各6帧回归通过；均只在RAM统计，不保存或显示场景、不闪光、不新增照明。后摄数据接近黑电平，曝光/光学响应、RGB、颜色及其它后摄仍未完成，完整适配goal active。

## 实际修正与源码

- 以实际fae1组合源码为基线，借鉴[Hotdog0114固定补丁](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0114-media-qcom-camss-unwind-failed-stream-starts.patch)，适配本机Linux7.3的prepare/unprepare与pipeline_alloc_start，避免复制旧PM配对。[本机补丁](camss-stream-unwind.patch)、[源锁](camss-source-validation.json)
- 启动某上游失败时，停止此前成功启动的下游实体，保留原错误；正常停止即使某实体报错也继续清理并执行pipeline_stop/flush。停止失败仍写内核错误，不能把尽力回收称为所有硬件故障已闭环。
- VFE先清除活动指针，pending先摘链，再只交还ACTIVE缓冲；活动/last/pending别名只返回一次。只对VFE170清gen2计数，避免覆盖gen1共享union。SOF配对、时钟/IRQ掩码、板级资源不改。
- 实际函数在ASan/UBSan下完成375个图启停与8192个buffer状态案例，四个负对照被检出。这是函数故障模型，不是IRQ/并发或硬件故障注入验收。[测试](camss-function-tests-validation.json)
- 树内W=1零诊断、intreeY/183 ABI/所有导入符号通过；canonical after228逐项恢复。新模块`ff9fdfa346249d836…`/777680B。[构建](camss-build-validation.json)

## 原生部署与物理取流

1. 新鲜236 guard、默认/加载note、两sensor OF、PM/无客户端核对通过。[基线](baseline-validation.json)
2. CAMSS ref0且五个相机设备suspended时只卸换空闲CAMSS一次；两sensor、MFD/P/Q/provider保持。备份旧fae1及模块元数据后原子替换，实际默认/加载note匹配，rails与双摄图保持。789相关文件仅该ko摘要改变。[部署](camss-install-validation.json)
3. 旧219/233探针硬编码前摄CCI1，不能验后摄。新探针要求完整OF Camera ID、Model、subdev entity及对应sysfs OF一致；只处理一个预期stream/plane、FrameSuccess和递增序号/时间戳。DMA_BUF同步、RAW10有效像素统计、显式pattern恢复/stop/release及回调异常处理均保留。[探针源码](native-physical-probe.cpp)、[构建](physical-probe-build-validation.json)
4. 首次wrapper在捕获进程启动前因写错`experimental_full_resolution`参数名失败，实际参数是`unprocessed_fullres`；原worker/失败保持。修正后第一次r2 launcher又因复用r1的xb日志路径退出，已核不存在r2 context/进程，再修正唯一日志名；未重复任何不明状态的捕获。[r1](rear-raw-capture-validation.json)、[启动核对](r2-launch-validation.json)
5. r2后摄、前摄RAW、前摄RGB各只启动一个有界worker，全部六帧、程序exit0；全图/所有subdev格式、两sensor控制、CSID图案、P/Q rails、五设备PM和MCLK均恢复。finally逐步捕获恢复错误，失败不会跳过后续步骤。[后摄](rear-raw-capture-r2-validation.json)、[前摄RAW](front-raw-capture-r2-validation.json)、[前摄RGB](front-rgb-capture-r2-validation.json)

后摄stride2048，每行2040有效RAW10字节、8填充字节不参与统计，序号0–5连续。完成时间间隔32.621–33.445ms，六帧窗口约30.15fps；这是完成节奏，不是物理MCLK/曝光起点标定。样本范围62–78、均值64.2454–64.2656，后续帧约32.36–32.59%像素值变化，**不是全零缓冲，但接近64黑电平**。没有据此宣称白天场景、光学/曝光响应或颜色可用。[数值分析](capture-analysis.json)

## 最终状态与回退

[最终检查](final-health-validation.json)：默认与加载的8模块note匹配；775ko/789相关文件、用户态/包/config及分区保持；两sensor、CCI0/1、CAMSS suspended，前后四rails OFF/users0，MCLK1/2关。三DSP running、SensorProxy三Has、Wi-Fi/chrony正常，taint和WARN/Oops/GPU/DSP fatal/BT重组0。蓝牙开启且1连接只观察，本轮未发起pair/connect/disconnect。GNSS空闲，未新增搜星/注入，无正CNR或fix；无SIM业务待验。

**当前权威模块清单改为设备`k237-camss-install/module-inventory-after-private.json`**，236清单中的CAMSS摘要已过时。boot235及MFD6021/lab5198/provider2223/imx319176f/前摄e49/FastRPC2abd保持；canonical仍after228，不能刷其旧相机输出。linux-port供电/相机完整profile和kernel/rootfs整合仍开放。

CAMSS回退精确文件与元数据在设备`k237-camss-install/before`；宿主私人237归档含原模块备份并保留候选，fae1完整冻结源在私人223。需重新核当前身份、无客户端和ref0/PM后再恢复文件/元数据及受控模块切换；本轮脚本只执行一次，不直接重放。235/236的PMIC、boot及更早回退继续保留；当前lab已绑定有消费者，不能重放236未绑定/ref0卸换。未写NV/校准/工厂备份。

## 下一步

只读审查确认实际r13缺IMX319 gain helper，寄存器码被当倍率；原厂3332行曝光还会被驱动默认1270行覆盖。这些是已证控制差异，尚不能单独解释近黑。先补最小gain helper，再验显式曝光/增益的RAW响应及元数据、CPU RGB；不需要用户准备纯色物体。[控制核对](CAMERA-CONTROL-FOLLOWUP.md)

继续本机OEM19.2MHz的S5K3M5 profile和其余后摄，前摄纯色准确度按用户延期。GNSS下一项应离线审本机匹配vendor二进制/rc/配置及依赖，已有[同平台资料](../kernel236/RELATED-LINUX-SOLUTIONS.md)不足以形成新的RF SET方案，不重复已覆盖的同CID/辅助数据矩阵。
