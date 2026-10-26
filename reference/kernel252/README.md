# 252：原厂室内 SBAS 跟踪、基带零测量与 Linux 对照

2026-10-17，继续使用原厂 realme UI 2.0 / Android 11、`RMX1931_11_F.16`，同251启动。按用户要求在当前位置室内排查，没有要求移到室外，也不把另一台手机作为前提。系统有 APatch root，未发现已安装模块；本轮没有刷写、重启、重启 HAL 或修改厂商配置。

**仍未取得卫星定位，但已把故障现象定位到基带搜星/测量阶段：原厂状态中的正信号全部来自 SBAS，GPS/GLO/Gal 的真实测量持续为零。当前证据不能确定是环境、RF/天线、时钟或更深配置中的哪一项造成，也不能宣称 Linux 独有故障。** [结果摘要](summary-validation.json)

## 有信号为何仍无定位

本轮分别观察原厂应用路径及直接 QMI 路径。累计字段不是唯一卫星数；普通/扩展 SV 列表可能重复，下面的原始 DIAG 字段不含这种重复格式。

| 路径与时段 | 实际接收/测量 | 定位 |
| --- | --- | --- |
| 原厂 HAL，辅助刷新前 | 94次SV事件；正信号只在SBAS，普通列表每次最多3个正信号、2个TRACK，峰值33.9 dB-Hz；GPS/GLO/Gal没有正SNR、TRACK或星历 | 成功位置0 |
| 请求刷新辅助数据后 | 128次SV事件；正信号仍仅SBAS，最多1个TRACK、峰值33.7；普通导航星座仍未有效跟踪 | 成功位置0 |
| 原厂内核直接QMI standalone/HIGH，90.054秒 | 89次SV事件，3664个有效SNR字段含双格式重复、全0/SEARCH | 成功位置0；Stop、注销及close均完成 |
| 再次直接QMI，同时采DIAG，90秒 | GPS900、GLO810、Gal160个实际C/N₀字段全部0，合计1870；各90份测量报告 | 无TRACK/fix |
| 原厂GPSTest/HAL，同时采DIAG，60秒 | SBAS峰值34.0，普通列表每次最多1个TRACK；GPS590、GLO531、Gal160个原始C/N₀字段全部0，合计1281 | 成功位置0 |

前两段含启动和查询等待，94/128是收到的事件数，不能当作严格90/120秒等长样本。[辅助对照](aiding-validation.json)、[直接QMI会话](native-session-validation.json)、[直接QMI+DIAG](native-diag-validation.json)、[原厂HAL+DIAG](hal-session-validation.json)、[两轮原始测量](native-measurements-validation.json)、[HAL原始测量](hal-measurements-validation.json)。

251预热CSV的61个正C/N₀完整记录也全部是Android constellation enum2，即SBAS，与本轮QMI system3交叉一致。[CSV复核](warmup-251-constellation-validation.json)、[Android官方枚举](https://developer.android.com/reference/android/location/GnssStatus#CONSTELLATION_SBAS)。SBAS提供增强信息，部分接收机还可利用其测距；这里的结论是**实际没有获得足够有效导航测量**，不是声称SBAS在任何接收机上都不能参与定位。[FAA说明](https://www.faa.gov/about/office_org/headquarters_offices/ato/service_units/techops/navservices/gnss/waas/howitworks)

卫星条目中的almanac可用，并不等于已捕获信号；本轮普通GPS/GLO/Gal的ephemeris均0。Android网络位置、注入的位置以及内部缓存坐标均不算卫星fix。原厂能报告SBAS的真实正值和TRACK，也不支持“整个接收机始终关闭”的断言。

## 排除到什么程度

| 检查 | 原厂实际结果 | 与Linux的关系及限制 |
| --- | --- | --- |
| 辅助轨道有效期 | LOC GET返回起点2026-10-16 22:00 UTC、168小时；刷新请求前后均有效 | 不能用“完全没有/已经过期的XTRA”解释当前全部现象；不证明每颗卫星数据完整 |
| 刷新动作 | 发送标准force_time_injection、force_psds_injection；后段未见新增0x35轨道注入或0x38 UTC注入；253更正：0x7D其实是Wi-Fi AP数据注入，xtra-daemon没有对应下载活动 | shell命令返回不能冒充刷新成功；没有清空辅助数据或冷启动复位 |
| 星座控制 | GPS=0（mandatory/always enabled）；GLO/BDS/QZSS/Gal=1（internally enabled） | 与221 Linux返回相同，没有发现这些星座整体被禁用 |
| 黑名单 | 已返回的GLO/BDS/QZSS/Gal四个掩码全0 | 与221相同；GPS/SBAS/NavIC字段未返回，不能把缺省当零 |
| 基带状态 | DMS=ONLINE；PDC活动平台、软件ID分别与243 Linux相同 | 不是整个modem离线；ID相同不证明所有运行时RF配置相同 |
| 固件/库 | 251已逐项验证34个MPSS文件匹配Linux部署、六个运行库匹配250/241 | 本轮仍同启动；不能将当前F.16与250第三方Android16混为同一个原厂系统 |

[有效期查询](validity-query-validation.json)、[开关/黑名单](controls-validation.json)、[DMS/PDC](dms-pdc-validation.json)。GET operation mode来自新建客户端，不能用其standalone值替代原厂HAL实际mode2。固定GET ID先通过本机匹配ELF的APS2闭包调用链核对，又与[高通官方IDL](https://github.com/qualcomm-linux/location-apis-qcom/tree/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948)及221证据一致；没有发送星座、锁或DMS电源SET。

## Linux适配差异

Linux247的2586个原始C/N₀字段全零；当前原厂两轮DIAG的3151个字段同样全零，GPS/GLO主要ObsState原值1、MeasStat字节11062000也相同。因此零信号已存在于modem测量中，不是Linux把正常坐标丢在GeoClue或桌面层。这里是不同时间的对照，旧Linux位置没有建立严格相同天空条件的A/B试验；直接QMI测试运行在**原厂内核**，也不是本轮重新启动过Linux。

Clock body174/前导3、PRX body722/前导5、Spectrum body331/前导2的包形与Linux相同，IMD body60有完全相同样本，Config body72也有匹配。PRX在这两组数据中只有offset76形成两边各自恒定的不同字节；这不是说其余字节逐包相同，也没有得到offset76的电气含义。Clock/PRX完整私有字段仍未解，不能凭ADC、AGC、谱或XO原值判断LNA断电、天线好坏或干扰强度。[不带语义猜测的字节比较](rf-linux-comparison.json)

**Linux仍有明确实现缺口：MEMSHARE client1。** 原厂251启动日志实际分配5MiB成功；Linux247只返回INVALID_ID，没有实际连续内存、物理地址和SCM所有权转交。该差异应继续补齐，但原厂具备这项仍未fix，不能将其直接发布为本次共同行为的唯一根因。[251原厂分配](../kernel251/README.md)、[247实际启动请求](../kernel247/README.md)

后续在当前位置继续核接收端的RF/Clock字段和初始化差异，并在安全持有连续内存、正确转交/回收SCM权限的前提下实现Linux client1 provider；再比较实际捕获结果。当前没有证据支持盲写NV、校准或猜GPIO，也没有把室外测试设为继续工作的条件。

## 采集、失败与收尾

原厂`diag_mdlog`可以读取`/dev/diag`；最初只看输出目录没有qmdl文件，不能据此判定没有响应。通过实际read/write追踪重组出LOG_CONFIG GET响应，取得原始equipment1的3304位日志掩码，全部为0。只临时OR入十个GNSS/RF日志位，每轮之后写回完整原掩码，并以GET响应逐字节确认恢复。第二轮同样恢复；没有使用会清空所有message/event/log设置的`-c`。

两轮GNSS日志分别626/412份，HDLC CRC错误0、完整read截断0、尾部残帧0；恢复阶段也均无CRC错误。请求的DRX147f/BDS1756未产生包，不把缺包解释成字段零。直接QMI及HAL日志都验证完整帧、v0/count/stride，缺记录不计零C/N₀。所有公开摘要不含坐标、卫星标识、设备/启动ID或raw payload。

初版QRTR bind使用node0被拒，改为getsockname取得本地node后绑定；未运行成功的采集不计数据。首版DIAG配置生成器因缺少bitstring依赖失败，该次没有读入自定义mask；随后改为只读CRC表常量并用独立位算法交叉核验。root使用`su --no-pty`避免251的PTY换行扩展；两轮15个源文件和早期GET trace均核SHA256，辅助采集32个文件也逐项核对。[导出核验](export-validation.json)

最终同boot、HAL原PID且TracerPid0、xtra-daemon运行、SELinux Enforcing；所有本轮strace/diag_mdlog/native客户端及GPSTest均退出，应用偏好与251恢复后的原始字节相同，定位开关3/stay-on0、vendor/ODM配置字节不变。收尾初版误用普通shell读取受限PID属性、并把子进程当init服务查询，核验断言拒绝；改为root读PID和实际进程检查后通过，没有因此重启任何服务。[最终状态](final-validation.json)

[固定GET客户端](loc-readonly.c)、[有界直接会话](native-loc-session.c)、[DIAG解帧](decode-diag-trace.py)、[测量解析](decode-measurements.py)、[辅助阶段解析](analyze-aiding.py)、[源码锁](source-lock.json)。解析器只读本地证据；raw输出必须放工作区外私人目录。原始资料在`E:/edk2-samurai-out/kernel252`，保留248完整Linux返回备份；最后Linux全机验收仍240。本轮完成诊断对照，没有宣布定位修复。
