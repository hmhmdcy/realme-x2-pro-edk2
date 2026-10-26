# 阶段128：WCN3990 单播密钥删除等待与5GHz

2026-10-12，goal active。本阶段从实际126启动继续，所有身份、凭据、固件、完整日志和镜像只存 `E:/edk2-samurai-out/kernel128`。

126当前基线：2.4GHz自动连接、桌面运行、taint0，内部CAMSS TPG历史验收保留。有限5GHz临时NetworkManager副本成功在5180MHz认证、DHCP、网关3/3、HTTPS200/577字节、软件索引HTTPS200/532242字节，gzip/tar结构和6034包索引可读；10样本45.5秒保持5GHz，随后恢复原UUID与2462MHz。原持久配置、MAC与11来源保持。但两次切换各新增一个key操作-110，不能把网络成功写成错误已修复。

新的本机过滤trace直接确认：两个单播DISABLE_KEY分别3208.157/3261.051毫秒返回-110，WMI各发送一次，没有security indication；四个SET_KEY各发送一次、各有确认并返回0，耗时0.335–2.596毫秒。group DISABLE_KEY在peer已离开后不发送WMI、返回0，不能以它证明组密钥替换的硬件确认。

参考[上游RFC](https://lists.openwall.net/linux-kernel/2026/09/18/12)与[已合并GTK重置修复](https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/stable-queue/+/refs/tags/v6.17.12/releases/6.12.58/wifi-ath10k-fix-connection-after-gtk-rekeying.patch)，128仅对WCN3990/SNOC、非组密钥DISABLE_KEY，在WMI发送成功后跳过不存在的确认等待。SET、随机组密钥替换、发送错误、其它芯片/总线/nohwcrypt保持。RFC还涉及QCA6174，本机没有扩大此范围。没有改原厂固件、板校准或regdom。网上[regdom工具](https://github.com/M0Rf30/wcn3990-regdomain)只作为排查参考，本机5180可见且传输通过，不使用其外机blob或改校准字节。

128候选通过实际函数提取的1152组gcc Werror/ASan/UBSan路径测试；完整内核/770模块/匹配initramfs蓝牙模块构建和depmod通过，所有770模块的可执行段与126一致，因为ath10k为builtin，修复进入Image。设备树108274字节SHA与126相同，复用已验证boot内嵌DT。保留126源码、boot/logdump、模块与127完整rootfs稳定回退；新模块128已在userdata平行放置，不提前加载。刷前GPT18与11来源、原boot/logdump/persist哈希通过。

实际部署与对照已完成：仅刷logdump，boot字节保持；原生USB SSH恢复，新boot/rootfsuserdata/内核128/taint0及分区实际SHA读回通过。live DT节点集合与126候选所有预期属性逐字节一致，GPT18与11来源保持。首次早期采样时Phosh/Phoc尚未启动，原记录保持false；后续服务正常完成，桌面运行。

128相同双频切换trace的两个单播删除分别0.027/0.018毫秒返回0，仍各发送一次WMI且没有确认；后续四次安装各收到一次security indication，耗时0.459–2.462毫秒、全部返回0。无trace overrun，不发送原始数据/密钥trace。5GHz再通过网关3/3、577字节HTTPS、532242字节/6034包软件索引和10样本45.47秒，回到2.4GHz后0新增key timeout、reason7、固件crash、DPU/GPU/Call trace。修复删除等待不等于历史reason7根因已解决。

随后移除原私有NM keyfile的band=bg并将通用连接名改为Samurai Wi-Fi，保留UUID/SSID/PSK/MAC策略/自动连接/IPv4/IPv6字段与root0600。先对原模板和live文件字节相等及唯一字段差异静态校验，实际增量安装后在5180MHz再次通过网关/HTTPS/11来源，成功才同步到rootfs模板。一次NetworkManager正常service restart，在第15个一秒观察内自主连到5180MHz，同一UUID，未调用手动connection up，HTTPS200/577字节和6样本25.2秒通过；不算手机断电冷启动。

最终50.15秒6样本桌面/MPSS/ADSP/hci0/5GHz/taint0通过，boot/logdump/persist与770模块/11来源复核通过，保存display/radio trace后关闭，DMA trace N，SLPI与sensorpower0、PCM关闭、双amp idle/failed0。累计DPU timeout1/GPU fault0，最终CRTC inactive；此结果不能声明持续显示或GPU故障修复。initramfs初始console警告1仍存在，可作为下轮有界修复项。

完整rootfs128从127保留类型/owner/mode/xattr/设备节点复制，换770匹配128模块及上述双频配置；936包保持，非模块变化只含Wi-Fi配置和两个stage marker。原127模板、sparse和115/118/126稳定回退保持。新F2FS镜像双dry-run fsck、稀疏payload/holes重建、21,132条目反向内容/type/owner/mode/symlink/rdev/xattr零差异通过；编码镜像实际chroot降权UID10000创建/读写/删除通过，boot/logdump/rootfs/modules四件套逐SHA验证完成。镜像1,817,937,508字节，SHA256 326280a49951bafec4f9a3bd4ac400b9e84277c41364250e579bea34b7fb4fb8。没有bulk userdata刷入或擦除，不能标目标已完成。

自动化工具初始两次trace字段筛选被当前内核拒绝，均在启用前失败并关闭/删除新instance，原件保留；去掉该辅助筛选后第三次采集通过，固定debug消息过滤仍在，debug_mask0、不记录原始WMI/HTT/密钥字节。初始日志路径假设和旧SCP密钥库引用已纠正，保留失败现场。完整git whitespace检查发现的是基线EUD源码既有两处空白；新mac.c补丁检查通过，除此文件的Git diff与126相同，没有顺便更改旧驱动。

仍保留物理摄像头、GPU、持续显示、GNSS fix、充电休眠、指纹等15组硬件缺口。5GHz冷启动、休眠、长期稳定及历史非主动reason7掉线尚未验收。网络测试使用[NetworkManager临时clone](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html)与[band属性](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/settings-802-11-wireless.html)，恢复原配置；日志通过设备实际logbookd/logread读取。

清理已完成：C/WSL obsolete110/112/114的3个vmlinux先用canonical objcopy分别证明与保留本地和导出Image相同，再将完整ELF私有归档逐member SHA回读后删除，实际分配563978240字节；稳定109/111/113/115/128 Image、源码diff/.config/Module.symvers/DTB/cpio保持，缺少证明的9个.o继续保留。E126卷两个被128替代的127 raw经新鲜稀疏payload/空洞恢复证明后删除，实际分配3894984704字节；127 sparse/模板/export、128全部产物与115/118/126稳定回退保留。三个E私有卷串行sync/卸载/read-only e2fsck全部0；宿主C余13301018624、E余29771546624字节，不resize/compact原WSL VHD。
