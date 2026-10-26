# 424：修正 LTM 衰减坐标，补统计缺失恢复，实拍完成自动对焦

继续完整多摄／ISP适配。本轮修正了423候选的一项实际输入域错误，并验证缺BG/lux时持有已确认曲线。普通／隔离IPA各205帧现场采集，共410个direct IPE作业、402次数学提交；两次主摄AF扫描均报告Focused，保存图像也显示中心细节提升。**完整GTM／LTM粗级统计、多摄与画质校准未完成，候选没有永久安装。**

## 输入域修正与恢复

优先查看已有CamxChi固定仓库、本机HAL及当前内核，没有重新下载固件、访问NV／OTP／个体校准分区。[来源及已定位入口](primary-sources.json)。原HAL `0x35fe8c..0x35ffbc` 将请求+2892的lux更新到LTM缓存；IFE父节点 `0x10000` 下，再写入当前/前次衰减索引。423误将物理曝光时间×增益坐标送入这个接口。8组原指令执行确认坐标和首次请求复位条件，没有数学provider：[原厂绑定](exposure-domain-validation.json)。

[IpeToneProfile](ipe_tone_profile.cpp)改用同SOF的`frame.luxIndex`，候选下一状态保存`ltmLuxIndex`；历史仍仅在最终图像／RAW配对成功后提交。物理曝光索引继续用于原有观测，不与lux混同。当前原生策略依旧在首次有效计算时令previous=current；未将Android最大流水线延迟／BET暖机条件冒充为Linux已验证策略。

[实际编译对象检查](profile-validation.json)将lux固定、只改物理曝光索引：修正程序的6008B输出完全不变，重现旧绑定的反例改变123字节；只改变已确认lux历史时，实际LTM输出改变120字节，证明衰减依赖正确坐标。首次历史、输入不变、失败输出保持也通过。原厂例子的实际TMC输出同时启用GTM且分配非零GTM份额；不能把当前缺少GTM硬件应用当成自然无效或完整原厂等价。

`prepareIpeParameters()`在已有观测缺BG／有效lux时，复用已经提交的6008B包；尚无已提交曲线则暂用既有旁路。此时fresh=false、数值版本和历史不变，后续有效统计从最后成功状态继续。不会捏造lux或把不完整观测当成新数学状态。无效token、旧epoch以及真实计算错误仍按原校验处理。

[真实ARM64 IPA模块检查](ipa-validation.json)覆盖首次缺BG、提交后缺BG、恢复，以及已有失败／忙时持有／旧回执／重启场景；原423模块在同一个首帧缺BG夹具中实际返回-ENODATA，反例日志私存。统计夹具通过原有合法性检查，没有放宽生产解析器。本轮未在手机上注入损坏统计或丢ACK。三个实际生成包通过[当前内核validator](packet-validation.json)。

仅改用户空间三个生产文件，私有IPA接口仍3、内核UAPI仍1／6008B。没有改SoC、板级DT、主线／传感器驱动、固件或应用图像处理。[完整补丁](0045-camss-ltm-lux-history-and-stats-hold.patch)、[零fuzz复现](source-validation.json)。

## 真实采集与AF

沿用423已验证的核心库／代理和原厂主摄配置，只重新构建变化的IPA。源码输入在构建前后哈希一致，两个实际变化对象重编；64.12s成功，核心／代理与423逐字节相同。IPA SHA256 `324a821f1c72f0ebb983d73f33a4500c4d696640932c362e0020e10958088129`，新签名通过：[构建](build-validation.json)。没有重复旧算法大矩阵或色彩Gamma回环。

采集器关闭测试图、开启AE／AWB，先等待24份匹配的元数据，再通过标准AfTrigger执行一次实际AF扫描；收到Focused或Failed终态后继续16帧，20s期限防止无限等待。计数由扫描完成决定，未用固定帧数冒充对焦成功。[采集器](capture.cpp)、[Werror构建](capture-validation.json)。pipeline fixture按原机制恢复媒体图与保存的控件，未直接编程镜头寄存器。

| 现场路径 | 图像 | 数学提交 | 不同参数摘要 | AF终态 | 首次／最终FocusFoM |
|---|---:|---:|---:|---|---:|
| 普通IPA | 205 | 202 | 56 | Focused | 1005／1633 |
| 隔离IPA | 205 | 200 | 59 | Focused | 810／1598 |

每次扫描有161份Scanning元数据；表中“首次”取AE预热最后一帧，不是首张图像。[逐帧归属检查](hardware-validation.json)核对每个新包的同SOF BHIST摘要、6008B请求、最终成功回执，并证明每次`previous-ltm-lux`都等于上一成功提交的lux。普通／隔离实际进程区分通过；持有分别3／5次，不推进历史。

从手机保存样本中按元数据选择AF前后帧，原始NV12解码查看，未加应用调色。中心区域归一化平方梯度分别由0.000565→0.001267、0.000489→0.001211；支持本场景中心细节提升。AF后画面仍有明显雾感及偏色，没有据AF状态或该指标宣布色准、MTF、噪声、全景焦平面已校准。[图像与元数据摘要](scenes-validation.json)。原始图像／校准数据仅存私有kernel424目录。

[设备事务](runtime-r1-validation.json)410作业全部direct成功，新增故障0、dump0、取消／failed／first_error0；最终jobs=completed=direct793，starts=stops25。core电源／时钟所有权、IRQ、映射、DMA、导入缓冲全部释放，PW／WP各恢复一个实例，owner_refs53为桌面CAMSS句柄，历史taint512保留。worker、client和collector均终态。正式420的r31／r26、419生产模块以及Image363／DT389／CAMSS389未改变。

## 确认的粗级统计缺口与下一步

[当前内核实际函数与完整原固件检查](coarse-gap-validation.json)：640和650×480、双核，使用主摄实际LTM／色彩／Gamma程序，只切换DC0/1；当前编码器的striping、32B job及整个512KiB硬件命令均完全相同。代码固定一遍、只提供全尺寸输入／输出，没有建立粗级统计产出与消费的链路。该检查明确否定“dataCollectionEnabled=1即可验收DC”的假设，不是DC功能通过。

完整DC需要恢复原厂粗级处理遍次、尺寸／裁剪与缓冲区绑定，再证明粗级数据产生和全尺寸IP消费；不能仅补一个标志、读取无关scratch内容或用普通像素变化代替。保留的原厂HAL已有LTMDCStripeConfiguraion、generateLTMDCmode/outW/outH等实际函数，完整striping和固件oracle可复用。

GTM属于IFE/BPS路径，所读固定源码使用64个18bit base／26bit slope的64bit DMI；这个描述尚未等同为本机完整二进制／硬件GTM已适配。已有本机IFEGTM10::Execute与GTM10CalculateSetting符号可继续原指令验证。接入时必须把IFE的GTM参数版本和对应ADRC/LTM绑定，处理统计→后续IFE参数生效→对应图像IPE的顺序；不能把刚取得的图像统计用于声称同帧已完成的上游GTM，也不能偷偷把GTM份额清零来宣称完整。

继续优先复用现有原厂文件和仓库，先补这些真实缺口，再扩展广角／长焦／前摄和视频模式的调校与部署。前摄原厂关闭TMC保持；第五2MP身份/mux、帧长／防频闪、连续AF、多摄几何／同步等[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)不缩小。公共仅作者代码／脱敏证据，本地提交、不push。

粗级探针首轮仅因ctypes自动NUL使尾部检查多比较一字节而失败，已用精确容量修正，没有改原生实现：[保留失败](probe-r1-failure.json)。
