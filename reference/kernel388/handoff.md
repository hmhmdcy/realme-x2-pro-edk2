# 当前检查点：388（IPE直接DMA与导出owner实测，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel388/README.md。387交接归档archive/NEXT-SESSION-through387-2026-10-21.md。用户已关灯，黑场／噪点按低照度解释，不能单凭亮度判故障；照明校准后做，不阻塞底层。完整目标未完成、未暂停、未blocked。

## 源与设备

WSL Ubuntu root。源码／build访问先reference/kernel284/storage.py::mounted_build()，持久ext4 /mnt/samurai-full282，绝不格式化／重建32GiB backing。主源source354，branch samurai-ipe-direct-dma388，HEAD95caf30a629bbaf454ebfc9ed25ce16ea3a952b5，父3878003933b7e31e4b5f4d27d21789d42da686831ba，干净。source-state.json、direct-dma.patch为最终；prepare-source.py仅初稿，后续脚本修正过。close-current确认最终源／proposed／父提交补丁一致。

libcamera沿用387候选，/mnt/samurai-full282/libcamera387-ipe-built/src/libcamera-v0.7.2；库SHA60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d，dispatcher/IPA未变。core350472B、adapter118752B、新SG100104B，private388 *-intree-r4.ko，W1/-Werror无诊断，9目标，共享build输出/config/symvers恢复。核心与较早307001测试版本相同，adapter后补owner。

手机同一378恢复boot，host388委托387→378→371→360原USBkey／known_hosts，guard /var/lib/samurai/k378-recovered/boot-id-private.txt。Image363/boot366内DT365、五包r29/config-stack r24、362四个私有Preview不变。没有永久安装／刷写／重启。静态ICPdisabled／仅SID2222；七SID仍临时owner。SSC旧EPERM/daemon4/SLPI offline未修，不盲重启DSP。

## DMA与所有权

新增camss-icp-a5-dma.c/h：核心持有DMA-BUF/attach/map，同一A5+IPE域直接DMA IOVA，校验偏移／连续DMA区间／32位／物理重叠。物理地址经自有IOMMU域查询，不能读导入sg_page/sg_phys，DMABUF_DEBUG剥离页字段。直接模式不分配image_input/output或复制像素，保留旧CPU fixture。未知MAP/FRAME/UNMAP继续保留，A5/IRQ+IPE reset/quiesce完成才放。

m2m用标准vb2_dma_sg，MMAP也经DMA-BUF进入核心。新增通用vb2_dma_sg_get_dmabuf_owner指定原始导出文件owner；旧接口THIS_MODULE行为不变、公共vb2结构体ABI不改。实际平台owner依赖adapter→SG，DMA-BUF allocator release完成后才module_put。m2m只覆盖get_dmabuf，status新增owner_refs。平台临时驱动suppress_bind_attrs，正式解绑生命周期尚待。

原型wrapper c0fc6e...仅构建、未上机，因内层deferred fput/observer问题revert到cd30cba...，不要复用unused-*。最终95caf...要求新SG符号，原SG不能加载新adapter；只能在framework事务或正式完整部署中使用。

显式V4L2 QBUF/DQBUF所有权，导入前等已有fence；未实现／证明完整异步implicit-fence发布互操作。去复制范围限候选m2m／libcamera→核心图像路径，不外推所有应用。仍1:1 NV12/NV21／IQ旁路，未宣称缩放或完整IQ。

## 最终实机及失败

/var/lib/samurai/k388-framework-r1，outer25554及native/pipeline客户端collector均终态。事务停PW/WP→卸原CAMSS/SG→临时新SG→重载原CAMSS→两套测试→恢复磁盘原SG/CAMSS并核对note/文件→已安装四摄各12帧回归→恢复服务。未覆盖原模块磁盘文件。final framework-runtime-validation通过。

导出探针关闭video FD后users0/jobs0/owner_refs1；关DMA-BUF FD只留mmap仍1；内容正确，最后munmap归0。原生18帧：NV12 MMAP6、NV21 stride672/sourceoffset16 DMABUF4、双并发各4。最终管线81：四摄各12、主摄RAW+NV12六、RAW-only六不启IPE、隔离主摄27/五阶段/GammaACK1。总direct99/copy0/cancel0/failed0；原始IFE时间戳与SOF保留。没有实测取消分支或HW错误并发。

check-framework-pixels独立核对18帧输入CRC／客户端每帧Y相同、各组末帧全图CRC/UV；UV MAE.203125不变，padding保留调用方0xa7（旧bounce0xa5）。模型20503 DMA边界、13核心生命周期、4导出生命周期ASAN/UBSAN均通过，不能代替完整硬件故障并发。

先前native-r1因读取DEBUG SG页字段失败，未提交图像、具体旧errno未记录；r2修好18帧、早期pipeline-r2为81。pipeline-r1上传中断，目录/worker未创建，孤立接收Python23617经pidfd核对终止。现已缓存校验复用大库。close-current首次核对器误把unified/git两种diff字节比较，修核对器后通过，不是源码错误。attempts-validation保留全部。

current-state：所有本轮worker/client/collector不活跃，原SG和CAMSS恢复，临时模块/video/media/FW移除，taint0、CAMSS/双CCI suspended、9rails disabled/users0，PW25932/WP25938各一。PID仅历史证据，后续查实态。

## 接续

优先正式SoC平台owner／板级启用，补显式在途取消／硬件错误并发，再接原厂Gamma/LTM/CCM完整IQ与reference/kernel363/REMAINING-CAMERA-SCOPE.md全部范围：第五2MP身份、更多模式、动态帧时长／防频闪、几何／多摄同步、连续AF。不得缩成只四摄或99帧。

继续保留373 reset后HFI、375 PC/WFI、376 token/严格ACK、379 MAP/UNMAP长度、381七SID/DMA retain与resetACK、377/378失败审计。383 Unicorn全局MEM_READ破坏Thumb IT/SP，只用有界hooks+完整CDM/job比较。原FW/HAL/汇编/CDM/完整日志/图像/个体校准仅private。公共mirror /home/cy122/edk2-samurai/repo的Platform/Realme/sm8150，本地提交，不push/PR，保留其它改动。
