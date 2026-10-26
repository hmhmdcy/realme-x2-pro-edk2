# 243：开窗接收复测、active MCFG 与 DIAG 传输诊断

2026-10-16。保持当前 Linux、236 启动/boot235；没有刷 Android、重启、替换固件或写 NV/校准。用户将手机移到窗边并开窗，报告其它手机可收到 GPS；仍记录为室内开窗，未伪称无遮挡室外。**开窗与Wi-Fi关闭两轮各90秒，共1722个有效SNR字段全0，根因尚未定位。** 新证据包括active配置、ldo10的UFS来源、无线电对照和DIAG首次版本响应；没有取得Android初始化报文或modem GNSS原始测量日志。

## 本轮实际结果

复用226-r3已验证同CID程序，核对源码/二进制摘要、GET/REGISTER/START/STOP白名单，standalone/HIGH观察90秒。89次SV事件中29次有普通/扩展列表，累计862个有效SNR字段全0且SEARCH；两类列表的重复累计不是862颗唯一卫星。另60次缺列表，不计零值。Start/Stop确认、CID释放、close成功。[会话](window-session-validation.json)、[严格解码](window-analysis-validation.json)

| 字段 | 242旧窗边会话 | 243开窗会话 | 可以推出什么 |
| --- | --- | --- | --- |
| 有效SNR字段/正值/TRACK | 946 / 0 / 0 | 862 / 0 / 0 | 当前 QMI LOC 接收结果仍无有效捕获，问题位于应用/GeoClue之前；不据此判定天线坏 |
| PGA原始字段 | −2至0 | −10 | 接收调试指标变化，含义不能扩写成LNA使能 |
| GPS AGC字段 | −0.78至0.37 | −12.15至−10.46 | 不具备相同输入功率的校准基线，不能单凭该值判强干扰 |
| GPS jammer原始字段 | 60至62 | 70至71 | 数值升高；没有该固件的标定阈值/单位，不换算dBm，不宣称已发现干扰源 |
| PQWM1/XO字段 | 90条 / 11 | 90条 / 11 | 无error_recovery增量；XO枚举11仍未获物理锁定含义证据 |

此次TimeValid=1、TimeSource原值7，TimeUncNs约8.9605—8.9609秒；有效时间不等于取得fix。ADC I139—167/Q132—159仍变化。开窗、其它手机有信号是用户提供的环境参考，不是本机同天线/同接收机的正常基线；不能把接收条件排除，也不应将所有负结果简单归为室内。

随后保持开窗位置/USB采集，单独经RFKill暂时关闭WLAN，再运行相同standalone/HIGH程序90秒：**860个有效SNR字段仍全0/SEARCH、TRACK0、无fix，另61次缺列表不计零值。** GPS AGC变为−3.37至−3.28，PGA仍−10，GPS jammer仍71；这是两段不同时刻的对照，没有A/B/A或输入功率标定，AGC变化不能单独归因Wi-Fi。结果仅说明“关闭本机Wi-Fi这一项未恢复接收”，不能排除其贡献、外部干扰、USB/显示噪声或其他RF问题。[WLAN会话](wlan-session-validation.json)、[对照解码](wlan-analysis-validation.json)

控制器逐轮确认WLAN softblock保持，自动恢复原RFKill状态，NFC/BT的RFKill状态保持。最初健康检查在Wi-Fi重新关联完成前要求NM设备state100而失败；后续只读确认自动重连到state100、WirelessEnabled=true、softblock=false，没有重启网络服务、改连接配置或再次切换无线电。[恢复过程](wlan-control-validation.json)、[最终状态](final-health-validation.json)。该轮正常Stop/release/close、trace无丢失并删除，包数据库/MM/辅助worker保持，无新增WARN/Oops/GPU/DSP fatal。

独立trace在Start前开启32种clk/regulator事件，取前、5/30/75秒及后快照，并增加genpd和TFTP/RMTFS日志对照。筛选的XO/RF/MSS时钟AP事件0，调压器事件28；AP可见域保持原状态。RPMH显示Y、固定标称频率及genpd的off-0都不是物理RF时钟或LNA电压测量，原因沿用[242源码核对](../kernel242/clock-source-validation.json)。不从这些摘要认定modem电源关闭。

为追查同名ldo10，随后在GNSS停止时建立另一独立trace，仅为`regulator_enable`的ldo10事件加stacktrace，观察35秒。**抓到两次使能，调用栈都经过`ufshcd_runtime_resume → ufshcd_resume → ufshcd_enable_vreg → regulator_enable`，来源为UFS运行时恢复。** 实际运行DT的`ufshc@1d84000/vcc-supply`恰好引用ldo10，范围2.504—2.960V；与先前同名2.504V调压器线索吻合。[调用栈归因](attribute-ldo10-validation.json)、[实际DT引用](map-ufs-supplies-validation.json)

这是本轮排除误判的具体结果：观察到ldo10跳变不能当作LNA动作。它证明所抓两次idle事件属于UFS，**未逐条证明此前90秒全部28条同名事件也属UFS**，也未证明本机真正LNA已经上电。该35秒未启动GNSS、未写调压器；trace无丢失并清理，故障增量0。

TFTP新增2行/RMTFS新增4行，逐字分析全部为QRTR del_client及其接收提示；**没有记录到本会话新的文件打开/配置加载，也无新增错误关键字**。这不是“请求文件成功”或“modem内存配置正确”的证据。原始文件服务内容保持私人。

## 当前配置与厂商初始化对照

PDC以六个GET-only事务查询platform/software的selected、list和info，ACK/indication均成功，各CID都释放关闭。1个platform、25个software配置，active ID均存在于列表、无pending；与207原生收据比较，两类active ID都相同。platform长度12636、version134224128；software长度35524、version134285321，存在同长度MCFG源候选。没有load/select/activate。[实时查询](query-pdc-validation.json)、[历史比较](pdc-runtime-comparison-validation.json)

首版比较读取了不存在的历史路径，结果保持null；后续找到`k207-pdc-queries-r2`及`k207-pdc-details`才完成ID比较，不将null改写为初次即验证成功。配置ID/长度/描述相同不是active内容的逐字节证明，更不是Android当时active配置的证明。

只读挂载本机vendor（ro,noload,nosuid,nodev,noexec），检查9项初始化文件，7项存在且与242重建ROM完全同hash；另2项class_core/post_boot脚本在两边都不存在。已卸载，没有执行厂商脚本。[本机读取](collect-vendor-init-validation.json)、[逐文件比较](vendor-init-comparison-validation.json)

ROM的vendor/bin、vendor/odm/system init文本共匹配13文件69行；GNSS rc及选定MPSS脚本中未发现明确板级RF/LNA GPIO/regulator操作。init.qcom.sh的MCFG准备与文件服务相关，不能把Android目录复制动作当作Linux必须照抄的RF开关。静态rc提到缺失脚本不能证明Android执行过它；vibrator的rf_hz命中也不是射频。[离线扫描](rom-init-validation.json)

结合242的34个MPSS文件及173个MCFG源文件与原机备份匹配，当前没有支持“换错整套modem固件/active配置漂移”的新证据。尚缺modem运行时RF profile、RFFE/LNA供电和实际XO测量，不能以静态文件相同排除这些差异。

## DIAG 新入口及失败范围

依据[linux-msm/diag固定提交](https://github.com/linux-msm/diag/tree/23c12c167e93215853af4e59c021551767f6fec8)分析QRTR端点，摘要见[source-lock](source-lock.json)。DIAG是service4097，instance按原始值0/1/2/4使用，不套普通QMI的version/instance移位。AP临时发布control/data/DCI并lookup command后，modem实际返回feature mask 0x03fef7、preset数量2并发布CMD；初始查不到4097不能直接解释为不支持诊断。[被动采集复核](inspect-diag-result-validation.json)

被动探针只发布/删除命名服务，没有发DIAG控制负载。r2错误bind本地BCAST地址在发布前失败，已关闭socket；r3完成后首版guard误要求远端CMD也消失，后确认我们拥有的3个AP服务和4个socket都清理，保留modem拥有的CMD不是清理失败。失败收据均保留。

Python r2只做传输feature协商和只读查询，**VERSION返回55字节/code0**；build-id、log-range、get-mask随后超时。VERSION响应后约1ms，观测到原modem control peer的DEL_CLIENT；因果未定，后续不能把该旧peer视作已确认存活。完整诊断daemon会额外设置mask/mode/buffering，本次没有运行它。[版本及超时](query-diag-validation.json)、[端点时间线](inspect-diag-endpoints-validation.json)

首次GNSS+DIAG worker在VERSION前置检查失败，**未启动GNSS、未发日志掩码**，独立trace及端点已清理。r4用新AP端口、uint32 feature回复，再比较connected raw/non-HDLC/HDLC三种VERSION封装，均未再收到版本响应；这几次只测试VERSION，不含NV/内存/RF命令。[首次失败](inspect-gnss-diag-failure-validation.json)、[重连](query-diag-reconnect-validation.json)、[封装比较](query-diag-framing-validation.json)

上游router在AP本地处理0x73 LOG_CONFIG，所以直接转给MPSS后get-mask超时也不能据此断言固件不支持日志。准备的四项GNSS日志掩码仅通过离线格式/位图检查，本次从未执行enable或zero-reset；没有原GNSS DIAG日志可解码，不能用“日志零包”推断RF没上电。后续先修复DIAG连接生命周期，再以真实报文版本/长度解码测量，避免将诊断传输失败当成GNSS根因。

## 下一步有区分力的证据

优先查清modem DIAG控制通道断开/重连顺序，获得接收机测量、增益/噪声和时钟质量的可解释原始字段；当前的QMI/PQWM1只能定位到接收结果全SEARCH。随后对RF干扰或供电候选做有依据的单变量对照。USB实际为high-speed，不能直接套USB3 SuperSpeed干扰结论；若做断线对照须先准备自动采集与重连导出，保证程序、时间和位置可比。

本轮没有证明缺失LNA GPIO、RF_CLK票或某个Android HAL调用；不据猜测部署板级补丁。其它手机的Linux修复案例及适用范围见[联网研究](RELATED-LINUX-GNSS.md)。

## 收尾与私有证据

首批74项与WLAN/归因补充36项，共110项原生归档成员逐一验证长度/SHA256。独立trace均删除，GNSS无残留进程，AP DIAG服务0，Wi-Fi恢复并连接，MM位置Enabled0/Signalsfalse/rate30，watch daemon running但active=false、数据worker计数仍0。三DSP运行、taint0，整阶段WARN/Oops/GPU/DSP fatal增量全0。[首批导出](evidence-export-validation.json)、[补充导出](wlan-evidence-export-validation.json)、[最终状态](final-health-validation.json)

原始NMEA、PDC ID、版本响应、启动身份和完整硬件快照在`E:/edk2-samurai-out/kernel243`，不公开。生产驱动、MM/辅助服务配置和包数据库未改。其余外设继续沿用240；243不是整机新验收。
