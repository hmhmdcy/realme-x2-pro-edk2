# 164：UEFI BeforeExitBootServices 面板复位候选

163实机显示TLMM probe晚于SMMU，无法覆盖更早的显示交接。164只修改BdsDxe中的本机Linux启动路径，在已核对的mainline boot option周围注册一次BeforeExitBootServices通知，通过Qualcomm TLMM协议配置GPIO6并驱动物理低。Linux原生面板初始化负责后续释放。镜像加载若未退出Boot Services就返回，关闭事件、不操作GPIO；不修改面板电源轨或内核。[补丁](before-exit-panel-reset.patch)

本地EDK2 Core在停止定时器和终止内存服务前调用BeforeExit组。采用这个组，避开退出后的外部协议调用；依据[UEFI规范](https://uefi.org/specs/UEFI/2.10/07_Services_Boot_Services.html?highlight=exitbootservice)。14个真实固件函数场景普通/ASAN/UBSAN通过，错误极性和错误事件组负对照被拒，使用实际EFITlmm头文件，协议结构48字节/GpioOut偏移32核对。[函数验证](actual-function-test-validation.json)

重新编译原代码、使用当前132/163设备树，所有模块与现机boot132逐字节相同；候选只改变BdsDxe，GUID `6d33944a-ec75-4855-a54d-809c75241f6c`，其它模块、设备树、BootShim、兼容DTB、Android header和ramdisk保持，gzip/FV/FFS/LZMA检查通过。编译有32条配置表达式/中间ELF RWX/LTO串行作业提示，4种模板全部在新编译的原代码中重现，未当作零提示构建。原始100663296字节boot已从实机备份且主机/设备哈希相同；候选尾部保持原字节。[固件与包核验](boot-package-validation.json)、[原始备份](boot-backup-validation.json)

按当前163启动身份正常停机/F2FS冻结、单次F1，仅刷boot164，保持logdump/kernel163。新boot自动桌面，DSI/CTL接管正常、关键显示错误0，但WCD934x音频WARN1、DMA prepare917、taint512，Phosh35.32秒，未通过零WARN软件验收。原因尚不明确，不归因于GPIO操作或宣称音频修复。[首次运行记录](runtime-validation.json)

只读mmap读取保留的UEFI日志，当前回调记录为`Success`，ring无丢失，证明请求实际在所注册的BeforeExit回调中执行。pread方式返回EFAULT，未放宽内核保护或写内存。[固件回调记录](firmware-log-validation.json)

165保持同一boot164和kernel163做一次正常重启复测，不新增刷写。用户已睡觉，实体白屏/花屏是否消失仍未观察，goal active。原版boot132及logdump158、logdump163均保留。
