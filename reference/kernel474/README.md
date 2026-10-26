# 474：组合候选的原生／隔离1080p与LTM消费

本轮将[473的processed IPE Manager容量租约](../kernel473/README.md)与[451的一次分配proxy](../kernel451/README.md)组合，复用441三模块、444 IPA6及其原签名、468长焦mode2驱动／原厂profile。不重建Image或框架，不改原厂IQ、本机标定、PLL、缓冲数或控制延迟。正式部署仍为440 r32／r27及434模块，候选没有永久安装。

| 定向验证 | 实际范围 |
| --- | --- |
| 原生路径 | 1920×1080 NV12，普通UID10000／cap0客户端32消费、32 IPE；清除强制隔离变量，核对实际进程与IPA映射 |
| 隔离路径 | 同尺寸32消费、32 IPE；实际proxy可执行文件为451候选，进程环境强制隔离值为1 |
| 传感器 | 两段均为原厂4208×2368 RAW10 mode2，输出1080p；保留mode3与本机个体调校 |
| FULL交付 | 实际graph／FD及有界环取证，70 QBUF、64 DQBUF；逐消费核同SOF FULL／PD10及最终参数历史 |
| LTM | 从隔离路径保存同一SOF的FULL／PD10／最终参数，仅更换真实→黑→白→同一真实PD10，完成4次IPE |
| 恢复 | 原sensor文件／note、正式模块／库包、服务恢复；worker退出、trace与用户目录清理，四camera PM suspended、core／m2m idle；外部R8检查通过，fault0／taint0 |

[独立审计](inspect-combined.py)直接检查缓存原件，结果见[硬件报告](HARDWARE.md)及[验收数据](hardware-validation.json)。数学／bootstrap分类按实际成功历史统计；不删除负回执，不把未消费FULL算作输出。两段均核Manager实际mask及正常stop的helper读回恢复，不能据此推断已存在隔离worker的CPU策略。

LTM审计固定FULL和6008字节参数，独立重建1080p黑／白PD10编码、重算完整输入／输出哈希；比较前三种完整NV12输出及真实重复的全部字节。实际GST消费对照继续使用现有客户端的约4096位置采样哈希，不冒认完整消费图逐字节比较。scratch诊断值不作为LTM消费证明。隔离段另有一次输入保存I/O，因此原生／隔离两段不作纯性能A/B。

主摄720p／1080p的同帧自动双遍和独立LTM因果继续复用[441](../kernel441/README.md)／[442](../kernel442/README.md)；原厂长焦mode2的720p因果复用[469](../kernel469/README.md)。本轮补齐该长焦1080p及组合候选的两种进程路径，未覆盖光学LSC／精确crop、AWB锁定、AF、编码录像、长期功耗或多摄同步。

[prepare-runtime.py](prepare-runtime.py)、[preflight-handoff.py](preflight-handoff.py)与[capture-body-tele.py](capture-body-tele.py)复用既有工具，只使用新事务`k474-combined-r1`。先卸CAMSS移除sensor节点再切换sensor；恢复逆序。该事务已终态，禁止重放。原件63文件、压缩归档11,306,790字节，SHA256 `fa55df0c76d3b07f011f55ef9fa3ba85e7968d306e0618754b65b51382ea7ae7`，私存`E:/edk2-samurai-out/kernel474/runtime-collected-r1`。

设备已明确交还充电侧；后续仅离线整理可回退候选包及mode2控制阶跃工具，当前正式基线没有更换。完整多摄／骁龙ISP目标继续。
