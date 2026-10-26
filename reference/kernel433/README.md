# 433：IFE GTM 提交契约、驱动参数与 SOF 生效回执候选

继续复用 432 已验证的原厂 GTM／TMC11 数据和数学。本轮执行了本机完整 IFEGTM10，确认寄存器／DMI 和 bank 切换，并把 typed GTM 参数、CPU DMI64 上传、PIX 更新 ACK 及 SOF 版本快照接入维护内核。10 个匹配模块 W1／Werror 构建通过，主机和 ARM64 的实际驱动／IRQ 函数检查通过。

**驱动候选尚未加载到手机，未新增实拍，也未接入生产 IPA。** “接到 ACK 回调”是代码和离线检查结果，不能据此宣布硬件生效、同帧数学历史关联或完整画质校准完成。最新实机证据仍为 [431](../kernel431/README.md) 的主摄真实同 SOF PD10 自动双遍 48 帧／48 次最终数学提交。

## 原厂完整提交路径

[原始 HAL 验证](transport-validation.json)执行本机 `IFEGTM10::Create`／`Execute`，复用原始解析得到的已选模式对象。三个更新分别在 `0x794` 写 GTM 配置，并经 `0xc24` 的 DMI 命令提交 512-byte LUT，selector 为 24／25／24；实际 DMI buffer offset 56 bytes，完整 LUT 均与 432 原厂数学输出一致。参数未变、AE/AWB 锁定和原厂禁用前摄各一个调用不重新提交 LUT。颜色 enable 的 bit 2 更新，周边位保持。

另一个明确注入的 DMI 传输失败返回错误；本机 HAL 仍切换内部“下次 bank”，但不发布本次颜色 enable。此行为仅记录为原厂事实，没有将失败当作生效回执。共执行七次完整 Execute，transport 边界只记录，不向硬件发送。平台状态仍为明确的离线夹具，模式管理器不重复执行。

[协议来源](protocol-sources.json)复用已保留的生成头与官方 Realme GPL CDM 源码，未重新下载。实际执行官方 `cam_cdm_util_swd_dmi_write` 作为 CPU DMI64 oracle，确认低字写 `0xc30`、高字写 `0xc2c`。该 CPU 路径不使用 HW-CDM 的 word-swap workaround；GTM 的两个 LUT bank 与 IPE DC 平均值表 bank 是不同资源。

## 驱动实现与版本含义

[驱动补丁](gtm-driver.patch)新增 SoC 专属 GTM 实现并复用既有参数／统计节点：

- 实验参数 type 9，完整 536 bytes：opaque cookie、显式 enable、保留字段和 64 个 base／slope 段。cookie 非零、flags 为零，disable 也要求完整块；base 18 bits、slope signed 26 bits，越界拒绝，不截断非法输入。
- CPU 上传完整非活动 bank，明确逐项地址、低字→高字，保存并恢复共享 DMI config／address 和时钟覆盖状态，填完后发布 bank。启用、停用只改 GTM 指定颜色位。既有 Gamma／LSC 等共享状态保留。
- 实验统计 type 3，32 bytes：cookie、ACK generation、状态和 bank。只有实际 PIX REG_UPDATE ACK 才推进 active cookie／generation；在输入 SOF 给每个硬件缓冲保存快照，统计完成时使用该缓冲的快照。

参数 DQ 继续表示参数已写入／提交，不被重新解释成硬件生效证明。GTM 的统计回执才表示驱动观测到更新 ACK，并将状态保存到对应 SOF。cookie 由调用方关联调校对象，generation 是本次开流内的真实 ACK 次序；都不是原厂 chromatix 版本号。

为避免旧的 PIX 更新 ACK 冒认新 cookie，含 GTM 的首个参数及随后受跟踪的参数，只在上一 PIX 更新已退休时开始；忙时保留在原队列。ACK 回调清除旧更新、发布已 armed 的 GTM，再取下一份参数并请求新的 RUP。重复或未 armed 的 ACK 不推进 GTM。ACK 在现有 ISR 中先于同次 SOF 处理，随后新请求也不会提前改变本次 SOF 的 active 快照。

公共 ISP 解析器本来允许重复块。本轮增加整包校验，拒绝同一参数缓冲含两个 GTM 事务，避免第一次已写、第二次覆盖版本。预开流仍可排队；停流清除 pending／active 状态，停止后的迟到 ACK 不会带入下一次开流。没有 GTM 配置的旧调用保持原路径，也不新增 GTM 统计块。

## 验证与候选

[实际函数验证](driver-validation.json)在主机 ASAN／UBSAN 和 ARM64 上各用九份原厂 LUT 执行当前 GTM 驱动体、实际参数 dequeue、PIX reg_update／clear、ACK 和 SOF 函数。覆盖全部 64 项非活动 bank 写入及共享寄存器保持；DMI64 的全部低／高字 trace 与官方 GPL 函数一致。每个 LUT 用例包含 200 个非法字段／flags／短块拒绝检查，并核对旧 ACK 隔离、未 armed ACK、后续参数排队、晚完成统计使用旧 SOF 快照、disable ACK 和 stop 状态清理。IRQ／寄存器和外围队列是离线夹具，未替代真实手机验证；官方 oracle 的原有 signed bitfield 比较警告仅在该外部函数周围局部屏蔽。

[源码核验](source-validation.json)确认补丁零 fuzz／offset 重放、当前 source clean、真实模块包含 GTM／ACK 符号。维护分支 `samurai-vfe175-gtm-ack433`，HEAD `04f8c5a3c815e2fa4244564da108227561a0321b`，父 431 `52127e55…`。首轮构建后补了重复 GTM 校验，第二轮才是当前候选；[第二轮匹配模块](intree-build-validation.json)十个模块通过、诊断为零，共享构建输出恢复。

当前 CAMSS 为 2934680 bytes，SHA256 `88e7c6ae9cd1e4bb81c807fecc584a2dfba1e671400e0418622d45fcd1f51c17`。ICP core 和 m2m 分别仍为 431 的 `d391fa24…`、`e6828a0c…`，没有修改 IPE 双遍、其 DMA 所有权或超时释放逻辑。板级 DT、传感器、电源和生产 libcamera431／IPA4 候选未改。

本轮未访问手机，没有重新观测设备健康、像素或 IRQ。431 末次恢复正式模块／服务／媒体图／资源、无新增 fault、taint 0 的证据保留为历史实机结果。原厂数据、轴、指令、完整日志和像素仅私存；公开内容为自有实现、GPL 协议引用及脱敏验证结果。

## 接续到完整自动链路

先用当前 typed block 和统计回执做有界手机验证：完整 LUT 的功能影响、低／高字顺序和两个 bank、真实 RUP ACK→SOF→对应图像／统计，并完成停流和正式环境恢复。之后接入生产 IPA 的原厂 GTM 数学与数据选择；硬件未证明前，不把离线 ACK 夹具升级为实机结论。

IPA 必须按实际回执 cookie 取回匹配的不可变 TMC／ADRC 对象，给对应图像的 IPE／LTM 使用，并关联最终成功历史。统计 N 只能生成后续 IFE 更新；不能拿图像 M 的新统计倒称其上游 GTM 已生效。IFE 已 ACK 的物理版本与 IPE 数学成功提交是不同阶段，IPE 失败不能伪造回滚已经生效的 IFE。原厂 GTM 非零份额、前摄禁用、缺统计 hold 和失败历史约束都要保留。

真实 PD10 与 DC 初始化／重复性证据继续沿用 430／431；片内 DC 平均值表仍没有逐字节导出。其它摄像头自动链路、模式／视频、第五 2MP、个体光学及多摄同步仍见 [363 剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)，完整目标保持 active。
