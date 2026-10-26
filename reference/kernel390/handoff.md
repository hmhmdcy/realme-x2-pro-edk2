# 当前检查点：390（正式CAMSS/ICP已部署，111帧通过，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel390/README.md。389交接归档archive/NEXT-SESSION-through389-2026-10-21.md。上一轮389是候选；本轮390实际部署并验证。完整目标仍active，用户关灯条件继续，黑／噪点不单独判故障。

## 实际设备与源

一次正常restart2→fastboot，只刷boot，实际boot389 SHAe0256ff5bad0f6a2139de8690974d5fc25a0b58cad4cec1bb22f26bf0280884f，logdump365/ Image363保持。真实icp@ac10000 status=okay，driver=qcom-sm8150-icp；无test模块/临时overlay。五模块＋原厂FW已永久写入根fs并depmod，模组/光学校准内容和用户空间包未改。

新guard=/var/lib/samurai/k390-active/boot-id-private.txt；host390读取private390/postboot-adoption-private.json，再委托原USB密钥和known_hosts。旧host389/378guard会拒绝当前启动，不要重用或重新授权。390所有module/quiesce/runtime/reload worker、client、collector均终态，无后台设备工作。原Image363/release7.3.0-rc6-rmx1931-samurai-k363+；Image源ba61a62293e0f6bc5838c06f2e85e033e3d702a8。

WSL Ubuntu root，源码/build访问先284/storage.py::mounted_build()，持久ext4 /mnt/samurai-full282，不格式化／重建32GiB backing。source354 branch samurai-icp-platform389，HEAD a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07，干净，本轮未改源。389/source-state、platform-and-board.patch为最终；正常CAMSS和ICP在同一qcom-camss模块，contexts/exports/retained DMA保留共同供应者，静态设备suppress_bind_attrs，注册CAMSS→ICP、退出逆序。m2m bound按device_is_bound，NULL builtin owner参数安全；不声称完整builtin内核或任意热拔插已验证。

装的是private389 *-intree-r4.ko：qcom-camss2838304B/SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288；adapter118944B/SHAa0167f6acce4edad159d43101a723846ed494cf71fe3bb27857d2d145b44a7b8；core350472B/SHA036f590...、helper、SG与388完全一致。新SG提供owner符号，不能单独装旧SG配新adapter。现有v4l2-isp未替换，代码/rodata与重编译相同。SoC默认disabled，Samurai实际静态板级开启完整7SID/5个仅IOVA节点，原camera_mem9ab00000/5MiB/no-map不变。

initramfs实际CPIO仅3个蓝牙模块，没有相机模块。五个目标是覆盖原CAMSS/SG，新增core/adapter/v4l2-mem2mem三文件；FW=/lib/firmware/qcom/sm8150/camera-icp.elf，SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。原模块778基线＋明确新增3，不能把旧“全部778原哈希未变”用于现状态。

## 本轮实际证据

runtime-r1：关video FD后users0/jobs0/owner_refs1；再关export FD只留mmap仍1；最后munmap归0。原生18帧：NV12 MMAP6、NV21 DMABUF stride672/sourceoffset16四、双并发各四，均direct。随后管线client仍检查旧snapshot-collector.py，首次capture前退出，整体r1失败但已完成native不重测。已修collector文件名；collector本身的sysfs链接匹配在首个FW前已resolve。

runtime-r2只补管线：四摄各12、主摄RAW+NV12六、RAW-only六不启IPE、隔离主摄27/5阶段/GammaACK1，共81 direct。原始IFE时间戳和SOF保留。累计99/copy0/cancel0/failed0。r1失败/阶段复用及所有清理明确保留，不把r1整体改成功。

reload-r1：停PW/WP、owner_refs0与DMA回收后正常rmmod qcom_camss，ICP与CAMSS注销；modprobe从已安装文件正常重绑，probe未启FW、计数归0。候选广角再12 direct。已安装原r29的四摄各12帧，IPE计数不变。故本轮IPE总111，重载后当前counter仅12。硬件窗口无新fault/watchdog/protocol错误，均正常PC/WFI；最后FW单session、12帧/43消息/44IRQ，direct12/copy0，imports0。

check-pixels复核r1实际18帧输入CRC、每帧客户端Y相同、各组末帧全图CRC/UV；MAE.203125不变，padding0xa7保留。hardware-validation汇总111，像素文件仅private。全部是显式V4L2所有权，未证明异步implicit-fence发布互操作、真实取消／硬件错误并发、缩放或完整IPE IQ。

current-state：正式模块、FW、DT和boot保留，m2m registered/users0/runningfalse/fatalfalse，CPU/IRQ/backing/映射/导入引用均释放；ICP/CAMSS/双CCI suspended，17clks0、9rails disabled/users0、taint0。PW7130/WP7133恢复，owner_refs53是普通桌面CAMSS句柄，不是缓冲数；停消费者后才查0。SLPI本次running，SSC间歇旧失败未因本轮修复，勿外推全平台健康。

## 回退与接续

private390/preflight及module状态保存所有原文件存在/缺失。设备/var/lib/samurai/k390-deployment/backup有原CAMSS/SG两模块，rollback-files-private.json列原三模块和FW缺失；本地private390/offline-module-rollback从363离线包再次匹配保存同样两原件。boot366原件SHA c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924。设备restore-files.py --offline-files-only只恢复文件/depmod，须先停消费者回收DMA，并配合boot366切换；未执行回退。已安装Image363和logdump365不动，不全量重装778模块。

五个libcamera包仍99990.7.2-r29，config/stack0.1.0-r24，362私有Preview保持。IPE用户空间仍用387私有候选/mnt/samurai-full282/libcamera387-ipe-built/src/libcamera-v0.7.2，SHA60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d，签名IPA/proxy沿用安装r29。下一步把已验证IPE管线落实正式用户空间包，再做显式在途取消/硬件错误并发，原厂Gamma/LTM/CCM完整IQ及363/REMAINING-CAMERA-SCOPE.md全部：第五2MP、多模式、帧时长/防频闪、几何/多摄同步、连续AF。照明校准后做。

继续保留388 DMA-only SG/自有域物理重叠/未知完成保留，A5/IRQ+IPE resetACK后释放；373/375/376/379、381、377/378失败审计和383 Unicorn全局MEM_READ破坏ThumbIT/SP陷阱。原FW/HAL/汇编/CDM/日志/图像/个体校准只private，公共mirror仍Platform/Realme/sm8150，本地提交，不push/PR，保留其它改动。
