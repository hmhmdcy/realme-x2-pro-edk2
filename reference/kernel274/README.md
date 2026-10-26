# 274：主摄镜头光学响应、标准镜头驱动候选与 ISP 分层

2026-10-18。继续完整目标：多个摄像头及骁龙 ISP 支持，区分 SoC、板级、公共驱动和用户空间，尽量将适配向底层收敛。**目标未完成，保持 active。**

手机仍为 boot273/Image183、775 模块/961 包、libcamera r21/config-r16/PipeWire r3。本轮没有安装新产品模块或软件包，没有刷写、重启、修改校准/OTP。最终四 sensor/双 CCI/CAMSS suspended，九 camera rails disabled/users0、四 MCLK 关闭，fault0/taint0/pstore 空；原桌面/PW/WP 进程保持。当前 SSC 启动失败、自动旋转不可用的问题仍在，不能以相机资源健康覆盖。[最终核对](final-health-validation.json)

## 已产生的实际进展

273 高分辨率手动控制失败之后，274 保留同样的八阶段计划、96 组 RAW/RGB、全像素统计和原阈值，比较原线程统计与独立统计线程。两轮均 96 组、零严格阶段不匹配；原失败没有稳定复现，**未据此修改或宣称修复 IPA/驱动根因**。[直接统计](main-manual-direct-r1-validation.json)、[工作线程](main-manual-worker-r1-validation.json)

读取固定哈希的本机 Sunny/Qtech GW1 BIN，按匹配 XSD 解码 actuator；再以受限的独立 ParameterParser 解码 XML，逐项核对位置命令、初始化、供电、初始码、区域及阻尼。两个变体分别为 LC898219XI/BU64253；不能只凭 GW1 传感器地址判供应商。原 BIN 载荷保持，厂商库没有作为硬件驱动执行。[直接解码](actuator-contract-validation.json)、[独立交叉核对](actuator-command-crosscheck-validation.json)

Sunny 配置的 8-bit 地址 0xe4 对应 7-bit 0x72，位置为 0x84 + 16-bit 大端数据，初始化 0xe0=1 后最小等待 1us；原厂初始码 208。主摄正常取流期间供电由现有 sensor 驱动管理，0x72 两次普通寄存器读取均得到应答。[只读验证](actuator-read-r1-validation.json)

随后执行有界原厂命令测试。r2 为未发位置命令与 208 对比；r3 为 208/304/400/496/592/688/784/880/208 九阶段，每阶段六份 RGB 统计及一张私人 JPEG。命令均获总线应答，镜头位置寄存器没有回显；**没有可读 chip-ID 或实际位置反馈证明**。取流正常停止，电源与时钟回收。

逐张查看原图以及多尺度离线分析证明了光学响应：304 阶段边缘扩散代理约 8px、880 约 46.5px，返回 208 后约 8.71px；窗帘细节能量也随失焦显著降低并恢复。不能把这解释为标定距离、全局最佳焦点或自动对焦已完成。自动曝光未锁定，JPEG 与统计并非同一 request；中央 ROI 多为平墙，原单一分数受噪声影响，不能独自验收 AF。[有界位置测试](focus-position-r3-validation.json)、[光学分析及限制](focus-optical-analysis.json)

## 已保存、尚未部署的底层候选

维护树 `/home/cy122/x2pro-linux/camera270-kernel` 当前候选分支 `samurai-main-focus274`，干净提交 `0798ee688921b987a67c045afeab093f9b0c274d`；父提交 3184c56 为现机相机来源，原 `samurai-main-camera272` 分支保留。未推送。[完整候选补丁](lc898219xi-candidate.patch)

- 通用 `onnn,lc898219xi` V4L2 lens 驱动，通过标准 `V4L2_CID_FOCUS_ABSOLUTE`、I2C、regulator 和 runtime PM 提供绝对位置控制；不含本机地址、208 默认焦点、场景/应用判断或原厂私有 HAL。
- 板级只新增 lens@72、`lens-focus`，将 VAF 唯一消费者由 sensor 移到 lens；现机仍是旧接线/供电消费者组合，**新供电归属尚未实机验证**。其余 SoC、CCI、CAMSS、其它 sensor 属性不变。
- 按器件资料处理 VDD 开机到 I2C 至少 5ms、重新上电前至少 100ms 关闭时间；板级独占 VAF 是这份候选能管理实际关闭间隔的前提。没有捏造读回握手或未定义待机寄存器。首次打开不写任意 DAC 默认值，显式位置命令/缓存目标按标准控制接口处理。
- W=1 lens 对象零诊断，板级 DTB 构建成功；新增 binding 文档和 LC/GW1/PM8008 三组 schema 零诊断。C 文件 checkpatch 零 error/warning；这不是上游接收记录。[编译](driver-build-validation.json)、[板级语义与 schema](lens-board-validation.json)
- 从实际候选提取并编译写表、控制、PM 回调，13 个主机用例覆盖短写/NACK、使能失败、回滚失败保留引用及重试、关闭失败、控制缓存和最小关闭间隔，UBSan 通过。没有声称已注入物理总线/PMIC 故障。[回调验证](lens-callback-validation.json)

只有对象/DTB编译，尚未生成并部署 Image183 匹配模块。标准驱动完整范围是 0…1023，本轮实机只验证了 208…880 的部分位置及返回命令，不代表完整端点标定。

## 用户空间与 ISP 的真实缺口

现 libcamera `CameraLens::init()` 打开 subdev 并持有至对象销毁；常驻 CameraManager 可能令采用标准 open/close PM 的 lens 长期上电。**部署前必须先将 Simple 管线的 lens 打开/关闭与实际相机 start/stop 生命周期配套**，验证仅枚举、取流、停止、跨进程/并用及异常退出，不能仅靠删掉内核 PM 回避问题。Simple 的 AF 算法、LensPosition 与实际距离的标定映射也尚未完成。

骁龙仍是 CSIPHY/CSID/VFE RDI RAW + CPU ISP。已对固定版本原厂 VFE170 和维护源逐项定位：原厂定义 20 bus clients/18 outputs，含 FULL/DS4/DS16、RAW_DUMP、FD 和统计；维护 VFE170 writer 配置的是 MIPI RAW，`formats_pix_845` 自身仍是 RAW 表的 TODO 占位。不能凭 `pix` 节点名称声称 Spectra 已接通。[分层与后续接口](ISP-ADAPTATION.md)、[源码证据](isp-gap-validation.json)

## 失败、修正及续作状态

首次解码错误假设原厂初始化 delay=0，实际为 1us；修正后独立 XML 核对一致。初版解析脚本先插入 272 路径再 import host，导致私人离线解码候选落到 272 私人目录；现改为先导入本阶段 host，新结果已写入 274，旧文件保留。

位置测试 r1 错误要求 0xe0 写 1 后必须回显 1，在发出初始化后主动中止，未发位置命令。原厂配置只规定 WRITE、不规定回显，公开资料也没有此寄存器图；保留 r1 失败，以 r2/r3 的普通命令应答和真实光学变化评价，不伪造握手通过。原记录中 `parked_at_oem_initial_code` 只表示最后成功发送 208 命令，**不代表读回物理镜头位置**。

第一次 checkpatch 使用带空格的参考路径触发内部 diff 参数错误，未视为检查通过；改用已逐字核对的 WSL 候选路径，得到真正的零诊断。最终 Kconfig 明确依赖 PM，避免不支持 runtime PM 的配置被选择。图像与原厂输入、原日志只在 `E:/edk2-samurai-out/kernel274` 等私人目录，公开目录只保存代码/摘要。

后续先补标准 lens 生命周期与实机驱动/供电验收，再推进 AF 校准、画质与四摄 GUI/录像，同时持续实现 VFE170 公共硬件 ISP 路径。SSC/正常启动、默认 GPU、旧 modem watchdog、第四颗后摄识别、完整新 Image/rootfs 与跨版本维护均保持开放；目标没有缩减为本轮候选编译。
