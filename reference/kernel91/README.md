# kernel91：Wi-Fi RAM服务与连接验证

当前实机内核是#90，见 [session91](../../sessions/91-wifi-rmtfs-and-connected-traffic.md)。

该目录保存自有增量实现、构建/受限部署/取证脚本。RMTFS仅固定NV只读快照加RAM COW；TFTP只允许固定4096字节RAM探针，固件源只读。完整第三方源码、固件、镜像、工具、凭据和现场均留私人目录。

2.4GHz WPA2/CCMP、DHCP、DNS、公网HTTP及Wi-Fi双向各4MiB SHA256已通过。5GHz连接和重启自动服务仍待验收。旧脚本含当次boot ID/哈希及拒覆盖守卫，不能在新启动直接重放；必须保存当前现场，生成新守卫。
