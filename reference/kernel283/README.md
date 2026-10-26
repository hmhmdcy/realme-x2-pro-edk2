# 283：VFE175 白平衡参数后端与首帧参数队列

后续[284](../kernel284/README.md)已核282 r3完整构建终态、验证归档实际778ko，并checkout WB完成正式Kbuild及Demosaic36候选完整链接；本文构建运行/未checkout等描述按当时阶段阅读。

2026-10-19。完整多摄及骁龙ISP目标继续active。本轮前的问答核对资料时，真实核到282 r3完整构建worker592/make794仍运行，按verified wait记录；本轮新增实际源码、编译与主机测试。**没有部署新驱动或取得硬件ISP图像，完整目标尚未完成。**

## 优先查现有方案，再核本机硬件

找到Qualcomm于10月7日重发的45补丁[IFE pixel path系列](https://lists.openwall.net/linux-kernel/2026/10/07/513)，覆盖SM8250、SA8775P和QCS8300。其新IFE subdevice、streams routing及参数/统计结构与279所用Bryan RFC采取不同路线，作者也明确尚未互相rebase；不把整个系列混入当前候选。

保存并固定cover、module、interface、scaler、top、参数UAPI及apply原帖。SM8250的[模块代码](https://lists.openwall.net/linux-kernel/2026/10/07/524)使用独立模块地址与U15Q10硬件WB；本机原厂HAL写0x6fc/4寄存器，增益是U12Q7。两者不能直接复制地址/参数。上述已投稿代码不等于已合入主线。[来源和本机差异](oem-wb-contract-validation.json)

本轮从既有本机原厂HAL（SHA e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde）静态核对写入地址、参数存储、调试标签及缩放常量，补齐282未定的通道顺序：0x6fc低12位green、高半字低12位blue，0x700低12位red；unity=128。原厂两个64位保留位mask与四个寄存器字段交叉核对。只记录互操作事实，原库/反汇编/模组及校准数据仍私存，不复制原厂实现。非零offset含义未由mask臆测。[可复核脚本](verify-oem-wb.py)

## 源码与分层

新候选提交 **97a4c563803fd943e5a4c3f0359548a3d758bcc5**，分支 **samurai-vfe175-wb283**，父282 **18b48939788bc7f95fb2999ea986846a67f0c62c**。完整构建仍读父源码，因此通过独立Git index建立候选提交和分支，没有checkout、切换或改写正在构建的目录。原候选目录仍干净位于18b/`samurai-vfe175-output282`；生产维护树仍276版本。[完整补丁](vfe175-wb-candidate.patch)、[提交与逐文件哈希](candidate-commit-validation.json)

| 层 | 本轮实际变化 |
| --- | --- |
| SoC处理后端 | 新175 pixel backend，按本机寄存器写三通道WB，保留非所属位；中性默认不复制原厂场景增益；只接受零offset |
| 标准参数 | 复用现有CAMSS_PARAMS_WB_GAIN和公共extensible parser，U15Q10舍入/饱和转换U12Q7；拒绝越界gain、未知flags、非零offset和padding；DISABLE允许仅header且不读payload |
| 参数状态 | DISABLE写unity实现WB旁路，缓存的增益保留；无flags更新不重新启用，ENABLE恢复；重新开流回到neutral默认，然后应用已排队参数。只缓存当前175处理状态 |
| 公共生命周期 | 复用现有公共initial queue helper，17x在prepare成功后、启用输出前调用；仅PIX调用，RDI不进入。之后的逐帧公共apply/回执沿用已有路径 |
| 缓冲区 | 公共IFE metadata容量从仅BHIST扩展为BHIST＋WB，避免WB结构通过parser却装不进已公告的buffer |
| 板级/固件/用户空间 | 没有更改DT、供电、固件、libcamera或应用；仍三个RDI，不开放尚未完整的PIX，不增加任意寄存器用户接口 |

这只补了硬件处理链中的WB及其参数接入，不等于去马赛克、颜色转换、缩放、gamma、统计或IPA已经完成。设备树继续只承载硬件描述；画质算法和模组调校仍须进入匹配IPA/数据包。

## 验证

- [实际后端和公共parser的ASan/UBSan测试](wb-host-tests-validation.json)：遍历32768个有效输入，逐项比较独立整数舍入与饱和；三个通道分别遍历32768个越界值。覆盖通道映射、保留位、零offset、短DISABLE精确分配、非法type/flags/size/padding、无flags保持旁路、重新ENABLE、FIFO与RDI零写入。
- 额外执行实际`vfe_params_output/apply_next/apply_queued`：启动参数按FIFO应用，完成在释放output_lock后回报，时间戳有序，空队列不写寄存器。测试同时检查17x调用位于prepare之后、output enable之前。尚未用硬件验证首帧生效时刻。
- [最终33组件ARM64 W=1/-Werror及独立聚合链接](wb-overlay-build-validation.json)零诊断。使用既有kernel saved GCC命令，编译独立暂存的全套CAMSS源码/头及更新UAPI，输出在私人目录；没有改旧构建对象或正在运行的282源码。不是完整vmlinux/ko链接。第一轮构建也通过，随后补启动队列接入而重新编译，原结果保留。
- 初次主机测试因直接引用未export的内核UAPI在Werror下失败；按UAPI宿主编译定义修正，原harness及失败收据保留，不是手机故障。[初次失败](initial-host-failure-validation.json)
- checkpatch零error、一条新增文件MAINTAINERS提示；现有`F: drivers/media/platform/qcom/camss/`匹配覆盖新文件。独立第二index从父提交应用保存补丁，重建tree逐字匹配提交；原工作区/index未改。没有推送。

## 现机与仍运行的完整构建

[现机只读复核](final-health-validation.json)：仍boot276/Image183、776模块/961包、libcamera r24/config-r19；50载荷和全部模块不变，十个加载note匹配，桌面/PW/WP原进程保持。相机休眠、rails/共享I/O/clocks回收，fault0/taint0/pstore空、无CCI错误，SSC/SensorProxy正常。没有新拍照、调焦、安装、刷写或重启。

282完整构建r1漏长焦已受控终止；r2因C盘满/源码读取IO错误终态exit1。此前已保留迁移pip缓存、恢复WSL、核9个源码，并新建E盘32GiB ext4构建卷。**r3仍使用固定18b源码构建**，原exec会话29220，worker592/make794；日志`E:/edk2-samurai-out/kernel282/full282-r3-w1-private.log`，输出`/mnt/samurai-full282/build`。本轮未重新启动它，继续核真实进程和结果。WSL空闲重启后须核镜像backing并恢复loop挂载，不向空挂载点写构建产物。当前存储和配置依据见[282](../kernel282/README.md)。

下一步先核原r3完整构建终态，然后在283候选上补175 demosaic、CST/CC、MNDS/round-clamp及统计/参数，再接libcamera pipeline/IPA并做真实硬件像素验收；四摄GUI/录像、画质、AF加速/Continuous/距离标定、第四颗物理后摄确认及完整Image/rootfs回归均保持完整范围。Shine OV02A1B原厂模组BIN在282私人目录，尚未证明实际芯片身份。当前仍RAW→CPU ISP，不能承诺免补丁升级。续作用[host.py](host.py)，保持276 guard；私人目录kernel283。不要重放prepare/commit非幂等步骤。
