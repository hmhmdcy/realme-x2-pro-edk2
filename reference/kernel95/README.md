# kernel95：正确路径的蓝牙自动加载（Linux #94）

见[sessions/95](../../sessions/95-bluetooth-autoload-and-dual-band-regression.md)。本轮只修正镜像加载器路径，配置/设备树/模块字节与kernel94相同，复用现有EDK2 boot，只刷logdump。

`prepare-and-build.py`和`audit-kernel.py`核对CPIO、符号链接、模块、配置和DT。`samurai-bluetooth`在Wi-Fi服务稳定45秒并产生ready后注册UART控制器，不选择永久地址、扫描、配对或连接。这个ready依赖仍是启动隔离方案，Wi-Fi失败时BT自动加载失败；独立生命周期尚未完成。

`test-connectivity.sh`使用私人RAM PSK/临时BT地址，等待MGMT未配置/已配置索引，验证认证/DHCP与NFC控制器。`coexistence-test.sh`和`coexistence-5ghz.sh`做有界扫描观测，后者逐样本确认5180MHz；测试TCP程序沿用kernel93私人二进制，RAM文件名含k93，实际阶段与频段由新的状态/路由/流量日志证明。

完整备份、停机、F1、刷写和采集脚本含单轮固定身份守卫，不能重放；必须重新获取现场。首次flash脚本候选文件名错误在写入前停止，独立失败输出保留，retry1重新审计后只写logdump。

刷写序列号读取私人`fastboot-identity.json`，不从当前任意连接设备自动猜测；实际执行日志保留。扫描结束后关闭蓝牙电源，驱动和RAM临时地址保留，Wi-Fi/显示仍正常。

专有固件、镜像、完整日志、可执行程序、附近设备身份、SSH与凭据位于私人`E:/edk2-samurai-out/kernel95`，不提交。其它线程的rootfs和历史显示快照保留。
