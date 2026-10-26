# Session92：连接驱动与真机验证

结果、边界和私人证据索引见 [session92](../../sessions/92-connectivity-drivers-and-runtime-validation.md)。

内核逻辑阶段92对应 Linux #91。Wi-Fi 2.4 GHz 网络和双向流量通过；蓝牙只扫描；NFC 控制器初始化/开关通过。开机 Wi-Fi 等待缺陷已在 `samurai-wifi` 中修正，部署版本仍需下一版开机验证。原始部署字节保留在私人 CPIO/镜像和审计中。

`bt-mgmt-probe.c` 仅用于有界本机 MGMT 观测和扫描，不提供配对命令。`test-address` 接受私人六字节临时地址文件，只配置本轮 RAM 身份；不能替代出厂地址。`nfc-controller-probe.c` 只查询和上下电控制器，不发固件下载或标签/eSE命令。

历史构建、F1 和刷写脚本均含该次现场守卫，拒绝覆盖证据。再次部署必须重新读取启动标识、分区和备份，不能重放旧脚本。只有 boot/logdump 在授权刷写范围内。
