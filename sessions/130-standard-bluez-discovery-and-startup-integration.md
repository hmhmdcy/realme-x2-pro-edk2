# 阶段130：标准BlueZ扫描与开机地址供应

2026-10-12，goal active。上一轮129属于真实进展：#129实际部署、console warning消失、新启动5GHz自主连接、936包/770模块完整rootfs129及权限/内容验收完成。阶段130继续自动蓝牙扫描，无人工配对、连接或外部设备操作，当前内核仍#129，未虚称新#130内核。

首先核验同一129 boot、taint0、QCA固件setup/hci0。内核MGMT只读实际READ_INDEX_LIST为空、READ_UNCONFIG_INDEX_LIST为单hci0、READ_CONFIG_INFO missing=2，证明“模块注册”尚缺本机地址供应。rootfs有既有samurai-radio-address/dms/bt-address工具，但服务默认未启动；标准BlueZ D-Bus activation为Exec=/bin/false，不能期待客户端自动补足启动流程。

现有同机DMS GET_MAC BT只读查询成功，严格验证回复/字节序/权限、配置MGMT后READ_INFO地址与RAM原始6字节相同，控制器powered/connectable/bondable均0，原厂NV/persist未改。所有地址、附近设备标识、固件、全日志和镜像仅在E:/edk2-samurai-out/kernel130及手机私有现场，公开目录仅自有代码与脱敏结果。

采用匹配已安装BlueZ5.87的官方[Adapter API](https://github.com/bluez/bluez/blob/5.87/doc/org.bluez.Adapter.rst)与[MGMT协议](https://github.com/bluez/bluez/blob/5.87/doc/mgmt-protocol.rst)。同一D-Bus客户端执行SetDiscoveryFilter/StartDiscovery/StopDiscovery，LE12秒、BR/EDR12秒和混合20秒，各轮实时Discovering=true/false及设备对象验证；独立MGMT和HCI monitor原始包交叉证明实际Inquiry、LE扫描和发现事件。首次临时daemon脚本调用不存在的dbus-python get_unix_process_id，写前未继续扫描，finally关闭服务/电源；保留失败现场，改用标准org.freedesktop.DBus.GetConnectionUnixProcessID后新目录重新测试。首次读取工具曾将ELF当文本，原始输出已私有留档，后续只读取已确认脚本及工具SHA，不将二进制作为文本依据。

临时daemon扫描三轮通过：53个MGMT found事件、14个不同地址/类型组合（不是14台物理设备），2091个实际HCI monitor包，23次同PID桌面/5GHz/MPSS/ADSP/taint0样本。此轮开启控制器再次出现1条phase2/115200/first00的Frame reassembly -84，后续QCA setup完成且扫描通过；验证器最初按“0新增错误”拒绝，检查原始时间窗后明确保留这个仍未修复的启动UART错误，其他DPU/GPU/固件/密钥/内核故障0新增，不以删日志或宽泛成功标记替代验收。最终扫描停止、powered0、临时daemon停止。

标准OpenRC bluetooth服务增加need samurai-radio及start_pre：经有界既有samurai-bluetooth start配置并读回本机地址后才运行原装bluetoothd，失败不能启动daemon。原main.conf只将AutoEnable从默认true改为false，服务加入default runlevel，保留用户控制器开关与完整BlueZ功能；不自动配对、连接或发射广告。实机原服务/config/cache先私有备份，再原子增量安装，正常rc-service start/restart都通过。标准service管理下的第二组LE/BR/EDR/混合扫描原始验收通过：52条found、15个地址/类型组合、789条HCI包、23健康样本，结束服务运行/控制器off。同一阶段实际排空GUI/无线/音频/三remoteproc后正常OpenRC暖重启，新boot仍129，服务无需手动启动，新RAM DMS查询与MGMT/DBus地址读回一致，控制器默认off。

完整rootfs130从已验129模板cp-a复制，内核保持129/770模块逐字节一致，936包、UID10000 home、固件/双频凭据/metadata保持。仅五处声明变化：Bluetooth服务、AutoEnable设置、runlevel链接及两stage marker。完整130 sparse镜像1817949796字节、SHA256 098cad1f7daf4e238e9a2d7aa45b2704516e962991f39fb55606dcd12cd3a252；双dry-run fsck/稀疏payload与空洞/两superblock UUID-label/21,135条目内容与metadata反向零差异、encoded chroot UID10000实际创建/读写/删除和四件套通过。129稳定镜像与模板保留，userdata没有擦除或全量刷入。

UART phase2 -84、配对/传输、物理冷启动/休眠/长稳继续开放；GPU/持续显示、物理camera、GNSS fix、充电/指纹及其它15组硬件边界保持。下一轮优先本次新暖启动的有界真实GPU像素回归；旧118的25失败仍未修复，不因新boot零故障直接判通过。

新暖启动第一个collector在NM尚未连接时freq断言失败，partial目录和原输出保留，没有手动activation；稍后只读观察已自主5180，第二collector先有界等待同一boot的自主频率/默认路由后新目录完整验收。50.24秒6样本服务/GUI/radio/ADSP/5GHz/taint0、网关3/3/HTTPS577字节/11来源/770模块/分区读回通过；boot UART错误累计2，本次窗口0新增。新boot DPU0/GPU0/final active CRTC1，但另10秒encoder vsync3182→3182/underrun0，无负载，不能称连续帧或GPU像素已修复。初始console warning0保持。

仅清理E129卷两个可由保留129 sparse新鲜逐字节/空洞证明恢复的旧raw，实际分配释放3895001088字节，129template/export/sparse与130全部产物保持。E129 sync卸载/read-only e2fsck0，稳定E118/122/126实际仍未挂载且本轮未修改；C新增删除0/9未证明.o保留/稳定Image存在。C余10477752320、E余18763751424字节，原WSL VHD未resize/compact。初次close因WSL空闲结束后/run锁不存在，在任何sync/卸载前失败；同次WSL先ensure重新核验挂载后完成关闭。所有作业terminal。
