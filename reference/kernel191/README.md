# 阶段191：完整XTRA辅助注入与LOC异步生命周期修复

**四条LOC注入路径的顺序/引用修复已部署。真实50406字节轨道文件经标准ModemManager接口完成50分片注入，固件有效期从0变为168小时。** 其中49个分片的完成indication先于ACK，修复在真实竞态下通过。UTC独立注入和完整清理通过；随后300.56秒标准GPS仍没有有效fix，完整GNSS适配尚未完成。

## 源码缺陷与修改

基于190已部署的固定ModemManager提交`7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a`，保留190辅助能力发现修复。原Inject Predicted Orbits Data和旧Inject XTRA Data均在ACK后才监听完成报文；UTC/位置路径虽先监听，但没有给ACK回调独立持有GTask，超时释放任务后再收到错误回复会访问失效对象。[原始源码](https://github.com/linux-mobile-broadband/ModemManager/blob/7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a/src/mm-shared-qmi.c)

四条路径统一先监听、保存提前的boxed输出、校验ACK后处理完成；ACK与indication/timeout分别持有任务引用，任务只完成一次。分片收到正确完成后才推进；如果完成报文给出Part Number，则核对当前分片，忽略旧/未来分片；缺省该TLV时保留原status-only兼容。Predicted Orbits不支持而回退XTRA前，拆除旧监听/超时并释放提前输出，从头重新分片。[补丁](modemmanager-loc-injection-order.patch)、[源码哈希](source-patch-validation.json)

## 回归与构建

使用实际生产C回调和真实GLib GTask/GObject，模拟QMI传输及输入数据，257个场景覆盖ACK/indication两种顺序、重复、错误、超时晚回复、1至50413字节/多种分片、旧/未来Part Number、无Part Number兼容、回退、大小限制及空输入。ASan/UBSan和泄漏检查通过。190代码的UTC/位置超时晚错误回复在实际g_task_get_task_data中触发ASan捕获的SEGV；两条数据路径漏掉提前完成而不返回。不是实机崩溃复现。[测试](loc-injection-host-validation.json)

移除ACK引用、忽略分片编号、保留回退前旧监听三个变体均在运行时被检出。初版255个测试只看最终发送字节，未检出“忽略分片编号”的变体；补充两个检查推进时序的场景后，才得到257场景和三个负例通过的最终结果。190能力发现回调逐字保持。

复用190的签名APK隔离SDK及native增量构建，只修改mm-shared-qmi.c，ARM64编译告警0（LTO工具的串行编译提示另列）。系统运行库解析和--version通过，构建RPATH已清除，APK数据库未变。原190构建源及未清RPATH程序先备份到手机k191-mm-build；主机190源仍保留，native190构建目录现在包含191源。[构建](mm-build-validation.json)

## 实机完整轨道注入

程序原子更新到`/usr/bin/ModemManager`，仅正常重启守护进程；MPSS和手机均未重启。D-Bus激活文件原样恢复，调试后SetLogging回INFO。XTRA能力1/服务器3、SIM缺失、bearer0和GPS关闭的预检保持。[部署](mm-deployment-validation.json)

重新读取本机广告的全局轨道服务器，TLS下载50406字节文件，URL没有query、fragment或凭据，不发送位置或设备身份。通过标准Location.InjectAssistanceData注入约0.801秒，D-Bus正常完成，同一MM进程保持，期间未启动GPS会话。[下载](assistance-download-validation.json)、[注入](assistance-injection-validation.json)

本机先尝试Predicted Orbits，随后按源码NotSupported回退旧XTRA路径；50次请求、50次ACK和50次完成，Part Number均为1–50。按分片编号关联后，49组为indication先到，1组ACK先到。本机这些indication的事务号没有与对应请求一致，不能简单按事务号归组判断顺序。本次原生覆盖的是XTRA回退路径；Predicted Orbits成功路径仍只有主机模拟覆盖。[报文](injection-wire-validation.json)

独立临时LOC客户端读取固件有效期：注入前0小时/时间戳315964800，注入后168小时/起点2026-10-14 23:00 UTC。两次查询均取得ACK/status0并正常释放CID、关闭设备，证明完整文件被固件接纳，不仅是第一片得到ACK。[前](validity-before-r2-validation.json)、[后](validity-after-validation.json)、[整体核验](assistance-end-to-end-validation.json)

首次before查询脚本错误地assert了GI get_result的成功返回值（该API成功返回None、失败抛异常），已正常清理客户端后退出1。原失败目录和日志保留；修正后的before-r2与after通过，没有覆盖首次记录。

## UTC、五分钟GPS与卫星观察

同步时钟下，独立LOC客户端一次UTC注入取得ACK和status0，并完成CID释放和close_async/close_finish，错误0/无截止退出。190首次UTC清理失败没有改记通过；这是新的完整通过记录。它不等于生产MM时间/位置请求回调已在真机被触发；这两条生产回调的顺序覆盖来自上述主机测试。[UTC](utc-injection-validation.json)

轨道有效后用标准MM Setup(6,false)、1秒刷新运行300.5578秒：295次GetLocation、303条不同NMEA、校验错误0；有效GGA/RMC/raw均0。结束Setup0、恢复30秒刷新/INFO，所列内核故障增量0。[标准GPS](mm-location-stream-validation.json)、[信号质量](nmea-quality-validation.json)

旁路客户端只订阅现有MM会话的GNSS卫星信息，没有额外start/stop引擎。最终15秒观察收到16条事件，全部缺省卫星列表，无法得到有效SNR。初次把缺省List当成错误，第二次又误用GI枚举拼法，均正常释放/关闭；第三次按TLVNOTFOUND处理可选字段后完成。三个独立目录均保留。不能把in-view数量当成实际跟踪，也不能据此直接断定接收环境或RF硬件原因。[卫星观察](sv-observer-validation.json)

## DMS电源与UIM补充对照

五分钟测试结束后发现DMS为shutting-down、MM PowerState为OFF；新短会话中GPS Enabled=6时，两次查询仍如此。源码允许failed状态通过SetPowerState(ON)，因此使用标准MM接口开启一次电源，没有请求基带重启；DMS变online、MM PowerState变ON。[活跃GPS电源对照](active-gps-power-validation.json)

Online后再测约90秒，仍无有效GGA/RMC/raw/CNR，结束GPS0并恢复30秒刷新/INFO。不能把原先OFF单独当作无定位的根因，也没有将这个手工开启步骤包装成持久驱动修复。[Online测试](online-gps-validation.json)、[信号分析](online-signal-quality-validation.json)

开启前后，两卡位的Card Status均是no-atr-received，Slot Status均报告absent/active；这是固件接口结果，不替代物理插卡确认。最初只匹配简单引号字符串的解析器漏掉详细/未加引号的状态，后按原始响应字段复核；开启试验的诊断正则也已修正，执行时原脚本私存，没有重做开启操作。[UIM对照](uim-power-comparison-validation.json)

7036.85秒复核仍同boot/taint0，DMS online、PowerState3保持，MM仍failed/sim-missing、无bearer；GPS0/刷新30秒，三个DSP running、所列故障增量0，NV源manifest核对通过。当前保留普通电源ON供后续蜂窝/GNSS排查，不重复开启或重启。补充23文件已字节快照归档，归档/成员哈希通过。[最新状态](radio-final-validation.json)、[补充归档](radio-supplement-export-validation.json)

## 当前状态、回退与续作

5871.48秒仍是189第二新boot，taint0，MM191运行、能力1/服务器3、GPS关闭/30秒刷新、SIM缺失/bearer0；ADSP/SLPI/modem及SensorProxy三项保持。Wi-Fi服务的NV源manifest核对通过，蓝牙配置及D-Bus激活文件保持，所列故障增量0；全boot189蓝牙重组1保留。USB190故障没有新增恢复证据，继续用严格原密钥Wi-Fi管理。[最终](final-validation.json)

- 当前程序SHA256：`b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc`，源码`949132f3203b78300224a1fb958cbd1fa44202661f35f64dbed4f84f3ff5ed24`。
- 前一版190程序`fbc40848…`在手机k191-mm-deploy/ModemManager.original和主机E:/edk2-samurai-out/kernel191/ModemManager.before191。发行版原程序`4d5a8258…`仍在190备份。回退前重新核对当前进程/身份/哈希，不能套用旧PID。
- 42个实机证据文件、原/新程序已私人归档；归档和每个成员的SHA256均核对通过，NMEA/QMI/设备身份/端点不公开。[归档](evidence-export-validation.json)

有效fix、GNSS-only GeoClue标准客户端和自动辅助加载、接收/RF/平台差异、冷启/长稳仍待解决；轨道168小时不保证跨基带重启保留。生产位置注入没有伪造或发送未知坐标。后续还需把190/191补丁正式入包，本地可执行文件覆盖会被APK更新或旧rootfs重写覆盖。

参考检索了同平台[hotdog路线图](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/roadmap.md)，其中没有可直接复用的GNSS有效fix方案，未据此借用其它机型的射频配置或校准。实体camera、蜂窝真实业务、蓝牙/Wi-Fi/USB稳定性及传感器剩余验收仍按[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)推进，完整goal active。
