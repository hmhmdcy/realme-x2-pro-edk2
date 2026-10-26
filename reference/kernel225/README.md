# 225：标准曝光与增益控制已部署

2026-10-16，手机为完整libcamera 99990.7.2-r13/config 0.1.0-r8；boot219/Image183、IMX471 e49、CAMSS fae1保持。本轮没有刷写或重启，全外设goal继续active。[安装](r13-package-install-validation.json)、[最终健康](final-health-validation.json)、[部署锁](../../linux-port/camera/deployment-lock.json)。

0018为CPU软件ISP路径加入曝光/增益独立Auto/Manual、AeEnable兼容优先级、自动期间忽略且不保留手动值、切换冻结/恢复、Camera::start初始控制，以及按捕获SOF延迟历史取得的实际模式/数值元数据。启动控制在stream-on前写入；模式来源cookie与控制值一起经过DelayedControls，元数据不回显当前请求。[0018](libcamera-manual-exposure-controls.patch)、[探针](manual-control-probe.cpp)。固定0.7.2已有Camera核心AeEnable预处理，本轮保持该源码。

首个完整构建发现生成的线程代理非void start遗漏输出参数，41314失败并恢复原树；0019只补生成器输出转发，随后10686完成r12/r7全部13包。独立算法测试又复现无效统计把较老捕获控制重新排回的问题，r12未部署；0020改为保持最新准备目标，同一测试源码在r13通过48项断言。[构建失败](first-build-generator-failure-validation.json)、[0019](libcamera-threaded-start-outputs.patch)、[r12行为失败](agc-preflight-validation.json)、[0020](libcamera-invalid-statistics-hold.patch)、[r13算法回归](r13-agc-control-regression-validation.json)。独立测试首两次编译缺私有include目录，原诊断私人保留，按实际构建包含目录补齐后才取得行为结果。

r13/r8完整官方abuild构建成功，保留原17补丁、全部管线/11框架子包/tuning，现共20补丁。13包、34个ARM64 ELF、5IPA签名及Qt/Python入口通过；原214树2254文件/链接/模式恢复，r12和r13对象树独立保留。[构建](r13-package-build-validation.json)、[产物](r13-forward-package-artifact-validation.json)、[主机QA](r13-host-runtime-qa-validation.json)、[源码顺序重放](candidate-final-source-validation.json)。IPA214/APK203原外部私钥复用，未公开；二次逐字重建未验证。

候选RAW/RGB 2M/4M×普通/隔离IPA八例共1024帧通过九阶段控制测试；覆盖启动前控制、独立模式、优先级、忽略、冻结、恢复、停止再启动默认自动。147帧的捕获来源与当前请求阶段不同，元数据仍与捕获历史一致；来源标签经SOF间隙和环形历史回绕后正确。[1024帧矩阵](r13-candidate-manual-matrix-validation.json)。这是控制关联验证，不是光学2/1帧延迟标定。

签名七包原生升级后，944包中937无关记录及49相机payload/模式/链接核对通过，空闲WP重载且桌面/PipeWire身份保持。实际系统默认环境再测RAW2M/RGB4M共256帧，九阶段控制与来源元数据通过；其中35帧模式来源不同于新请求，仍正确。[RAW128](r13-system-raw-1928x1088-threaded-manual-validation.json)、[RGB128](r13-system-rgb-2296x1728-threaded-manual-validation.json)、[重载](wireplumber-reload-validation.json)。安装记录中的pending字段是安装瞬间历史，由这些后续验收解决。

相同生命周期探针在候选普通、候选隔离和安装后各40请求通过，每次同一Camera对象五次RAW/RGB重配、20完成且有元数据/20取消，没有挂起或重复取消。[安装后生命周期](lifecycle-r13-system-threaded-validation.json)。安装后实验4608×3456 RAW/RGB各36帧、cam/GStreamer各6帧通过。完整模式控制器已终态，参数N/WP恢复；16MP不是九阶段手动矩阵的覆盖范围。[完整RAW](raw-exposure-metadata-system-r13-4608x3456-validation.json)、[完整RGB](exposure-metadata-system-r13-4608x3456-validation.json)、[普通客户端](standard-gstreamer-validation.json)、[关闭实验](full-finish-validation.json)。

当前r13→r11/config-r6回退使用设备k224-r11-package-candidates/forward的实际七包及225事务保存的world/repo/配置，保留fae1/e49模块。原生降级模拟通过，完整往返未执行；r11→r8/r3属于224历史回退，不能混用。canonical配方、配置和部署锁已提升r13/r8，内核源锁仍223。

房间关灯条件保持，没有闪光、外部照明或保存场景。223暗光RAM数值统计仍是最近像素证据：RAW有效值62–133/std约2.66，有帧间变化；RAW/RGB各6帧均非全零。225客户端只检查控制/元数据/流程，CPU ISP内部仍读取RAW统计，不能由此宣称新亮光画质已验收。[历史暗光](../kernel223/dark-frame-classification-validation.json)。

最终相机/CCI/CAMSS休眠、两前摄电源关/用户0、图案0/参数N；GPS关闭/watch空闲、chrony Normal、三DSP running、BT关且无连接、taint与五类fault0、NV源保持。Modem仍State−1/原因2/Power1，UIM absent/no-atr是221历史查询。[191成员私人归档核对](final-evidence-validation.json)。r12主机构建和算法失败日志另在私人225目录，不声称位于手机归档。

前摄本阶段控制链已收尾，后续优先后置四摄、GNSS与蜂窝主要阻塞，并验证宿主musl交叉构建加速。真实CFA/几何/颜色/方向/光学延迟/标定、GUI/实时性能及GPU ISP仍开放；实验TPG普通Bayer不能证明真实Quad颜色。[上游依据](UPSTREAM-NOTES.md)、[加速安排](ACCELERATION-PLAN.md)、[全外设清单](../../linux-port/docs/HARDWARE-STATUS.md)。
