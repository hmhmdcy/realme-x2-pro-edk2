# 260：桌面 GNSS 定位通过与无 SIM 电源管理

**Linux 普通桌面应用已收到真实卫星定位。** 拔 USB、放到原厂成功的室外位置后，300秒 GNSS-only GeoClue 请求收到280次 LocationUpdated，其中262次通过旧脚本的严格坐标校验；每次时间戳都与前次不同、距当前时间小于10秒。首个通过校验的更新在请求开始后12.97秒，末个在292.96秒；这是已有辅助数据条件下的结果，不能当作冷启动 TTFF。[室外回收](outdoor-validation.json)、[可复算分析器](analyze-outdoor.py)

GPS 每份报告去重最多9颗 TRACK，C/N₀最高46.7dB-Hz；原始 GPS 测量有2052份新记录，覆盖294.58秒。标准 MM LOC Start 没有指定水平精度，固件默认 LOW，本轮没有额外原生 HIGH 客户端。被动观察器只订阅测量和卫星报告、没有自己的定位会话，其零位置 indication 不能否定桌面应用已收到的坐标。时钟 reset 计数在采集中保持22，不能据此证明与原厂初始化等价；本轮未收到 PGA 报告，不能记为0。

旧采集脚本只接受 `Accuracy>0`，而 GeoClue 2.8.2 的 `get_accuracy_from_hdop()` 对 HDOP≤1 返回0。余下18次更新未保存被拒绝字段，不能追认全部有效，也不能直接计为18次丢星；严格子集中的间隔同样不能当作射频失锁。1/3/0这些上报值来自 HDOP 映射，并非实测米级误差或零误差。后续[诊断客户端](geoclue-validation-client.py)已改为接受有限、非负精度，记录每次事件的判据、相对时间和新鲜度，不输出坐标或 GNSS 绝对时间；原始本轮记录保持。

已部署 `samurai-gnss-assist 2-r1` 和配套旧系统版本约束包。此前实机四轮桌面请求通过，辅助服务自动完成两次 LOW_POWER → ONLINE → LOW_POWER；本轮室外又自动完成一次上线和低功耗回收，停止后 Enabled0、SignalsLocation=false、刷新率30、PowerState2，无手工规范化设置。[实机开停](lifecycle-validation.json)、[安装核对](installation-validation.json)、[代码与测试](../../linux-port/packages/samurai-gnss-assist/)

259的 OFFLINE 状态不能通过正常 ONLINE 或 LOW_POWER 恢复，普通 modem Reset 的成功回包也没有改变实际状态。清理客户端后重启一次 Linux，严格固定原 SSH 密钥，重新核对不同启动身份、相同内核/根设备和3个程序配置哈希。新启动 DMS 为 SHUTTING_DOWN，正常 SetPowerState(3) 后 GET 确认 ONLINE；随后 ONLINE → LOW_POWER → ONLINE 的请求和独立 GET 均成功。旧257/259启动 guard 已失效，当前 guard 为 `/var/lib/samurai/k260-work/boot-id-private.txt`。

新策略只作用于 `realme,samurai`、MM失败原因为缺SIM且无SIM对象的 modem，并仅响应实际 GPS 来源。初始 PowerState1 时先 GET DMS，只从 SHUTTING_DOWN 恢复；显式 OFFLINE 保持不动。服务只回收自己建立的在线状态，空闲使用 LOW_POWER，不调用 OFFLINE 或 Reset；预先在线的状态、外部电源改变、服务替换和不确定的失败回包都保留，不盲目重复写入。

14个生产控制器回归场景在 PC 和实际手机均通过，包括立即停止、模式查询中取消、服务替换、失败不重试、预先在线、外部改变和释放失败。签名校验、原始回退包载荷匹配及升级模拟通过后，仅升级辅助服务和兼容约束包；958包数量、ModemManager进程所有者和其203版本均保持。新的249 MM候选没有因此上机。[版本约束配方](legacy-stack/APKBUILD)

实机 UID10000 四轮请求为0、15、0、20秒。两个持续请求由新服务自动上线和回收；两个立即停止的请求没有留下电源租约。最后45秒空闲及清理后20秒观察中，Enabled0、SignalsLocation=false、刷新率30、PowerState2，无手工规范化设置。此次手机已拿回，具体室内摆位未重新确认，且测试早期网络时钟尚未同步；零坐标不能用作室外接收性能结论。

随后网络校时已同步（chrony stratum3，4个源在线），辅助服务成功完成空闲 UTC 注入和客户端释放。没有手工设置系统时间或绕过同步检查。室外采集在拔 USB 后等待90秒再执行，临时会话 inhibitor 和 Wi-Fi 省电设置均已恢复。22个本地导出文件逐项 SHA256 核对，测试成功与无线 SSH 长连接无关。suspend_success为0、BOOTTIME与MONOTONIC差接近0，无本轮系统休眠或 WLAN/remoteproc 崩溃证据。收尾再次核对生产程序哈希，移除测试入口，GPS空闲、隐私和原配置恢复，taint0。[收尾核对](cleanup-validation.json)

无线 SSH 仍未稳定。电脑原路由选 Mihomo；普通单机路由添加权限不足，随后通过其[本地 API](https://wiki.metacubex.one/api/#configs)临时只排除此手机，读回确认、路由选回 WLAN，SSH仍失败。25秒仅采本电脑与手机的网络头：手机看到9次ARP请求、发9次回复，却未见TCP22；SSH监听、Wi-Fi关联均在。尚不能区分AP、电脑邻居处理和手机发送路径。临时代理排除已撤回，原配置文件未改；不能把这次诊断称为无线修复。[无线诊断聚合](wireless-validation.json)

尚未证明电源差异是259室外失败的唯一原因，也未修改PGA、RF、物理时钟、NV或校准。默认 LOW 桌面请求本轮成功，因此没有部署 HIGH 补丁。原厂256、原生 Linux258和桌面260均已有室外定位证据；位置、启动、辅助数据等并非单变量控制，不能把室内 PGA −6/−10 的差异认定为根因。完整5MiB MEMSHARE/SCM provider、冷启动、休眠恢复、长期稳定性和绝对精度仍开放。
