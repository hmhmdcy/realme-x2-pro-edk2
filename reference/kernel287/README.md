289（2026-10-19）：现机为288完整Image/778模块，四摄RAW＋CPU ISP回归234帧；本轮定位内部TPG继承C-PHY及Gamma SRAM上传缺时钟，修复候选ff8d2e9fc完整构建通过、未部署。临时硬件对照192个LUT字精确读回，黑白亮度恢复但色度仍错误，CST/统计/IPA继续；根部署锁已更新。[289证据](../kernel289/README.md)。

# 287：原厂依据、VFE175 Demux与MNDS16后端

2026-10-19。继续多摄及骁龙ISP适配，本轮将已有原厂资料转成SoC公共后端，补Bayer Demux和NV12缩放/色度抽样。**完整构建通过，未部署，仍三个RDI资源；Spectra硬件成像尚未接通。**

## 原厂资料能提供什么

原厂设备树提供接线、供电、时钟、复位、CSI/CCI拓扑和模组线索；原厂sensor/lens驱动及vendor模组文件提供模式、曝光/增益协议、镜头命令与时序。它们是适配和调校的有效起点。旧私有binding应转换为当前标准描述，不能整树直接搬入。

画质还需要黑电平、颜色矩阵、阴影、噪声、AF端点等数据。内核开源并不意味着CamX/Chromatix算法和全部调校已经开源；系统vendor中的BIN/XML、HAL和EEPROM/OTP是不同来源。参数必须匹配模组、模式、单位和当前处理链，libcamera不能直接加载原厂CamX BIN。个体校准只读保留，不作为整型号常数。[完整来源/边界](../kernel276/OEM-TUNING.md)、[原厂设备树](../../linux-port/docs/ANDROID-DT-REFERENCE.md)

已经使用：长焦S5K3M5模式和细分增益、GW1模组镜头命令及标准单次AF，另有VFE175/CSID175协议。此前用户摆好场景后的长焦曝光/增益测试及明亮预览已记在271，旧近黑样片不能继续作为最新结果；画质仍未完成。[271实测](../kernel271/README.md)、[278 AF](../kernel278/README.md)

## 本轮来源与实现

[静态核对](register-contract-validation.json)对固定本机HAL SHA e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde断言42处指令，包括FULL输出选择、使能指针链和实际Full-C尺寸字段。固定CamxChi 9f17f1b568626b393e785b369c5dc94543774d7a的六份参考已在286私存；原厂GPL内核固定9668fcdc6ec15be7a10d66f7b93c347829e0fdb6用于CSID解码交叉核对。没有执行OEM库或复制专有实现，原HAL和反汇编保持私人资料。[可重核脚本](verify-register-contract.py)、[官方内核](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)

- **Demux**：复用CAMIF的16种8/10/12/14位Bayer码识别，四种CFA路由、独立Gr/Gb/R/B unsigned15 Q10增益、两个12位黑电平；配置0x560起七字，lens 0x40 bit2。保持保留位，写完配置后屏障再使能，失败/停流只清自有使能。
- 初值全部unity1024/黑电平0，**不是已标定参数**。RAW10名称和CSID decode_format不能独立证明内部归一化应乘16；实际对齐和处理域仍待TPG/RAW验证，不用亮度补偿掩盖未知协议。
- **MNDS16**：Full-Y0xa3c、Full-C0xa68各11字，frame0x4c bit3。Y尺寸14位、C尺寸16位，相位22位/分辨率29:28，尺寸按减一编码；单stripe初相位/skip为0，pad保留bit30。
- 亮度横/纵缩放与色度横/纵二分抽样分别计算。每轴比率严格小于64，因此NV12总体亮度缩小比率须小于32。全部四轴先验证后MMIO；放大、奇数尺寸、超范围和未实现ROI直接拒绝。16384仅字段限制，不声称硬件支持该线宽；FULL输出4096限制保持。
- pixel prepare先核格式和几何，再Demux→Demosaic→Gamma→CST→MNDS→RoundClamp→WB；失败统一清理。metadata stop不关闭主图处理，RDI不访问处理寄存器。没有修改DT、固件、用户态或新增私人UAPI。

候选树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，分支samurai-vfe175-demux-mnds287，提交 **6ddf1ba4cfafe221a38cc12667a1aac06f3f9ec5**。八文件补丁从209d1ea0f在独立index重现完整tree；WB五函数和Dem/CST/Gamma/Round源码保持。补齐共用Bayer声明头的linux/types.h。checkpatch 0 errors/1新增文件MAINTAINERS提示，原CAMSS目录规则覆盖；未推送。[提交收据](demux-mnds-commit-validation.json)、[组合补丁](vfe175-demux-mnds-candidate.patch)

## 验证与未完成范围

[实际函数ASan/UBSan](demux-mnds-host-tests-validation.json)通过：Demux262144增益/131072黑电平输入，至少2048000组轴比例、NV12各轴/尺寸字段、保留位、失败零MMIO与实际17x启停；已有Gamma/CST/位深/Demosaic边界继续通过。mock prepare449次MMIO只证明软件顺序，不是硅上结果。

初次测试包装器三引号语法错误先于测试终止；首个比例用例误把63倍亮度缩小当有效，源代码正确拒绝，因为NV12色度为126倍。改用31倍有效/32倍无效边界后通过，失败日志保留，没有放宽驱动检查。原Gamma64均匀段sRGB最大模型误差约20个10位码值仍在，不宣称画质完成。

[正式Kbuild](demux-mnds-full-build-validation.json)：39CAMSS组件W=1/-Werror及完整Image/778实际ko/DTB通过，两阶段终态exit0；本轮增量诊断0，不覆盖282全新构建1140条历史warning。耗时 95.81 秒，Image 44235264 字节，SHA **89305a4ae16f5c11dabcd6f1c5514ec5b94bdf407c3df137119fab7b0bf3d547**。DTB仍dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d，config保持0c26bd91…。778实际ko逐一哈希，私存清单。

构建前核对现有E盘ext4 backing后重挂，未格式化；286六项产物按原收据另存私人kernel287/completed-depth-gamma286。最新输出/mnt/samurai-full282/build，release k279candidate+，不能混入现机k132+模块。一次性保存/构建/更新脚本已经执行，不直接重放；下次先用284/storage.py核挂载。

[现机只读检查](final-health-validation.json)：仍boot276/Image183、776模块/961包、libcamera r24/config-r19；50载荷和全部模块保持、十个加载note匹配，原Phoc/Phosh/PW/WP进程保持；四sensor/lens/双CCI/CAMSS suspended，九rails/共享I/O/clocks回收，fault0/taint0/pstore空、无CCI错误，SSC/SensorProxy正常。本轮未安装/刷写/重启/取流/调焦。

## 当前分层与升级判断

| 层面 | 已到达的位置 | 仍有的依赖/缺口 |
| --- | --- | --- |
| 引导 | 原厂XBL/ABL→BootShim→EDK2→EFI-stub Image→Linux rootfs | samurai专用启动与显示交接；发行版内核安装/DT/initramfs及回退尚未完整打通 |
| 固件 | EDK2本机资源适配、modem/DSP/Wi-Fi等固件可用 | Qualcomm/OPPO二进制仍必需；本机完整ACPI/持久变量未完成，Linux主要用DT |
| 硬件描述/板级 | SM8150公共描述＋RMX1931 DTS/sensor dtsi；接线、供电、方向逐步归DT和设备包 | DTB仍随boot固件打包；部分实验供电/策略及bring-up ignore_unused待继续收敛，不能称全树标准binding验收 |
| 内核/SoC/驱动 | 固定主线7.3-rc6基础上维护驱动；公共CCI PM、PM8008 MFD/regulator、sensor/lens和CAMSS后端已有修复 | 生产树29本地提交/134改动文件；ISP候选40提交/175文件，含未部署功能。源码在树内和个人fork发布均不等于上游接受 |
| 用户空间 | V4L2/MC/libcamera/PipeWire/GStreamer/桌面公共接口；四摄有RAW/CPU成像、主摄单次AF实测 | libcamera配方28补丁含既有发行版补丁，PipeWire另6项目补丁，Mesa/MM/GeoClue/libssc亦有适配；Spectra pipeline/IPA、完整画质/GUI录像/Continuous AF未完成 |

生产树仍camera270-kernel/samurai-cci-io276/0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8。上表Git规模相对固定a90ee4305c4a5df72c11b31dacfdc76e00fcf78a，2026-10-19本次读取；不以行数评价质量，也不把候选等同现机整套统一Image。270审计的25提交/23个libcamera补丁是历史数值。[历史审计与具体收敛](../kernel270/LAYERING-AUDIT.md)

[本轮分层收据](layering-validation.json)重新读取两棵源码树、包配方与现机：EFI和DT均存在，/boot为空，clk_ignore_unused、pd_ignore_unused、regulator_ignore_unused仍在实际启动参数中。说明整机仍依靠bring-up资源保留策略，驱动自身休眠回收通过不等于整机电源依赖已经收敛。

**有实质底层收敛，但尚不支持无补丁主线更新。** 公共驱动PM与生命周期修复、标准芯片驱动、板级DT、设备调校数据的分工已经推进；未上游的代码仍须随版本维护，内核也不承诺内部模块ABI稳定。[内核官方说明](https://docs.kernel.org/process/stable-api-nonsense.html)

普通包曾完成55包升级/3新依赖，不证明关键栈任意更新。接近最小补丁需要通用修复进入内核/libcamera/PipeWire等上游，设备差异留在标准DT/固件/调校包，并以新内核、配套关键包、冷启/PM/硬件回归证明。当前新内核与rootfs整套统一部署未闭环，不能承诺未来只换发行版内核即可保留全部功能。

下一步先评估最小PIX/FULL与内部TPG验证闭环，验证IPP/CAMIF、输入域、DMI和Y/C输出，再扩展真实统计/参数、GTM/CC及libcamera pipeline/IPA；不必等全部算法完成才做第一张硬件图。四摄GUI/录像、AF加速/Continuous/距离标定、Shine OV02A1B接入及统一Image/rootfs继续；GPU默认故障/CPU回退和旧modem watchdog仍开放。完整目标保持active。
