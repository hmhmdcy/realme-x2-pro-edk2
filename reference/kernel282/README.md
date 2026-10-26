# 282：复用多流修复，补 VFE175 FULL 双平面输出

后续[284](../kernel284/README.md)已核282 r3完整构建终态、验证归档实际778ko，并checkout WB完成正式Kbuild及Demosaic36候选完整链接；本文构建运行/未checkout等描述按当时阶段阅读。

2026-10-19（本轮跨午夜）。用户已将目标明确为：继续多个摄像头及骁龙ISP适配，**直至适配完成**，优先现有方案并按SoC／板级／公共驱动／用户空间收敛。281已补CAMIF；本轮补公共多流修复和175 FULL输出源码，并启动完整Image／模块构建。**完整硬件成像、统计与pipeline/IPA仍未接通，目标保持active。**

## 现有方案与适用范围

检索到Hitesh Patel发布的2026-09-28 v5 CAMSS多摄修复系列。原帖的RB3 Gen2／CSI桥实测不是本机实测，但相关公共17x问题在本地候选源码中可直接核对：

| 原帖 | 本项目处理 |
| --- | --- |
| 1/6：write master buffer DONE被过滤 | 原候选先读/清BUS状态，却只在无关top IRQ bit9存在时处理DONE；已去掉该门控，按BUS状态处理。[作者原帖](https://lists.openwall.net/linux-kernel/2026/09/28/1471) |
| 2/6：RDI写主机选择 | 279已使用vfe_get_output_v2，RDI n固定到client n；不重复套补丁 |
| 3/6：另一条流仍运行时重置整个VFE | 停止只关闭本线路输出；stream_lock内最后一次递减才复位，阻止复位期间启动新流。[作者原帖](https://lists.openwall.net/linux-kernel/2026/09/28/1534) |
| 对3/6的维护者审阅 | 按建议把只停止WM的helper改void；未把“审阅通过”写成已经合入上游。[维护者反馈](https://lists.openwall.net/linux-kernel/2026/09/28/1669) |
| 4/6及CSI桥发现/端点链接 | 未纳入本次两个修复；当前本机直连sensor与桥聚合拓扑分别处理 |

Patchew在WSL和Windows均超时，lore raw返回403；随后从可访问的原始邮件镜像取得两个作者帖和审阅，固定HTML/解码文本SHA256。没有执行下载脚本或把其它平台的测量算到本机。[来源与适用性](existing-solutions-validation.json)。`research-multistream.py`保留最初未完成下载路径，成功收集使用`pin-posted-fixes.py`；不存在需要等待的下载进程。

公共修复独立提交 **`2985ef200e4ae28d567f5919a4d8657ac0559b65`**，父281/`21facb9a7941ecd0a624a9e4fccd9ae544dde7b5`。[补丁](multistream-prerequisites.patch)、[提交](prereq-commit-validation.json)。没有复制已存在的固定RDI映射，也没有改板级DT。

## VFE175 FULL 输出源码

继续按281固定的realme官方GPL内核 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 中`cam_vfe175.h`／`cam_vfe_bus_ver2.c`实现，不套用780的packer或地址移位。新增输出候选提交 **`18b48939788bc7f95fb2999ea986846a67f0c62c`**，父2985；分支 **`samurai-vfe175-output282`**，目录仍 `/home/cy122/x2pro-linux/camera279-isp-kernel`。[补丁](vfe175-output-candidate.patch)、[最终源码哈希](candidate-commit-validation.json)

| 层 | 实际修改 |
| --- | --- |
| SoC资源／板级 | 沿用281两个full IFE的显式175 ops；仍三个RDI，没有开放PIX节点。DTB、供电接线及固件无修改 |
| 175输出后端 | FULL固定Y/C client3/4，NV12 packer0xe，Y全高/C半高，独立stride/frame increment、byte address不右移、关闭UBWC、group0完成掩码。启停只改自己拥有的字段，保留其它client状态 |
| 数据与边界 | 按OEM单个FULL的4096×4096上限，验证偶数尺寸、16字节stride、足够sizeimage及固定描述符。当前仅支持单IFE的一个FULL NV12输出，不暗示双IFE合成、DS或统计已完成 |
| 公共捕获准备 | 在SG映射与plane容量检查后调用可选prepare_dma_buffer，检查连续Y/C布局、地址对齐及最后一个字节都位于32位DMA窗口内。metadata原prepare_buffer保持独立，未增加用户态私有协议 |
| 完成与缓冲 | 17x处理全部六个composite组；PIX走公共group完成/缓冲回收，Y/C不分别派发RDI DONE，避免一图完成两次。RDI/Lite RDI3仍走独立完成路径 |
| 公共输出适配 | 175输出callbacks对RDI委托原WM函数；PIX按独立Y/C高度处理，不使用合计行数的line_based高度上限 |
| 用户空间 | 未改libcamera／PipeWire／应用；标准typed参数/统计与pipeline/IPA仍待接入175处理后端 |

这次把280的IPP、281的CAMIF之后需要的FULL传输部分写进了驱动，但**尚未配置全部成像模块或获得硬件NV12图像**。当前资源不会把这段不完整处理链暴露给应用。原厂HAL和反汇编仍在私人目录，本补丁没有引入闭源库或任意寄存器用户接口。

## 验证与失败

- 公共修复先以281父源码作负对照：实际ISR遇到BUS-only DONE不回调；两条流中停止第一条会复位并清掉另一WM。修复后实际ISR／stop／disable函数在ASan/UBSan及真实pthread锁下通过：BUS-only DONE、保留peer、最后一次复位、复位失败返回、双WM停止、同时停止只复位一次、复位和新enable互斥。[负对照与最终测试](multistream-host-tests-validation.json)
- 新后端按OEM逐项核对26个client寄存器地址、单FULL尺寸和packer。实际后端、公共capture prepare、17x ISR及公共buffer retirement在ASan/UBSan下通过：非法描述/格式/stride/size拒绝、32位最后字节边界、capture hook时序、两个plane仅完成一次、pending补充/耗尽、迟到和无关组中断、Lite RDI3、RDI适配器逐次寄存器写入与旧函数完全相同、PIX高度策略。[输出测试](full-output-host-tests-validation.json)
- 所有测试的MMIO是主机模拟；并发测试是真实锁，不能替代本机硬件并流、DMA或画质验收。当前硬件资源仍未开放PIX。
- 公共修复31组件、输出最终32组件ARM64 `W=1 KCFLAGS=-Werror`构建通过、零诊断，DTB保持。这里是聚合对象构建，完整Image／模块结果另计。[公共构建](prereq-build-validation.json)、[输出最终构建](output-final-build-validation.json)
- checkpatch公共修复零error/warning；输出零error、一条通用新增文件MAINTAINERS提示，已确认现有CAMSS目录匹配覆盖新文件。[输出检查](output-checkpatch-validation.json)
- 初次公共负对照测试器包含只用于新代码的未使用mock，Werror拒绝；输出测试器缺vb2_queue字段也先编译失败，均保留初稿/日志并修正，随后通过。[公共测试器失败](initial-host-failure-validation.json)、[输出测试器失败](output-initial-host-failure-validation.json)
- 输出准备脚本首次因capture/metadata有相同代码后缀而断言失败，只改到本轮Makefile/header；保存两文件差异并核对归属后恢复，改为限定capture函数再成功。没有在半修改状态运行构建/设备动作。[源码准备失败](output-initial-source-failure-validation.json)

## 完整构建与配置纠正

为补齐对象构建之外的链接／模块一致性，开始对固定18b489397完整构建 `Image modules qcom/sm8150-samurai.dtb`，3并发、W=1。首次复核发现配置漏启用已支持的S5K3M5长焦，于是核实原make PID／父进程／命令后SIGTERM，原会话已确认终态-15；核无残留构建进程再修改配置。首次运行不是成功的完整构建，保留1053条未分类诊断、相机诊断0和原日志。

`olddefconfig`后仅有一项差异：`# CONFIG_VIDEO_S5K3M5 is not set`→`CONFIG_VIDEO_S5K3M5=m`，其余保持。更正配置SHA **`0c26bd9147ac31b92d824b8dbd529384772be3c8ae819314240cdd6cbde3a6ca`**，九项相机驱动配置全部为模块。[配置纠正](full-config-correction-validation.json)、[相机fragment](camera-config.fragment)。完整配置和原有嵌入bootconfig私存，后者只有display/radio追踪配置且未改，输入已固定哈希。[嵌入输入](embedded-build-input-validation.json)

更正后的r2曾启动，但在1025秒后因编译器读取Xen/mac80211源码发生`Input/output error`而终态exit1，不是成功构建；相机诊断0。随后Windows C盘实际剩余0字节，WSL VHD位于C盘，WSL启动也报错。[r2失败](full-r2-failure-validation.json)、[原启动记录](full-r2-build-start-validation.json)

已将1419个pip下载缓存文件共3725983899字节完整迁到E盘私人目录保留，以文件数/总字节数核对；C盘释放约3.7GB，WSL恢复启动。重新读取并核对本轮7个源码文件及先前报错的2个文件，均匹配提交内容，Git源码干净。原源码和旧构建目录保留。

为使编译产物不再占用C盘VHD，独占新建E盘32GiB普通文件 `E:/edk2-samurai-out/kernel282/full-kernel-build282.ext4`，核类型/路径/新建状态后仅格式化该新文件，挂载为独立ext4构建卷并验证loop backing。新的输出为 `/mnt/samurai-full282/build`，临时目录也放卷内。[存储恢复与源码核对](build-storage-recovery-validation.json)

**r3完整构建已从固定18b489397重新启动**，配置仍为纠正后的同一SHA；当前只证明启动，未把它记成完成。[r3启动收据](full-r3-build-start-validation.json)。原会话29220，当前worker592/make794；进度marker为私人`kernel282/full-kernel-r3-build-state-private.json`，日志为私人`kernel282/full282-r3-w1-private.log`。WSL空闲重启后loop挂载会消失，worker会先核对已有镜像和backing再挂载，不能向未挂载的空目录误写产物；没有再次格式化镜像。先核原句柄/真实进程，观察超时不另起构建。完整构建使用固定源码，后续改处理模块前先核原任务终态，避免混合产物。

## 现机与继续完整目标

本轮尚无新驱动部署、刷写或重启，也没有新相机采集。现机仍boot276/Image183、r24/r19、776模块/961包；最终50载荷和全部776模块保持，十个加载note匹配，原桌面/PW/WP身份保持；四sensor/lens/双CCI/CAMSS suspended，九rails及共享I/O OFF/users0、六相关时钟0，fault0/taint0/pstore空、无CCI错误，SSC/SensorProxy正常。[现机检查](final-health-validation.json)。生产维护树仍干净0d6927612，未将候选当作已经上机的修复。

继续核完整构建结果与诊断，补VFE175模块使能、定点参数、去马赛克/WB/CST/缩放/round-clamp及硬件统计，再以标准参数/统计接口连接libcamera pipeline/IPA，完成真实像素验证。随后四摄标准应用/录像、异常与PM、画质、AF加速/Continuous/标定和完整Image/rootfs回归。当前仍RAW RDI→CPU ISP；不能用本轮输出代码、主机测试或构建替代完整适配，也不能据此承诺免补丁升级。

续作用[host.py](host.py)，仍核276 boot guard；私人资料`E:/edk2-samurai-out/kernel282`。公开源码两提交均未推送，候选分支和既有回退保留。只有r3完整构建可能仍运行，其它本轮下载／测试／对象构建／采集及r1/r2构建均已终态。另只读取得原厂Shine OV02A1B模组BIN并已卸载vendor，供下一轮核对第四颗后摄；文件存在不证明本机芯片身份，私人原件与收据均在kernel282目录。
