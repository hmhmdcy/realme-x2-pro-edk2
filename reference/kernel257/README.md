# 257：从原厂F.16返回Linux，恢复完整系统并验证无线SSH

2026-10-17，用户明确要求刷回Linux、配置无线连接，随后移到室外复测GNSS。**已恢复248保存的完整Linux系统，实际进入新的正常Linux启动；Image183、F2FS可写根、958个软件包及无线SSH均已验证。** 当前没有新的Linux室外定位结论，后续须等用户确认室外放好并拔掉USB后采集。[恢复结果](restore-validation.json)、[无线验证](wireless-validation.json)

## 备份与目标核对

- 切换前核对当前RMX1931、F.16、root和真实USB连接；保存新的Android启动身份，不借用旧Linux启动身份发操作。
- 当前六个UFS LUN的12段GPT头尾与248逐字一致；userdata仍为119,033,245,696字节，Linux目标为`/dev/sda16`，起点7,370,473,472字节。
- 重新核验推荐的boot、logdump、完整标准partclone压缩镜像和离线工具SHA。使用`linux-userdata-clean-r6-private.pcl.zst`，4,589,045,416字节；没有把它作为Android sparse镜像交给fastboot。
- 当前Android的boot、logdump、DTBO、vbmeta和GPSTest数据已另存私人目录；336个共享文件已保存，其中335个与稍后的独立手机SHA一致，1个持续变化的xlog另取静态快照并核SHA。私人备份不公开。[文件保存核对](android-file-backup-validation.json)

## 实际启动过程与失败记录

bootloader确认同一设备、已解锁及分区尺寸后，先写匹配的boot235和Image183的logdump；这一对单独恢复后仍回到原厂bootloader，未开始userdata恢复。

核对发现当前原厂vbmeta标志0、旧Linux配套标志3，DTBO内容也不同。原厂两项均已备份，随后恢复匹配的旧Linux vbmeta，再恢复匹配DTBO；补齐后的启动链进入Image183的RAM恢复环境。没有重新刷同一候选去盲目重试，也没有恢复GPT、modem NV、校准、persist或整个固件集。标志3的两个位定义见[AOSP AVB头](https://android.googlesource.com/platform/external/avb/+/refs/heads/main/libavb/avb_vbmeta_image.h)。这次过程没有单独证明vbmeta和DTBO各自是否为充分或必要条件。

最初尝试RAM SSH时手机尚在bootloader，没有接受新主机密钥。进入RAM后严格匹配此前独立固定的恢复环境主机密钥，并核对Image183、机型和新的启动身份。Linux侧实际读回boot、logdump、vbmeta、DTBO四个分区，SHA均与所选备份一致。一次后续fastboot只读查询因设备已经离开fastboot而超时；其后的`continue`没有执行。[启动核对](boot-validation.json)

## RAM暂存和真实userdata恢复

恢复工具运行于RAM，userdata先保持未挂载、只读。完整压缩镜像分段传入限制为5 GiB的tmpfs；最初保护检查发现该子挂载没有出现在工具chroot中，接收器拒绝写入，补齐bind后才开始暂存。

USB SSH大传输发生两次中断。每次都先确认仍为同一RAM启动、userdata只读，停止唯一匹配的自有接收进程，复核最后一个已确认分段的SHA，再仅截去RAM文件中未确认的尾部。分段由16 MiB逐步缩为4 MiB、1 MiB，最终完整字节数和SHA与推荐镜像一致；没有在中断阶段开始写userdata，也没有改动PC原备份。

只在整份RAM镜像核验成功后，启动独立恢复worker。目标固定为已核对几何的userdata，使用正常块设备恢复模式，保留partclone CRC和目标尺寸检查，不使用跳过CRC/尺寸或创建PC raw文件的参数。解压和partclone均返回0，随后同步并将目标重新设为只读，执行F2FS `--dry-run --no-kernel-check -f`，返回0。

恢复后以只读、norecovery方式挂载，原Linux根标记SHA与备份匹配，软件包数958，保存的Wi-Fi配置1份；核验后卸载。9份恢复状态/日志逐件与手机源SHA一致。源代码见[恢复worker](restore-userdata-worker.py)，该文件使用本轮RAM启动guard和固定镜像/目标校验，记录的是本次操作上下文。

## 正常Linux启动及无线连接

RAM环境的ADSP正常停机，DSP均offline；补挂debugfs后发现显示CRTC仍活动，因此使用恢复系统的libdrm副本在RAM中按已有方法解绑fbcon、关闭CRTC，连续三次确认inactive、taint0。随后按Image183已验证的EUD退场顺序提交一次正常重启。[重启源码](ram-reboot-to-linux.py)

SSH在切换时断开，未收到进度标记；没有据断开直接宣称成功，也没有重发重启。随后使用**正常Linux原主机密钥**连接，核对不同于RAM的boot ID、Image183、`/dev/sda16`上的F2FS可写根和958个包，确认已进入正常Linux。原RAM及旧247/248/Android guard均失效，当前guard为`/var/lib/samurai/k257-runtime/boot-id-private.txt`。

正常启动taint0，ADSP、SLPI、modem均running。Wi-Fi在启动后自动连接，SSID与刚才Android保存的网络一致，原配置autoconnect已为yes，无需改密码或新建配置。通过wlan的IPv4地址另建严格固定原主机密钥的SSH连接，确认boot ID与USB一致，`SSH_CONNECTION`中的服务端地址确为wlan地址。

无线端点、SSID、密钥、Android原文件和完整状态均只在工作区外私人`E:/edk2-samurai-out/kernel257`。公开记录不包含这些内容。此次恢复的仍是已部署boot235/Image183及248完整系统快照，未部署249的新用户态或新内核；其它硬件沿用240及各专题的原验收范围。[收尾状态](final-validation.json)、[源码锁](source-lock.json)

## 后续GNSS对照

用户已收到可以拔USB、移到刚才室外位置的通知。放好确认后，以无线SSH开始Linux测量，比较[256原厂成功基线](../kernel256/README.md)中的持续fresh、TRACK、有效位置、PGA和频率指标。原厂302份成功位置回包不能算成Linux验收；本轮没有为追求定位结果直接修改PGA、RF寄存器或校准，也没有在恢复期间启动新的GNSS测试。后续用户已确认放好并拔USB，[258](../kernel258/README.md)完成Linux室外持续定位实测；本页的等待状态仅描述257恢复结束时刻。
