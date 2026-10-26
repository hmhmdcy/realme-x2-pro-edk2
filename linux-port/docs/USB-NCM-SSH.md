# 普通USB网络与SSH（session72）

当前诊断initramfs自动提供CDC NCM和公钥SSH。手机169.254.42.1/16，Windows系统
UsbNcm自动绑定并使用APIPA地址；无需改主机默认路由。独立重启后无需host com-up
也能认证SSH。EUD仍可用于早期日志和F1，两条路径共存。

本机专用密钥/known_hosts在E:\edk2-samurai-out\kernel72。使用
reference/kernel72/usb-ssh.ps1执行命令、scp-usb.ps1传文件（显式-O）。
SSH端口22只绑定USB地址，密码认证已在编译和运行时禁用。主机密钥是手机唯一密钥，
仅保留在本地实际initramfs/构建产物，客户端私钥只留主机；两者不进入Git。

手机脚本/usr/sbin/samurai-usb start由init异步调用；status可查看UDC/接口/SSH PID。
启动时先等UDC就绪，再创建单NCM函数、启用网络、devpts和Dropbear。
Windows显示426Mbps是驱动链路报告，实测协商high-speed；没有USB3/OTG验收。
NCM枚举刚出现时服务/主机地址可能还没就绪，要以实际SSH回执确认连接。

源码脚本为linux-port/scripts/samurai-usb.sh与build-dropbear-usb.sh。
构建Dropbear用固定2026.94官方tar和SHA，输出静态ARM64 multicall，包含
dropbear/dropbearkey/scp；许可证在refs/dropbear-2026.94-LICENSE。
实际initramfs是/home/cy122/x2pro-linux/initramfs，原EUD/init逻辑保留。
kernel72-initramfs.config把本地UID/GID1000映射成包内root；更换构建用户时按
实际源文件所有权配置并验证CPIO，不能把固定1000当通用发行配置。
历史安装/构建/部署和验证代码在reference/kernel72，可按当前布局复用；
处理一次性安装步骤，将所需修改合入现有init/initramfs并保留回退。

本轮只刷一次logdump，boot固件与DTB未改；直接回退kernel71/logdump-k71-touch.img。
日志可保留在手机后SCP下载，也可流式采集；按用途核验完整性。
72阶段文件传输采用手机SHA256、gzip CRC和长度校验。
双向4MiB SHA、PTY、自动SSH、EUD保留及原始失败记录详见sessions/72。
