# 阶段129：初始console节点与实际启动验收

2026-10-12，goal active。上一轮128属于已完成的进展：真实刷机/单播key删除超时修复/5GHz与匹配rootfs验收。本轮从权威现机重新核对同一128启动、taint0/Phosh/Phoc/5180MHz及11来源；所有身份、配置、固件、原始日志和镜像均只存E:/edk2-samurai-out私有目录。

128完整内置cpio的dev目录为空，实际dmesg在18.936649秒出现unable to open an initial console。实际init/main.c在wait_for_initramfs后、执行/init前console_on_rootfs打开/dev/console；用户态init才挂devtmpfs。官方[initramfs文档](https://www.kernel.org/doc/html/latest/filesystems/ramfs-rootfs-initramfs.html)明确cpio可包含字符节点；本机drivers/base/Kconfig明确DEVTMPFS_MOUNT不影响initramfs启动，不能依赖该选项自动补节点。

隔离C/WSL kernel129完整复制128源码与initramfs，仅增加root:root/0600、字符5:1的dev/console，改变release和对应源路径；内核驱动Git diff与128完全一致。静态调用实际gen_initramfs及逐newc字段核验：395旧成员与所有内容/mode/uid/gid/link/rdev一致，候选仅多一个节点。完整129 Image/770模块/匹配initramfs蓝牙三模块构建、vermagic/depmod通过；最终cpio396成员，除了新增console和三模块匹配vermagic的字节更新，旧内容全部保持。770模块的可执行段全部与128相同，DTB与126嵌入版本逐字节一致。

刷前实际GPT18/11来源、boot/logdump/persist读SHA、118/126/128旧模块和BT动态release路径通过，129模块平行放入userdata而不提前加载。先保存trace并排空GUI/DRM/音频/无线/三remoteproc，sensor供电0、PCM关闭、双amp idle。第一次入口冻结成功但9505调试端口没有枚举，未发OUT，自动解冻回执及根文件系统实际创建/读写/删除探针通过，旧128启动仍排空。现有eudtool com-up经9501控制端口恢复9505/6-5/Shared；加入冻结前独立枚举守卫，Windows CRLF枚举正则问题修正。

第二次入口新冻结回执后，仅发送一次9002，OUT完成2字节，随后USB重枚举/Errno5；F1文本回执缺失，没有重发OUT/reset。独立read-only fastboot命令确认同一私有serial、msmnile产品、boot96MiB/logdump64MiB几何。刷机guard保留回执缺口，要求单次OUT完成+成功冻结+300秒内独立fastboot观察，且实际写入前再次独立枚举/产品/几何验证。PowerShell ConvertFrom-Json将UTC日期解析为System.DateTime/Kind=Utc，旧Parse转换丢Kind导致错误减8小时；实测真实age99.279秒，误判stale发生在写入前。改为保留DateTime.ToUniversalTime或DateTimeOffset解析，保存初始观察后重新只读核验，才实际仅刷logdump并重启。

实际新#129原生USB SSH恢复，boot/logdump/persist真实SHA读回、live DT所有预期节点/属性、GPT18与11来源一致；原始init用户态已运行，initial console warning从1变0，live console为root:root/0600/字符5:1。首次完整runtime Phosh/Phoc都已运行，taint0。5180MHz由新启动自主连接，没有手动activation、更换UUID/SSID/PSK/MAC策略或profile字节；网关3/3、HTTPS200/577字节、Alpine索引HTTPS200/532242字节/gzip/tar/6034包与50.44秒6样本通过，0新增key/FW/DPU/GPU/内核fault。ping文本为BusyBox的3 packets received，验证器先按3 received误判；读取原始3/3和0% loss后修正格式解析，没有重跑网络或放宽成功数量。

最终50.17秒6样本Phosh/Phoc/radio/ADSP/hci0/5GHz/taint0，11来源/770模块/boot-logdump-persist复核通过。trace保存后关闭、camss DMA N/SLPI offline/sensor供电0/PCM closed/amp idle failed0。累计DPU timeout3/GPU fault0，最终CRTC inactive；本次窗口0新增不代表持续绘制或旧118 GPU像素故障修复。内部TPG126历史验收及相同代码保留，物理camera未验收。

完整129 rootfs从128保留类型/所有权/权限/xattr/设备复制，936包、770匹配129模块、原双频配置保持，非模块变化仅stage marker和新129 marker。Android sparse 1,817,941,604字节，SHA256 6a110017145c0fd3f08a72e374d74a952a5242c4188c0c8252064b0aa14d99cc；双dry-run fsck/两superblock UUID-label/稀疏payload与hole重建，以及21,133条目反向导出内容/type/mode/uid/gid/symlink/rdev/xattr零差异通过。boot/logdump/rootfs/modules四件套逐SHA及encoded镜像chroot降权UID10000实际创建/读写/删除通过；完整userdata未全量刷入或擦除。

仍保留15组硬件边界：GPU/持续显示、物理camera/PM8008/HAL、GNSS真实fix、充电休眠/指纹、5GHz物理冷启动/休眠/长稳及历史非主动reason7。下一轮优先有界蓝牙自动扫描/停止回归，无需配对或人工观察，若出现难错先留档换项。目标不能标完整可用。

清理收尾通过：仅删除E126卷两个旧128 raw/restored，先新鲜逐payload/空洞证明可由保留128 sparse恢复，实际分配释放3894992896字节（约3.63GiB）。旧128模板/sparse/export、当前129全部产物与稳定115/118/126回退保持；C/WSL本轮没有新增删除，9个无证明旧.o保留。E118/122/126/129四私有卷串行sync/卸载/read-only e2fsck全部0，宿主C余9542823936、E余20590710784字节，原WSL VHD未resize/compact。所有本轮作业已terminal。
