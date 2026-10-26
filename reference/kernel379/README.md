# 379：两路 IPE CONFIG_IO 控制链路实机通过

RT(type2) 与非 RT(type3) 两个独立 IPE 会话各完成 MAP → CONFIG_IO → UNMAP，再依次销毁；INIT/PING/PC、WFI、正常停机、DMA/PM 释放与模块卸载全部通过。两个会话实际返回 scratch 各 48 字节；13 messages、14 IRQ、watchdog/protocol error 均 0，CMD 读写 120 words、MSG 读写 133 words，与每个命令/回复的实际长度精确吻合。见 [运行审计](io-runtime-validation.json) 和 [事务终态](boot-runtime-validation.json)。本轮没有重启，候选未永久安装，图像帧提交数仍为 0。

## 原厂依据与修复

继承 [377](../kernel377/README.md) 从固定仓库和本机原厂 HAL/固件还原的 1216 字节 IO 配置、84 字节 image descriptor、NV12/NV21 与端口 0/8/9 布局，以及 [378](../kernel378/README.md) 移出 debug 映射的 `0x07600000` 配置槽。

本轮仅修正 SoC 核心 ACK 解析：MAP/UNMAP 检查已定义的 header 状态，忽略未初始化的 12 字节尾部；CONFIG_IO、DESTROY 仍检查各自有效 payload 状态。长度、双 64 位 token、opcode、IRQ 错误锁存、超时与所有权规则保留。此前失败和自动重启如实保留，未改写为成功。

原厂 async dispatch、callback 分配/释放与 IO callback 在 Unicorn 执行；分配器改为返回非零字节，MAP/UNMAP 尾部确实保留原内容。VMM、流队列、OS/cache/log/postMessage 仍是桩，不冒充真实引擎处理。旧 parser 对同一 dirty-tail 场景失败，新 parser 通过。40 个实际函数体会话场景、25 个 owner 场景及分发/清理检查通过，相关 C 模型启用 ASAN/UBSAN。见 [固件模型](firmware-io-validation.json)、[反例](negative-control-validation.json)、[函数体模型](session-validation.json)。

维护源 `/mnt/samurai-full282/source354`，分支 `samurai-a5-ack-status379`，提交 `6b8e3b1a28ff9ea60391045b03b746499d1d9400`。core/test 以实际 k363 内核配置进行 in-tree W=1/-Werror 构建，无诊断，见 [构建](intree-build-validation.json)。实际 Image363、boot366/DT365、libcamera r29 与 config/stack r24 保持。板级 DT、主线媒体框架、传感器驱动和用户空间本轮均未改。

## 四摄和设备状态

在 378 恢复后的同一启动重新采集：IMX471、IMX319、S5K3M5、S5KGW1 各 12 帧 640×480；主摄隔离 IPA 27 帧、5 个控制阶段和 Gamma ACK 均通过。无新增相机故障、taint0，CAMSS/双 CCI 休眠，9 相机电源 disabled/users0。见 [四摄回归](camera-runtime-validation.json)。

恢复启动出现既有 SSC FastRPC attach 失败（daemon exit4、SLPI 已清理到 offline），不是健康状态。故障上下文已私存，未盲目重试 DSP；临时 nodeps 启动恢复桌面，依赖配置未改，PW/WP/phoc/phosh 各一进程。SensorProxy 未运行，自动旋转不可用，根因仍待。见 [SSC 状态](ssc-failure-validation.json)、[桌面恢复](desktop-restore-validation.json)。

[收尾检查](final-state-validation.json) 的 passed 仅代表本轮 camera/ICP 检查完成：17 个 ICP/BPS/IPE 时钟 enable0、临时模块/DT/固件和 worker 均无残留，静态 ICP disabled；`whole_platform_healthy=false` 单独记录 SSC 降级。没有写 NV/OTP/工厂校准，没有刷写或主机主动重启。

## 后续范围

下一步仍是数据面：从既有原厂 HAL/固件和 GPL 管理器取得 frame/IQ/CDM/striping 所需布局，核对 A5 与 IPE 引擎的独立 SMMU SID、DMA 可见性、缓冲区寿命和 frame completion，再接 libcamera m2m 与实际 Gamma/LTM/CCM。配置接受不证明图像处理、输出画质或多摄同步。第五 2MP 身份、更多模式、动态帧时长/自动防频闪、光学/几何校准与连续 AF 仍未完成，见 [剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。目标继续 active。

原厂 ELF、HAL、完整日志、回包、异常现场与个体校准只在 `E:/edk2-samurai-out`，公共 Git 仅放自写代码、补丁、来源与脱敏结论。访问 ext4 源码前仍需调用 `kernel284/storage.py::mounted_build()`。
