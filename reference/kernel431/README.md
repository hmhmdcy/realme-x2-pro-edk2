# 431：原厂 bank 策略确认；生产 IPA 同帧 PD10 自动双遍实拍通过

继续复用本机原厂 HAL／ICP、426／428 模式选择和 424 调校及数学实现。**普通和隔离 IPA 各 24 帧主摄实拍，共 48 个自动双遍作业、48 次最终成功数学历史提交。** 当前生产请求路径已接同 SOF 的真实 FULL／PD10。GTM 仍未应用到硬件，其生效版本与历史关联未完成；片内平均值表未逐字节读出，画质尚未验收。候选没有永久安装。

## DC bank、初始化和遍次

[原始指令检查](bank-validation.json)继续执行本机固件，而非按参考源码猜 bank。维护 m2m 使用 RT handle type 2；实际内核日志也记录 type 2。原厂 command handler 将其映射为 context kind 0，创建上下文时存入该字段；最终 LTM 序列化选择 DC/IP bank 0。非 RT type 3 的离线反例映射为 kind 1、两个选择位均为 bank 1。原始 ARM64 HAL 的位插入指令确认 DC/IP selector 分别在 bit 14／15。

RT 粗级控制为 DC 开、IP 关、sum-clear 开；全尺寸控制为 DC 关、IP 开、sum-clear 关，使用同一 bank。延续 430 已核对的原厂最终 distributor／BL，没有增加 CPU 猜测 bank、跨遍覆盖或 MMIO 读取。当前配对 m2m 使用一个 IPE 核、固件命令流按 DC→IP 执行；430 冷启动与持续请求的因果验证保留。

以上确认的是**实际会话参数对应的原厂命令策略和功能行为**，不是片内 RAM 寄存器读回或整张平均值表导出。没有把全 a7 的 scratch 当 DC 表，也没有把 sum-clear 解释为已经读取到全部 SRAM 单元为零。

## 生产队列、原厂系数与失败修复

[用户空间补丁](0046-camss-pd10-auto-pair.patch)基于 424，改 9 个文件。按已选模式解析可选 `ife_ds4`，系数逐项和总和校验，沿既有 typed ISP parameter block 上传；实际 IPA 输出的 16-byte DS4 block 与 428 已实机验证的原厂块完全相同。测试私有主摄 profile 只给 4608×3456 对应模式添加该数据，不推断其它模式或模组。

IPA 私有接口升为 4，明确返回 PD10 能力；缺少该配置的旧 profile 保持原路径。pipeline 配置 IFE DS4、内部分配与队列、在 FULL 前启动 DS4。完成的 FULL 与 PD10 按真实 kernel SOF 配对，大小／状态匹配后进入实验 QN10 的两个内存平面。libcamera 的 NV12 Y／UV 逻辑视图经同 DMA-BUF、相邻 offset 和容量检查合成 FULL 平面；额外平面为 PD10。两个源 FD 和原始 SOF 保留到 OUTPUT、CAPTURE 和 media-request 三方完成，停止仍先 join 再释放。

数值计算遵守既有 single-pending 约束，在最终图像／RAW回执发送后再派发下一幅图像。修复全局 deadline 会提前处理新到图像的问题：改按每张图像实际到达时间判断 250ms，保留有界 sensor-context 历史供迟到统计回调使用；未放宽曝光／gain／版本合法性检查，也没有伪造统计。

[底层补丁](request-coarse.patch)仅改 m2m 一个文件：从已验证的当前请求判断是否需要 DC，匹配单遍或双遍固件会话。合法的首帧／hold 旁路无需虚构 LTM；改变模式时使用原有 destroy／create 和不确定完成保护。QN10 的两个提交平面始终由队列持有，未使用的粗级平面不额外导入硬件。SoC core、板级 DT、传感器、电源策略、现有用户 UAPI／6008B 包和 DMA 释放策略不变。

前三次实机集成未验收，均保留记录并恢复正式环境：r1 在本地逻辑平面校验拒绝，数学提交 0；r2 完成首帧后，未提交历史导致下一请求拿到空旁路，旧 paired session 拒绝；r3 旁路/DC切换和 13 次真实提交成功，但旧超时提前恢复图像并删除曝光上下文，导致后续 AE 校验失败。r4 才是完整通过的本轮候选，没有将这些失败算成通过。

## 实拍与软件证据

| r4 路径 | 图像／自动双遍 | 成功数学提交 | 不同参数摘要 | 曝光／gain变化 |
|---|---:|---:|---:|---:|
| 普通 IPA | 24 | 24 | 23 | 4 |
| 隔离 IPA | 24 | 24 | 22 | 5 |

[逐帧硬件审计](hardware-validation.json)核对 PD10_READY SOF、同 SOF BHIST／lux／曝光观测、6008B 生成、实际队列成功、最终成功回执和版本递增。每次 previous-ltm-lux 等于上一成功提交的 lux；普通／隔离进程身份分别核对。所有保存 NV12 的大小及实际亮度均与元数据一致。隔离路径多出的一份无应用图像统计在停止时中止，不推进数值历史。

另有同一次开流的“旁路→DC→旁路→DC”四个实际请求：两个旁路输出相同，两个 DC 输出相同，且 DC 输出与 430 的相同真实输入结果逐字节一致。r4 合计 52 direct jobs，failed／cancelled／first_error 为 0。worker/client 终态退出，正式模块、媒体图、服务和资源恢复，无新增相关 fault、taint 0。正式仍 420 r31／r26、419 core／adapter、Image363／DT389，未永久安装。

[真实 IPA4 检查](ipa-validation.json)包含签名、原厂 DS4 块、可选能力、缺 lux hold、busy、失败、旧回执、停止／重启历史；TMC／LTM 数学和数值历史实现逐字节沿用 424。[实际维护会话函数](session-validation.json)在 ASAN／UBSAN 和 ARM64 qemu 执行七个转换／失败保持场景。[源码审计](source-validation.json)对两个补丁零 fuzz／offset 重放，校验实际产物和共享构建输出恢复。内核 10 个匹配模块 W1／Werror 零诊断；最终用户空间 build 7 成功。

实际查看未调色的 NV12 解码样本，场景可辨认，仍有明显雾感／偏色。不能据完成计数、参数变化或照片可辨认宣布完整画质校准；本轮也没有重新做 AF 或光学全矩阵。

## GTM 与接续范围

[已有原厂 GTM 定位](gtm-location-validation.json)核对四份原厂文件的 45 个 IFE/BPS module roots，区别于内部子树目录；14 个普通 IFE 模式查询均与本机原模式管理器匹配。保留本机 `IFEGTM10::Execute` 和 `IQInterface::GTM10CalculateSetting` 指令供继续恢复。**目录／模式选择通过不等于 GTM 数学、寄存器应用或生效版本已通过。**

接续须执行本机 GTM 数据解析与数学，补 IFE 参数块及真实 ACK 生效版本，再将对应图像的 GTM／ADRC版本绑定到 IPE 和最终历史。顺序仍为“统计→后续 IFE GTM 应用→对应图像 IPE→最终成功提交”，不能拿当前图像直方图倒称已改变上游 GTM，不能清零原厂非零 GTM 份额来宣称完整。

当前实拍范围为主摄 4608×3456、FULL640×480／PD10160×120、single-exposure linear AE/AWB。其它摄像头自动双遍、其它尺寸／视频、第五 2MP、个体光学校准和多摄同步仍见 [363 剩余清单](../kernel363/REMAINING-CAMERA-SCOPE.md)。前摄原厂 TMC 关闭策略保持。原件、指令、系数、完整日志和照片仅私存，公共仅自有代码与脱敏证据，本地提交、不 push。
