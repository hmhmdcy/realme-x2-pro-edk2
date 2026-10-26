# 阶段126：DMA 守卫、完整 rootfs 与实际刷入验证

2026-10-12。目标 active，未验收完整系统。保留功能稳定的115/118镜像、模块和恢复资料。继续自动检查，不要求人工观察。

## 已完成

126 使用独立 release `7.3.0-rc6-rmx1931-samurai-k126+`，避免覆盖118模块。SM8150 DMA映射逐段检查连续性和全部plane长度，限制在原厂 `[0x07400000,0xe0000000)`；实际函数抽取测试覆盖19边界和512随机SG情形，CSID parent电源引用测试覆盖6故障分支及正常/共享引用生命周期。Werror、ASan、UBSan通过。完整Image、770模块和DTB构建通过，其他769模块可执行段与125相同，fixed IPA代码保持。严格CAMSS、endpoint和IOVA schema正反例通过。

蓝牙服务原来硬编码legacy目录，现按当前release选择模块；3个蓝牙模块可执行段与旧定制版逐字节相同，initramfs与完整rootfs均使用126模块。完整rootfs含936软件包、770模块，稀疏镜像1817929316 bytes，展开119033245696 bytes，SHA256 `0f9fcf7f17ddf1fca947c8e162622df9381dd1133edca0f4743bbd47b295938f`。两次fsck、稀疏重建及21,130条目内容/权限/UID/GID/xattrs/链接反向比对通过。userdata未全量刷入或擦除。

已完成当前118 boot身份、GPT18、boot/logdump/persist与11来源hash核验，并行安装126模块，原118目录保持。GUI/DRM/音频/三个DSP/无线排空后sync和F2FS冻结，EUD单次9002取得F1回执，fastboot身份/大小核验后只刷logdump。新启动确认#126、正确release、taint0；boot/logdump/persist和GPT18及11来源再次核验通过。USB SSH恢复，蓝牙、基带、Wi-Fi有正常启动日志；稍后Phosh/Phoc均运行，早期采样未启动应如实保留。DPU启动仍有3次frame done timeout，不能算显示故障修复。

排空脚本曾错误要求NetworkManager停止后Wi-Fi仍绑定；实机证明已解绑且wlan不存在，改为必要时解绑、最终检查driver/wlan缺失。第二处脚本把原生remoteproc `modem` 错写成 `mpss`，已修正，并保留原resolver对compatible、DT路径、固件和唯一设备的验证。采集脚本DRM地址ae00000错误，实机为ae01000/card1/minor1，修正并续采未完成部分，未覆盖启动身份。

## 实机发现与当前修复

加载qcom_camss成功，但没有media/video节点，无deferred probe。live FDT没有CAMSS节点。实际本机UEFI PlatformBm.c明确依赖DtPlatformDxe安装的内嵌DT，FAT samurai.dtb不会替换它。第一次126复用115 UEFI，导致新增CAMSS设备树没有生效；静态包内DTB通过不等于启动DTB生效，已在日志中证实。现在补建嵌入126 DTB的canonical UEFI，要求除DTB FFS外其他可执行模块逐字节保持，并恢复原UEFI源码/blob/FD/FV/boot后再刷入。

有限TPG工具已由实际126 UAPI编译静态AArch64，host/QEMU和实机hash自测通过，仅接受126 release。计划经标准media/V4L2 ioctl读取3帧320x240 GRBG10P，逐帧检查错误标志、时间戳、序列、有效像素与预填充差异和hash，并恢复图/格式/控制/缓冲区。实际capture未执行，CPAS版本、IOVA实际安装和DMA内容仍待证实。

参考[固定内部TPG脚本](https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/47087509c4289c2580c54f5433e55366b2e00445/scripts/test-mainline616-camera-csid-tpg.sh)只借鉴标准接口测试方式，参数与安全守卫来自本机源码；[EDK2项目](https://github.com/edk2-porting/edk2-msm)为背景，设备树加载结论以本机固定源码和live FDT为依据。

PM8008四输入/全芯片复位、物理sensor/原厂HAL settle、GPU CCU translation、GNSS fix、指纹、充电休眠等长难项仍开放。此处不把TPG或rootfs文件完整性写成完整硬件可用。

## 已完成嵌入DT刷入与真实TPG

canonical固件审计通过，除DTB FFS外其他UEFI可执行模块/bootshim/兼容DTB保持；原源码/blob/FD/FV/boot逐字节恢复。第二次当前126 fresh preflash与排空/trace保留关闭/sync/fsfreeze/F1单次回执通过，只更新boot，logdump保持。boot SHA256 d85f110275758c981691daf0d189a50c4ae45e718da4b947085ca624c6b653f8；logdump5684fee4cf88d9edea0aed503606f3f81735e1a9fb6fce0c51aa766ebd38c8b2。新boot不同、live DT节点集合及每个预期属性精确匹配126 DTB，CAMSS自动绑定，22个media实体、8个video/14个subdev节点。

真实TPG3帧320×240/stride400/size96000，序列0/1/2、时间戳递增，三个不同预填充全部96000有效字节被覆盖，FNV64同为af89995da687f925，首帧SHA25658109bf2b6a4791284bc6299d99d1ed5011b3cc15516e580a31bad64233d0460。三个IOVA dffa0000/dffc0000/dffe0000及完整96000-byte plane均在原厂窗口内；bufinit和bufprepare两次核验共6条trace。VFE0 IRQ+8、CSID0+1，PHY/VFE1/CSID1 IRQ无变化；三个CAMSS domain前后suspended/user0，两路IFE off。STREAMOFF、REQBUFS0、图/format/control恢复调用均成功，dma_trace关闭、taint0，capture期间无新fault，SLPI和物理sensor供电保持关闭。

按照[官方packed Bayer布局](https://docs.kernel.org/userspace-api/media/v4l/pixfmt-srggb10p.html)解码76800样本，0/1020各38400，非恒定横向条纹、全部240行重复两行图案。不能仅凭覆盖预填充当成正常图像，已排除all-zero/恒定内容；Bayer颜色分量次序及完整10bit动态范围未证明。CPAS成功路径通过100/101版本守卫和十项QoS读回，接受此版本族属于从实际成功路径推断，精确revision未单独记入硬件日志。此结果不代表外部PHY/sensor/物理摄像头可用。

最终同boot的6次10秒间隔采样50.19秒：Phosh/Phoc保持、wlan up、MPSS/ADSP运行、hci0存在，PCM closed/双amp off/muted/failed0，zram证据已采。NV6/source4/vendor1及770模块、boot/logdump/persist保持；trace完整私有保存后关闭。采样期间0新增DPU/GPU/SMMU/WARN/BUG/Oops，整个boot仍DPU1/GPU0，最终CRTC active0。因此只能认定有限窗口恢复和内部数据通路，不认定持续绘制或休眠长稳。Bluetooth sysfs没有name属性的采集错误已改为hci0目录/uevent核验，并同boot续采；没有伪造缺失属性。

## rootfs语义检查与清理

126镜像完整导出内容/metadata无差异，但语义审计发现账户UID/GID10000，home及60条目仍1000，另85个系统配置/固件资源属主1000；实机相同路径为10000/10000，当前桌面没有该问题。系统20978条目root-owned，所有usr特权文件root-owned，问题限定用户home。126 rootfs镜像保留为诊断/重现，暂不全量刷入；127副本只修正这60个home与85个系统资源条目的属主并保持内容/mode/xattr，验证真实降权创建/读写/删除从EACCES变为成功，随后重建完整镜像。系统目标尚未完成。

按用户要求清理obsolete110/112/114生成ELF对象。逐一核对旧Image/DTB/cpio与E导出，排除tracked/symlink，只选有Kbuild .cmd证明、Git ignored的生成ELF；归档全部候选并逐成员SHA回读，再逐file当前hash核对后删除。共4072+5552+5565=15189文件，allocated2677497856 bytes，3个可恢复私有gzip archive总800763433 bytes。tracked diff/源码/.config/Module.symvers/Image/DTB/cpio/.ko保持；稳定109/111/113/115的Image hash未变，118卷和115/118回退套件保留。WSL根实际free增加2677428224 bytes，宿主C最终约16.06GB free；未resize/compact VHD，不把guest释放量等同hostfree增长。其它工作目录如MediaCrawler/telegram/angr不属于此任务，未动。

127首个WSL启动请求曾返回WSAETIMEDOUT；检查WSL已停止，E126无loop，readonly e2fsck=0，随后检查rootfs127尚不存在，故修正尚未执行，没有半成品副本。重新启动后使用cp -a保留设备节点/hardlinks/ownership，不用普通copyfile复制/dev/null。后续必须等待terminal再运行依赖脚本。
