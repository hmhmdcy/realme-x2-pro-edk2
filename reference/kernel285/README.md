# 285：VFE175 CST12色彩转换后端

后续[286](../kernel286/README.md)已新增Gamma16/FULL输出位深，候选209d1ea0f完整构建通过；仍未部署或开放PIX。本文Gamma/round-clamp未实现及285最新输出按当时阶段阅读。

2026-10-19。继续完整多摄和骁龙ISP目标。本轮落实CST12及启动/停流集成，已完整构建；**未部署、未开放PIX，也未取得Spectra硬件成像。** 现机仍boot276/Image183/r24/r19，经本轮只读检查保持。

## 来源及硬件事实

先复核af9e2a023候选HEAD/干净工作区和284完整构建终态，再开始新分支。检索并复核既有[公共IFE参数系列](https://lists.openwall.net/linux-kernel/2026/10/07/534)和[SM8250参数应用方案](https://lkml.iu.edu/2610.0/12010.html)。继续使用公共输出/参数架构，但没有将不同硬件的OPE参数或其它IFE地址套进175 CST。

[CST12静态核对](cst-oem-contract-validation.json)对本机原厂HAL SHA e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde的实际ELF字节重新断言：0xf30起12字、系数有符号13位Q10、offset11位、clamp10位，calc+968 bit0通过实际指针写0x4c。不是Gamma的0x48，也不是根据结构字段顺序猜使能地址。可重核[脚本](verify-cst-contract.py)。

原厂默认三行系数槽位为(601,117,306)、(-338,510,-172)、(-427,-83,510)，支持G/B/R槽位推断；**物理顺序仍待硬件彩条/RAW验证**。本轮按标准公式独立推导矩阵，没有复制原厂实现或把该默认配置宣称为模组画质标定。[标准色彩公式](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/colorspaces-details.html)

原厂BIN/反汇编和带专有声明的布局参考保持私存，公开的是互操作事实、来源元数据及新写的GPL驱动。无OEM二进制执行、无OTP或校准写入。

## 实现及分层

候选树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，分支 **samurai-vfe175-cst285**，提交 **d1a5f84405cfa774765e9b8ffabd6d1533dec2b6**，父af9e2a023。[补丁](vfe175-cst-candidate.patch)、[提交和补丁重现](cst-commit-validation.json)

| 层 | 实际变化 |
| --- | --- |
| SoC后端 | 新CST12内部配置/格式转换/停流函数，仅SM8150 full VFE175；Lite、其它SoC及无效参数在MMIO前拒绝 |
| 格式与数学 | 从实际NV12格式的ycbcr_enc/quantization选择BT.601或BT.709、full或limited；DEFAULT按V4L2规则解析。四组Q10矩阵保持中性轴Cb/Cr精确为零 |
| 数值范围 | 10位非线性RGB输入；limited Y为64…940、Cb/Cr为64…960并以512为中心；full为0…1023。所有9系数、offset、min/max先完整检查，再写任意行 |
| 寄存器 | RGB语义配置转换为硬件G/B/R槽；读改写保留每字非所属位。输入offset固定0；不支持尚未验证的非零输入减法。12配置字→屏障→0x4c bit0，无提前PIX RUP |
| 生命周期 | pixel prepare先拒绝不支持的色彩格式，再Demosaic→CST→中性WB。主FULL停流及enable失败清CST/Demosaic使能；辅助metadata停止不关闭主处理；RDI不进入CST |
| 板级/用户空间 | 无DT/固件/应用变更，无新UAPI、私有寄存器节点或用户态协议。现有三个RDI资源保持 |

此矩阵完成RGB到YUV编码，**不承担传感器CCM、色域转换、Gamma或模组画质算法**；前级必须交付匹配的非线性10位RGB。当前公共camss-video协商仍固定sRGB/601/full，本轮按它实际返回的full配置；没有静默改掉所有RDI格式的色彩声明。后续开放PIX时还须完善格式协商并与Gamma/CC处理匹配，四组内部矩阵通过测试不等于用户态已可选择全部配置。

## 验证与构建

[实际源码主机测试](cst-host-tests-validation.json)使用当前内核导出的V4L2 UAPI及实际CST、Demosaic、WB、17x enable/stop函数，ASan/UBSan通过：9字段各65536个有符号系数输入，9个offset/clamp字段各65536个输入，min>max、保留位、配置/屏障/使能顺序、DEFAULT/JPEG/不支持编码与量化、RDI/Lite/其它SoC隔离、主/辅助输出停流及失败回滚。MMIO为模拟，不能证明物理槽位、硬件舍入或画质。

独立以ITU浮点方程核四种矩阵各33³个RGB点，共143748点；系数近似最大误差 **0.871519/1023**，不含硬件舍入。每种矩阵全部1024个中性输入的色差和精确为0。初次测试直接包含未导出UAPI导致缺compiler.h，改用内核headers_install工具后旧mock重复定义__counted_by被Werror拒绝；删除多余mock定义后通过，两份初始失败日志私存。产品源码没有靠关闭内核告警通过。

[正式完整构建](cst-full-build-validation.json)91.75秒终态exit0：35个CAMSS组件W=1/-Werror及完整Image/778实际ko/DTB两阶段均成功，本次增量构建诊断0。没有将此结果宣称为全树从头无warning；282初次全编译的历史1140条warning继续保留。

- Image44235264字节，SHA **5ff0a3d2583c15ecc316c19d7e30b7a20d401eba1ad540f8cf1ba37596575909**。
- DTB114556字节，SHA仍 **dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d**；config也逐字保持。
- modules.order的778个`.o`项目均按Kbuild映射到实际`.ko`并哈希。模块清单私存，不能把对象文件当模块。
- 五个WB函数和Demosaic源码与父提交逐字一致。独立index应用补丁重现完整tree，原工作区/index干净，未推送。
- checkpatch 0 errors/1通用新增文件MAINTAINERS警告；现有CAMSS目录条目覆盖。

构建前仅通过284/storage.py核backing并恢复已有E盘loop；没有格式化。先逐项校验并另存284 Image/DTB/vmlinux等六项到私人`kernel285/completed-demosaic284`，282基础完整778ko归档继续保留。最新输出为`/mnt/samurai-full282/build`，release仍 **7.3.0-rc6-rmx1931-samurai-k279candidate+**，与现机k132+不同，部署须配套Image/模块，不能单独混装CAMSS ko。构建会话34473已终态，无待续编译；PID588/784/1949只属于该次进程，不作后续活任务凭据。

## 现机与续作

[本轮只读健康检查](final-health-validation.json)证明仍776模块/961包、50载荷及全部模块保持、十个加载note匹配；原Phoc/Phosh/PW/WP进程保持，四sensor/lens/双CCI/CAMSS休眠，九rails/共享IO/clocks回收，fault0/taint0/pstore空、无CCI错误，SSC/SensorProxy正常。本轮无刷写、安装、重启、拍照或调焦。运输用[host.py](host.py)，始终保持276 guard。

下一步位深证据已取得：[RoundClamp路径](next-round-clamp-facts-validation.json)的实际HAL跳转表证明VideoFullPath=0走0x333910，Y寄存器对0xe18/0xe1c、C对0xe38/0xe3c。匹配布局参考提示输出8/10位，round bits为10-output bits，clamp取输出位深；**不能将CST的10位端点直接填入8位输出clamp**。RoundClamp尚未实现，继续核实际位域/顺序及输入Demux/Gamma/GTM/MNDS。Gamma64/65节点、DMI选择和GTM初步事实保留在私人kernel284；不要将OPE256×u8 LUT直接当175 native64-word LUT。

完整ISP仍缺前级位深/Demux、Gamma/CC、MNDS/round-clamp、真实统计和参数、libcamera pipeline/IPA及TPG/RAW硬件回归。继续四摄GUI/录像、AF加速/Continuous/距离标定、画质、Shine OV02A1B确认及统一Image/rootfs；GPU/modem watchdog等旧开放项保持。当前仍RAW→CPU ISP，完整目标active，不声称免补丁升级或相机适配完成。

本目录implement/save/build脚本已执行且有一次性状态保护，不直接重放；主机测试和静态核对可按当前源码重跑，脚本会保留前次失败日志。
