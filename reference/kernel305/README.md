# 305：S5K3M5 几何接口修复与四摄回归

2026-10-19。已在当前 #298 内核上替换长焦传感器模块，修复 V4L2／libcamera 的活动阵列与裁剪描述。四摄产品路径仍为 RAW＋CPU ISP；303 硬件 IPA／AE 候选未安装，完整多摄校准目标继续 active、未完成。

## 来源与分层

先核对 [Hotdog 同传感器补丁](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0081-media-s5k3m5-report-camera-geometry-and-orientation.patch)，再核本机三份模式寄存器表；没有直接采用其它手机方向或校准数据。来源哈希与范围见[源码收据](kernel-source-validation.json)。

只改 sensor 驱动 s5k3m5.c：[补丁](s5k3m5-geometry.patch)。SoC CAMSS／CCI、板级 DT、供电、原厂固件和模式寄存器保持。活动坐标原点采用固定边缘之后的首个有效像素；完整活动阵列 4208×3120，19.2 MHz 二合一模式输出 2104×1560，裁剪仍为完整活动阵列。24 MHz 的 2104×1184 模式裁剪为 (0,376)/4208×2368；该时钟的两模式只核寄存器表，未在本机取流。

原驱动只报 ACTIVE 的 CROP／BOUNDS，并把输出尺寸当作阵列尺寸；修复后支持 ACTIVE／TRY 的 NATIVE_SIZE、CROP_BOUNDS、CROP_DEFAULT 和按格式选择的 CROP，拒绝非法 pad／target。静态物理属性、方向、控制延迟仍需独立证据，没有在 handler 伪造。

## 当前部署与验证

USB NCM 与原严格密钥 SSH 已恢复。重连后发现启动 ID 已变化，仍为 #298、taint0；重新采集并保存本次启动 guard、模块清单和服务身份。没有沿用 303 的启动 ID 或进程记录。[启动基线](current-boot-preflight-validation.json)

当前 Image／DTB 仍来自298；778模块中仅 s5k3m5.ko 改变，SHA256 d1a85e75b9344423097c8189ed65a0320abcb3f7ba3d5fdac34e3c8758f056c9。模块在原输出配置下以树内目标连同 CCI 构建，W=1／Werror 零诊断，intree=Y，vermagic 匹配，导入符号可用。构建后原 Image、DTB、配置、符号表与保存的生成文件恢复。[构建](kernel-build-validation.json)

本地源码分支 samurai-geometry305，提交 18b0a5a753e9363594f682049bf131169488c644，树 /home/cy122/x2pro-linux/camera305-sensor-kernel 干净；原 #298 树和分支保持。未来完整内核重建应包含305传感器修复；当前不是新的完整 Image 部署。[源码提交](kernel-commit-validation.json)

- 8项标准几何查询通过，覆盖 ACTIVE／TRY、非法 pad／target 和 ACTIVE 格式保留；libcamera 属性确认为 4208×3120，活动区域一致，原裁剪告警消失。[安装与回退事务](geometry-install-r3-validation.json)
- 四摄交替18段、272帧通过，含长焦 SIGINT 68帧后重开12帧；17个正常段由 fixture 验证恢复。中断段的旧 fixture 将预期中断和恢复失败共用退出码1，因此另加明确恢复结果的工具补测。[四摄回归](four-camera-regression-validation.json)
- 独立补测长焦中断64帧、重开12帧，子程序正常退出，明确的恢复返回0，媒体图以及保存的格式／裁剪／控制／video状态均恢复。[中断恢复](interrupt-restoration-validation.json)
- 最终核对全部778模块，其中其余777个原样；961包、50相机载荷及 APK数据库／world保持。桌面PID保留，PW／WP正常重启。五sensor／lens、两CCI、CAMSS休眠，9供电用户0，MCLK／CCI clocks0；所测fault、CCI错误、pstore、taint均0，匹配实验worker退出。[收尾](final-health-validation.json)

## 保留的失败与续作

初次单模块 modpost 缺 CCI 导出；独立 M= 构建虽成功但缺 intree，**未加载**。正确做法是树内同时构建 CCI 与 sensor 目标。一次 WSL 会话中断后确认无匹配make，再按已核快照恢复，未据超时重放手机事务。所有日志与旧候选私下保留。[构建恢复](build-interruption-recovery-validation.json)

第一次安装的8项几何查询已通过，但校验误以为 cam -l 会输出型号，触发完整回退；修正为真实 camera ID／属性后建立新事务，成功部署。R2失败和回退证据保留，没有覆盖。[R2](geometry-install-r2-validation.json)、[R3准备](r3-preparation-validation.json)

私人根 E:/edk2-samurai-out/kernel305；当前传输入口305/host.py使用 USB、原密钥和新启动 guard。R2／R3 安装与回归均终态，不重放。未刷写、未重启、未写EEPROM／OTP／NV。

继续从原厂 S5K3M5 调校提取模式数据，为长焦建立独立硬件 profile并实测控制延迟；随后补 RGB 统计／AWB、主前摄和其它模式。303的AE低照度上限证据属于上一启动，目标亮度收敛仍待验证；304的EEPROM布局／校验／LSC几何与golden合成仍未完整确认。几何修复不等同完成图像质量校准。
