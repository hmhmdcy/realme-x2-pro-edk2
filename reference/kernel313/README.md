# 313：硬件处理流复用单次自动对焦

2026-10-19。主摄硬件NV12候选路径已接入标准Auto AF触发、粗扫／细扫／峰值复核和取消。真实场景扫描224帧，23次镜头命令均成功，最终在DAC256复核后报告Focused；最终取消／退出另44帧通过。产品接入、RAW兼容和完整校准仍未完成，目标active。

## 复用及分层

复用r24已有`ipa::ContrastAf`，来源[0028](../../linux-port/packages/libcamera/0028-simple-contrast-autofocus.patch)，沿用主摄`lc898219xi`配置和DAC208～926范围。复用CameraSensor／CameraLens发现及标准驱动控制，不增加板级镜头地址或寄存器硬编码。镜头在采集期间打开，结束后关闭。

硬件NV12图像完成后，从CPU同步的Y平面提取有界320×240对比度网格，沿用FocusStatistics分区／归一化评分；不对处理后Y图套RAW Bayer采样。扫描时暂停AE／AWB新提议，使用CLOCK_MONOTONIC采集时间、镜头命令完成确认、100ms稳定时间及帧长＋曝光保护，排除镜头运动前或曝光跨越运动的样本。图像仍由VFE处理；对焦评分是CPU算法，**没有接入VFE BAF或PDAF**。

通过AfModeAuto／AfTrigger／AfState及FocusFoM公开，只有触发后扫描，取消返回Idle；未暴露Continuous或未校准的LensPosition距离映射。[标准控制语义](https://docs.libcamera.org/master/internal-api/namespacelibcamera_1_1controls.html)。本轮只改通用pipeline／IPA和主摄调校目录，SoC、DT、板级供电、内核和传感器源码未改。[补丁](hardware-af.patch)、[当前源码](source-state.json)。

## 修复和实测

首次r1、诊断r2在开流前0帧失败：重新配置会重置隔离IPA序列化缓存，init时保存的V4L2 ControlInfoMap引用了缓存中的ControlId，之后焦距控制查询失效。改为只保存独立的焦距范围值；pipeline初始化时读取当前镜头控制，不跨重新打开缓存其ID映射。两次失败原样保留：[r1](af-scan-r1-validation.json)、[r2](af-scan-r2-validation.json)。未通过调宽光学阈值绕过。

实际AArch64 IPA DSO检查加入init后清空动态镜头ID映射的回归断言，明确要求AF能力存在，覆盖触发、取消、镜头写入失败上报及扫描期间抑制3A提议；v1和v2既有检查通过。[IPA检查](ipa-contract-validation.json)、[相关Werror构建](build-validation.json)。此前直接DSO测试未模拟代理缓存重置，未发现该生命周期问题。

[r3扫描](af-scan-r3-validation.json)：主摄4608×3456输入、640×480 NV12输出，224帧均含有效AF／曝光／增益／WB元数据，零帧错误。9个粗扫点、13个细扫点及回到峰值的1次复核，全部23次镜头写入返回0；每点三个合格评分。细扫DAC256中值17548，最终复核17562，最终状态Focused。扫描期间曝光33197µs、增益3.09375、量化WB约1.88235／1.66176保持一致。仅证明该场景及输出上的对比度收敛，未代替正式清晰度、重复性或距离标定。

[r1取消](af-cancel-r1-validation.json)：43帧，实际进入Scanning、发出一次镜头移动后接受Cancel并返回Idle，无元数据错误。采集fixture恢复包括镜头DAC在内的20项控制及媒体格式／选择；不把取消后Idle当成Focused。

收尾审查补充停止保护：running=false后，剩余图像回收不再处理AF或发送镜头命令。仅此退出条件改变，光学算法及运行中分支保持；r3扫描证据按范围复用。最终第6次相关构建通过，[r2取消／退出](af-cancel-r2-validation.json)44帧通过，所有控制元数据有效且资源释放。普通SSH查询也不再逐条比较启动ID，采集worker只在实验开始检查一次兼容状态。

全部实验进程已终态；桌面PW/WP保持，CAMSS与两CCI休眠，九路相机供电关闭、用户0，相关故障增量0、taint0。[资源收尾](final-health-validation.json)。全机已有GPU／modem／SSC问题仍开放。

## 当前使用及后续

设备仍为298 Image＋305长焦模块＋309 CAMSS，同一USB启动。产品libcamera r24／config-r19仍RAW＋CPU ISP；候选仅独立目录运行，未安装系统包、刷写或重启。312六模式默认AE/AWB与缓冲恢复证据按范围沿用：[312](../kernel312/README.md)，没有重跑未变更组件。

SDK同名`libcamera299-inline`现在是313源码，使用本目录`build-candidate.py`；旧312／311／308／303构建脚本会覆盖当前接口。现有源码／四个YAML为权威输入，prepare脚本只保留生成过程。新库、IPA及代理匹配使用；`build-runtime.py`编译应用，`pack-runtime.py af`打包。不要重放已提交的af-scan r1～r3和af-cancel r1～r2。

下一步完善硬件handler的RAW兼容，再做产品包／消费者接入；当前单NV12候选不能直接代替产品已有能力。主摄其它模式／输出上的AF、连续AF和距离图未验。正式黑电平、颜色／CCM、阴影和模组绑定继续；304 EEPROM完整校验／绑定／几何未齐，未应用个体值。用户延期纯色／遮光保持，不阻塞其它工作。
