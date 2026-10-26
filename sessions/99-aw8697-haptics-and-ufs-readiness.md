# 99：AW8697 原生振动接入与 UFS 就绪竞态

2026-10-11。按用户更新后的目标转到下一硬件，接入振动马达。蓝牙不配对连接，NFC无标签时只保留控制器验收，充电阶段收尾；全硬件 goal 仍 active。

Linux #98 已部署，AW8697 通过标准 `EV_FF/FF_RUMBLE` 和电气状态检查。三次20%/150ms短振动均观察到 GO=1/STATE=6，结束后 GO=0/STATE=0。随后10%强度测试证明关闭文件、SIGKILL后停振，以及长请求在约1.02秒被驱动看门狗停止。六次启动/停止、一次看门狗、error=0、taint=0。**用户是否感到实际振动仍待确认**；没有完成机械输出、休眠/唤醒或断电冷启动验收。

下一阶段已准备将无线就绪等待修复持久化，见 [kernel100](../reference/kernel100/README.md)；本阶段的成功无线恢复是 RAM 手动恢复，不能算自动启动修复完成。

## 本机来源与实现

本机19781设备树和驱动来自 [Realme发布的内核源码](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)：QUP7 `89c000`、I2C `0x5a`、reset GPIO116、IRQ GPIO24，芯片ID `0x97`。19781的LRA_0619配置提供170Hz/F0系数260、普通驱动上限52及过驱动125；Shipping API 29的235Hz备选不能盲用。频率/驱动选择以19781配置为依据，本次未独立读取已安装vendor的shipping API。

[Hotdog AW8697实机记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-11-haptics-aw8697.md)及其源码用于核对同芯片连续模式。该机的物理振动证据不代表RMX1931，未照搬其设备树或驱动强度。当前主线AW86927使用不同寄存器映射，不能直接绑定AW8697。

自有驱动 [aw8697-samurai.c](../reference/kernel99/aw8697-samurai.c) 仅匹配 `realme,samurai-aw8697`，先读ID再写运行期寄存器。支持标准FF_RUMBLE、工作队列I2C、20ms过流/过温状态轮询、1秒看门狗、关闭/挂起/关机停振；请求强度同时缩放普通/过驱动。失败时停振并保持复位，不无限重试。保留芯片复位保护阈值，不写NV/OTP、不上传波形固件、不开放原始寄存器写接口。IRQ已描述但本候选未启用处理器。

实际WSL内核DTS新增三个节点及QUP7的status/clock-frequency；其它节点语义保持。`INPUT_SAMURAI_AW8697=y`、`FF_MEMLESS=m→y`，CPIO与阶段98逐字节相同。工作区旧DTS镜像已落后于实际内核，原件保持；本次实际完整DTS见 [导出](../reference/kernel99/sm8150-samurai.dts.after)，不能用旧镜像构建。

## 构建与部署

内核HEAD `e42788eafb0bb9d8dfce319c71ca54c5207b2295`，EDK2 HEAD `f23a9f8aa619388412c8aad5834a460e51eae9eb`。驱动W=1编译通过。真正重建EDK2的内嵌DTB：只有原始DTB FFS及其压缩容器变化，其它可执行模块/EUD/F1源码保持。只刷boot和logdump，保留Android、userdata/GPT、原NV/persist及SSH身份，无提交/推送。

刷前完整96MiB boot和64MiB logdump备份通过；F1 receipt后独立fastboot核对本机身份、产品及两分区大小再写。F1包装进程在收到receipt后遭遇EIO/USB消失而返回1，现场保留；实际两次写入和重启返回成功，不能用包装进程返回码覆盖真实receipt/fastboot证据。

| 产物/证据 | SHA256 |
|---|---|
| Image #98 | `d765d0d7d23c47c2229c63a83094be8656d4cfd8c5cda3d794141f2141e6cc91` |
| DTB | `31479df0d1cb8b935f69c4ebdd396d25274a400ebde67fbbcf133737a4ba2868` |
| 原样CPIO | `dfa0e0b5d2bb09101c5f73de98a64f983da7edd434b4eabe7ddba62e87d52e2d` |
| boot头部镜像 | `7fa3a6879f8e3409fff129befedc32c6e67785fac18665984f52bf2d0f067c1f` |
| logdump | `c325eb6421b1194c17e309143183e0cf97192a395d7f4e537e829047ae6abea9` |
| 完整boot读回 | `91b64b25be666ec62778e96bbb2e67b985c84ac1d84f4dca10c0d0911ac068df` |
| 首次无线失败现场7文件 | `403a478f965b359d8aba1d49658fb7b30d9a5572c0e4e5c1b931b92550159a28` |
| 短脉冲18文件 | `5ce3363277851bd08fcd38d0016a031c146c767de4610b1a89023f4cd0b8f23e` |
| 生命周期14文件 | `904b18dd766eff774547bbf90058521d68ce41d98f8eec93a3d10d0bd4ec714e` |
| RAM无线恢复11文件 | `56c223704de7ed1c50eb1efb6bf3c979f57da553cb8e61dcde07aff21627f0a9` |
| 5GHz恢复验证14文件 | `d8aa7f2123e93da37fcf637c3dae57d147210a6580fa0ea68f276ad07194efcf` |
| 最终141文件checkpoint | `8518599702fa99be94e63f2689eb295d13516db965cd71dda1fddd83d95d72f2` |

私有文件在 `E:/edk2-samurai-out/kernel99`。清单逐一验证、子测试原包绑定、boot头部/完整分区/logdump/init/模块/服务读回通过；唯一RAM服务差异是就绪等待修复，已明确区别于刷入CPIO的旧服务。六个原NV及persist不变。

## 新发现与保留失败

首次自动Wi-Fi服务在dmesg **37.347674秒**退出1，NV所在sdf分区表直到**37.729198秒**才出现。失败目录已有验证后的固件，NV目录/原源哈希清单仍空，MPSS未启动，自动Wi-Fi日志为空。旧等待条件只查modem分区，不能证明所有NV源就绪。蓝牙随后没有全新离线身份来源，也退出；不能把此前WLAN查询故障隔离成功当成MPSS离线时身份可用。

[修复](../reference/kernel99/wifi-all-source-readiness.patch)在prepare前有界等待modem和六个NV源，逐个检查同机型号、标签与扇区数，最多60秒；超时直接失败，不开始部分复制。已保存原失败目录及服务，RAM替换服务后MPSS/WLAN/独立BT查询成功，手动5GHz认证/DHCP/网关/DNS/HTTP通过，蓝牙保持关闭。此修复在本阶段没有刷入CPIO，自动连接热点也未实现。

两次显示frame-done timeout **146.422852、775.627053秒**保留，首个发生在MPSS尚未启动时，未证明与无线或振动的因果关系。两个BT帧错误均power-on pulse/115200/chunk1/partial0/first00。振动测试窗口未增加显示超时；不能据此宣称整次启动显示无故障。最终日志环已滚掉最早311行，首次失败原包保留从0秒开始的日志，其余连续重叠部分核对通过。

第一次振动采集因debugfs尚未挂载退出，未播放；新目录重试通过。首次驱动编译缺失devm_device_add_file API，改为devm_device_add_group后通过。首次恢复联网脚本误以为WPA未运行，在任何联网更改前退出，空目录保留；新目录使用现有空配置WPA的reconfigure成功。这些原件没有覆盖。

## 后续

先将全源就绪等待刷入并暖启动验证，保持振动驱动/DTB/模块不变。机械确认仍等待用户；若没拿手机则用全新目录重复低强度短脉冲，不能重放starts=0的旧脚本。若无感觉，先核对本机motor/Shipping API配置和实际驱动输出，再决定调整，不能只以GO/STATE宣称马达可用。

继续振动恢复/机械验收和下一硬件接入，同时保留 [阶段98](98-independent-radio-identities-and-key-delete-trace.md) 的2.4GHz两次非主动reason7、单播删除约3.1秒等待、BT UART上电脉冲和显示独立问题。休眠、冷启动、长期双频、音频/传感器/摄像头/指纹/GNSS/蜂窝等见 [15组清单](../linux-port/docs/HARDWARE-STATUS.md)。不写充电配置/解封/NV/OTP/FET/OTG/MCU/GPIO，不用I2C_FORCE；GPIO116是本机振动复位。旧显示85–88快照及另一线程rootfs01保持。
