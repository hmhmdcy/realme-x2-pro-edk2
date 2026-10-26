# 238：IMX319 增益换算、48帧控制与同平台方案核对

2026-10-16。完整构建libcamera r14/config r9候选，在手机RAM中验证IMX319的48帧手动曝光/增益控制，补采并离线分析匹配vendor GNSS库，重新核对Realme/OPPO/一加的Linux方案。**RAW控制通过；RGB启动一帧全零，严格验收失败，r14未替换默认r13。GNSS仍无正CNR/fix，完整适配goal active。**

用户要求的机型、传感器、源码入口及适用条件见[Linux摄像头/GNSS对照](RELATED-LINUX-SOLUTIONS.md)。本轮没有要求纯色物体、保存/展示场景、闪光或增加照明，没有GNSS SET/搜星、重启或刷写。

## 增益修复与完整构建

- [0021补丁](0021-imx319-gain-helper.patch)仅注册`imx319` helper，使用`AnalogueGainLinear{0,1024,-1,1024}`。保留r13原20补丁、完整管线、Qt/Python/GStreamer等子包及5个IPA签名，不复制其它传感器blackLevel/尺寸/延迟。
- [真实C++ factory测试](gain-helper-test-validation.json)遍历961码，检查有限/单调，1/2/4/8/16倍与0/512/768/896/960对应；旧r13缺helper负对照有效。通用反算存在148个低一代码的整数截断，已按实际ARM产物记录，未改全局基类。
- [13个包构建](package-build-validation.json)、[完整目标](r14-full-feature-configuration-validation.json)、[签名和ARM用户态QA](r14-host-runtime-qa-validation.json)通过；原214目录2254文件/链接/模式已恢复，r13对象缓存保持，新r14源码/对象和13包另存。49个运行文件由7个包解出，仅暂存在手机RAM。
- 首次准备脚本错误锚点导致缺recipe；主线程错误地继续启动构建，构建在编译前终止并恢复原214。随后修正锚点/添加前置断言后才完成真实构建。[失败记录](first-preparation-failure-validation.json)保留。

## 真实相机试验与保留失败

探针核完整OF camera ID、Model、实体和sysfs，确认真实IMX319、FrameSuccess、单stream/plane；显式start/reuse手动控制，DMA同步后只统计有效像素，最后恢复整个媒体图、格式、两sensor控制、P/Q供电、PM和时钟。

1. 首次RAW尝试因配置父目录700、UID10000无法读取CPU配置而失败，无计入成功的帧。保留[失败](controlled-rear-validation.json)，修正到755并用相同UID确认可读后另开r2。
2. [RAW r2](controlled-rear-r2-validation.json)48帧通过。四阶段各12帧、最后6帧settle：约1999us/1倍→31995us/1倍→31995us/8倍→1999us/1倍。[离线分析](control-response-analysis.json)得到均值约63.973→64.717→70.595→63.973，噪声也随曝光/增益增加；只能证明控制链和数据变化，不能独立证明光学成像正常。
3. I²C发送事件曝光码201→3216→201、gain码0→896→0，8核trace丢失计数0。trace不是ACK/readback。过渡帧像素/元数据可差约一帧，物理控制延迟未标定，最后6帧覆盖稳定区间。
4. 首RGB请求1632宽超出CPU去边后的1624宽，验证阶段退出，未配置/启流；[失败](controlled-rear-rgb-validation.json)保留。修正请求后另开r2。
5. [RGB r2](controlled-rear-rgb-r2-validation.json)实际程序正常退出、48帧元数据及清理均通过，但q1/sequence1全部为零，wrapper严格检查失败，`passed=false`保留。q0为14–15，q2约33–38；其余47帧非零不是颜色/成像验收。

实际软件ISP源码的首次参数同步与动态BLC16→12可以解释前三帧数值，尚缺同帧实际参数证据。上游历史BLC255→16修复已包含，不能重复套补丁或复制一加IMX371猜测黑电平。下一项固定2ms/1倍短采并记逐帧BLC/Gamma/ColourGains/实际Debayer参数，必要时同request配对RAW/RGB；先解释黑帧，再验前摄候选回归和默认安装。

另纠正一次工具判断：最初搜索simple.cpp/software_isp.cpp没找到RAW统计日志，错误称其不存在并在r2改用配置/元数据证据；该日志实际位于debayer_cpu.cpp、保留补丁0015中，原生r2 stderr也确有`RAW-only CPU statistics enabled`。[原生日志复核](evidence-validation.json)已确认；r2原始收据和失败均保留，RAW CPU统计路径有正证据。

## GNSS 来源核验

[首采](vendor-audit-validation.json)及[补采](vendor-followup-validation.json)均识别实际vendor几何，ro/noload/nosuid/nodev/noexec挂载，仅选GNSS文件，不执行代码、不读NV/persist，正常卸载，分区前后摘要一致。分别导出54和27成员并逐一校验，私有ELF/配置不公开。vendor属性为Android16/SDK36/2025-12-01；API30实现和API36接口构建标记共存，不能直接判ABI错配。

实际关键库与锁定公开samurai vendor逐字节相同；vendor115↔238相同只发布布尔结论。liblbs_core三种0x84辅助服务配置已解码，但未观察Android运行发包，未找到RF/LNA初始化缺口。vendor没有gps.conf不是整机缺文件：设备树布局指向ODM，旧205/228的gps/ODM资料来自社区仓库，当前本机ODM来源仍未知。详细证据与Linux软件边界见[研究](RELATED-LINUX-SOLUTIONS.md)。

## 当前部署、清理和续作

- 仍236启动/235 boot，CAMSS ff9、前摄e49、IMX319176f、MFD6021/lab5198/provider2223及FastRPC2abd保持。775ko/789文件与237权威清单相同，默认libcamera r13/config r8及包数据库、用户态、loader保持。[最终状态](final-health-validation.json)。
- 所有238 worker终态，临时挂载和trace已清；两sensor、CCI0/1、CAMSS suspended，四相机rails OFF/users0、MCLK1/2关。三DSP、SensorProxy三Has、Wi-Fi/chrony正常，taint和各类fault0。蓝牙开启、1连接只观察；GNSS空闲0/Signalsfalse/rate30，无新数据worker，MM失败状态符合当前无SIM背景但不代替GNSS RF诊断。
- [97原生成员](evidence-validation.json)已私有导出并逐一校验，含失败、48帧统计、I²C请求trace和清理；vendor payload另有已验证导出，避免重复归档。没有场景像素或私有归档指纹公开。
- canonical仍精确after228；其中旧相机输出不能整套刷入。235/236/237冻结源及boot/MFD/lab/CAMSS回退依旧有效。当前lab有消费者，不能重放“未绑定/ref0”热卸流程。
- 首要续作是RGB启动参数/BLC；S5K3M5继续按本机19.2MHz OEM双投影解码和独立边界核验，不能复制Hotdog 24MHz/供电。GNSS下一项为最小匹配ODM gps.conf来源核验，未形成新SET方案。其它后摄、物理颜色/光学响应、GNSS真fix、蜂窝业务及全机长稳仍开放。
