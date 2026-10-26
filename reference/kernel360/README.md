# 360：Gamma／曝光合并与 r28 软件包候选

2026-10-20。将349已验证的IFE Gamma与359原厂曝光程序合并到同一实际CAMSS IPA候选，保留pipeline接口版本1。核心库、签名IPA、worker及完整r28／配置r23包均构建通过，组合及打包载荷检查通过，尚未安装。随后发现手机已恢复Linux和原密钥USB SSH；原r27／338版本四摄短采集通过。完整多摄／ISP适配继续。

公共源码以342 r27为共同基线，三方合并349／359。只有CAMSS的Meson源文件列表需要合并两边新增项，`camss.cpp`和公共libipa构建列表自动合并。独立的原厂Gamma、曝光表及防频闪算法源码保持一致；本轮不改板级地址、传感器驱动、内核或运行设备。[合并清单](merge-validation.json)。

配方新增 `0037-camss-static-ife-gamma.patch` 与 [0038曝光补丁](0038-camss-factory-exposure-program.patch)，从r27顺序零fuzz应用后，23个相关源文件与组合候选零差。准备 `libcamera99990.7.2-r28`、config／stack `0.1.0-r23`；当前正式r27／r22配方保持不变。公共默认配置不加入原厂或个体参数。[源码与配方](package-source-validation.json)。

核心目标构建177.45秒，完整框架包构建294.85秒，配置包8.44秒。13个包保留原有完整消费者集合，七个运行包及r27／r22回退包分别生成签名仓库；六个IPA模块、Python、qcam、GStreamer与V4L2均保留。APK签名及打包核心库对IPA签名的验证通过，使用剥离调试符号后的实际打包IPA／核心库再运行主摄和非对称RGB两组组合检查通过。公共默认YAML逐份与配方一致，没有夹带私有原厂表、个体校准或密钥。[构建](package-build-validation.json)、[载荷检查](package-artifact-validation.json)。生产构建保留原Meson `werror=false`，合同工具单独Werror；未重跑未改算法的全量检查。

私有8份Preview／Video完整配置给已有5个物理模式／10个用途上下文同时加入所选原厂曝光程序和Gamma。每个Gamma根按原管理器的实际模式选择，曲线核对已有原厂指令参考块；WB、LSC、CCM及lux内容保留。未映射的前摄裁剪模式保持generic，不补造缺完整IQ的高分辨率配置。[配置](profile-validation.json)。

实际ARM64 IPA在QEMU中完成12组路径检查：10个原厂上下文、主摄线程代理和IMX319非对称RGB诊断。每组核对6个原厂曝光分配输入及9次开流的完整776字节Gamma块，共72次分配比较／108次Gamma包核对。正常EV、防频闪、延迟统计与历史元数据、原子拒绝、WB合并ACK、重启以及切回legacy配置均通过，AE或WB后续更新不重复上传Gamma。[组合检查](ipa-contract-validation.json)。统计和V4L2控制仍由合成夹具提供，不证明实机时序或画质。未改公共AGC控制器，复用359的480帧零差回归。

启用Gamma的私有配置需要348或后续支持参数类型7的CAMSS。349在旧338内核已观察到启动拒绝，本轮没有用用户空间补偿绕过它。当前固定帧预算、手动频闪、无数字增益等359适用范围继续保留；独立进程IPC仍受QEMU `clone3` 限制待设备验证。IFE Gamma不等于原厂最终显示色调，后级IPE Gamma／LTM／CCM及ICP／HFI、图像会话仍需完成。

收尾时USB9008消失并出现NCM，原密钥USB SSH成功登录新启动，仍为k298、CAMSS338，八核在线、taint0；ICP实验模块和临时DT节点不在，17路ICP/BPS/IPE时钟引用为0。没有pstore文件，无法补出CPU5精确卡点，也未确认9008退出的触发方式，不把恢复归因于本轮主机操作。[启动观察](recovered-boot-validation.json)。此前复位过程及板级错误见[357记录](../kernel357/README.md)。

R5原记录仍停在 `load-boot-test`、terminal=false；原工作进程已不存在。本轮只移除 `/lib/firmware` 下专用临时副本，先核对与352原件及R5保留副本一致；原R5状态及固件备份保留，没有把旧实验改写为成功。新建独立360启动记录，原305／356记录不变。[清理结果](recovery-cleanup-validation.json)。认证、内核原日志和可能敏感的调试输入继续私存。

安装版本仍为r27／配置r22，四颗物理摄像头枚举与342原安装记录一致；PipeWire节点不与硬件相机重复计数。[枚举](recovered-camera-validation.json)。随后按当前ID各请求640×480 NV12短采集4帧，共16帧，均退出0、无帧错误，相关新故障0、taint0，CAMSS与两CCI恢复休眠。没有保存场景图像、安装新包、替换内核／模块或再次触发ICP启动。[原版本采集](recovered-baseline-capture-validation.json)。这不等于新r28实机验证或光学校准。

下一步在新启动上以配套348 Gamma参数ABI临时验证r28组合候选，再推进动态帧长及更多模式、正确板级内存后的ICP／HFI与IPE完整图像链。当前无需再为恢复SSH强制重启手机。
