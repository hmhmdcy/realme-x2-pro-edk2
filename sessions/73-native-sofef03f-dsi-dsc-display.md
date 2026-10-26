# 73. 原生SOFEF03F DSI/DSC与60Hz显示输出（2026-10-10）

**本轮实现并部署本机原生面板，Linux #64自动替换遗留simpledrm为msmdrmfb。**
1080×2400@60、面板DCS状态0x9c、彩条—白屏—彩条硬件CRC及两次启动各三次
显示关闭/开启通过。亮度写入通过，光学图像和亮度硬件读回尚未验收。
启动交接仍有SMMU context fault；GPU、90Hz、休眠和其余硬件继续待验。
仅写一次boot、两次logdump，Android、userdata与GPT保留。
源码、完整日志和校验见[reference/kernel73](../reference/kernel73/README.md)。

## 73.1 从本机原厂数据建立实现

本轮新基线#62，完整54914字节dmesg经设备SHA/gzip CRC/长度校验。
板上面板标识SOFEF03F_M/Samsung1024；Android启动参数选择SOFEF03F DSC command
90fps display，实际live DT包含60/90两套timing。没有把SOFEF00等不同尺寸面板当作
同一硬件。参考[Realme官方内核仓库](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)
提交9668fcdc6ec15be7a10d66f7b93c347829e0fdb6，以及20261005T074931Z原厂Android
live-device-tree.tar/boot.txt/panel-touch.txt；旧工程的实现未重新使用。

面板1080×2400、68×152mm、四lane RGB888、DSC1.1/8bpc/8bpp、540×30 slice两片、
两片合为一个packet。原厂live有51条on命令，比旧源码多D1/D3/D9修正；显示开启29
是独立post-on命令。新驱动使用实际51条命令、保留各等待时间；生成128字节DSC PPS
后先与原厂逐字比较，匹配才以Samsung DCS0x9e发送。主线API用法参考
[Samsung S6E3HA8驱动](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/panel/panel-samsung-s6e3ha8.c)
和[MSM DSI host](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/msm/dsi/dsi_host.c)。

供电和GPIO按本机逐项核对：L14A1.8V IO、L17A3V模拟电源（与触摸共享），GPIO25
使能VCI、GPIO152使能VDDD、GPIO6低有效reset、GPIO8 mdp_vsync TE。reset raw1/0/1
等待5/10/10ms，供电/关电顺序依原厂代码。面板关闭仅释放自己的regulator引用，
不强制关闭触摸共享L17A。DSI host vdda为PM8150L L3C1.2V，PHY vdds为PM8150
L5A约0.88V；live-phy-supplies有原厂phandle解析。最初准备脚本的猜测标签在执行前
被纠正，没有用错误供电标签构建或刷机。

新代码patches/0009包含panel driver/Kconfig/Makefile/binding及显示DTS增量，
在session72原始文件上dry-run、实际应用并逐字匹配真实Linux树。保持既有EUD、
earlycon、RMI驱动和真实init/USB脚本。binding及目标DTBS检查通过。
只实现stock60Hz porches（H32/16/16、V12/4/12，166657kHz）；主线按压缩数据计算
DSI bit clock，本轮没有实现原厂固定1.107GHz时钟或90Hz切换，不能扩展验收结论。

## 73.2 依赖、构建与实际固件

首次#63内建MSM/DPU/DSI7nm/panel/backlight/LLCC，关闭不使用的OCMEM模块依赖；
内建initramfs UID/GID1000→包内root映射保持。首版未自动显示：MDSS在26秒记录
defer timeout，显示时钟在约31秒才就绪。手动drivers_probe使MDSS绑定，随后明确
DSI等待88e7000.refgen。这次reprobe用于定位，不冒充自动启动成功。

开始误判为缺SM8150专用显示时钟驱动，检查后明确SM8150使用SM8250共享驱动，
不存在SM_DISPCC_8150选项；错误方向在再次构建/刷机前终止。实际#64修复是
REGULATOR_QCOM_REFGEN=m→y及DRIVER_DEFERRED_PROBE_TIMEOUT=10→60。
新内核自动绑定MDSS/DSI/DPU，约35.5秒读到面板状态0x9c，随后fb0=msmdrmfb；
最终devices_deferred为空，未依赖手工reprobe。

| 已部署产物 | 字节数 | SHA256 |
|---|---:|---|
| #64 Image | 31840768 | 013b694a9711536bcd76776a9e42f43f3aea75e918e3bfa9eaf6d40ec47802cd |
| 固件原生DTB | 96796 | b8936a1b74d4bae97e0ca2be742a899d15655ed061d4ed718ab4fa76cd417844 |
| boot-k73-display.img | 6680576 | 57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999 |
| logdump-k73-display-deps.img | 67108864 | c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7 |

UEFI在干净bd23aaa基线上只更新实际嵌入DTB并正常构建，没有运行rootfs生成脚本。
101个FFS、FV/FFS校验和、LZMA、Android header/gzip/shim和兼容append逐项通过；
模块差异只有显示DTB和已有提交带来的固件版本字符串。DTB语义变化为6个面板/
pinctrl节点、10个显示/供电属性；GPU/GMU和此前触摸/CPU/USB节点保持。
两次make Image无新增编译warning；checkpatch结果和initramfs ownership/perms/
symlink/独有主机身份校验归档。包内无客户端私钥；两份私钥仍只在本地。

第一次确认F1新回执、独立fastboot序列62bc28a1/msmnile及分区大小后刷boot和#63
logdump。第二次同样取得新F1，仅刷#64 logdump；脚本生成时误替换reboot参数导致
unknown command，写入已成功，修正为正常reboot，没有再刷。最后第三次F1用于
同镜像重启；初查fastboot过早为空，等独立新枚举后只reboot。失败文件保留。
最终按PARTNAME查到boot=/dev/sde11、logdump=/dev/sde32，读回boot镜像前6680576
字节和整个logdump，与上表逐字哈希一致。旧cycled-facts误取/dev/sde9=dsp，
不能作为logdump核验；save-facts.sh已纠正，final-facts才是有效分区证据。

## 73.3 实际输出数据流和复测

#64首次boot_id=96bbf7e3-6192-4252-a8d6-79b5aec7ca9d，复测boot_id=
fc4fe164-1e90-402a-b841-ce870ba9ddfb，均taint0。KMS工具要求DRM driver=msm、
connected DSI connector36和1080×2400@60，实际native节点card1（simpledrm card0
移除）。工具使用dumb framebuffer、模式设置、vblank等待、command-mode DIRTYFB
与DPU硬件CRC，最后关闭/开启CRTC并恢复诊断控制台；不是截图软件哈希。

| 测试图案 | 两个硬件CRC |
|---|---|
| A：8条彩条 | 69961448 / 60af15f5 |
| B：白屏 | 25e11871 / 25e11871 |
| A：再次彩条 | 69961448 / 60af15f5 |

每次启动A/B/A各8条硬件采样全部稳定并符合上表。两次启动分别三次60次vblank等待
耗时0.991882/0.995547/0.994140秒和0.988739/0.999445/0.995889秒，每组序号差59。
两次各三次disable/unprepare→prepare/enable均通过，面板每次仍读0x9c，控制台恢复。
亮度120/256/400的DCS写操作和sysfs请求值通过，驱动没有get_brightness方法，
不能把actual_brightness软件属性解释成硬件52读回或实际亮度测量。
GPU/GMU仍disabled；renderD128由MSM注册，不代表Adreno渲染已实现。

首次CRC测试因静态command-mode画面没有后续提交而超时，补上每采样一次DIRTYFB后
通过，两个无效记录保留。一次无界cat CRC文件已Ctrl-C终止并确认无遗留进程，
最终工具采用8次采样/每次2秒poll。这些失败属于测量工具限制，不隐去或作成功证据。

最终完整59284字节dmesg（gzip13273，SHA4c35ab03e37c91532eb7346314daa2a76cac3b6e8e5bfb4922e6e458047bf386）
和5492字节facts（gzip1770，SHAa691e169a919660be6b437e61a5851c643ef16d05dae8d082916be345f138c75）
都由手机先保存，再SSH/SCP取得并校验设备SHA/gzip CRC/长度。六UFS、S3706、三个CPU
policy最高1785600/2419200/2956800、温度和configured/high-speed NCM保持，自动SSH
同主机身份成功。EUD原生命令K73_EUD_NATIVE_OK以及重启后的K73_REBOOT_EUD_OK
都返回目标输出；三次F1有回执、finally dispose/detach。最终COM14回Windows，
9501/9500/9505/NCM composite/NCM五节点OK，Shared/未Attached，无host owner。

## 73.4 未解决问题与下一项

启动首次原生接管时仍记录SMMU fault。最终日志35.312615～35.313090秒有10条，
IOVA0x9d1d2d00..0x9d239e00、SID0x800/0xc20落在旧splash0x9d000000+0x2400000；
后续约132～140秒的显示测试没有再记录，暂无panic/Oops/BUG/WARN回溯或显示underflow。
这些现象支持旧DPU数据路径与映射交接的推断，尚未验证根因或修复。
[维护者的旧启动路径讨论](https://lkml.iu.edu/hypermail/linux/kernel/2202.2/01145.html)
说明保留旧CTL可能导致交接问题；其CTL_FETCH_ACTIVE方案不能未经代际核对套在DPU5。
保留错误打印，不通过关闭IOMMU或删节点消音。旧initial-console Warning、RPMh读回-95、
QMP orientation/aux_bridge等也仍有各自既有边界。

先修显示交接，再接本机Adreno640/GMU。已核对vendor PARTNAME/UUID/ext4，临时以
ro,noload挂载，只读复制GPU固件后卸载；本地tar SHA83df98ec09d34411cc20c9cecd61ea9f3419ca6f8d12c6b1265bb7ae7f1ba8a8。
七个文件的SHA/ELF32 program headers见gpu-firmware-manifest，专有blob未入Git，
没有在本轮启用GPU。随后继续电池/充电、无线/音频等14组功能。90Hz、休眠、实际
光学图像、触摸精度、USB OTG/USB3尚未验收，完整GUI/rootfs仍未安装。
FAT空闲35082240字节，仍未建立保留Android数据的大持久rootfs分区方案。
回退需成对恢复kernel73/boot-before.img和logdump-before.img；全硬件目标保持进行。
