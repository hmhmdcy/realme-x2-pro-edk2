# 469：原厂长焦 mode2 的 720p LTM 实际消费

本轮复用468的原厂4208×2368模式、私有原厂IQ／本机标定，以及441模块、461 core、444 IPA6／旧proxy。只增加同帧输入保存与四次回放，不构建Image、SDK或新模块，不改原厂表／控制延迟／capacity／缓冲数。[独立缓存审计](inspect-ltm.py)及[结果](hardware-validation.json)通过。

| 验证 | 结果 |
| --- | --- |
| 实际模式／消费 | 4208×2368；1280×720 NV12隔离普通GST客户端32帧，UID10000／cap0 |
| 同帧自动双遍 | 32消费／32 IPE＝29数学＋3bootstrap；原始回执0重复／负值，FULL／PD10／GTM／WB／成功历史匹配；无SOF缺口 |
| 实际FULL取证 | 动态graph＋真实FD＋35 QBUF／32 DQBUF；全部消费匹配FULL DQ，八CPU事件零覆盖／丢弃 |
| LTM因果 | 固定SOF12的FULL、PD10和最终参数副本，真实→黑→白→同一真实PD10，四次IPE均成功 |
| 输出核对 | 前三次完整NV12互异，真实重复逐字节相等；真实回放与实际GST消费帧的约4096位置采样哈希一致 |
| 恢复 | 原sensor文件/note、正式440／434栈、服务及R8充电配置恢复；worker退出、trace／用户目录清理，camera PM suspended、core/m2m idle，fault0／taint0 |

保存输入取自461现有自动trace点：同一request／SOF的FULL、coarse及实际最终参数，条件为sequence≥12且tone fresh，**不要求AWB锁定**。本案AWB locked帧仍为0。实际消费对照仅为现有GST客户端的采样哈希，未保存完整消费图做逐字节比较；真实重复回放之间则比较全部1,382,400字节。审计独立重建黑／白PD10编码并重算每次完整输入／输出哈希，不仅依赖worker布尔结果。

四次scratch诊断CRC相同、changed_bytes均为0；不能据此声称scratch发生写入。LTM实际消费结论来自固定FULL／参数、仅改变PD10所得的完整输出差异，以及真实输入重复的一致性。720p因果结果不外推长焦1080p；主摄两尺寸因果证据继续复用[442](../kernel442/README.md)。

[prepare-runtime.py](prepare-runtime.py)、[preflight-handoff.py](preflight-handoff.py)、[capture-body-tele.py](capture-body-tele.py)基于已实测467／468工具，仅使用新的`k469-tele-ltm-r1`事务。先卸CAMSS释放sensor节点，再换468 sensor候选；恢复时先卸候选CAMSS，再恢复原sensor及正式CAMSS。原件中的worker展示字段`stage=467`来自旧prefix，保持原样；审计以唯一plan／handoff／namespace和载荷哈希核身份，不用该旧字段冒认阶段。该终态事务禁止重放。

原件59文件、压缩归档4,753,255字节，SHA256 `6869f41ee07ee7bd73866165edb8a51f4e9d7813464369bfdcdf79a5b8c0efda`，仅存私有`E:/edk2-samurai-out/kernel469/runtime-collected-r1`。外部新鲜R8两样本保护有效／error0、29.7℃，100mA SDP／250mA CC及原CV保持；净电流瞬时−8／＋3mA不作持续净充电／图标验收。设备已明确交回充电，后续设备基线以其新鲜交接为准。

[控制延迟审计](control-delay-review.md)区分原厂maxPipeline／probe调度与实际控制生效：306的两帧实测只覆盖mode3；mode2仍待独立曝光／增益阶跃。没有把全局原厂2帧直接当作mode2证明。

[470缓存时序](../kernel470/README.md)显示两模式1080p Pair→receipt中位约38ms，参数返回尾部约15.8–15.9ms，实际串行处理积压；FULL timestamp是完成时间，邻DQ窗口不能冒认物理SOF。下一最小增量复用451一次分配proxy，仅替换这一个载荷并保留调校／缓冲／PLL；需要原始SOF时刻时启用已有452有界环。LSC光学、AWB锁定、长焦AF、编码视频、长稳及其它多摄目标仍未完成。
