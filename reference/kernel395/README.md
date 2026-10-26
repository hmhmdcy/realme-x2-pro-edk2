# 395：修复 A5 强制复位到 DMA 退映射的顺序，并部署正式核心

在394真实ACK丢失会重启的场景中，将强制复位改为脉冲：assert、等待与冷启动一致的2微秒、deassert，再读回A5 enable/wake均清零。之后仍须取得两路IPE新复位确认，才能退映射和释放资源。[本轮同类故障实验](fault-experiment-validation.json)完整恢复通过，没有重启；[正式核心安装及四摄回归](normal-install-validation.json)通过。完整多摄／ISP目标仍active，完整IQ及光学校准未完成。

## 依据与改动层次

复用已保留的原厂ELF/HAL逆向、Realme GPL仓库及现有主线驱动工作。继394直接恢复／CPU停机审计后，从既有本地downstream仓库读取同一提交9668fcdc6ec15be7a10d66f7b93c347829e0fdb6的资源退出实现。[六个函数审计](oem-resource-audit.json)覆盖平台资源关闭、默认和叶级时钟／regulator关闭及IRQ关闭；这些函数没有直接reset_control操作。该结论只限所查调用链，不推断整个OEM驱动从不复位。

Linux Qualcomm复位实现的assert/deassert行为和已实测的A5冷启动序列支持采用复位脉冲。394错误路径把全局ICP/AHB reset一直保持到IPE处理及DMA退映射；395在此之前释放reset并验证CPU未随之启用。**394精确重启指令、物理总线故障机制仍未证明**，本轮证明的是此修正使同类实机实验完整返回。

[生产补丁](forced-reset-pulse.patch)只改核心的停机实现及对应PM注释。deassert失败保留reset标志；读回CPU运行则标记CPU存活并返回错误；再次停机先处理遗留reset再访问CSR。任何复位、读回或IPE确认失败继续保留RAM／PM及未知DMA引用。没有删除强制复位、跳过IPE确认、缩短超时或提前释放图像。

SoC核心维护源为source354，branch samurai-a5-reset-pulse395，commit3a793050772b5e23d22ce9a82dc8ba23000dddb0。板级DT389的7SID／5地址区间、Image363、boot389、FW、CAMSS复合模块389、adapter393及r30/r25用户空间保持；公开API／ABI不变。正式部署只替换一份core模块。

## 验证与实际故障语义

[22个实际停机函数模型](stop-validation.json)在ASan/UBSan下通过，包含assert/deassert/CPU读回/IPE复位失败保留、重试、幂等、协作和非协作停机。provider禁止保持总线复位时访问CSR／IPE或退映射；旧393实现的未知完成反例会被拒绝。这个模型约束是验证假设，硬件实验另行列证。

[正式核心构建](intree-build-validation.json)与[临时测试核心构建](test-intree-build-validation.json)均ARM64、W=1/-Werror、诊断0。正式core354864字节，SHA68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88。临时测试核心使用[编译宏补丁](temporary-ack-loss.patch)，[七个实际ACK解析器模型](hook-validation.json)通过；测试参数仅临时模块存在，生产源码及最终加载模块均不含测试开关。

本轮只进行一次ACK丢失注入，沿用394相同客户端和确认过滤方法。真实成功帧ACK经过原解析器全部校验后被消费一次，不唤醒等待者；两个独立session各预热一帧。设备始终保持394启动guard。

|阶段|395实机结果|
|---|---|
|ACK丢失及真实等待|一次，约5.104476秒，完成超时-110|
|复位前|pending1、request_mapped1、两个导入引用各1|
|强制复位|pulse完成，读回enable/wake清零，block_reset0|
|IPE复位后／退映射前|ACK3,3，pending0／request_mapped0，两个引用仍各1|
|后续顺序|DMA aliases retired，然后PM release返回0|
|双会话错误传播|超时任务-110、同伴-5；错误输出不交付成功|
|同伴目标|完整保持预填内容；超时目标只在复位后核对像素|
|未关闭的旧消费者|新上下文仍拒绝，global fatal保持|
|旧消费者全部关闭后|fatal清除，新上下文完成真实像素核对|

故障epoch jobs6/completed3/direct3/failed3/first_error-110/cancel0，其中失败三次均为预期故障语义。没有把已被抑制确认的硬件帧计作应用成功，没有把故障计数并入正常四摄epoch。两次FW运行后所有映射、导入、CPU／IRQ／PM释放，watchdog／protocol错误0。

这验证完成确认丢失导致的未知完成恢复及双上下文传播；不能外推真实总线挂死、watchdog、每一种MAP／UNMAP／硬件错误或全部光学模式。

## 如实保留第一次安装事务失败

[第一次完整事务](runtime-validation.json)中的上述故障客户端已通过，随后安装正式395并做默认四摄。前三颗各完成12帧，GW1底层完成13帧，应用取12帧且无bus错误、fixture恢复成功。“底层完成数必须等于应用取帧数”的脚本断言拒绝了该结果，事务自动恢复393磁盘和加载模块。该事务仍标记passed=false，不改写成功。

[原GStreamer客户端](../kernel316/gst-hardware-probe.c)使用异步libcamerasrc和有两个缓冲的appsink，应用取满12帧后才转NULL；另有在途完成帧是允许的。第二次正常安装检查实际提交数＝完成数＝direct数、完成数至少覆盖应用交付数，并独立核对core帧数和session关闭、所有错误／取消为零；逐颗持久化交付及额外完成数。没有忽略未完成作业或放宽错误要求，也没有重复故障注入。

第二次root为k395-normal-install-r2，worker8282已终态；正式395四摄各12帧640×480 NV12，恰好48个底层direct作业，额外完成0、starts/stops4，failed/cancel/first_error0。没有LD_LIBRARY_PATH或调校覆盖。[第一次故障客户端与第一次正常49帧](fault-experiment-validation.json)和第二次正常48帧分别保存。

## 当前状态与接续

[最终核对](current-state-validation.json)：正式core磁盘SHA与加载note匹配，adapter393／CAMSS389及四份个体配置保持，七包r30/r25不变；正式测试参数不存在、source干净。CPU/IRQ/PM/backing/map/import全部回收，ICP/CAMSS/双CCI suspended，17相关时钟0、九路电源disabled/users0，taint0。PW8440／WP8443各一、uid10000。两次事务worker／client／collector均无活动进程；第一次collector未捕获新dump，第二次正常安装没有运行collector。旧394失败及ramoops保持。

旧393 core的两个回退副本已读回核对；390平台／boot366、391旧r29/r24七包、393旧pair备份保持。当前使用host395委托host394和394guard，无新启动，无刷分区。实验状态改为临时文件fsync、replace和目录fsync，避免394未落盘问题；不能据此假定所有普通日志都绝对持久化。

后续优先继续底层错误恢复的相关缺口，再推进已提取的原厂Gamma/LTM/CCM完整IQ及[363全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)：第五2MP身份／mux、多模式、动态帧长／防频闪、几何／多摄同步、连续AF及光学画质。当前仍1:1 NV12/NV21 IQ旁路，异步implicit-fence发布未证明。关灯黑场／噪点按低照度解释，照明相关校准后做。SSC／旋转未全面复验，旧间歇故障不宣称修复。

私有固件／HAL／原厂源码／ASM／CDM／全日志／图像／个体校准只留private395及前序；公共镜像仅本地提交，保留无关改动，不push／PR。
