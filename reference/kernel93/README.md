# Session93：真实固件名、启动隔离与共存

阶段93对应Linux #92；完整结果、哈希和边界见 [session93](../../sessions/93-connectivity-startup-and-coexistence.md)。

构建只修正Wi-Fi UFS分区等待返回值，并在UART13指定本机revision-21蓝牙固件。完整CPIO保留审计、单属性DTB审计、FV及两个分区镜像校验通过并已部署。

首次MPSS启动失败，BT固件有启动重试，显示CTL接管-22导致当前DRM缺失，不能将此版本记为开机稳定。受控MPSS重试及90秒Wi-Fi/BT共存通过；2.4/5GHz认证、DHCP和双向4MiB TCP均通过；NFC只验证控制器。完整检查明确保留全部失败。

私人证据位于E:/edk2-samurai-out/kernel93。`stop-connectivity.sh`、`retry-mpss-bt-off.sh` 和刷写脚本包含一次性设备启动守卫；后续必须重新取证和生成守卫。没有充电、NV、persist、userdata或GPT写入。
