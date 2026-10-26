# 阶段218：原生尺寸Quad Bayer CPU候选

2026-10-16。手机仍部署216前摄模块与214完整r5软件包、boot211/内核183，未刷写或重启。本轮不启用闪光灯，只对真实暗场RAW做内存统计，不保存或展示房间画面。

已实现不折半输出的RAW10 Quad Bayer双线性解码，完成宿主ASan/UBSan和手机普通用户的400组独立参考比较；手机还处理了三帧4608×3456合成输入。四线程每帧约136–139 ms，不能当作30fps或实拍画质验收。[算法与接口依据](build-test-notes.md)、[原生CPU收据](native-core-validation.json)。

system heap同时分配四个完整RAW和四个完整RGBA缓冲，共334,430,208字节，映射与DMA同步通过且全部释放；没有据此声称CAMSS完整尺寸导入通过。[分配收据](heap-capacity-validation.json)。

libcamera集成候选已完成警告视为错误的独立构建与四项Meson测试。手机普通用户使用真实FrameBuffer与system heap，50组合成输入逐像素检查通过，包括四种CFA、六种RGB格式、非单位颜色矩阵、边界、统计及完整→普通→完整切换。[CPU类收据](cpu-isp-tests-validation.json)、[构建](candidate-build-validation.json)。实验选项默认关闭，产品配方与锁文件未替换；217内核/DTB候选未安装。

使用候选库与原r5签名IPA，当前模式[暗场RAW](candidate-dark-raw-validation.json)六帧有0.44–0.47噪声和约33%–36%逐帧变化，支持真实暗场判断；[数字白RGB](candidate-white-rgb-validation.json)六帧首帧起254。独立构建前缀造成的首次配置预检失败及修正见[记录](initial-regression-failure-validation.json)，没有把失败记成黑帧或通过。

新发现217的COMPOSE描述不能被现有libcamera正确消费，还需修订；[几何接口审计](geometry-interface-audit.md)。当前前摄实机仍仅1928×1088，完整传感器模式、标准CFA描述、时序和画质未验收。

[最终健康](final-health-validation.json)：49条相机payload及944包保持、3DSP running、相机休眠且供电/时钟释放、GPS关闭、BT关闭无连接、taint/五fault0。私人最终归档59成员逐个哈希核对通过。[总收据](final-validation.json)、[归档核对](final-evidence-validation.json)。

全外设目标继续active：GNSS真实定位/正CNR、完整前摄实拍及后置四摄、GPU ISP、蜂窝实际业务等仍开放。继承[217检查点](../kernel217/README.md)中的启动、回退和未验收项。
