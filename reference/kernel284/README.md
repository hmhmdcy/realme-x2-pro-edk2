# 284：匹配 Demosaic36，完成候选内核与模块链接

后续[285](../kernel285/README.md)已完成CST12内部后端、正式完整构建及本轮现机只读复核；当前候选d1a5f8440，仍未部署或开放PIX。本文CST待实现及af9最新输出按284阶段阅读。

2026-10-19。完整多摄及骁龙ISP目标保持active。上轮283有实际WB源码/测试进展；本轮继续按原厂和现有方案补去马赛克，并将对象候选落实为完整Image/模块。**尚未部署新内核、开放PIX或取得硬件ISP图像，目标未完成。**

## 完整构建与可恢复产物

先通过原exec会话29220核到282 r3真实终态exit0，1900.76秒，固定18b源码干净。Image/DTB/vmlinux/Module.symvers/modules.order生成成功。随后保存Image等七项及全部实际778个`.ko`，归档内每个模块再读出验证SHA。[完整构建和归档](base-full-build-validation.json)

原282脚本只检查modules.order所列文件存在，而当前Kbuild清单使用`.o`后缀；它不能独自证明`.ko`齐全。本轮最初归档拒绝该后缀，按Kbuild规则逐一映射到`.ko`后，实际778载荷均存在并通过归档校验。未把对象文件冒充模块。最初32字节空tar保留，完整归档为私人`kernel284/completed-base282/modules-verified.tar.gz`，36214047字节，SHA c1fe1e8e4fa57ed84e63263b371bd53b851e3e045d0840d220c2e395713fc850。

282从头W=1构建有1140条warning、0条error，CAMSS诊断0：1098条override-init，34条其它，6条format-truncation、1条format属性建议、1条未使用函数。原日志及分类保留，不称全树零warning；没有据当前观察声称这些告警已修复。

归档完成并核原进程终止后，正常checkout283 WB提交97a4c5638，再走正式Kbuild：CAMSS W=1/-Werror及完整Image/modules/DTB两阶段均通过、无新增诊断，实际778个`.ko`全部哈希。[WB完整构建](wb-full-build-validation.json)。随后才开始本轮Demosaic源码修改，不在运行的编译中混入源码。

## 原厂实际选择与已有资料

283已固定Qualcomm的[45补丁IFE系列](https://lists.openwall.net/linux-kernel/2026/10/07/513)，模块/参数框架继续作为公共方案参考；SM8250模块地址与本机不相同，不直接套用。原厂本机HAL SHA e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde。

本轮补齐此前未定的Demosaic版本选择：原厂Titan175枚举0x10705分支将平台mask2写入node+0xa9ec；53项模块表以descriptor+8与该mask相交。Demosaic36 descriptor mask3匹配，Demosaic37 mask4不匹配，故本机选 **Demosaic36**。相邻1920是另一能力字段，本轮最初“应为4920行宽”的假设被实际字节否定，没有作为驱动尺寸上限。[二进制指令/数据核对](oem-pixel-contract-validation.json)、[可重核脚本](verify-oem-pixel.py)

按本机实际指令恢复Demosaic寄存器和保留位：config0x6f8拥有mask0xb13；lambda G/RB分别位15:8/31:24；classifier W为低10位有符号，A为31:20，匹配原算法限0…400；lens enable为0x40 bit10。字段顺序另以匹配XSD的八个float及本机加载/打包指令交叉核对，lambda G/RB对应关系保持。原厂bring-up默认三字0x100/0x8000/0x08000066只用于初始硬件配置，**不作为模组/场景画质标定**。

同时核到CST12基础互操作事实：0xf30起12字、系数有符号13位Q10、offset字段11位、clamp10位、使能0x4c bit0。最初按顺序推断的0x48已被最终指针→寄存器链否定；CST calc+968写0x4c，而Gamma calc+964写0x48 bit3。未按错误推断实现驱动或写硬件。其实现仍待做，不能将OPE现有Q8分段色彩参数直接当作175 CST矩阵。通过固定版本的CamxChi头/模块文件作布局交叉参考，最终位域仍由本机HAL核对；原厂实现、反汇编和参考原件均私存，没有复制闭源实现或引入OEM运行库。

## 本轮源码与分层

当前候选树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，分支 **samurai-vfe175-demosaic284**，提交 **af9e2a02365a2ec1a19d3cc42da5c65e84c244c4**，父WB/97a4c5638。原生产维护树仍276版本。[补丁](vfe175-demosaic-candidate.patch)、[提交/逐文件哈希](demosaic-commit-validation.json)

| 层 | 实际修改 |
| --- | --- |
| SoC处理后端 | 新VFE175 Demosaic36配置/prepare/stop；只支持SM8150 full IFE，拒绝Lite/其它平台；lambda、classifier先校验，再MMIO；保留所有非所属位 |
| 配置与使能 | 写config/lambda/classifier，屏障后才更改lens bit10，不提前发PIX RUP；使用未校准bring-up默认，仍需IPA调校承载 |
| 生命周期 | pixel prepare返回错误；启动失败清模块使能；主FULL输出停止时清理，辅助metadata停止不关主模块；RDI保持零处理寄存器写入 |
| 原有WB | 五个WB转换/校验/写入/apply函数逐字匹配283父源码；prepare在Demosaic成功后初始化WB，既有typed参数语义保留 |
| 板级/固件/用户空间 | 无修改；板DTB保持，仍三个RDI，不开放PIX，不增加应用私有协议或任意寄存器接口 |

CST/CC、输入Demux/位深、gamma、MNDS/round-clamp、统计及pipeline/IPA仍未完整实现。Demosaic和WB源码/链接成功不等于整条硬件成像已可用。

## 验证与限制

- [实际Demosaic/pixel及17x enable/stop主机测试](demosaic-host-tests-validation.json)ASan/UBSan通过：W/A分别遍历全部65536个16位输入，lambda完整0…255、64种模式、保留位、配置→屏障→使能顺序、RDI/Lite/其它SoC拒绝及零MMIO、主输出与metadata停流区分、取output失败、prepare失败及enable失败回滚。
- 测试MMIO是模拟；不能证明本机颜色、插值质量、硬件时序或电源消耗。尚无新硬件采集。
- [Demosaic最终正式Kbuild](demosaic-full-build-validation.json)：34个CAMSS组件W=1/-Werror及完整Image/778模块/DTB两阶段成功，当前增量构建无诊断。Image SHA **455d08bc6da428893ea27f9386561bcb682c011535d5152fed392210b0b264d8**，DTB仍dcdd74ec…。[组件数、实际ko和九项相机模块vermagic](candidate-artifacts-validation.json)
- 候选release **7.3.0-rc6-rmx1931-samurai-k279candidate+**，与现机k132+不同，后续部署须配套Image与模块，不混装单个ko。最新候选输出在E盘ext4卷`/mnt/samurai-full282/build`。
- checkpatch零error、一条新增文件MAINTAINERS提示，现有CAMSS目录匹配覆盖。独立index应用补丁重建tree匹配；五个WB函数和原index/工作区干净复核。[补丁重现/WB保持](patch-and-wb-preservation-validation.json)
- 初次主机mock把三参数wm_stop写成两参数，编译拒绝；原harness/log保留，修正后通过。最初未挂载构建卷的保存尝试在读取前终止，后来仅重挂既有镜像，没有格式化。[保留失败](initial-failures-validation.json)

## 主机存储、现机与续作

C盘在WSL运行时余量曾降至约327MB。已把npm下载缓存12394文件、5246694179字节完整迁至E盘私人目录保留，迁前核路径/reparse/无活动包管理器，迁后核文件数/总字节；没有删除缓存或更改已安装运行时，C盘随后约7.6GB可用。[存储记录](host-storage-validation.json)。282已保存的pip缓存继续保留。

[现机只读检查](final-health-validation.json)：仍boot276/Image183、776模块/961包、libcamera r24/config-r19，50载荷和全部776模块保持、十个加载note匹配；桌面/PW/WP原进程保持，四sensor/lens/CCI/CAMSS休眠、九rails及共享I/O/clocks回收、fault0/taint0/pstore空、无CCI错误，SSC/SensorProxy正常。本轮无手机安装、刷写、重启、新拍照或调焦。

本轮构建、归档、缓存迁移、测试和只读采集均已终态，没有待续的r3/WB/Demosaic构建；原r3会话29220已退出，PID会在WSL重启后复用，不能再凭旧592/794推断有活任务。续作从af9干净候选继续，先用`storage.py`核backing并恢复已有loop挂载，不能向空挂载点写产物。非幂等prepare/commit/build步骤不要直接重放。

下一步继续CST/CC、位深/Demux、gamma、MNDS/round-clamp及真实统计/参数，连接libcamera pipeline/IPA后以TPG/相机RAW对照验证硬件像素。再做四摄GUI/录像、画质、AF加速/Continuous/距离标定、第四颗物理后摄确认与完整Image/rootfs回归；GPU及旧modem watchdog开放范围保持。当前仍RAW→CPU ISP，不承诺免补丁升级。私人CST字段/下步线索见kernel284，运输用[host.py](host.py)并保持276 guard。未推送；目标继续。
