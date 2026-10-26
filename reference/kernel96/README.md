# 阶段96：Wi-Fi解绑权限回收、蓝牙生命周期与本机地址

已部署Linux #95，DTB/boot/配置/三个BT模块不变。CPIO只改init和`samurai-bluetooth`；内核只改ath10k qmi.c/qmi.h。全部是对当前已验证真实工作树的增量，不重放历史守卫。完整结果见 [session96](../../sessions/96-wifi-msa-lifecycle-and-provisioned-addresses.md)。

`samurai-bluetooth boot`等待Wi-Fi尝试的实际结束状态，成功或失败均可继续。240秒仍没有结束记录就拒绝重叠启动；最早60秒、最多30秒显示等待和10秒安静窗口保留隔离边界。`start/stop/status`支持独立操作与幂等启停；RAM锁拒绝并发，不强制卸载。服务只注册驱动，地址/扫描/连接均不自动执行。真实冷启动失败分支尚未验收；阶段95仅用人为失败标记测试过dispatch。

`ath10k-qmi-unbind-msa.patch`记录每个成功授予的MSA区域，在QMI工作停止后随解绑回收，仅处理实际授予的区域，避免失败/部分初始化的重复回收。保留SCM错误和fixed-perm原语义，不跳过安全错误。阶段95解绑重启出现MSA分配-22，阶段96相同步骤恢复了wlan0、认证、DHCP和双向流量。

`dms-mac-read.c`只允许DMS GET_MAC 0x005c的WLAN/BT两种只读查询；动态查找唯一service2/v1/instance0，验证源端口、事务、消息/TLV长度、result/error与6字节地址。本机安装的cnss-daemon先检查数组最后字节的标志位，再反转WLAN地址；BT HAL的DMS函数原样复制。有效的全局单播地址与完整回复仅写0600 RAM文件。初次发送返回值、初次WLAN字节顺序误判与执行权限失败均保留在私人日志中。不能把该本机实现的顺序盲套其它机型。

本机vendor/persist仅ro,noload挂载，前后完整哈希一致，隐藏`.bt_nv.bin`不存在。vendor是当前安装的同机Android分区，不能仅因脚本名而宣称其为未经修改的OEM镜像。未执行OEM库/探针、未写原NV、persist或userdata。

地址目前只在RAM应用并实测，跨暖启动一致；还未自动集成到启动服务，也没有Wi-Fi/MPSS首次失败时的离线地址来源。`bt-mgmt-probe`关闭connectable/bondable，仅用于查询、临时地址和扫描；不包含配对/连接命令。后续优先用严格扫描版本，原版本的私人二进制/源码/日志保留。

初始2.4GHz、热重启恢复后的2.4GHz、5GHz各双向4MiB、网关/DNS/HTTP及90秒共存通过。MPSS offline时BT扫描通过；收紧接入标志后又扫描成功并SET_POWERED=0。141个主现场文件和14个补充文件逐一校验，boot/logdump/模块/服务读回通过，6个原NV/persist不变。公网ICMP仍失败；BT有8次Frame reassembly -84与1次波特率重试。配对、断电冷启动、休眠/长期运行、NFC标签/eSE及其它硬件仍待办。

本目录仅自有代码/补丁与脱敏说明。完整日志、固件、镜像、厂商库、MAC/周边设备身份、PSK和密钥在私人`E:/edk2-samurai-out/kernel96`。使用新启动现场和新输出前缀；只刷boot/logdump，保留Android/数据/GPT/原NV/密钥及显示85–88快照。另一线程rootfs/F2FS工作不改，充电不写配置或运行旧OEM探针。整体goal仍active，本轮无提交/推送。
