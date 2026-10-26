# 272：GW1 主摄标准驱动候选、板级描述与离线验证

后续[273](../kernel273/README.md)已实际部署本候选并取得主摄RAW/RGB及实景；下文“未部署/未上电”描述272当时状态。完整控制切换测试、AF/Spectra及SSC开机问题仍开放。

2026-10-18。本轮有源码和构建进展：新增 GW1 驱动、静态 DTS、binding 与 libcamera helper 候选，完成主机故障注入和编译。**没有安装新模块/软件包，没有上电主摄、刷写或重启。主摄出帧、AF、完整多摄和 Spectra 成像处理仍未完成，目标保持 active。**

## 当前实机与候选分开记录

实际部署保持 [271](../kernel271/README.md)：boot270/Image183，774 模块、961 包；libcamera r20/config-r15，S5K3M5 原生细分增益。前摄 IMX471、后摄 IMX319/S5K3M5 有原生采集和此前实景证据。本轮仅做[只读检查](current-idle-validation.json)：原启动身份匹配，三 sensor/双 CCI/CAMSS suspended，六相机电源 disabled/users0、三 MCLK 关闭，无相机客户端，taint/fault0，桌面和 PW/WP 身份保持。当前 pstore 空不代表旧 modem watchdog 已修。

内核开发树 `/home/cy122/x2pro-linux/camera270-kernel` 当前改为分支 `samurai-main-camera272`，提交 `3184c56b7f206ab000ab79bc99eb83d35c3e1d65`，工作树清洁，未推送。父提交 ac7ccc2 及原 271 分支保留。本目录 [source-lock](source-lock.json) 锁定**未部署候选**；产品 camera/deployment-lock.json 和 kernel/source-lock.json 仍锁定真实 271 部署，没有晋升候选。

## 原厂依据与适配范围

- 原厂 Android 本机日志 slot0/slave_addr0x20/sensor_id0x0971 确定主摄 7-bit 地址 0x10 和芯片 ID 0x0971。与 Sunny 描述地址相符，不能单凭地址断定实际模组供应商。[控制和地址](control-contract-validation.json)。
- 重新读取两份固定哈希原始 BIN，与保存的两种 XML 投影逐项比较，双方初始化及全部十个模式一致。模式 1/6 只有一条页面选择指令，不能独立当完整模式使用。[本轮输入复核](input-revalidation.json)。原厂库仅静态检查指令，没有执行。
- 驱动先支持具有完整配置的 4608×3456、4608×2592 两模式，保留 51 条初始化记录中的 11 段间接 RAM burst、10ms 等待及模式内 8-bit 0x0101 写入；更多模式、完整分辨率、高速/HDR 仍开放。[生成记录](table-generation-validation.json)。9280 宽完整模式超过当前 CAMSS 的 8191 宽限制，没有冒充已接通。
- board19781 供电顺序采用 VANA→VDIG→VIO→VAF→解除复位→MCLK；断电采用 MCLK→复位→VIO→VDIG→VAF→VANA。PM8008 Q 的 L1/L3/L7、PM8150 GPIO1、TLMM GPIO13/MCLK0、CCI0 master0、CSIPHY0 均通过标准资源描述。VAF 是本机原厂序列要求的模组电源，供电不代表 AF 已有驱动。不启用未在 sensor 序列中使用的 Q L4，不猜测未知 PLDO 输入网。
- 曝光最小 6 行、FLL 余量 6 行；普通模式模拟增益原生码 32…1024，即 1…32 倍、步进 1/32。HDR 模式 9 使用其它限制，不在当前候选范围。group hold、FLL/曝光与增益使用真实寄存器；不编造黑电平、控制延迟或 ISO 标定。

初始化/模式写入在实际读取芯片 ID 之后才允许执行。使用通用 `samsung,s5kgw1`、regulator、GPIO、clock、runtime PM、V4L2/MC 接口，没有新实验供电 provider、运行时 OF 注入或应用机型判断。[完整内核候选补丁](s5kgw1-candidate.patch)。

## 已验证及边界

1. [独立输出树编译](driver-build-validation.json)：正常 Kconfig 开启，W=1 sensor 对象零诊断，DTB 构建成功。首轮因缺少 regmap.h 失败，确认原进程终止后修正并重编；原失败日志保留。
2. [现机匹配模块](current-module-build-validation.json)：GW1 ko 80344 字节，vermagic 与 Image183 匹配、导入符号可用、W=1 零诊断；CCI ko 与现用 f9c9272a…逐字一致，无需替换。canonical 的源/配置/Image 和既有构建产物按快照恢复。模块尚未加载。
3. [板级语义和 schema](board-validation.json)：相对部署 DT270 新增 11 节点，只改变 CCI0 对应总线 status，未删除节点，其它外设及已用相机属性保持。GW1、CAMSS、PM8008、PMIC GPIO、reserved-memory 五组校验零诊断；不扩称全树完整验收。
4. [实际 C 写表函数](table-writer-test-validation.json)：2/4/6/8 字节整字负载下 12 次完整运行、13816 次预期传输逐项匹配独立 OEM 记录，108 个失败位置均及时返回。每个 burst 分块重复 0x6f12 地址，不错误地递增寄存器地址；字节序、尾块、8-bit 翻转和等待保留。
5. [实际供电回调](power-sequence-test-validation.json)：30 个主机用例覆盖可选 AF 电源、原厂上电顺序/等待、失败回滚、重入拒绝、共享 regulator 引用保持、断电失败保留引用并阻止恢复。[实际控制回调](control-test-validation.json)另有 16 个用例，验证 group hold 释放尝试、FLL/曝光余量、失败返回和 PM 引用平衡。均使用 UBSan；这些不是实际 PMIC/GPIO/总线故障测试。
6. [libcamera helper 候选](helper-candidate-validation.json)：实际 ARM C++ factory 测试遍历全部 993 码；原三 sensor helper 保持；旧 r20 缺少 GW1 helper 的负向对照返回 3 符合预期。[新增补丁](0025-s5kgw1-native-gain-helper.patch)。只使用保留 r20 SDK 编译候选 helper/test，没有构建或安装 r21 APK，也没有改动旧 r20 源/库。

checkpatch 零 error、三 warning：新增文件的 MAINTAINERS 归属、binding/驱动拆分投稿、Kconfig 帮助段长度。当前提交是本地候选，不是上游接收记录。

## 接下来继续实机与完整适配

VT pixel rate 1.92GHz、C-PHY LINK_FREQ 499.2MHz 是按 PLL/原厂时序推导的候选，**没有物理验证**；不得把 vendor outputPixelClock 683316000 直接当阵列像素时钟。C-PHY 的总线频率、symbol rate 与 pixel-array rate 区分参见 [Linux 接口定义](https://www.kernel.org/doc/html/v5.16/driver-api/media/tx-rx.html)。寄存器推导裁剪亦需原始帧和实体场景核对。

后续需先完成 r21/helper 配套原生包及回退；重核手机身份、保存当前 boot270/包/模块，再以仅改 DT 的固件和匹配 GW1 模块做受控实机 probe。首次只接受真实 chip ID；随后有界验证 C-PHY RAW、实际帧间隔、PLL/接收器 settle、曝光/增益及资源回收，同时回归现有三 sensor。共享 CAMSS/CCI/PMIC 有消费者时不卸载，失败不反复重放旧事务。此处的 boot270 guard 只用于当前启动；新启动必须重新建立身份。

主摄出帧后仍须接入 AF/模组校准、其它后摄、正常 AE/AWB/颜色/噪声、更多模式/GUI/录像/长稳。已用 Qualcomm CSIPHY/CSID/VFE RDI 采 RAW，处理仍 CPU software ISP；C-PHY 接入也不会自动接通 Spectra 硬件成像处理。完整统一 kernel/rootfs、默认 GPU 故障和旧 modem watchdog 保持开放。

本轮私人原始输入、日志、主机测试、候选模块与环境在 `E:/edk2-samurai-out/kernel272`，测试 helper 在 SDK `private/gw1-helper272`。公开目录不含场景像素、SSH/签名密钥或启动身份。旧构建/测试脚本的一次性目录已经终态，不能直接重放；修订使用新目录和新事务。
