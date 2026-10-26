# 295：VFE175 BHIST 有效计数、实景曝光响应与首包缺陷

2026-10-19。当前实机 **#295 / 7.3.0-rc6-rmx1931-samurai-k295+**，源码 `samurai-stats295` / `d249946aefa1a01d99fd5484825a4458423b7348`。完整 Image 与独立778模块已部署并读回，加载模块 build-id 与磁盘一致；boot276、DTB、原厂固件、961个包和50个相机载荷保持。多摄及骁龙ISP目标仍 active，**统计首包、BLC、IPA和完整画质未完成**。

## 实际结果与限制

| 验证项 | 实测结论 |
| --- | --- |
| BHIST 稳定帧 ROI | S5K3M5真实CSI图案2，2104×1560；全幅820560、半幅410280、最小4×2区域2，10个统计阶段稳定帧均精确匹配。共99图像/90统计包。[定量证据](statistics-pixel-validation.json) |
| 统计生命周期 | 图像关闭/重开但统计队列保持，以及图像继续时统计停止/晚启动；三个buffer均重新出现，图像不被独立统计启停破坏。 |
| WB参数及帧号 | 10类非法包拒绝、7次混合参数完成；QBUF后改用户buffer不影响快照；11阶段最大颜色通道误差<1.235。五次可观察变化首帧10/19/28/37/55与PARAM_DQ一致。[颜色](stats-pixel-validation.json)、[帧号](frame-association-validation.json) |
| 广角实景 | IMX319，1632×1224，图案全部关闭，曝光500→3000→500；18图像/18统计包。图像Y均值74.8023→92.1108→74.8024；稳定统计均值bin71.4364→110.6519→71.4400、人口均499392。[图像](optical-pixel-validation.json)、[统计](optical-statistics-validation.json) |
| 私人预览 | 已查看曝光3000的本机样片，能辨识边缘与场景结构，仍暗、偏绿，未校准BLC/AWB或完整IQ；私人像素不进入公共文档。[复查](optical-review.json) |
| 四摄产品路径 | 原有libcamera RAW＋CPU ISP：18段237帧，主摄SIGINT33帧后重开12帧通过。主/前摄硬件ISP路径仍未验收。[回归](four-camera-regression-validation.json) |
| 启动与资源 | 当前桌面、SSC、SensorProxy默认启动成功，三个代理能力存在；未重试SSC、未临时nodeps。camera/lens/CCI/CAMSS均suspended、9路供电及共享IO关闭、MCLK/CCI时钟0、fault0/taint0/pstore空；Wi-Fi/HCI、modem/adsp/slpi正常。[最终检查](final-health-validation.json) |

**首个统计包仍不可靠，统计功能尚未完整验收。** 长焦第一次启动sum17567538901、图像重开后的首包1160356，预期均820560；广角实景首包17552007722，预期499392。它们被驱动以正常状态返回，后续稳定帧恢复正确。统计晚启动的首包本次正常。不能将只检查稳定帧的旧 `passed=true` 晋升为全部统计有效：原稳定帧报告保留为 [stable-only历史](statistics-stable-only-validation.json)，[当前统计验收](statistics-pixel-validation.json)明确 `passed=false`、`ready_for_automatic_exposure=false`。

接下来需处理统计RAM初始化/第一份有效数据的时机与错误标记，保留首包负对照，再推进IPA；不把无效首包丢给用户态AE自行猜测。当前尚未证明统计与图像严格SOF对应，队列饥饿/合并IRQ、多参数request及多模式长期运行也未验收。WB五次颜色变化的帧号证明有独立、有限的范围。

## 原厂参考如何帮助了这次修复

[294](../kernel294/README.md)新增统计通路和通用metadata回收后，所有bin为零。初次HAL指令解读误把RS使能bit5当作BHIST；此次补齐固定公开Camx端口枚举和UINT32 path布局，再核对本机原厂HAL，确认BHIST端口16/偏移64→`0x44 bit4`，RS端口12/偏移48→bit5。[独立证明](../kernel294/enable-correction-validation.json)

本轮修复落在VFE175 SoC驱动，一行更正使能位；原有RMW会保留RS位。新的独立bit合约使真实旧函数失败，修复函数通过ASan/UBSan及10万ROI测试，图像重启/部分启动失败回收也通过。未修改板级DT、固件、UAPI或产品用户态包；#295所有采集均使用标准MC/V4L2队列，没有用户空间MMIO写入。#294只读诊断另行保留，未执行原厂二进制或复制原厂实现。

原厂DT/内核适合提取供电、GPIO、时钟、CSI布线、传感器模式和寄存器协议；HAL/Chromatix与本机EEPROM/OTP可能提供调校和模组校准。**DT本身不能提供完整画质**，也不能直接把Android厂商驱动/私有ABI搬成主线适配；其它手机的调校XML未作为本机参数使用。公开资料、私有工厂载荷、每台机器校准的用途与来源分别保留。

## 项目目前在哪一层

| 层面 | 当前状态与更新边界 |
| --- | --- |
| 引导 | 原有boot276/EDK2＋UEFI链，logdump FAT载入主线派生Image与DT；EFI存在，/boot为空。两次受控正常切换分别部署294、295，只刷logdump；不是发行版通用安装/自动内核升级已经验收。 |
| 固件 | 保留现有原厂固件、NV与校准；主线驱动调用固件不等于固件开源。本轮固件未更新。#293 SSC EPERM根因仍未关闭；294/295默认启动成功只证明这两次结果。 |
| 硬件描述/板级 | Realme接线、供电、复位及模组描述通过DT和标准consumer表达；原有板级启动/服务配置仍存在。clk/pd/regulator三个ignore_unused仍在，不能据局部相机PM通过声称全机电源已经收敛。 |
| 内核/SoC/器件驱动 | 7.3rc6基础之上有本地SoC和器件适配，包括本次通用metadata生命周期、VFE175统计及使能修复。实际树相对base为52本地提交、177改动文件；本地提交不代表上游接受。 |
| ISP/用户空间 | 标准V4L2排队＋项目树中的typed CAMSS参数/统计ABI，参考公开RFC，尚不能据此声称接口已获上游接受。tele/wide硬件NV12/WB/稳定BHIST已做实验；产品应用仍RAW＋CPU ISP，硬件pipeline/IPA未集成。 |
| 升级可维护性 | libcamera配方28补丁（含发行版既有补丁）、PipeWire另6个项目补丁；没有本轮跨新内核、全rootfs或关键包升级验收。**目前不能承诺零补丁或最小补丁更新**。[只读分层审计](layering-validation.json) |

底层收敛已发生，但仍需修复首包有效性、BLC、主/前摄硬件路径、模组调校、AF Continuous/距离映射、Shine OV02A1B、GUI录像与长稳；GPU默认路径故障、旧modem watchdog和整机功耗问题未结案。本轮 `checked_runtime_healthy=true` 仅覆盖所列当前检查，`whole_system_healthy=false` 保留。

## 构建、回退与续作

完整构建148.55秒，五阶段诊断0、40个CAMSS组件严格编译通过、778模块vermagic/depmod一致、3个嵌入BT模块与安装树一致。[构建](boot-candidate-build-validation.json)、[封装](boot-package-validation.json)、[启动读回](postboot-identity-validation.json)、[失败记录](preparation-notes.json)

Image SHA `39a3d712e7927a850b7e7a92d3181a407339026dd73d0dd62e415279176664d9`；logdump `ddd66658c711ff45efc0e578e291affc98a1301f8700d7bb88e47af7bc95b0b6`；config `f084bcf761c222cb77ea00ecd26b944f40401de8abc9a71b308c4d0a9963871a`。输出 `/mnt/samurai-full282/build`，先用284/storage.py核对backing并挂载；input-initramfs295/modules295。

运输用本目录host.py和 `/var/lib/samurai/k295-work/boot-id-private.txt`；按driver/entity发现总线节点。294 R2六产物已核对保存在私人kernel295/completed-boot294-r2，294及293/292/290等独立模块树保留。稳定回退首选#290镜像SHA `0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a` 和原778模块；未做回退往返。本轮所有构建、切换和采集已终态，勿盲目重放已完成脚本。
