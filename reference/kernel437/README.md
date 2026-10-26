# 437：AWB 收敛状态与实际 WB 增益关联

修复主摄自动 tone 候选中的 AWB 元数据掉锁：原算法已有收敛结果，但等待 GTM 回执的帧没有重算 AWB，代码却把这些帧直接报告为 `AwbLocked=false`。现在保留最后一次有效收敛所对应的实际 WB 增益和 SOF；相同增益的等待帧沿用该状态，增益不同不会套用旧状态。无有效 BG、无已知参数、禁用／重新配置和重新开流均清除状态。

普通／隔离 IPA 实拍分别在 50／52 帧达到连续 8 帧锁定，合计 102 张图像、96 次 GTM／TMC／LTM 数学提交及 6 个显式启动帧。两路各有 5 个未重新计算 AWB、但 WB 增益相同的锁定帧。正式模块、服务和资源已恢复，新增故障 0、taint 0，候选未永久安装。[逐帧证据](hardware-validation.json)。

本轮只修正状态关联，没有放宽原 AWB 的区域筛选、最小信号、增益范围、速度、0.015 容差或三次稳定计算条件，也没有用锁定标签代替颜色精度。**绝对色准、光学校准和其它摄像头自动 tone 仍未验收，完整目标保持 active。**

## 基线与因果验证

复用 436 修正 BLS 的原厂主摄 profile，库／IPA／代理均按指纹核对。436 的 AF 实验 205 帧只有 16 次有有效区域的 AWB 计算，扫描期间本来就暂停 AWB。因此另做无 AF、无策略切换的稳态基线；采集器以连续 8 帧锁定结束，240 帧／20 秒仅作有界上限。

原 436 模块在 240 张图像中出现 63 个 locked 帧，但最长连续锁定只有 1 帧；62 次能直接观察到前一帧锁定、下一帧 WB 增益相同且未计算 AWB，却变成未锁定。[基线审计](steady-baseline-validation.json)。这是状态报告错误，不是“整个 240 帧算法没有收敛”。

新增 `AppliedAwbStatus` 绑定实际量化 WB 增益及观测 SOF，不绑定只变化 GTM／LSC 的整包 revision。相同 WB 增益下的后续有效统计可以保留已确认收敛；旧 SOF 不会被后来观察追认，改变任一实际增益也不匹配。无效或未收敛的 AWB 结果会清除状态，缺 BG 时同时复位原算法的稳定计数，恢复后重新满足原条件。缺少配对统计时的 `frameMetadata()` 回退仍不制造锁定结论。

## 验证

- [实际 ARM64 模块测试](awb-module-validation.json)：合成合法 pre-WB 网格，模拟真实 typed GTM ACK 延迟，证明等待期间保留同一 WB 状态、缺 BG 清除、恢复后重新收敛及重启清除。
- [旧模块反例](awb-baseline-validation.json)：同一个 ARM64 测试器加载原 436 IPA，在已收敛后的 SOF5 等待帧复现 locked0／预期1；新模块通过同一用例。失败仅为离线断言，日志私存，没有设备内核故障。
- [实际头文件检查](awb-header-validation.json)：改变有效增益不沿用旧锁定，旧 SOF 不追认，无效／未收敛／复位／非有限增益均处理。
- [IPA 回归](ipa-validation.json)：legacy factory／bypass、原厂 profile 和真实 GTM／成功历史契约通过；未重做无关原厂数学大矩阵。
- [源码及补丁检查](source-validation.json)：仅 IPA `camss.cpp` 和新状态头两文件，零 fuzz／offset 重放后与候选逐字节相同。原 `HardwareAwb`、原厂 BLS／tone profile、库和代理均保持一致。[补丁](0049-camss-applied-white-balance-status.patch)。

实机两种代理路径都保留同 SOF FULL／PD10、实际 GTM cookie／generation 和最终成功数学历史；每路两个 GTM bank，上一 lux 仍来自成功提交。普通路径最终 4772K，隔离路径 4759K，是现有参考模型的估计，不能当作测得的物理白点或色准认证。8 帧连续锁定包含每路 5 个等待帧及重新计算的稳定帧，逐个与实际 WB 和应用元数据对应。

## 产物与下一步

候选 `/mnt/samurai-full282/libcamera437-awb-history/src/libcamera-v0.7.2`，build1／IPA5。IPA SHA256 `a4c0b7e6…`，新签名 `3d2eea58…`；核心库仍为 436 的 `af3bc105…`，代理 `093df5fa…`。原厂修正 profile 仍为 `b4b6daa2…`。内核、板级 DT、传感器和像素数学未修改，继续匹配 434 模块。staging 使用匹配的新 IPA 与签名，不能把旧 435／436 IPA 混入当前验证。

所有现场 worker／client 已终态，未刷写、重启或写 NV／OTP／个体校准。完整日志、图像、原厂数据和运行二进制只存私有 `E:/edk2-samurai-out/kernel437`。准备脚本保留历史阶段前置，不能盲目重放。

下一步扩大广角、长焦的原厂 GTM／TMC／LTM 和真实 PD10 自动链路，再验证前摄原厂禁用／旁路语义及其它尺寸／视频。四摄 DS4 模式资料已在 [426](../kernel426/README.md) 恢复，可优先复用；不要照抄主摄模式。平场、颜色／噪声、完整 OEM tone 分支、第五 2MP、多摄几何／同步等[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)继续保留。
