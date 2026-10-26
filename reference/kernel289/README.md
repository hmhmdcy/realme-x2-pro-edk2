# 289：内部TPG历史隔离与Gamma SRAM时钟修复

2026-10-19。完整多摄及骁龙ISP目标继续。本轮在实际288启动上定位两项底层缺陷，完成两个独立本地修复及完整构建。**现机仍#288；289候选未部署。临时硬件对照证明Gamma上传缺时钟，修正后黑白亮度恢复，但色度仍错误，完整硬件成像/统计/IPA尚未完成。**

## 当前身份与已有方案

[实际预检](runtime-preflight-validation.json)确认288启动、五sensor/lens休眠、旧288五个worker终态且进程消失、fault/taint0；没有依赖旧PID猜测活性。[288整体部署](../kernel288/README.md)的Image、778模块、boot276/DT和r24/r19用户态保持。运输用[host.py](host.py)，委托288严格SSH身份和新boot guard；本轮未重启、刷写、安装包或替换模块。

继续使用279固定的[IFE标准media/V4L2方案](https://github.com/0xB0D/ife-tests)和已有隔离TPG工具；本轮外部搜索DMI资料时只找到[较早VFE代码](https://android.googlesource.com/kernel/msm/+/a2cd6eaf5deaa40098eb6b692797519bc173381e/drivers/media/video/msm/msm_vfe32.c)及无关结果，不把旧VFE32寄存器套到175。[本机官方VFE175定义](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/media/platform/msm/camera/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/vfe17x/cam_vfe175.h)固定提交/文件SHA重新核对：color CGC override在0x34，enable在0x48；Gamma位3由既有HAL静态协议及本轮硅上对照共同支持。[来源与硬件结论](clock-contract-validation.json)

## 先纠正TPG连接历史

首轮DMI读回后0帧超时，图与PM均恢复；不能据此断言DMI操作破坏了流水线。将读回移到三帧之后的r2依旧在读回前0帧；[原288工具只读快照](baseline-capture-validation.json)也失败，说明问题先于DMI访问。

与288成功r3寄存器逐项比较，主要差别是RX_CFG0从D-PHY四线0x132103变成C-PHY三线0x1002102，TPG_CTRL从0xa06437变成0xa06427，IPP保持halted。四摄回归最后的GW1 C-PHY连接保留在csid->phy；禁用MC物理链接没有清除这份历史。gen2 RX及TPG配置直接复用它。

通过标准MC链接短暂建立csiphy1的D-PHY历史、断开后再运行完全相同的隔离工具，重新得到3帧，最终原图逐字恢复。[D-PHY历史对照](dphy-capture-validation.json)。这只是诊断对照，不作为应用工作流。

[公共gen2修复](csid-gen2-tpg-isolation-candidate.patch)让内部源使用固定四线D-PHY和顺序lane映射；外部sensor继续使用其物理配置，不修改保存的PHY参数。没有RMX1931判断、DT变化或新增私有接口。**该新RX配置尚未启动实测**，不能把对照工具等同候选驱动验收。

## Gamma SRAM：读回、时钟及像素响应

| 对照 | 实际结果 |
| --- | --- |
| r1，CGC不变，显式地址读取 | 每个selector的64项重复同一字；0帧超时，后来由PHY历史对照解释 |
| r2，改为捕获后读取 | 捕获阶段0帧，未触碰DMI，保留失败 |
| r3，D-PHY历史＋显式/连续读取 | 3帧通过，但两种读法均每表只有1个不同字 |
| r4，计划加Gamma CGC读回 | 第二帧与第一帧hash相同，但恒定prefill碰上有效像素，90%变化门槛误判；没有执行CGC部分 |
| r5，位置相关prefill＋CGC bit3 | 3帧通过；六个bank每表64项均不同，两种读法一致，但每表0项匹配要求曲线 |
| 上传同一sRGB曲线，临时切bank | 3通道共192字逐项精确读回；同流9帧，丢弃切换后3帧，再保存新帧；黑白亮度恢复，色度仍失败 |

[无CGC读回](gamma-lut-dphy-validation.json)、[有CGC读回](gamma-lut-pattern-validation.json)、[上传与九帧](gamma-upload-capture-validation.json)。开发工具用volatile 32位MMIO和屏障，只在V4L2 helper持流、CAMSS active期间访问；区域来自实际DT并检查边界。先使用真实标准图/格式/控制捕获，再进行有界协议实验，未执行厂商HAL、写OTP或校准。

原驱动在像素尚未到达时上传SRAM，没有强制Gamma模块时钟，后续enable不补发先前丢失的写入。打开0x34 bit3后，同样的显式地址及数据端口可以完整读写，支持将时钟保持加入SoC后端。[Gamma修复](vfe175-gamma-clock-candidate.patch)只在上传和切bank期间保持该位，保存/恢复其它时钟位和共享DMI状态；曲线、sensor参数、用户空间均不变。

[同流像素](gamma-upload-pixel-validation.json)：临时修正前白块Y167/UV98,190，黑块Y151/UV68,234；修正后白块Y254、黑块Y0，**两者UV仍0,0而非128,128**。这证明Gamma故障得到解释，也证明颜色链仍有缺陷。未加入增益补偿或应用颜色过滤器，不把亮度改善当完整画质完成。临时工具恢复原LUT bank、CGC、DMI寄存器；先前inactive bank的恢复写入已执行，但没有重新逐字读取验收。

r4工具误判已用位置相关prefill修正，并保留原90%门槛和plane/tail检查。[实际prefill函数检查](prefill-validation.json)覆盖3个seed和256种常量，常量碰撞比例均低于1%；不靠放松门槛让测试通过。

## 尚未解释的色度/偏移

在临时Gamma正确的同一TPG流，将CST三个矩阵全部置零，分别只在high或low字段写512，并保持clamp0…1023；每次切换丢弃3帧，完整15帧通过。[CST实际序列](cst-constant-capture-validation.json)。两组实际图像均Y/U/V全零，SHA一致。[像素和worker终态](constant-pixel-and-workers-validation.json)

这不证明两个偏移字段应交换，也不证明其它值或signed语义无效。下一步应结合本机寄存器事实，用128/256等常量、受控矩阵/使能对照，区分偏移单位与符号、CST、MNDS色度、round/packer及通道顺序；不要直接用512这一组结果重写算法。12个CST寄存器和Gamma寄存器恢复读回均通过。

## 源码、检查及完整构建

当前工作树`/home/cy122/x2pro-linux/camera279-isp-kernel`／`samurai-tpg-gamma289`干净，最终提交 **ff8d2e9fc04ef92407ff83c40c4e059eb620f0f7**；TPG独立提交 **5ad34a2d007c1506e70dc91739362d1bf801eb8b**，父为部署288的8c79b7e。两文件+24/-15，两个本地提交未推送；checkpatch均0错误0警告。[组合补丁](tpg-gamma-fixes-candidate.patch)、[提交收据](fixes-commit-validation.json)。本地树内不代表上游接受。

- [TPG实际函数ASan/UBSan](tpg-isolation-host-validation.json)：2621440组lane数/分配、C-PHY/D-PHY、PHY编号历史；内部配置确定、外部配置保持，VC/disable及原配置未修改。
- [Gamma实际函数及完整既有处理/生命周期回归](gamma-clock-host-validation.json)：所有192项DMI数据写均强制要求Gamma时钟；四种CGC原值精确恢复、inactive bank/共享DMI状态保持。旧Gamma代码负对照在时钟要求处失败，未靠writes计数判断根因。
- 测试包装器首轮宏续行提取失败，Gamma函数提取正则、include/uapi路径和__EXPORTED_HEADERS__初次遗漏均先于测试通过修正；编译失败日志私存，不修改驱动去迎合错误包装器。
- [完整构建](fixes-full-build-validation.json)：39CAMSS组件W=1/-Werror及完整Image/778实际ko/DTB，两阶段exit0，22.01＋79.63＝101.64秒，增量诊断0。不覆盖旧全新构建1140条诊断历史。

Image59243008字节，SHA **a28ecd3d29ac7d3bac3c37ab1f336d33317e5c0ff70617d44b469ea185873d2b**；DTB仍dcdd74ec…、config仍34204656…，Module.symvers及modules.order保持。旧288六项完整产物先存私人kernel289/completed-boot288。最新输出/mnt/samurai-full282/build，使用284/storage.py核backing/挂载后再读写；仍采用input-initramfs288，不重放旧无initramfs构建。

**该Image尚未打包/安装/启动验收，release与现机相同。** 不能按288新release独立目录的假设安装；后续安排独立release、匹配initramfs内置BT/全部模块、实际CPIO/FAT核验和回退后再部署。现机模块全部仍匹配288，不将候选构建晋升为当前系统。

## 最终设备状态与分层

[最后健康核验](final-health-validation.json)：全部778现机模块、旧776模块和50相机载荷保持；九rails/共享I/O OFF/users0，五sensor/lens/双CCI/CAMSS suspended，四MCLK/双CCI clocks0；fault0/taint0/pstore空，CCI错误0。Phoc/Phosh/PW/WP身份保持，三个DSP和SensorProxy正常；八个289诊断worker终态且进程消失。本轮没有新增实体四摄/AF/GUI/录像验收；288的234帧回归明确属于RAW＋CPU ISP。

TPG历史隔离属于公共gen2接收后端，Gamma SRAM时钟属于VFE175 SoC后端。板级接线、固件、模组参数及用户空间未改变。MMIO开发工具不进入生产应用接口。当前内核仍有bring-up资源保留参数和下游补丁，硬件ISP统计/参数、libcamera pipeline/IPA、实体硬件成像、四摄画质/录像/GUI、AF加速/Continuous/距离标定、其它模组及完整rootfs仍需推进，目标保持active。

根入口及相机部署/源码锁已从旧278/287记录更新为实际288＋单列289候选，原件和SHA清单见[更新前归档](../../archive/camera-before289-2026-10-19/manifest.json)。原288镜像/778模块、183回退logdump/776模块及248整机备份保留，本轮无回退往返。
