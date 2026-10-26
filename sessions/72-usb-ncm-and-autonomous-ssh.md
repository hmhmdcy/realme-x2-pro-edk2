# 72. 普通USB NCM与自动SSH接入（2026-10-10）

**本轮把未配置的UDC变成实际可传输文件的普通USB网络，并部署到#62 initramfs。**
Windows自动加载系统UsbNcm驱动，EUD/COM14同时保留；双向4MiB随机文件在部署前后
均通过SHA256校验，收发错误为0。仅刷一次logdump，不写boot、userdata或GPT。
完整日志先在手机保存，再通过EUD或已认证SSH/SCP导出并核对SHA256/gzip CRC/长度。
证据在[reference/kernel72](../reference/kernel72/README.md)。全硬件目标仍在进行。

## 72.1 新基线和原生USB实现

新回执确认旧#61、boot_id=a31c1158-fbca-4515-83ac-1a3b40ee808e、taint=0。
手机保存73173字节完整dmesg，gzip15594字节，SHA256为
5809a52e1603f6e8d66506c50ef708fc2e59edff49825265b7939121b8020071。
EUD严格base64解码、gzip CRC、SHA和长度全部通过。随后同一压缩文件经普通USB
TCP下载，哈希完全相同；没有从实时残缺文字推造完整日志。

实际运行内核已有CONFIG_USB_CONFIGFS_NCM/USB_F_NCM/USB_U_ETHER=y，UDC存在、
gadget目录为空。依照[Linux官方configfs流程](https://docs.kernel.org/usb/gadget_configfs.html)
创建单一NCM函数，绑定a600000.usb。采用内核legacy/ncm.c中的0525:a4a1以太网
产品标识，设备class/subclass/protocol=EF/02/01让Windows枚举IAD函数；只导出网络。
固定MAC来自本机序列号：手机02:62:bc:28:a1:01，主机末字节02。
手机地址169.254.42.1/16，Windows自动APIPA，无主机网络配置、默认路由或转发变更。

[微软官方文档](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/supported-usb-classes)
及[官方驱动仓库](https://github.com/microsoft/NCM-Driver-for-Windows)说明NCM类驱动。
本机Windows实际绑定UsbNcm Host Device #3，接口71/MAC相符，PnP全部OK。
手机实测configured/high-speed/carrier=1；Windows显示的426Mbps是驱动链路报告，
不是吞吐率实测。三次ping全部成功。未关闭EUD、换驱动或修改控制路径参数。

## 72.2 SSH、实际initramfs与构建

从[Dropbear官方2026.94发布](https://github.com/mkj/dropbear/releases/tag/DROPBEAR_2026.94)
取得源码，tar SHA256为e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81。
按官方INSTALL/MULTI方式交叉构建静态ARM64 dropbear/dropbearkey/scp multicall。
localoptions.h明确关闭密码认证，运行只监听USB的169.254.42.1:22。
首个构建缺crypt()失败已保留；应用上述公钥认证配置后构建通过。
glibc静态NSS链接警告保留，实际root认证、执行命令、PTY和SCP均已通过。
binary1254736字节，SHA256=c2ba3e24f1f4aa54392f3871bd0a617febdb14515ba7657e015be27573a581bb。

客户端密钥新建于本地E:\edk2-samurai-out\kernel72；只把公钥放入手机/root/.ssh。
手机生成独有Ed25519主机密钥，公钥先从EUD可信回执读取，客户端使用专用known_hosts
与StrictHostKeyChecking=yes。该主机私钥通过已认证SCP复制到本地实际initramfs，
跨重启保持身份；两份私钥都不进入Git。仓库仅保存源码、许可证、公开证据和构建方法。

samurai-usb.sh负责NCM、USB地址、devpts及密钥SSH；init仅在原configfs挂载后增加
一个异步hook，其余原init/EUD shell/F1逻辑逐字保留。添加root passwd/group/shells/
nsswitch和SSH/SCP链接。原initramfs源码属UID/GID1000，配置只改INITRAMFS_ROOT_UID/
ROOT_GID为1000，使包内归属root；实际CPIO校验权限、UID/GID、内容、symlink和
没有客户端私钥。EUD/earlycon/RMI I²C/DTS/DTB的构建前后哈希全部相同。
仓库旧init快照缺少此前已经在真实init生效的EUD shell/存活循环；本轮镜像源码补齐
这段旧逻辑。相对于实际运行源文件，仍只有新增USB hook，不是重新改写EUD路径。

Image30906880字节，SHA256=95beb0b34e1c7b082d2986f83f9e3528199599e01af10fbcd1fe4ad4b12f54e2。
logdump67108864字节，SHA256=13a8263dac6c75f909b6fa8dc89520949c7009ddcb9de2b2a5f6125e26d4292b。
make Image无新增warning/error。FAT中Image逐字匹配、DTB不变，空闲36016128字节。

## 72.3 部署和验收边界

Windows单次F1无回执，独立fastboot为空，因此没有写分区。WSL既有工具随后收到
F1回执、设备离开导致EIO，finally dispose/detach；独立fastboot确认62bc28a1/
msmnile/logdump64MiB后，仅写logdump且Writing OKAY，boot固件保留session71版本。
一次WSL attach初始lsusb未枚举，finally释放；后续加入有界枚举等待，未改变EUD参数。
后续同镜像重启有初始fastboot枚举为空的记录，等新枚举后再reboot，无额外刷机。

新#62首次boot_id=c93bf272-84a1-4b83-a55a-9376085c729b、taint=0，自动NCM/SSH启动，
同一主机密钥通过认证；/usr/sbin/samurai-usb再次start只报告already started。
PTY实际/dev/pts/0，tty/stty与K72PTYOK通过；SCP显式-O使用已构建的legacy scp协议。
部署前后各一对4194304字节随机文件，上行原件/手机哈希、下行手机/主机哈希均一致。

首次新内核完整53519字节dmesg（gzip12603字节）SHA256为
d10761d7d2c0e4728b38cbf44d6d97e551df29b07b5a67fd1f2b74c1b0771ae7。
六个UFS盘、S3706A/event2与三个policy最高1785600/2419200/2956800保留；无新
panic/Oops/BUG/WARN回溯。旧QMP/RPMh/PM8009等仍按既有功能边界处理。
EUD原生命令在NCM工作时取得#62的新boot_id/taint回执；F1再次返回独立fastboot。

同镜像复测还专门观察不发送host com-up的启动。两份最初的elapsed字段因PowerShell
自动把JSON日期转为DateTime后丢失offset而错误，明确废弃，不作为启动时长证据；
修正的原始ISO时间观察在94.569秒时NCM已自行枚举，host_com_up_sent=false。
随后再做独立SSH复测，其确切boot_id/结果见independent-ssh-validation与最终facts。
com-up只用于恢复EUD的COM枚举，不能把其后的SSH测试冒充之前的结果。

最终独立复测boot_id=5ecfab9e-fa56-4ead-acf8-a5147904980e、#62/taint0，
没有发送com-up即取得新SSH认证/状态回执，旧known_hosts身份保持。一次NCM刚枚举时
SSH尚未就绪，失败保留；之后的新回执才算通过。最终完整53594字节dmesg
（gzip12566，SHA256=be43829e3a55bfdda53835a12ba45d7bf84f83c8ef2c03d272aee8f985f02ebd）
及2285字节facts（gzip784）都通过设备SHA/CRC/长度。随后一次正常com-up恢复COM14；
五个PnP节点OK、9505 Shared/未Attached，无host owner，原工具/驱动/回退哈希相同。

目前证明的是USB2设备模式、NCM/SSH/SCP、自动启动和EUD共存；OTG、USB3、休眠恢复
及长期稳定性没有验收。触摸仍沿用session71基本输入证据，不因本轮注册再次声称
完成触点精度/休眠测试。下一优先项为本机SOFEF03F原生面板/DSI/DSC和GPU，再
电池/充电、无线/音频等。全系统rootfs容量/Android数据保留问题尚未解决。
