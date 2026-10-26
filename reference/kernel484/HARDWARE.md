# 484 实际安装与默认路径独立缓存验收

验收通过：481 的真实原生 APK 前进 r33/r28 → 回退 r32/r27 → 再前进 r33/r28 已完成，最终保留新基线。两次前进相位共 14 个默认路径用例通过。484 只读取已收原件，没有访问手机、SDK 或执行 target 程序；冻结 481–483 文件未改。

收集原件 234 文件，归档 6,390,546 字节，SHA256 `ae1abfc9ae5c936ca83bce8145b242f373748a8d35a870457feb4e1e3b597bed`，已逐个比对解包文件。实际 worker PID 28188／start_ticks 2003163；终态 state SHA256 `3a6d31ab222c91639017df3c10b24f52d683ae890a903b10899597382452ea9a`。检查器及完整计数见 [inspect-installed.py](inspect-installed.py)、[hardware-validation.json](hardware-validation.json)。

三个 `/sbin/apk … add 精确七包版本` 均为真实事务、exit0；31 份命令回执的 stdout／stderr 哈希及成功终态闭合。961 个数据库条目中，954 个非七包条目各相位不变；回退相位的全部条目逐项等于原始数据库，包括七包。数据库原始备份仅供取证，没有直接覆盖数据库。原始 world 在回退时逐字节恢复；最终 world 只改变七包 pin，其余行字节不变。旧仓库文件及属性保持，新增加的 61 仓库入口精确指向 8 个冻结签名文件；最终模拟使用原生默认仓库，没有临时 repositories-file 覆盖。

四模块／四 profile、文件 root:root／0644、已加载 build-id 与冻结物料相符，67 份原文件备份哈希通过，两个原始 symlink 的目标元数据保留。三次切换前均无 live camera FD，owner_refs=0；固定 worker 顺序先卸 CAMSS、m2m、ICP core、sensor，再替换并反序加载。顺序依据是冻结代码和成功回执，没有独立硬件时间戳轨迹。正式旧 sensor `966b29d8…4059f29` 的真实回退和新 sensor 的再次加载均已闭合。

每个前进相位的实际结果如下；两轮相同，不预设 bootstrap 数量：

| 用例 | 消费／帧对 | IPE 成功 | 数学提交 | bootstrap | 未入队负回执 |
|---|---:|---:|---:|---:|---:|
| 主摄 GST 640×480 | 32 | 32 | 29 | 3 | 0 |
| 广角 GST 640×480 | 32 | 32 | 30 | 2 | 0 |
| 长焦 GST 640×480 | 32 | 32 | 29 | 3 | 0 |
| 前摄 GST 640×480 | 32 | 32 | 30 | 2 | 0 |
| 主摄 RAW 4608×3456 | 6 | 0 | 0 | 0 | 6 |
| 长焦 RAW 2104×1560 | 6 | 0 | 0 | 0 | 6 |
| 主摄 RAW＋640×480 dual | 6 对 | 6 | 3 | 3 | 0 |

合计 GST 消费 256 帧、RAW-only 24 帧、dual 12 对，268 次 IPE 全部 direct 完成，242 次数学提交。四个 RAW-only 用例的 24 条负回执均为实际未入队 observation 的旁路丢弃，不能计作 IPE 失败，也不能写成“全部回执无负值”。所有观察、队列、回执、数学 revision 和同 SOF 历史全量闭合，没有 queued 失败、未 resolve abort 或额外成功未消费帧。processed 用例均有同 SOF PD10 ready、IPE 队列和成功回执；八个 GST 的交付 SOF 均为 0–31。

全部 14 个用例实际 UID10000／CapEff0、有效签名、app=IPA PID；库／IPA／GST 插件 maps 使用系统 `/usr` 文件，安装的 `/etc` 四 profile 与预期哈希一致，没有私有 LD／profile／IPA 覆盖。12 个实际活跃租约的 live mask 为 4–7，stop 均恢复原 0–7；两个长焦 RAW 没有租约且 stop 明确 inactive。主摄 RAW 的 lens 租约活跃不代表开启 IPE。

外部 health r1 原失败保留：`process()` 对所有 `(deleted)` 的泛断言遇到 WirePlumber 的 8 条不可执行 PipeWire memfd 而停止。r2 只允许已识别 `/memfd:pipewire-memfd:` 且无执行权限的 deleted 映射；实际 PipeWire 14 条、WirePlumber 8 条。磁盘文件路径 deleted 或可执行 deleted 仍拒绝，后续 CORE／BASE inode 与 expected SHA 核验保留。r2 实际通过，state 哈希一致，两样本 1.1255 秒、同 boot、taint0、fault delta0、充电限制不变。最终服务 PW28681／WP28687 身份闭合；其 owner_refs=57 与原 baseline 相同且前后稳定，不能与卸载前的 0 引用混淆。

174 条 WARN／ERROR 完整保留：14 条 `/root/.config/libcamera/configuration.yaml` 查找 ERROR、42 条缺静态属性、42 条属性库提示、56 条 rotation 默认、20 条 V4L2 `0x2027` 格式 WARN。另有每例一次、共 14 条 `libcamera is not installed`／添加 `//src/ipa` 的 INFO；实际 IPA／maps 仍为有效签名的 `/usr` 路径。本轮 UID10000 测量程序继承 `HOME=/root`，证明了系统库与已安装 profile 的实际消费，未验证正常用户 HOME 下的个人配置覆盖，也未消除 build-tree fallback 提示；保持已测 ELF 字节。

初版本地检查器错误地要求 RAW 都有活跃租约、以及最终运行服务仍须 owner_refs=0，两次失败及修正依据均另存私有 484；实际原件未改。此次结论只覆盖有限默认 640 和必要 RAW 用例、真实原生包事务及短时健康；不新增 720p／1080p、隔离分支、重启、长稳、光学／画质或 LTM 扰动因果证明。原生全局 hooks 保持启用，但本组包无自带 scripts／triggers，不声称已执行这些缺省不存在的路径。
