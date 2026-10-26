# 250：Android 实际 GNSS HAL 初始化与室外正信号

2026-10-17。用户已自行刷回 Android 16 / crDroid，并授予 KernelSU shell root。本轮先在原开窗窗边采集，再按用户确认移到无遮挡室外，通过 Android 原生 TLS 无线 ADB 继续；身份与同一次启动均重新核验。当前 Android 是第三方 ROM，不能称为已验证正常的原厂系统基线。

**室外已取得真实正 C/N₀ 和 TRACK，首轮 180 秒仍没有 GNSS fix。Linux 此前均在窗边测试，尚无同一室外位置的 Linux 对照，零 CNR 根因仍未闭环。** 用户表示高德能定位到所在小区，精度和来源不确定；同时段框架 GPS 成功位置上报仍为 0。保留应用定位可用这一观察，暂不据此确认卫星定位成功。

## 实际初始化采集

使用 [Android init 的 sigstop 调试流程](https://android.googlesource.com/platform/system/core/+/refs/heads/android11-release/init/README.md)：只停止一次 `gnss_service`，让 init 在子进程 exec 前暂停，附加系统 strace 后恢复，并清除暂停标记。服务仍由 init 按原 gps 身份与 SELinux 域启动。未手工以 root 身份执行厂商 HAL，也未修改厂商配置。

运行映射中的六个库均逐字节哈希匹配 [241 的实际 ELF](../kernel241/hal-elf-validation.json)，包括 libgnss、libloc_api_v02、libgps.utils、libqmi_cci、libloc_core、liblbs_core。因而这次运行报文可与 241 静态分析对应，不再以文件存在推测实际采用。

窗边初始化 trace 为 4,599,775 字节，严格重组得到 1,839 个 QMI 包，其中同一 LOC socket 1,837 个；孤立 resumed 为 0，末尾六个未完成调用不计入包，TLV 截断/重复拒绝计数为 0。采集后的 trace 传输 SHA256 与手机一致。实际 wire、坐标、卫星标识、设备身份和原始日志留在工作区外私人目录；公开 [解码器](decode-android-hal.py) 只在摘要输出质量统计。

## 与 Linux 的逐项比较

| 项目 | Android 实际执行 | Linux 已知路径与结论 |
| --- | --- | --- |
| 事件注册 `0x21` | HAL/MHAL 标签，AFW=1，notification=false，同一 client 持续持有 | 生产 MM 缺附加字段；241 的 AFW/master 原生试验已补过，窗边仍无正信号，尚无室外同条件对照 |
| master `0xBA`、测量 `0x88` | 确实发送，测量 mask=63；成功 ACK/完成状态 | 241 已在 Start 前成功补入，不能把“缺调用”直接当根因 |
| 能力查询 | `0x1E/0x9D/0xA9` 与三次 `0x84` | 有查询差异；查询成功不证明 RF 上电 |
| GPS lock `0x3A` | 实际出现 4/3 两种值，最终 3 | Linux MT=3；245 的 NONE 对照无正信号 |
| SUPL/LPP/LPPe `0x54` | LPP 先 1 后 2，LPPe CP 后为 2，UP 为 0，另有配置字段 | 生产 MM 没有完整厂商配置链；属于待重放差异，未证明与原始 CNR 的因果 |
| blacklist/type `0xB6` | 两次，有效性掩码与数值掩码成对出现 | 不将全 1 的有效掩码误读为禁用所有星座 |
| NMEA `0x3E` | 初始化 mask=131072，主要 modem 调试句；标准 NMEA 可由 HAL 合成 | Linux 标准 mask=63；原始 SV/raw 质量可直接比较，字符串数量不能当卫星数量 |
| CTU/PACE `0xCA/0xCB` | enable=0，两项 ACK 均 result1/error94 | 该运行路径没有成功应用这些项，不能列为 Linux 必须补上的已生效 RF 开关 |
| 平台电源 `0xD0` | 完整初始化及窗边会话中没有发送 | 241 Linux 探针 ACK result1/error57；不能再以静态条件分支推定 Android 必然发送 RESUME |
| Start 模式 | `0x4A` mode=2，HIGH=3，通常 1000ms；存在系统/应用请求变化 | Linux standalone=4、HIGH=3；后续需要同天空条件比较模式与辅助策略 |
| Wi-Fi AP数据注入 | 室外实际出现 `0x7D`，两次 ACK 成功；253核对官方IDL后更正，此消息不是UTC注入 | 真正UTC消息为`0x38`；不能用该报文证明时间辅助成功，见[253更正](../kernel253/PROTOCOL-CORRECTION.md) |
| MEMSHARE | Android 启动日志确认 client1 查询/分配 5,242,880 字节成功 | 247 Linux 观察到 client1 未提供；属于具体运行差异，尚未验证它是零 CNR 原因 |

[实际请求顺序、ACK、配置路径与库匹配](android-init-validation.json) 不含 master 注册载荷、服务器原文或整包报文。ACK 与异步完成是两类结果，未收到完成时不补为成功。更早的 [241 比较与负结果](../kernel241/README.md)、[246 modem 原始零 CNo](../kernel246/README.md) 仍保持原有接收环境和统计范围。

## 窗边与首轮室外

| 指标 | 窗边约 3 分钟 | 室外 180 秒 |
| --- | ---: | ---: |
| SV 事件 | 187，均缺卫星数组 | 182，均有普通和扩展数组 |
| 有效正 SV SNR 字段 | 无字段，不能计为测得 0 | 1,354，含普通/扩展重复 |
| SV 最高 C/N₀ | 无有效字段 | 44.7 dB-Hz |
| 原始测量 `0x86` | 1,122 事件均缺数组 | 1,273 事件，357 个有效单条数组，916 个缺数组 |
| 原始测量正 CNo | 无字段 | 357/357，最高 41.7 dB-Hz |
| 框架 CN0 统计报告 | 0 | 148；最强四颗均值约 30.81 dB-Hz |
| 成功位置 / TTFF | 0 / 0 | 0 / 0 |

普通列表单独统计，避免与扩展数组重复相加：每份最多 GPS 正信号/跟踪 1 颗、GLONASS 1 颗、QZSS 2 颗。GPS 有星历的跟踪目标最多 1 颗；GLONASS/QZSS 的有效星历标志均未置位。该结果没有证明已具备定位所需的可用测量与几何条件。星座枚举按 [公开 Qualcomm LOC IDL](https://android.googlesource.com/device/google/marlin/+/2772c7e5d4b1e21dc0aad600d3acc84db0476145/location/loc_api/loc_api_v02/location_service_v02.h) 解释：QMI QZSS=7，与 Android 的枚举值不同。

室外 trace 5,558,447 字节、3,133 个 LOC 包，12 个请求 ACK 均成功；传输 SHA256 一致，解码错误 0，采集结束 TracerPid=0、GNSS 服务 running。用户在本轮使用过高德，框架记录了其 GPS、被动位置和原始测量订阅，因此这是多个实际应用请求共存的观察，不能称为仅 GPSTest 的单变量实验。

随后续测 300 秒，沿用此前室外测试安排，用户未另报位置变化。trace 为 8,162,329 字节、5,144 个 LOC 包，SHA256 与手机一致；同 HAL 进程及同 LOC socket inode 已独立核验。301 次 SV 事件含 520 个正 SNR 字段（含普通/扩展重复），最高 34.7 dB-Hz；82 个 raw 记录为正，最高 29.6 dB-Hz，其中 fresh=true 为 3。位置 status0 和框架成功位置/TTFF 仍均为 0。信号比前轮弱，不能把这段时间的变化唯一归因于软件配置；本阶段没有改配置。结束后 TracerPid=0、服务 running，采集器与日志进程已退出。

用户另报原装系统的一加 15 在 GPSTest 可见卫星/CN₀、但无 Fix，未明确该机测试环境。该现象本身不足以证明 APP 故障。[官方 FAQ](https://github.com/barbeau/gpstest/blob/master/FAQ.md) 的位置显示依赖已取得的位置；本轮同时采用框架和 modem 的独立证据。本机 GPSTest 的精确/粗略位置权限均已授予，FINE_LOCATION AppOps=allow，GPS 请求真实生效。查询官方 release API 时最新版本仍为 v3.10.6，与本机所装一致；没有因此排除所有兼容性问题，也没有以一加的表现认定 realme 硬件异常。

## RF、时钟与配置判断

1. Android 室外有真实正测量和 TRACK，证明至少部分卫星接收及测量链路能够工作；不能继续把整条链路持续关闭或完全损坏作为既定事实。此前窗边负结果不足以区分环境与 Linux 初始化。
2. `PQWM1` 的 XO 原值始终 11，clock_bias_unc=321；这两个值在无测量的窗边和有正测量的室外均存在。Linux 246 online 的同类数值也出现过。因此不能把 XO=11 直接解释为失锁、或把 321 直接解释为零 CNR 原因。
3. 窗边 TimeValid=0、TimeSource=255；室外出现有效时间和 source3—7。ADC/PGA/AGC 有变化，但缺电气标定，不能转换成 LNA 电压、天线功率或物理 XO 锁定结论。
4. HAL 初始化多次打开 `/vendor/etc/gps.conf` 返回 ENOENT；现有文件位于 `/odm/etc/gps.conf`，本次 trace 未见 HAL 打开 ODM 文件。这是实际配置路径问题，可能影响辅助与策略；在这一现状下仍已出现室外正 CNR，不能称其必然导致全零。尚未做配置映射 A/B，也未修改 vendor/odm。
5. Android 内核在任务专用目录尝试只读挂载 debugfs 返回 ENODEV，未取得 clk/regulator/gpio summary。旧文件中的 ENOENT 也不是测得时钟或供电为 0。没有借此改寄存器、NV、校准或启动参数。

当前继续保留 Android。高德应用定位可用、卫星定位尚未验证成功，分别记录。Linux 返回之后最有区分力的试验是同一室外位置、相同固件与天线状态下重跑原始质量采集；在完成它之前，不发布 RF/LNA 根因或 GNSS 修复完成结论。

## 当前操作与复核

本轮没有刷写、格式化、OS 重启、改厂商分区或写 NV。无线 ADB 的地址/端口变化后通过 mDNS 重新发现，再核对同机与同 boot；私人端点未写入公开文档。GPSTest 为官方 v3.10.6，保留独立 CSV，结束强停可能丢尾部缓冲，因此以已完整导出的 modem trace 和框架快照为主要证据。

解码器严格检查 QMI 完整包长度、TLV 唯一性、SV 数组步长和 raw 数组长度。沿用的普通/扩展 SV、非有限/无效字段、空数组及 malformed raw 回归均通过；新解码器对窗边历史 trace 的包数和质量统计与先前独立结果一致。Android session ID 由系统选择，成功位置统计不再沿用旧 Linux 探针固定 session ID 的限制。

[质量统计与解析回归](android-quality-validation.json) 不含原始位置和卫星身份。离线复核可运行 `python3 reference/kernel250/decode-android-hal.py 私人trace --output-dir 私人输出目录`；输出目录会包含原始 wire，须继续按私人资料保存。若后续附加到同一 HAL 时没有重新注册事件，解码器默认拒绝猜测 LOC socket；只有独立验证同 boot、同 HAL PID 和同 socket inode 后，才可使用 `--loc-fd` 指定继承的描述符。

[当前检查点](../../NEXT-SESSION.md)；[248 Linux 返回备份](../kernel248/STATUS.md)。原始 userdata/boot 返回备份继续保留；Android 到 Linux 实际往返仍未执行。
