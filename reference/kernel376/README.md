# 376：两个IPE固件会话并存、创建与销毁实机通过

**原厂A5固件已实机创建两个不同的IPE RT/非RT会话，同时持有后分别销毁。** 两次create、两次destroy、INIT/PING/PC/WFI及完整DMA/PM释放、模块/overlay卸载均通过；同一启动、相关故障0、taint0。尚未配置图像IO或提交帧，`image_frames=0`，不能据此宣称图像处理或多摄同步完成。[实机结果](boot-runtime-r1-validation.json)、[日志/队列核对](session-runtime-validation.json)。

## 优先复用与原厂接口核对

复用352保存的[CAMSS维护者原型固定提交](https://kernel.googlesource.com/pub/scm/linux/kernel/git/bod/linux/+/ebd1e440443121d18f730ab2aeea5586a754f36f)，对照Realme GPL固定`9668fcdc...`的HFI头文件和355保存的ICP管理器。再次检索未取得可直接替代目标A5会话的实现；这一结论只限检索与该固定原型，不代表其它仓库不存在实现。原型的async结构还多出一个字段，不能直接用于本机。[原有复用评估](../kernel352/icp-reuse-assessment.json)、[原厂来源](../kernel352/oem-icp-sources.json)。公开Android源码中也保留了[同系列ICP接口与管理器](https://android.googlesource.com/kernel/msm/+/eacb4d075bc59acd305b6843112a94229962851e%5E1..eacb4d075bc59acd305b6843112a94229962851e/)，未把旧平台差异混入本机。

原厂ELF保留符号，执行完整原始create handler，以及destroy实际调用片段、CreateCallbackData、OnDone_IpeDestroy和ReleaseCallbackData，OS/流分配/日志/缓存/postMessage为桩。确认create命令28字节/ACK32字节，destroy命令44字节/**实际ACK48字节**；两种回包均保留两个64位token。销毁payload实际16字节，与头文件packed12字节声明不同，payload也不保证回显提交的token。原始汇编/数据包仅私存。[原始指令验证](firmware-session-validation.json)。

## 分层实现与验证

仅修改SoC A5核心、公开接口和临时诊断owner：[补丁](ipe-session.patch)。支持多个调用者持有独立会话对象，命令仍由生命周期mutex串行。唯一递增token绑定每次命令，不发送内核指针；严格核对类型/长度/两个token、销毁opcode和返回状态。销毁ACK没有handle字段，handle归属通过本次命令token关联，不能伪称回包含有handle。

排队后超时或不可识别回包会阻止继续创建会话；明确拒绝的销毁保留handle供重试。stop先销毁已知会话；无法确定状态则走强制复位，复位失败保留CPU/会话/DMA/PM所有权。正常停止保留375的协作式路径。IRQ解析完成后才复用待应答状态；补充修正成功ACK覆盖同批watchdog错误、IRQ join期间错误遗漏的竞态，旧函数体两个反例均失败，新代码通过。

实际生产parser/send/session/quiesce/stop和头文件27条模型、owner23条路径，以及worker分发/清理模型通过ASAN/UBSAN或相应Python检查；包括两个并存会话、错误token高位、迟到消息、错误opcode、错误44字节销毁回包、超时、重复handle及清理失败。提供者为桩，实机另验。两模块实际k363 in-tree W=1/-Werror最终构建无诊断。[核心模型](session-validation.json)、[owner](owner-validation.json)、[构建](intree-build-validation.json)。

维护分支`samurai-a5-ipe-session376`，最终提交`b6c779010ec222c6f70a4912e3d3205fd6414b5c`；初始`2630955b...`，父375 `94a92da1...`。仅最终r2模块用于一次实机实验，未永久安装。保留373 reset/wake之后HFI参数编程与读回；板级DT、主线OF/IOMMU/设备链接、传感器和正式libcamera/校准均未改。

实机7条消息/8IRQ/1debug、watchdog/protocol0；命令队列读写44word、消息61word，和INIT56字节、PING、两组create/destroy及PC应答的实际ABI长度精确一致。两会话peak2、最终0，CPU/IRQ/PM/映射/时钟组/域均归零；17时钟enable0，模块/节点/临时固件无残留。没有主机复位、刷写或NV/OTP/校准写入。

当前仍374-recovered同一guard，用host376；Image363、boot366/DT365、r29/r24与362私有Preview保持。现有四摄与主摄隔离Gamma复用375同启动证据，本轮未重复未改动的摄像头扫描/采集。桌面、SSC、三个remoteproc和相机资源终态另行检查。[终态](final-state-validation.json)。

## 下一步

进入IPE CONFIG_IO、IQ/命令buffer布局、SMMU与缓冲区归属、帧完成与libcamera m2m；继续优先核对原厂代码和固件指令，再接已提取Gamma/LTM/CCM。会话成功尚不证明IPE发动机DMA、帧处理、ISP后级画质或几何同步。

第五颗摄像头身份、更多模式、动态帧时长/自动防频闪、光学/几何/多摄同步/连续AF仍在[完整剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。整体目标active。
