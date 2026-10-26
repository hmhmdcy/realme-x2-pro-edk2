# 435：主摄生产 IPA 接通原厂 GTM／TMC／LTM 与最终成功历史

主摄单曝光自动链路已在生产 libcamera 候选中接通：真实统计生成后续 IFE GTM，实际 ACK 回执绑定图像与 PD10，再由该帧 IPE／LTM 消费匹配的不可变 TMC／ADRC，最终请求成功才提交数学历史。

第三轮普通／隔离 IPA5 各完成 24 张实景。合计 48 个 IPE 作业，其中 42 帧完成原厂 GTM／TMC／LTM 自动双遍及 42 次数学提交，另 6 帧是首个真实 GTM 尚未生效前的显式启动处理，没有冒算数学提交。正式环境已恢复，无新增 fault、taint 0，候选没有永久安装。

**画质尚未验收。** 已查看两种路径的最终 PNG，仍有明显雾感、偏绿及环状亮度分布。当前证据证明链路、版本与成功历史的对应关系，不能据此宣布完整多摄校准完成。其它摄像头、模式／视频、光学与完整原厂 tone 支持仍需继续；片内 DC 平均值表也没有逐字节读回。

## 真实自动实拍

[逐帧审计](hardware-validation.json)核对[第三轮终态](runtime-r3-validation.json)的主摄 S5KGW1 4608×3456、FULL 640×480 NV12、原生 160×120 PD10，保留单曝光线性 AE／AWB、无 face 的既有模式约束。

| 路径 | 实景／IPE 作业 | 已观测 GTM 版本 | 完整数学提交 | 显式启动帧 |
| --- | ---: | ---: | ---: | ---: |
| 普通 IPA5 | 24 | 8，两个 bank | 21 | 3 |
| 隔离 IPA5 | 24 | 8，两个 bank | 21 | 3 |

每路有 9 次参数提交，最后一次可在停流前尚未 ACK；没有将“已提交”计入已生效版本。所有保存成片都有同 SOF 的真实 PD10、统计与 IPE token，队列 SOF 严格递增。42 次 PREPARE 与最终成功回执逐个对应，revision 仅随成功推进，LTM 的上一 lux 来自前一次成功历史。普通路径的 IPA 与应用同进程，隔离路径确认不同进程。

普通路径的具体例子：统计 SOF 0 生成 cookie 2，在 SOF 3 观测到 generation 2／bank 1；图像 3 的 FULL＋PD10 使用该版本对应的 TMC，最终提交数学 revision 1。图像 4、5 继续使用 cookie 2，之后统计 3 生成的 cookie 3 在 SOF 6 生效。图像自身的新直方图用于本帧 LTM 选择和后续 GTM，未被倒称为已经影响其上游 GTM。

内核记录每路 RT type 2，启动时 scratch 48，随后切换为 DC 多遍配置的 46128；两路共 48 次固件逻辑帧完成，无失败、取消或协议错误。启动的三帧只使用明确的 colour 配置，不提前宣称 GTM／ADRC 已可用。随后 21 帧使用原厂 LTM／DC 配置、真实同 SOF PD10 和已验证的 431 双遍传输。内核 core 的帧计数按开机／逻辑帧生命周期解释，没有将它误算成 coarse＋FULL 的物理遍数。

## 原厂数据和数学

[私有配置导出](profile-export-validation.json)复用 431 已选模式和 432 的本机原厂 GTM root、归一化轴、整数轴及对比度轴。主摄模式 2／4 均选择原 UID 21；原来的调校字段完全不变，仅增加 GTM 节点。实际实拍范围是 4608×3456；2592 高模式仅准备了配置，未在本轮扩大验收。

原厂 `manual_curve_enable`、`v2_enable` 均保持原值 1，没有为了通过校验清零。这里明确使用原生 ADRC 的 TMC11 model2 分支，其行为已由本机完整 GTM 计算验证；这不代表已经移植所有 legacy／manual／v2 算法。新配置要求 GTM enable 与所选 TMC11／use_gtm 一致，矛盾配置拒绝。

[原始 HAL 对比](native-gtm-validation.json)将实际编译生产 profile 输出的三份 ADRC 交给本机完整 GTM，使用原解析对象和原 flags：每份 512 bytes LUT 均零差异。复用 [432](../kernel432/README.md) 的数值原语和已验证 CPU canonical packing，没有 HW-CDM word swap。

TMC 按原生策略持有直方图：trigger 不变时 force update 不强行换成新直方图，保留已有 histogram；trigger 改变才更新被选 histogram。完整被选直方图及其 SOF 留在不可变数学对象中。日志的 `source-sof/source-histogram` 指提案来源统计，若原生策略持有更早 histogram，实际数学对象仍保留那个更早输入，而不是改写日志所指统计为已消费的新直方图。

[统计域检查](statistics-domain-validation.json)没有新拍摄，而是复查 434 的 61 组真实测试图：九阶段 GTM 明确改变 FULL／PD10，BHIST 与 BG payload 各自始终逐字节相同。在固定输入与 WB、当前选定 tap 下，这支持统计位于 GTM 上游；不扩展为所有 tap／模式的寄存器证明。

## 实现与提交顺序

[完整补丁](0047-camss-gtm-applied-tone-history.patch)从 431 生产候选修改 15 个文件，核心变化是：

- 将原有 TMC 生成从 IPE 消费中拆出。统计 N 产生未来 GTM 和不可变 TMC；图像 M 的 LTM 从真实回执对应对象取 ADRC，LTM smoothing／上一 lux 仍只取成功历史。
- 新 `IfeGtmHistory` 分开 pending 与实际 active，只有合法 cookie／generation／bank／status 回执才推进，并要求 ready 版本的来源 SOF 严格早于应用图像。参数 DQ 在 IPA5 中只记录提交；同包 WB／CCM／LSC 的上下文也在实际回执后确认。
- 每个 IPE token 持有 `shared_ptr<const Version>`。IFE 继续更新或 IPE 失败时，该图像的 TMC 不变。数学状态记录其实际 GTM cookie／generation；失败丢弃数学提案，不伪造回滚已生效 IFE。
- 缺 lux／忙时仅在 committed LTM 与该图像的 GTM cookie 相同才复用；没有真实版本信息时不提交错误的旧 LTM，成功历史保持。启动阶段显式 colour-only，不生成第一份虚假成功数学状态。
- 普通代理的同步方法直接调用模块，而统计走排队线程。16 个模块入口串行化共享状态；最终 `frameProcessed` 改成同步，下一图像开始前完成成功或失败回执。隔离 worker、proxy、库和 IPA 必须使用匹配的 IPA5 cohort。

## 两轮实机失败及修复

[r1](runtime-r1-validation.json)报告 3 帧，其中最后一帧失败；此前已有两次成功数学提交。等待 IPE 的 FULL 所对应 PD10 被旧的“过期”清理回收，之后新图像越过旧图像处理。修复在低层 pipeline 保留所有等待 FULL 已占有的 PD10，只回收未被认领的 SOF；按最旧等待图像的 SOF 完成 IPE，保留原有有界超时，没有靠延长超时掩盖问题。

[r2](runtime-r2-validation.json)推进到 6 次成功数学提交，随后应用请求进入时统计停滞：控制等待旧 GTM 实际 ACK，统计提交却被这个等待请求阻挡，而 ACK 正需统计带回。现改为 EAGAIN 时继续处理统计；IPA 标记控制等待，在控制得以执行前暂停新的自动 ISP 提案，避免不断生成新 GTM 使请求饥饿。

两轮均保留原日志、样本与失败，正式模块／服务／资源恢复，无新增 fault、taint 0。第三轮使用第六次用户态构建，两种路径均完整通过，未再出现配对超时或请求失败。

## 检查、产物及范围

[实际 ARM64 IPA／profile 检查](ipa-validation.json)包含旧 factory／bypass 配置、新 GTM 原厂 profile 及真实模块方法；Werror 编译的契约检查覆盖 DQ 不冒认 ACK、启动不提交数学、来源 SOF、不可变上游 TMC、原生 histogram hold／refresh、IPE 失败、错误版本拒绝、相同版本缺 lux hold、控制等待恢复与重启。统计是明确的合成夹具，不冒充实拍。

[历史对象检查](history-validation.json)在主机 ASAN／UBSAN 执行实际 history 头；[PD10 保留检查](retention-validation.json)执行实际 `coarseReady()` 体，模拟多个 FULL 等待时连续收到新 SOF，验证占有缓冲保留和未认领缓冲有界回收。[源码核验](source-validation.json)检查实际签名、15 文件 hash、生成 proxy 的同步最终回执和 16 个方法锁；[补丁重放](replay-validation.json)对权威 431 输入零 fuzz／offset，结果与最终源码逐字节一致。

用户候选：`/mnt/samurai-full282/libcamera435-gtm-history/src/libcamera-v0.7.2`，[build 6](build-validation.json)，私有 IPA5。libcamera SHA256 `5edff049…`，IPA `51052914…`，proxy `093df5fa…`。第一构建的 shadow 警告和调校 YAML alias 不兼容均已修正并保留相关记录；最终编译无诊断。历史准备／修复脚本记录各阶段状态；重建最终版本应使用 431 基线与最终补丁，不盲目重跑一次性修复脚本。

内核未修改，继续使用 434 的 `9bc07e63…`／`samurai-vfe175-gtm-reopen434`，CAMSS `3edb28d1…`、core `d391fa24…`、m2m `e6828a0c…`。板级 DT、传感器、电源与 DMA 双遍实现没有重做。两种用户态路径每次都停止后回收源平面、结束固件 session，并恢复正式 420／419 模块及服务。

DC 继续使用 [431 原厂 bank 规则](../kernel431/bank-validation.json)：RT type 2→kind 0→bank 0，粗遍 DC 写并 sum-clear，全尺寸遍 IP 读同一 bank。重复性和 PD10 因果消费仍继承 [430](../kernel430/README.md)，本轮补上自动实际版本与数学历史。片内整表没有逐字节导出，a7 scratch 不是统计，不恢复 429 越界诊断或猜测 MMIO。

下一步优先定位当前亮度环状分布、雾感与偏色：保存同一帧的 IFE 输入／PD10／IPE 输出，分离 LSC／GTM／Gamma 与 IPE 局部处理的影响，结合原厂模式和信号域检查收敛。随后扩大其它摄像头及模式自动链路。其余完整范围见 [363 清单](../kernel363/REMAINING-CAMERA-SCOPE.md)。原厂数据、轴、LUT、完整日志和图像只在 private kernel435；公共仅自有代码和脱敏证据，完整目标保持 active。
