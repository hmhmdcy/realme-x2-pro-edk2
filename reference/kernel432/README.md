# 432：原厂 GTM 数据恢复与 TMC11→GTM 数学验证

本轮推进原厂 GTM 的实际解析、计算和可移植数学实现。四份保留的原厂文件共 45 个 IFE/BPS 根配置，与原厂解析器 XML 及本机 HAL 解析结果一致；原厂 TMC11 完整输出已经进入原厂 GTM 完整计算函数。可移植的 TMC11 model2→IFE GTM 数学在主机和 ARM64 各 27 个用例逐字节匹配。

**尚未下发到 IFE，也未完成 GTM 生效版本与对应图像／IPA 数学历史关联。本轮没有访问手机或新增实拍。** 431 的主摄真实同 SOF PD10 自动双遍 48 帧／48 次最终历史提交仍是最新实拍证据；完整多摄和画质校准目标保持进行中。

## 原厂数据与原始解析

[数据恢复验证](factory-gtm-validation.json)核对 45 个根配置及其 DRC／HDR AEC／AEC 触发树、reserve、26 个区域字段和 90 个标量。原文件的 464-byte 区域序列化布局不能直接当运行时结构使用。独立 BIN 读取结果全部匹配保留原厂 ParameterParser 生成的 XML。各模组的原始 enable、payload 和模式树没有修改；前摄三个根配置全部禁用。

[原始 HAL 解析验证](native-parse-validation.json)执行本机 `chromatix_gtm10TypeClass::Parse`，入口 `0x2085f0`。45 次实际解析均完整消耗原始条目，所有叶子的 360-byte 运行时区域、根 enable 和 reserve 与独立解码数据逐字节匹配。类对象为 192 bytes，供 IQ 使用的 payload 从类对象加 88 开始。原始文件中的 revision 使用计数／引用关系定位，不能套用其它模块的字段偏移。

14 个普通 IFE 模式查询继续沿用 [431 原始模式管理器证据](../kernel431/gtm-location-validation.json)。本轮使用其中对应摄像头及模式的 GTM 配置，未下载新固件。参考源码固定在保留的 CamxChi revision，哈希见 [来源记录](primary-sources.json)。完整 XML、原件、源码副本、系数、轴和指令仅私存。

## 原厂 TMC11 与 GTM 计算

[完整 GTM 计算验证](native-math-validation.json)执行本机 `IQInterface::GTM10CalculateSetting`，入口 `0x37c818`。45 个原始解析对象的插值结果一致，分别写出完整 512-byte IFE LUT。这里对 BPS 根配置使用的是 IFE 输出格式的离线数值夹具，不是 BPS 硬件链路验收；禁用根的直接计算也只用于离线结构核对，未改变生产启用策略。

[TMC11→GTM 验证](adrc-validation.json)在四摄各一个原厂 Preview 上执行三次本机完整 SWTMC11 Execute，共 12 次。后三摄的 9 次启用结果由 GTM 原函数按照 TMC11 version 1 读取，并通过其真实指针赋值路径消费；前摄三次继续禁用，不强行进入 GTM。原厂非零 GTM percentage 保留，输入改变可以改变最终 LUT。

原始计算函数的输出包含独立寄存器指针和 LUT 指针。最终夹具验证全部 512 字节确实被写入、末尾哨兵完整、目标代码／只读数据区不可写，并核对 bank 位仅修改指定寄存器位。早期夹具曾使用错误 revision 引用以及错误输出指针；相关离线失败私存，早期结果已由更正后的完整输出验证替代，未涉及手机。

平台信息由明确的离线初始化夹具提供，未读取手机的 Android HwEnvironment；原 `GetInstance` 沿已有初始化状态返回，GTM 计算指令没有替换。主比较使用 selector 2、关闭 word swap；另有 selector 0／2／3、swap 开关、GTM LUT bank 0／1 的 12 种独立组合。**这里的 GTM LUT bank 与 IPE DC 平均值表 bank 是不同资源。** 数学库调用使用主机 libm，不能称为原厂 Bionic 全运行环境复现。

## 可移植实现

[GTM 数学原语](libipa/gtm_tmc11.cpp)复用已有的 TMC11 PCHIP 采样，加入 GTM 的 Q12／6-bit 比例限制、原厂浮点舍入、26-bit 有符号 slope 和 IFE 的 18-bit base／32-bit 高字 slope 打包。轴、曲线和模式数据由调用方提供，没有嵌入原厂表。

[主机／ARM64 对比](portable-validation.json)各执行 18 个有效用例（9 组原厂 ADRC × 两种 word 顺序）和 9 个非法输入保持输出用例，共 27 个，最终 LUT 与原始 HAL 逐字节一致。主机启用 ASAN／UBSAN；两架构均 `-Wall -Wextra -Werror`。额外的 12 种 native bank／swap／selector 组合确认 bank 和数据字序可以独立变化。

该函数仅覆盖已验证的 TMC11 model2 数值路径。完整 legacy BHIST、manual／v2 fallback、TMC10 和其它模型尚未全部移植；它也不选择模式、不下发 IFE、不确认生效版本、不提交帧历史，尚未编入生产 IPA 候选。

## 分层状态与下一步

本轮仅新增可复用用户空间数值代码和原厂数据验证工具。维护内核仍为 431 HEAD `52127e558704de6a640d076ef605182fe6fff0d7`；SoC 驱动、板级 DT、传感器、电源及生产用户空间候选均未修改或加载。431 末次正式模块／服务／资源恢复、无新增 fault、taint 0 的结论保留为历史实机证据，本轮没有刷新设备健康观测。

DC 的 RT type 2→context 0→bank 0、粗级 DC／sum-clear、全尺寸 IP 消费，以及相同输入重复性和真实 PD10 生产自动双遍见 [431](../kernel431/README.md) 与 [430](../kernel430/README.md)。片内平均值表仍没有逐字节读出，不能把命令策略或全 a7 scratch 当表内容。

接续优先恢复本机 IFEGTM10 的参数／寄存器／DMI 提交契约，在 SoC 层增加 typed block 和真实生效回执，再接 IPA 的版本关联。顺序必须是“统计→后续 IFE GTM 生效→对应图像 IPE／LTM→最终成功历史提交”。当前图像的直方图不能倒称已经改变该图像的上游 GTM；也不能清零原厂 GTM 份额来宣称完整。完成硬件和版本关联后再实拍核验，画质仍需验收，其它摄像头／模式与同步范围见 [363 剩余清单](../kernel363/REMAINING-CAMERA-SCOPE.md)。
