# 蓝牙服务前提与手机对端角色（2026-10-23）

本轮只读复核固定源码和旧rootfs115，没有访问手机/SDK、构建、安装或连接对端。结论是：**不能由k363的`CONFIG_BT_LE=n`推断普通LE/GATT缺失，也不为此新建Image**。确实缺少的`BT_BNEP`和`UHID`分别影响PAN和BlueZ HOG输入桥接；它们不能替代实际profile/数据验收。

## 内核、控制器与BlueZ的证据范围

本轮Linux证据来自k363原构建记录的精确提交`ba61a62293e0f6bc5838c06f2e85e033e3d702a8`，用`git show COMMIT:path`只读提取，未使用canonical 58d工作树替代。BlueZ固定5.87提交`65d11edee469c24dcc8d075b8be9c040cebaaf98`，PA固定17.0提交`1f020889c9aa44ea0f63d7222e8c2b62c3f45f68`；文件摘要和来源见[source-lock.json](source-lock.json)。

| 层次/功能 | 精确代码或已有证据 | 能得出的结论 |
| --- | --- | --- |
| 控制器LE feature与旧raw扫描 | 原185控制器/扫描缓存 | 只证明当时控制器与路径，不等于363当前BlueZ主机功能或本轮连接通过 |
| 普通LE主机协议 | k363 `net/bluetooth/Makefile:13..22`将L2CAP、SMP、MGMT、HCI连接/事件/sync无条件编入BT；`BT_LE`只条件加入`iso.o` | 该配置名在这棵固定树中不能单独作为普通GATT阻断条件；ISO socket相关入口另受该flag限制 |
| MGMT LE能力 | k363 `include/net/bluetooth/hci_core.h:1959`的lmp_le_capable只读LMP feature；`net/bluetooth/mgmt.c:828..833`据此产生supported LE/advertising，`:890`读HCI_LE_ENABLED产生current LE | 静态配置与控制器feature、实际MGMT supported/current必须分开记录；当前值仍待设备窗口 |
| GATT与广告管理器 | [BlueZ adapter.c:9409](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/src/adapter.c#L9409)按MGMT_SETTING_LE且非BR/EDR-only创建database与adv manager | 没有接口时先查MGMT、ControllerMode、daemon/监听失败；不能以准备脚本存在当作已具备 |
| GATT服务注册 | [gatt-database.c:3935](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/src/gatt-database.c#L3935)为普通异步RegisterApplication；`:4062`建立LE ATT监听 | 该基础接口不要求全局Experimental；仍需真实接口、注册成功、链路与完整挑战回执 |
| HOG作为本机输入host | [hog.c:216](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/profiles/input/hog.c#L216)为LE bearer；[hog-lib.c:1427](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/profiles/input/hog-lib.c#L1427)创建UHID；[uhid.c:194](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/src/shared/uhid.c#L194)打开/dev/uhid | HOG需要可工作的LE/GATT和UHID；当前UHID=n缺少用户态到Linux输入设备桥。普通GATT读写不依赖UHID |
| Classic HID host | [device.c:93](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/profiles/input/device.c#L93)默认UserspaceHID enabled，`:1542`打开UHID失败回退kernel；`:931`使用BTPROTO_HIDP | 既有hidp.ko可能服务经典HID回退，不能替代HOG；实际输入事件/配对仍未验收 |
| PAN | [manager.c:166](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/profiles/network/manager.c#L166)先bnep_init；[bnep.c:68](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/profiles/network/bnep.c#L68)创建BTPROTO_BNEP socket，缺协议则plugin初始化失败 | NM插件/网络profile存在也不能弥补BNEP=n；还须匹配PANU/NAP角色、地址配置与实际IP数据 |

内核线已准备[独立模块配置候选](../bluetooth-host-config-20261023/modules.config)，后续仅考虑BNEP/UHID的n→m模块方案；当前资源窗口未交还，不在本轮构建，也不改BT_LE。普通LE准备工具保留，实际执行仍需先满足本次身份、健康与设备窗口条件。

## 旧rootfs中的实际服务与工具

[rootfs115-summary.json](rootfs115-summary.json)由[audit-rootfs.py](audit-rootfs.py)只读APK数据库及指定文件生成；它是旧镜像线索，**不是当前设备快照**。

- BlueZ5.87-r0和OpenRC脚本在；main.conf没有生效的ControllerMode覆盖。system `org.bluez.service`使用`Exec=/bin/false`，不能假定一次D-Bus访问会启动守护进程。
- PA17.0-r7与pulseaudio-bluez在，default.pa加载bluetooth-policy/discover；pulseaudio-wireplumber禁用WP的hardware.audio与hardware.bluetooth。继续沿用PA音频链，避免另起竞争音频后端。平台5-r2新增依赖只是固化现有插件。
- NM1.58.1-r1与networkmanager-bluetooth及对应插件在；PAN仍被缺BNEP限制，且本地NAP服务还需要明确桥/地址/共享策略。
- Python3、py3-dbus、py3-gobject3、GLibUnix typelib在。APK数据库未列出btmon/btmgmt，标准bin/sbin路径也没有；当前现场可能另有历史工具。[手机LE脚本](../bluetooth-le-peer-20261023/phone-gatt-peer.py)已按主线要求复用130/185原生monitor实现：优先btmon，找不到才记录原生monitor JSONL，不为工具缺失新增依赖或重建。该新backend仅有离线生命周期验证，现场捕获仍待核对。
- OBEX并非缺包：`/usr/lib/bluetooth/obexd`属于**obexd-enhanced5.87-r1**，依赖bluez~5.87且与bluez-obexd冲突；另有obex-capabilities和GNOME bluetooth-sendto。session `org.bluez.obex`激活文件存在。不能再装冲突包覆盖，也不能仅凭二进制存在认定接收agent/文件权限已就绪。固定上游OBEX代码只作基线，enhanced补丁与上游完全等价未证明；只用公共测试文件验收，不读取联系人/消息。

## 一加15可承担的对端范围

用户确认有一加15，当前系统版本、已启用profile和应用能力尚未读取。下面给出**角色匹配条件**，不是该机已支持或已通过的承诺。

| 目标 | RMX1931本机角色 | 一加15需要的角色/现场条件 | 本轮判断 |
| --- | --- | --- | --- |
| SSP配对、绑定/重连 | BR/EDR peer、BlueZ agent | 用户操作配对界面并匹配明确设备身份 | 可作为受控手机对端；仍须真实绑定/重连证据 |
| LE/GATT | 已备专用server+广告 | 有权限的GATT central/client应用 | 适合；已有Windows central更易固定挑战程序。普通配对UI不等于GATT客户端 |
| LE反向角色 | GATT central/client | peripheral/server应用及实际广告能力 | 先核对能力；不能由手机型号推断可广播 |
| 音乐接收 | PA本地A2DP Sink | 一加暴露A2DP Source并发送媒体 | 是可安排的手机到手机方向；PA端点注册和扬声器路由还须核对/实听 |
| 音乐发送 | PA本地A2DP Source | 一加实际提供A2DP Sink | 不能默认具备；普通手机播放音乐能力不能代替sink，需支持该角色的软件或实际耳机/音箱 |
| 本机手机通话到耳机 | PA native本地HFP AG | 对端HFP HF | 一加不能默认代替耳机；两个AG不匹配。需实际HF耳机/明确HF实现后再做SCO双工 |
| PAN上网 | 本机PANU | 一加明确启用蓝牙网络共享NAP | BNEP补齐后才有意义；Bluetooth连接不等于bnep接口/IP流量成功 |
| HID/HOG输入 | 本机HID/HOG host | 键鼠，或明确提供HID device角色的应用 | 手机通常的host使用方式不足；HOG输入还需UHID。不得把手机与手机普通配对当HID验收 |
| OBEX OPP | 发送client或接收server | 相反方向的OPP发送/接收UI与授权 | 可先用小公共测试文件；完成双方传输、内容摘要与清理才算通过 |

PA角色以源码为准：[bluez5-util.c:2834](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/modules/bluetooth/bluez5-util.c#L2834)按codec能力导出本地A2DP Sink/Source；[backend-native.c:1284](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/modules/bluetooth/backend-native.c#L1284)把内部HFP_HF映射成本机HFP AG注册。该枚举指对端HF，不能误称本机已有native HFP HF；一加作为AG并不能直接验收此路径。CVSD/HCI与现有缓存SCO能力继续沿用[原有受控验收条件](../bluetooth-oem-20261023/NATIVE-CVSD-ACCEPTANCE.md)，能力声明和本地signal均不算实际SCO数据通过。

下一设备窗口先只读确认同一启动/充电manifest、实际MGMT supported/current LE、BlueZ unique owner及GattManager/LEAdvertisingManager、btmon路径、PA端点和已授权对端profile；随后选一个满足角色条件的最短事务。不重复185扫描来代替363连接，也不在本轮改变手机、SDK或另一会话构建。

公开镜像仅本目录4个文件。固定源码缓存、首次canonical交叉阅读和缺路径404记录在本私有输出，未作为当前结论；无需镜像。
