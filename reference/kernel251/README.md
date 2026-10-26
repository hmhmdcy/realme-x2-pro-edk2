# 251：原厂 realme UI 2.0 室内 GNSS 与 Linux 对照

2026-10-17。重新连接 USB ADB，确认本机为 Android 11/API30、`RMX1931_11_F.16`，存在可用 shell root；用户明确接收环境为**室内**。没有取得成功卫星定位。当前保留该 Android，没有刷写或 OS 重启。最后 Linux 全机验收仍按240，返回文件仍按248。

## 实测结果

先安装已有官方 GPSTest 3.10.6 并授予定位权限。初次屏幕休眠时应用出现后台启动服务异常，没有实际搜星；root 唤醒屏幕、正常解除无密码锁屏并启动后才确认真实 GPS 请求。早期包含未启动时段的180秒观察不能作为连续搜星结果。

随后分别保存预热 CSV 和有界 modem 会话，不能混算：

| 证据 | 信号/测量结果 | 定位结果 |
| --- | --- | --- |
| 原厂室内预热 GPSTest CSV | 61个正 C/N₀ 状态字段，最高34.4 dB-Hz；这是应用状态回调，未取得同时段 modem raw 正测量 | UsedInFix=0，没有 GPS Fix 行；一个尾部不完整状态行不计入信号统计 |
| 原厂室内有界 modem 会话 | 名义180秒，uptime实测179.20秒；179次SV事件，普通/扩展列表合计10024个有效SNR字段全0/SEARCH，TRACK0 | 180次位置事件：status1共179次、status4一次；成功位置0 |
| 同期原始测量事件 | 1074次均缺数组，**没有原始C/No字段，不能说1074个零C/No** | 无可用raw fix证据 |
| 同期框架与第二份CSV | 六个30秒快照的位置/TTFF/CN0报告均0；CSV4835个完整状态字段均0，另有截断尾行 | GPS provider无成功位置，GGA正fix quality/RMC A均0 |
| 247 Linux，室内开窗窗边 | modem DIAG中2586个实际原始C/No字段全0，QMI也全0 | 无fix |
| 250 第三方Android，室外 | SV最高44.7、raw最高41.7 dB-Hz，有TRACK | 180秒及随后300秒均无fix |

10024包含普通/扩展重复格式，是累计字段数，不是唯一卫星数。预热和后续有界会话是两个时段，不将信号波动唯一归因于软件。用户只确认本轮为室内，没有声称与Linux旧窗边位置完全相同，也没有建立原厂和Linux在同一天空条件下的一对一对照。

原厂框架已有network位置，native internal state也出现坐标；后者不能独立作为GPS fix。此次真实QMI包含52次位置注入`0x39`、两次Wi-Fi AP数据注入`0x7D`，均有成功ACK，但成功位置依然0。253已更正此前将`0x7D`误标为UTC的说法；真正UTC注入消息为`0x38`，见[协议更正](../kernel253/PROTOCOL-CORRECTION.md)。注入的数据与成功卫星位置上报是不同方向。

[严格解析与质量摘要](stock-validation.json)保存各阶段统计，不含坐标、卫星标识或原始wire。完整trace5727616字节、3098个QMI/LOC包，LOC由实际`0x21`注册请求识别；60个请求ACK均成功，重组孤立resumed/TLV拒绝/质量解码错误均0，末尾6个未完成调用未计入完整包。沿用250的普通/扩展列表、缺有效位、非有限值、畸形raw数组和PQWM回归均通过。

## 对 Linux 适配的具体意义

| 项目 | 当前原厂证据 | 与Linux的关系 |
| --- | --- | --- |
| GNSS用户态库 | 六个实际映射库的文件SHA256均与250/241分析对象一致 | 可以继续使用原有本机ELF分析；不能简单归因于库版本不同 |
| MPSS固件 | 按242实际部署清单逐项核34个文件，34/34相同 | 排除了这34个固件文件的字节差异；本轮未重新查询active MCFG或运行时RF profile |
| 配置文件 | vendor与ODM的gps.conf均存在；vendor48个启用键、ODM39个。vendor另有10个RF_LOSS键且为0，ODM另有XTRA_VERSION_CHECK，公共键中NTP_SERVER不同 | 250第三方ROM实际打开vendor路径ENOENT；当前文件存在消除了该文件缺失现状，但本轮未取得原厂完整初始化open链，不能冒称已逐调用确认采用。RF_LOSS为0不证明LNA关闭 |
| MEMSHARE | 启动dmesg中client1/proc0查询成功，5242880字节分配成功 | 247 Linux观察器返回INVALID_ID且未提供物理内存/SCM，是真实实现差异；尚无GNSS因果验证 |
| 时间与XO | 本轮PQWM的TimeValid=1、source7、XO原值11、clock_bias_unc321，仍无fix | XO=11在250室外有正信号时同样出现，不能据此判断物理失锁 |

当前结论是：原厂室内也没有fix，并非已经证明“原厂正常、Linux异常”。预热正信号说明原厂状态回调曾报告部分接收；随后全零和此前第三方室外正信号又说明接收有明显时段/环境差异。后续用户明确要求继续当前位置室内排查，不把室外作为前提；[252](../kernel252/README.md)已进一步确认这些预热正信号均SBAS，并取得原厂基带真实零测量对照。Linux MEMSHARE的完整client1 provider及厂商配置链仍值得继续实现/验证，不能直接把某一项发布为根因或修复。

## 方法、失败和收尾

本轮静态构建官方strace6.19，只放入任务临时目录。交叉工具链的新io_uring头将两项保留字段改名，采集工具仅相应调整该无关decoder；GNSS采用的socket/read/write跟踪未改。来源为[官方发行包](https://strace.io/files/6.19/strace-6.19.tar.xz)，源SHA256 `e076c851eec0972486ec842164fdc54547f9d17abd3d1449de8b120f5d299143`。没有替换系统工具或厂商库。

尝试250的init-owned暂停流程时，当前shell域被SELinux拒绝`ctl.stop`，在停止服务前就失败；cleanup显示complete0，不以shell返回0冒充成功。HAL仍是原PID、没有重启。随后只附加当前HAL，采集GPSTest停止/启动带来的实际注册、Start、注入和Stop报文，**不是原厂完整初始化trace**。没有关闭SELinux或修改策略。debugfs的clk/regulator/gpio节点不存在，本轮没有取得对应电气摘要。

原厂su会分配PTY并启用ONLCR。首次二进制流导出发生换行扩展，tar解析只读出首项，已拒绝作为完整归档；关闭该PTY的ONLCR后重新导出，capture29成员中的28个文件、app3成员中的2个文件全部与手机源文件SHA256逐项相同，trace也独立核对一致。首次失败及修复原因已记录。[归档完整性](export-validation.json)。应用原偏好同样逆转一次已验证的PTY扩展后恢复，并以禁用ONLCR的原始读回逐字节核对。

GNSS服务running、TracerPid0、SELinux Enforcing，定位开关仍3、stay-on仍0；GPSTest已停止，测试偏好恢复，vendor/ODM配置原始字节均保持。没有NV、校准、厂商配置或分区写入。[最终核验](final-validation.json)

原始trace、CSV、坐标、设备/启动身份及失败收据只保存在`E:/edk2-samurai-out/kernel251`。公开[分析器](analyze-stock.py)只输出质量/一致性摘要，但会将完整wire保存在传入的私人目录；不要把该私人目录同步到仓库。现有248完整Linux返回备份保持，未执行Android→Linux往返。
