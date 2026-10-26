# 325：GW1标准测试图案与主摄两模式LSC

2026-10-20。已部署只修改GW1传感器驱动的标准TEST_PATTERN控制，主摄4608×3456及4608×2592的工厂LSC均经已安装r26 IPA→318 ISP→NV12实际验证。其它内核模块、Image、DT及软件包保持。现在四摄均有工厂LSC配置的实际链路证据，其中广角还验证过真实个体补偿；默认调校仍未启用这些实验表。完整光学/个体/多摄校准目标active。

实现依据324固定的[真我官方GW1源](https://github.com/realme-kernel-opensource/realme6-kernel-source/blob/0933e0e5b2fd30faa7857f5024a86f3759713374/drivers/misc/mediatek/imgsensor/src/common/v1_1/s5kgw1_mipi_raw/s5kgw1mipiraw_Sensor.c#L16376)：16-bit寄存器0x0600中，0关闭、2彩条，注释明确3为Shade Color Bar。新V4L2菜单为0 Disabled、1 Color Bars、2 Shade Color Bars，映射0/2/3；未变更彩条最初已验证的菜单索引。控制复用原有runtime PM缓存、group hold错误释放与启动时handler setup。没有私有ioctl、板级调校属性或用户空间寄存器写入。[补丁](s5kgw1-test-pattern.patch)、[源记录](kernel-source-validation.json)。

变更在独立树/home/cy122/x2pro-linux/camera325-gw1-tpg-kernel，分支samurai-gw1-tpg325，提交4318dd1c2f7b8971b267cc50d9129e86e99bccdb；以318提交为父，仅一个驱动文件18行新增/1行修改。W=1/Werror模块与CCI依赖构建通过，intree/ABI/导入符号匹配，checkpatch零error/warning/check。共享输出中的所列模块/依赖及配置/生成元数据已恢复；不是新的完整Image构建，也不是上游接收记录。[构建](kernel-build-validation.json)、[提交](source-commit-validation.json)、[格式](style-validation.json)。

R1直接rmmod被媒体引用拒绝，原模块与服务恢复，未装入候选。R2改为先正常解绑GW1再卸载/换模块，不卸共享CAMSS/CCI/镜头驱动。Color Bars两模式off/Qtech/Sunny六项均稳定取流，正常系统GStreamer与PipeWire也通过；但该图案通道已经饱和，三份LSC图像分别逐字相同，不能用于证明增益效果。[R1](install-r1-validation.json)、[R2](install-r2-validation.json)、[饱和彩条](main-color-bars-image-validation.json)。

因此按同一厂商源明确的3值补Shade模式，复用未改采集二进制，在R3更换最终模块。六项均按图像实际稳定条件得到3帧，标准ACTIVE格式读回确认两种传感器模式；同时验证启动前缓存控制与流中0→2菜单切换均成功，媒体/控制恢复。两套主摄文件分别作为显式诊断配置，不声称已经绑定本机供应商，也不当作当前场景lux/CCT。[R3](install-r3-validation.json)。

Shade图中四份factory均明显区别于LSC关闭。独立网格重采样与近似RGB模型，对基准图像梯度确定的彩条内部区域进行比较，p99误差1.669～1.783/255，最大3.242～3.402/255，平均0.452～0.479/255。剔除的跳变行来自未校正基准；保留完整私人图像，不按校正结果挑选区域。模型从NV12反推线性RGB，近似Bayer重建和硬件空间插值，不能作为RAW光学精度或正常照明校准。[图像分析](main-image-validation.json)。

最终模块SHA61c81f47bd29925f95ef6ad146e8f3231b3b01b3f64f458a09680eb450d2a167，loaded-note SHA b80626da86f24d4eaf53ca78e3baa6462cf204adfc257de859bf418f0e9fbd57。默认系统GStreamer主摄640×480及PipeWire各12帧通过，四摄/四PW节点枚举，测试图案最终为0关闭。CAMSS/两CCI休眠、全部相机rails关闭用户0，相关故障增量0、taint0，PW/WP各一且uid10000；所有worker终态。[最终状态](final-state-validation.json)。

原9f1a…模块在/var/lib/samurai/k325-install-r2/s5kgw1-before.ko；中间Color Bars版本在k325-install-r3/s5kgw1-before.ko。每个目录保留对应proof/日志与回退文件，旧安装脚本前置已不满足，不重放。未刷写/重启或写EEPROM/OTP/NV/persist；默认libcamera r26/config-r21及318 CAMSS保持，实验工厂表只在私有运行配置中。

后续直接继续主/前/长焦个体读取、布局、绑定和动态AEC/CCT触发。324已核出EEPROM前缀，正常V4L2持有供电下可只读推进。正常光线下阴影/颜色/黑电平、畸变/多摄几何同步、真实曝光时间与连续AF仍未完成；暗室不阻塞源码、原厂数据与内部图案工作。
