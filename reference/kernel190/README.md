# 阶段190：修复GNSS辅助能力发现的提前indication竞态

**已部署ModemManager修复，真机SupportedAssistanceData从0变成XTRA（1），辅助服务器从0变成3；尚未获得有效GPS fix。** 内核、DTB及模块保持189组合，当前仍是189第二次热重启后的同一启动。完整外设goal继续。

## 根因与修复

安装版本为ModemManager 1.25.95_git20261005-r0，对应源码提交`7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a`。原实现发送LOC Get Predicted Orbits Data Source后，等ACK成功才注册完成indication的监听。本机基带实际先发完成indication，再发ACK，导致ModemManager漏报文，十秒超时后缓存“无辅助能力”。独立QMI探测能读出三个服务器，证明不是固件没有该接口。

修改前和修改后都捕获到同一事务的顺序：`request → indication → response`。修改后的同一顺序成功得到XTRA/三个服务器，修复有实机对照。[原始源码](https://github.com/linux-mobile-broadband/ModemManager/blob/7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a/src/mm-shared-qmi.c)、[补丁](modemmanager-loc-early-orbit-source.patch)、[真机报文顺序及状态](mm-native-validation.json)、[部署前后](mm-deployment-validation.json)

补丁在发送请求前连接信号并安排超时；提前收到的boxed输出先持有引用，等ACK校验成功后处理。ACK回调另持一个GTask引用，超时/错误/提前完成不会释放仍在使用的对象。收到有效完成后先拆除本次信号与定时器，再注册原有时间/位置辅助请求事件。未改变辅助数据协议或伪造能力位。

从生产文件提取实际C回调，使用真实GLib GTask/GObject、模拟QMI传输进行23种顺序、重复、协议/传输错误及超时/晚回复测试，ASan/UBSan与泄漏检测通过。固定原版在`indication → ACK`场景运行失败，故意破坏ACK门控的变体也被检出。QMI传输是模拟，不能替代基带测试。[主机回归](mm-orbit-source-host-validation.json)

## 构建、部署与回退

官方Alpine源码归档与APKBUILD SHA512匹配；保留发行版原有Intel补丁。在手机上提取经过`apk verify`的SDK及补充开发包，没有安装或升级系统包；链接库覆盖为本机正在使用的运行库。udev、QMI/QRTR、MBIM、Polkit、elogind休眠支持保留；关闭文档、绑定和测试产物生成，仅替换守护进程可执行文件。[源码归档](mm-source-archive-validation.json)、[发行版补丁](mm-distro-patch-validation.json)、[构建](mm-build-validation.json)

清除构建RPATH后，候选程序通过本机系统库依赖检查及`--version`。原子替换`/usr/bin/ModemManager`，在SIM缺失、无bearer、GPS关闭的预检后重启守护进程，没有重启MPSS或手机。D-Bus激活文件恢复原件，调用SetLogging恢复INFO。标准库、插件和APK安装数据库保持。[候选检查](mm-candidate-validation.json)

- 当前程序SHA256：`fbc4084873e8e79d4bcdfa37982f4016a9e898f7123cecd37ba941ed55f27f69`。
- 原程序SHA256：`4d5a8258f6fc32f1c9b7a7d6e5de88d7bf68f1ef0e575cbffd009e52e66bd179`。
- 原件在手机`/var/lib/samurai/k190-mm-deploy/ModemManager.original`及主机`E:/edk2-samurai-out/kernel190/ModemManager.original`，候选也已保存在主机。回退应核对当前身份/进程与原件哈希后原子恢复并正常重启守护进程；不要套用旧PID。

这仍是本地可执行文件覆盖；APK更新、旧rootfs132重写会覆盖它，补丁正式入包待做。

## 已测GNSS能力与边界

SIM缺失并不阻止当前版本的独立GPS接口：标准Location.Setup(6,false)成功，约125.93秒得到131条内容不同且校验有效的NMEA句子，结束Setup(0)并恢复30秒刷新率。但GGA/RMC均无有效定位，GPS raw报告0，C/N0数值字段0。GSV最多列出12颗仅是“in view”信息，不能称为实际跟踪或锁定。[标准接口](mm-location-stream-validation.json)、[质量分析](nmea-quality-validation.json)

同步时钟下的一次UTC注入取得ACK和独立完成status0，CID释放成功；该首次探测错误调用了不存在的Qmi.Device.close，最终触发截止时间、进程退出1。已修正后续脚本使用close_async，但不能将首次清理记为通过。[原始失败范围](utc-first-probe-validation.json)

独立LOC查询返回三个轨道服务器，allowed-sizes TLV缺省；ModemManager自身有默认分片处理，缺省TLV不是其能力丢失根因。轨道有效期查询未见已加载数据。已通过TLS下载一个广告的全局轨道文件50413字节，核对URL无query、fragment、凭据，没有发送位置或设备标识；尚未注入或证明轨道有效期更新。[下载](assistance-download-validation.json)

核对了实际GeoClue 2.8.2及ModemManager源码：两者已有SIM缺失场景的独立GPS支持，初期“必须绕过failed状态”的假设不成立。尚未修改GeoClue授权/代理或冒用桌面应用。有效fix、GeoClue标准桌面客户端、室外/精度与热冷启动仍待测。

下一步先审查同文件Inject XTRA Data的ACK后监听，以及Inject UTC Time/Position的独立异步引用生命周期，再做全文件辅助注入、有效期确认和标准GPS回归；不能把本次能力发现修复当作这些路径均已安全通过。

## USB传输失败及恢复现场

主证据归档在手机完整生成，但USB下载只到1933312/1958876字节后中断。手机及Windows仍显示NCM连接，双向IPv6探测不通，UDC configured、USB0 carrier1、预期IPv6地址仍在。Windows重启该网卡被系统拒绝访问。没有发送手机重启。

用本机已有DHCP记录中的Wi-Fi地址和原严格SSH公钥重新连接，确认同一启动、kernel183、taint0；经Wi-Fi完成归档并核对SHA256。Windows混合表格曾被误读为磁盘满，复核E盘约80GB可用后立即纠正，没有迁移或删除文件。

通过Wi-Fi核对仅有`ncm.usb0`后，对原UDC执行一次解绑和一次重新绑定，最终configured、同一启动；此后Windows邻居仍为Probe，**没有USB恢复的正向证据**。这是一次恢复尝试，不是NCM根因修复。当前管理链路使用`host.py`及私有Wi-Fi端点文件，原USB身份记录保留。[USB现场](usb-stall-validation.json)、[手机反向探测](usb-phone-ping-validation.json)、[Wi-Fi严格身份确认](wifi-transport-probe-validation.json)

4216.59秒复核：修复程序继续运行、辅助能力1/服务器3、GPS关闭、modem仍SIM缺失、bearer0，ADSP/SLPI/modem与SensorProxy三项存在性保持；taint0、所列内核故障增量0。保留189原蓝牙重组1，不能称全boot无错。[USB操作后的状态](post-usb-validation.json)

322个主证据文件及原/新程序已私人归档，主归档SHA256核对通过；USB补充归档也核对通过。NMEA、原始QMI/ModemManager日志、网络端点、身份和密钥均不公开。[主归档](evidence-export-validation.json)

## 尚未完成的整机项目

GPS真实fix与辅助注入/桌面桥、蜂窝真实SIM注册和数据/通话/SMS、实体摄像头PM8008/CCI/C-PHY出图，以及蓝牙phase5/Wi-Fi与USB稳定性仍开放。189传感器三轮PM通过的范围保持，普通信号竞态、共享池stop/start/SSR与人工运动/精度验收仍开放。参见[当前检查点](../../NEXT-SESSION.md)和[硬件状态](../../linux-port/docs/HARDWARE-STATUS.md)。
