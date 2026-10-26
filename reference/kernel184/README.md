# 184：外设适配继续推进

2026-10-15。用户要求无人值守修复GPS、摄像头、蓝牙、传感器、蜂窝通信等Linux适配问题。当前基线是已部署kernel183、boot/DTB172及runtime/modules132。184是本次工作阶段号，不意味着已部署新内核。

按WORKING-BOUNDARIES保留NV/校准、私人数据和电池保护边界；蓝牙只扫描不连接、不新增振动。每次切换依据当前设备状态，保留失败证据。

推进顺序：当前启动的私有外设基线；原00121 SLPI的`wise_light`与标准`ambient_light`接口差异及真实采样；本机固件版本与惯性传感器注册；实体摄像头PM8008/CCI/C-PHY；蓝牙UART启动与PM；QMI LOC标准定位服务；蜂窝SIM与IPA业务路径。需实物条件的验收保持开放，软件层能验证的修复继续推进。

相关源码：本机[官方Android R内核](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source)，同SoC[Hotdog适配仓库](https://github.com/Sr-0w/hotdog-linux-bringup)，[libssc](https://codeberg.org/DylanVanAssche/libssc)，[libqmi LOC](https://github.com/linux-mobile-broadband/libqmi/blob/main/src/qmicli/qmicli-loc.c)。外机结果只提供工程方案，不作为本机验收。

工具使用postmarketOS的kernel109主机身份；旧kernel72 initramfs的known_hosts不匹配当前系统。首次旧工具连接被严格主机验证拒绝，随后使用已有的正确身份成功，未绕过SSH验证。

## 本轮结论

[libssc补丁](libssc-wise-light.patch)修复已证明的名称兼容缺口。原00121固件全量查询`ambient_light`为空、`wise_light`为唯一可用实体实例。原始QRTR探针收到96个1025测量事件，五次QMI操作结果成功、非法帧0，停止ACK通过；独立Google Protobuf编码/解码及八个非法输入用例通过。[原始通路](light-runtime-validation.json)、[协议测试](light-wire-validation.json)。lux均0，原始通道0至192且有变化，不能认定光照响应/准确度已修复。

原装libssc 0.4.4只固定查询标准名称。补丁增加设备环境配置`LIBSSC_LIGHT_DATA_TYPE=wise_light`；默认及其它值保持标准类型，公共函数签名保持。使用[Debian原版源包](https://deb.debian.org/debian/pool/main/libs/libssc/libssc_0.4.4.orig.tar.gz)，SHA256 716d6bd6…；117个APK经设备验签提取到独立SDK，链接使用本机已有运行库。ARM64共享库/CLI编译成功，SONAME及导出函数名集合与安装版本一致，系统包数据库保持。[构建验证](libssc-build-validation.json)。整理后的单脚本未另做全新干净构建；完整实测使用保留的r4构建目录及r6链接结果，源码/依赖/日志均保存。

第二个新183启动的[完整v4用户态测试](userspace-v4-validation.json)：同一候选库默认名称返回254、无样本；OEM名称返回0、41个测量、正常禁用。原装SensorProxy在独立库路径下报告HasAmbientLight=1、单位lux、HasProximity=1、HasAccelerometer=0，同一D-Bus连接ClaimLight/ReleaseLight成功，daemon按TERM退出0。系统库和包数据库均未改变；光照值仍0。配置与后续启用说明见[SSC兼容层](../../linux-port/ssc/README.md)。

## 失败、重启及当前现场

本轮首次成功SLPI停止后，同一boot第二次原固件启动返回−110，没有进入候选库测试。[独立失败记录](slpi-restart-failure-validation.json)保留；SLPI离线、供电0、taint0，根因未证明。不能绕过ready握手或把旧样本称作新启动成功。后续每个控件试验都在新boot进行。

用户态v3的CLI对照已经通过，但测试脚本误给SensorProxy使用不支持的`--debug`，daemon退出1。原日志/报告保留为[失败](userspace-v3-failure-validation.json)；检查实际`--help`后改为`G_MESSAGES_DEBUG=all`，新boot的独立v4通过。首个只读基线遇到缺media-ctl而中断，partial目录保留，r2显式记录工具缺失。手机直接APK下载TLS错误/180秒边界失败；改在主机取得官方APK、设备验签，不关闭TLS或签名验证。SDK的Python路径、mount头/元数据和intl/传递链接依赖的初始失败日志也保留，未把它们记作成功。

两次当前183身份/boot172与logdump183/persist及NV校验、排空GUI/音频/无线/三个DSP、F2FS冻结后，各只发一次已审查RESTART2；新fastboot身份和产品验证后各只发一次reboot，**没有刷写分区**。第二轮上传前缺新工具目录而失败，确认尚未切换后续作；首次即时fastboot枚举为空，保存原结果后只等待新枚举，未重发RESTART2。[第一次新启动](reboot-runtime-validation.json)、[第二次新启动](reboot-runtime-r2-validation.json)均有0秒日志、taint0、Phosh/声卡出现，所列核心故障0，蓝牙重组仍2。

[最终534.62秒](final-validation.json)：当前第二新183 boot，taint0；ADSP/modem running，SLPI offline/供电0，临时进程全部停止；Phosh运行，PCM关闭、双功放静音。原始来源/NV/boot/logdump/persist校验保持。所列WARN/Oops/GPU/DPU/ASoC/IRQ读取/SLPI启动超时0；蓝牙重组2独立保留。没有重复本轮以前的音频PM或声学测试，也不将旧183 boot的完整音频验证归到此boot。

私人证据在E:/edk2-samurai-out/kernel184和手机/var/lib/samurai/k184*；公开报告只含脱敏结果。系统库未替换、自动SLPI服务未开启。完整外设适配goal仍active。

## 继续顺序

1. SLPI停启ready握手和持续文件服务；原00121固件的光照准确度、本机OEM项目元数据/注册分支及LSM6DS3C。C28/C35、A.11历史失败与样本仍各自保留；不导入他机校准。
2. 蓝牙当前每新boot两条phase2/115200/first00重组错误；核对power pulse与有效H4流的边界并做仅扫描对照，保持其它真实协议错误可见。
3. LOC标准定位服务和UTC/aiding链。当前libqmi源已提供Inject UTC Time及其异步状态indication，不把QMI ACK等同定位成功；真实fix和桌面位置仍未验收。
4. 实体摄像头：本机PM8008四输入来源、冷地址/复位和chip-enable，再推进CCI/C-PHY和传感器出图。未找到可证明这些输入接线的本机公开图纸；其他设备的BOB输入仅作对比。
5. 蜂窝管理器sim-missing，真实注册/移动数据/通话/SMS需要卡；可以继续完成IPA/双槽/业务状态与错误传播的软件工作。其它外围待办继续见硬件清单。

同SoC仓库此次通过GitHub树接口重新核对，仍为47087509c4289c2580c54f5433e55366b2e00445；Git clone的TLS失败原样记录，未用失败下载替代资料。其光线与注册经验只提供方向。本次没有借用外国固件或证明所有硬件已可用。
