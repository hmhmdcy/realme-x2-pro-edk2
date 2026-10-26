# 456：原 Image363 加 0064 的独立 core Image

本轮只处理 V4L2 core 在允许释放 sd 的回调后继续写 devnode 的顺序问题。源码固定为原 Image363 提交 ba61a62293e0f6bc5838c06f2e85e033e3d702a8，仅应用 [453 的 0064](../kernel453/0064-media-v4l2-core-clear-devnode-before-subdev-release.patch)，将 sd->devnode=NULL 前移。不使用当前 source354/441 HEAD 的另 39 条路径变化，不混入 DT、CAMSS、videobuf2 或 lens driver 修改。

本轮不访问手机、不占 SDK、不构建 DTB/全 modules/rootfs、不封装或启动 boot。451/452 冻结目录、453/455 源码和 O 未写；共享 source354 的 index、共享 O 的相关输入及当前 DTB 受前后指纹保护。

## 原始输入与隔离

[预检](preflight.py)先走 449 mounted_build 守卫。私有原 Image363 SHA 15746aab…匹配原收据，从实际 Image 嵌入提取 config，精确为 23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed。GCC 保持原 aarch64-linux-gnu-gcc 15.2.0；MODULE_SIG 关闭、SYSTEM_TRUSTED_KEYS 为空，没有生成或替换签名证书。原 input-initramfs363 的 396 项 mode/uid/gid/内容/链接目标与原私有 manifest 一致。

共享 Image、vmlinux、Module.symvers、modules.order 仍匹配原 363。共享 DTB 已为 0cc9dfd2…，与原 363 的 dcdd74ec…不同；最初将 DTB 一并视作 363 输入的预检因此拒绝。确认本轮仅 Image 目标、不读取 DTB 后，改为保护其现状哈希，不借此更新或验收 DT。共享 .config 同样不作为原配置来源。

预检 ext4 可用 11.74GB，共享 O 约 2.32GB、源码约 1.90GB；连同 2GiB 构建余量和 2GiB 最低保留，空间门槛为 8.52GB，具备准备条件。[准备脚本](prepare-source.py)在私有 kernel456-core0064-private 创建独立 Git clone/index，固定 ba61；零 fuzz/offset 应用补丁后只有 drivers/media/v4l2-core/v4l2-device.c 改动，改后 SHA 8378f997…。

O 是完整独立可写副本；不是共享 vmlinux.o 链接，也不复用 453/455 O。迁移时移除旧 source 链接、生成 Makefile 和不可信配置生成项，恢复精确原配置，让 Kbuild 根据新路径、真实依赖和命令重建。没有通过 touch/utime 或链接共享对象强迫“一对象构建”。准备后尚余约 7.51GB。

## 构建与身份

[构建脚本](build-image.py)只请求 make Image，使用私有源码/O、-j4、W=1。保留原 release 7.3.0-rc6-rmx1931-samurai-k363+ 和原配置；采用本次真实构建时间及显式 #456 banner 元数据。每秒检查空间，低于 2GiB+256MiB 时停止本任务 make 进程组，给最低 2GiB 留余量。完整编译/诊断日志只在私有 kernel456，不以扩大重编本身作为失败。

实际 [Image 构建](build-validation.json)成功，1110.662 秒；新路径引发 3329 个 CC/AS 对象重编，模块对象为 0。最低可用空间 7262167040 字节，未触发资源阈值。全局 W=1 记录 1129 条诊断，其中 1098 条为 -Woverride-init、error 为 0；0064 变更文件零诊断，不能称全树零告警。完整日志和对象/诊断清单留私有 kernel456。配置文件及新 Image 中实际嵌入配置均精确保持 23e088a9…。

真实产物：

- E:/edk2-samurai-out/kernel456/Image-k456-core0064-private，59243008 字节，SHA256 0ad2f0cb8ba6ed9cdc6426f9a5d672f2c7b9583a6f3469ffc55854232fdbbc5c。
- E:/edk2-samurai-out/kernel456/vmlinux-k456-core0064-private，190393832 字节，SHA256 13e95a39d9c4b3cabc0387237061bae5085a6f6bca98f3f6bc94695c90e1f542，build-id 41bbcc5fb1f4fca6bc49f379b907c6fa73f2c0f1。

banner 为 #456 SMP PREEMPT Fri Oct 23 14:26:52 CST 2026。构建、实际 ELF/GDB/依赖审计均已结束；CPU 构建资源已交回主线，不再 make、重链接或做重内存操作。SDK 始终未占。

这是新的候选 Image。相同 uname release 是为保留现驻模块 ABI，不能用于证明 0064 已运行。未来由主线安排实际启动窗口时，必须核对新 Image SHA 和运行内核 /sys/kernel/notes 中的候选 vmlinux build-id，才可考虑 455；旧 363 build-id 为 ba199b015285fffacdc65d360a52854301a2d494。这里不提供封装或启动动作。

## ABI 与布局证据范围

[核对脚本](check-abi.py)对实际 ELF 导出命名和生成的 builtin symvers 元数据做比较，不把复制过来的完整 Module.symvers 当作新 Image 的证明。原 363 实际 builtin 导出 15097 个，与原 Module.symvers 的 vmlinux 条目一致。原配置关闭 MODVERSIONS，因此符号相同本身不能代替布局/头文件检查。

原 reduced DWARF 可取得以下 8 个完整结构的尺寸、对齐、成员类型和 bit offset；完成后与新 vmlinux 逐项对照：

| 结构 | 原 363 大小 |
| --- | ---: |
| v4l2_subdev | 384 |
| v4l2_subdev_internal_ops | 48 |
| v4l2_device | 120 |
| video_device | 1208 |
| v4l2_subdev_fh | 160 |
| device | 800 |
| module | 1152 |
| i2c_client | 880 |

这 8 类结构的实际尺寸、对齐、全部可见成员类型和 bit offset 均与原 363 一致，[ABI 收据](abi-validation.json)通过。另 7 类辅助结构在原 ELF 中缺少完整定义，不能称为已从 DWARF 比较：v4l2_ctrl_handler、dev_pm_info、regulator、kref、mutex、list_head、media_entity。455 的实际 .ko 同样采用 -femit-struct-debug-baseonly，API 头类型缺失；收据明确 comparison_available=false、equal=null，不用空集合冒认全部类型通过。其自身 bu64253 结构实际 DWARF 为 712 字节，sd 位于 0，下一 ctrls 位于 384，直接对应内核 subdev 的 384 字节嵌入跨度。

已核对 455 实际模块 SHA 2f4abac1…、41 个真实未定义导入全部在候选实际导出中，重新生成的 vmlinux.symvers 元数据与原 363 的 builtin 部分完全相同。除驱动自身外的 734 个真实编译源码依赖与固定 363 候选逐字相同。原配置/编译器相同且相关头逐字相同，为 DWARF 缺失项提供源码/构建条件证据；这不是缺失 DWARF 的实测尺寸，也不代替实际内核并发、PM、热解绑或模块加载验证。

编译器将目标内联进 v4l2_device_release_subdev_node。实际反汇编中，原版在偏移 256 的唯一 devnode 清零 store 位于唯一间接 release 调用之后；候选中已位于调用之前。两份反汇编留私有，没有仅以源码补丁或新 build-id 推测改动进入二进制。

原 vmlinux 中真实嵌入 initramfs 为 15063774 字节，SHA 319b665d4bdbf9647efb1ae1055438e5a7990c69e7016190c9625de414b81678；候选为 15063818 字节，SHA 17818eae341d8e9eda0211b9608865554e37a35570a362636c77998b2b256acc。首次严格整档 SHA [比较失败](abi-initial-archive-validation.json)；未隐去该差异或重链接去抹平元数据。

两份解压归档均为 29770752 字节、396 项，无增删。逐项 data/mode/uid/gid/nlink/dev/inode/内容均一致，只有 396 项 newc mtime 字段改变；原时间为一个值，新时间共 14 个值，不能写成统一时间。仅将每个 mtime 字段归零后，两份归档逐字节完全一致，SHA bcf4d2f47a5f01a43d8c525e9bcc9e9eddbed9dc44bff42b5e47b323ba5fff9e，连顺序和填充也相同。

最终条件明确为 archive_byte_identity=false、only_mtime_changed=true、396 项其余数据/元数据完全一致；主线接受这项构建归档元数据差异，保留真实构建元数据，不为此伪造时间、改输入或重链接。不能笼统声称 rootfs/归档字节未变。原固件、模块内容和输入目录前后保持原样。当前通过仅覆盖构建与离线 ABI/机器码条件，runtime 未验；没有打包、部署或启动。
