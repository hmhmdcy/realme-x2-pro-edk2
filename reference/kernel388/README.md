# 388：IPE 直接 DMA 与导出缓冲区所有权，最终 99 帧通过

去掉原生 IPE 路径中输入、输出图像的核心 CPU 复制。最终源码通过原生 V4L2 18 帧及实际 libcamera 81 帧验证，并实测关闭视频 FD 后 DMA-BUF 文件和 mmap 对平台所有者的保留。原模块已恢复，恢复后的四摄各12帧通过。完整多摄／ISP适配校准目标继续 active；本轮没有永久安装、刷写或重启。

## 分层与复用

先检查现有内核仓库的 vb2-dma-sg、DMA-BUF、dma-resv、CAMSS 及已验证的[387 libcamera 接入](../kernel387/README.md)，复用标准内存分配／导入与调度；沿用反编译原厂固件所得的 HFI、条带、IQ旁路及会话证据，没有重写用户空间图像算法。

SoC层新增 [camss-icp-a5-dma.c](camss-icp-a5-dma.c)：核心持有 DMA-BUF、attachment 和 mapping，在 A5 与两路 IPE 共用的既有七SID域内直接使用 DMA IOVA。验证有效区间、偏移、对齐、32位边界及物理重叠。物理地址只经自有 IOMMU domain 查询；CONFIG_DMABUF_DEBUG 会提供去掉页字段的 DMA-only SG 表，不能读取导入表的 sg_page/sg_phys。已合并 SG 不假定物理连续。

媒体驱动层改用标准 vb2_dma_sg，核心保留 DMA-BUF引用直到 MAP/FRAME/UNMAP 确认完成。未知结果时继续保留，只有 A5/IRQ和两路IPE完成quiesce/reset才释放。直接模式仅申请请求元数据，不申请 image_input/image_output，也不复制像素；旧 CPU 指针 fixture 仍可用，拒绝混合输入模式。

通用媒体层新增小的 vb2_dma_sg_get_dmabuf_owner(vb, priv, flags, owner) API。给原始 DMA-BUF 导出文件指定实际平台模块所有者，分配器释放完成后才 module_put；旧 get_dmabuf 仍传 THIS_MODULE，不改变公共 vb2 结构体ABI。m2m只覆盖标准memory_ops的get_dmabuf。平台owner依赖adapter，adapter依赖DMA-SG，保留完整模块链。当前临时owner suppress_bind_attrs；正式设备解绑／热拔插生命周期仍需单独设计。

板级持久 DT、Image、传感器驱动、已安装 r29/r24、362私有校准配置均不改。用户空间直接复用387候选库，SHA256 60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d。静态ICP仍disabled，七SID平台所有者仍为临时实验。显式V4L2 QBUF/DQBUF约束缓冲所有权，导入前等待已有fence；没有证明完整异步implicit-fence互操作。

## 源码与构建

主源 /mnt/samurai-full282/source354，branch samurai-ipe-direct-dma388，最终 HEAD 95caf30a629bbaf454ebfc9ed25ce16ea3a952b5，父387 8003933b7e31e4b5f4d27d21789d42da686831ba。以[source-state.json](source-state.json)及[最终补丁](direct-dma.patch)为准；早期prepare-source.py仅是初稿，后续修正脚本保留演变。最终源、proposed文件和从父提交生成的补丁已经逐一核对，源码干净。源码／build访问前必须调用284的mounted_build挂载保护。

[in-tree r4构建](intree-build-r4-validation.json)使用现有k363配置、W1/-Werror，通过且无诊断。核心350472B／036f590c603097c15188316c9fd20d66e8f4cd437644e746b848b7e424706cb0，adapter118752B／371b845aad860a87924d44f2e5fff810765b6a7f407bb031f28d143384d6b5df，标准SG100104B／735bded11ddedc9e0cad393bb3e35d2aa97b9d161161562ae9856f909cd6a643。共构建9目标，恢复共享CAMSS/V4L2输出、config及symvers。最终adapter要求新增SG符号，不能直接在原SG上加载。

## 验证与适用范围

[DMA模型](dma-validation.json)对实际导入函数运行20503个ASAN/UBSAN用例，含DMA-only表、合并SG、越界、物理alias、引用回滚和domain变化时保留。[核心生命周期模型](transfer-validation.json)13例验证直接模式无图像bounce、旧fixture、未知MAP/FRAME/UNMAP保留、队列引用先丢弃、quiesce失败不能free。[导出模型](export-owner-validation.json)4例覆盖文件/VMA/observer引用及deferred fput释放顺序。provider模型不等于真实硬件错误并发证明。

[最终framework-r1实机](framework-runtime-r1-validation.json)先保存并停止PW/WP，在引用归零后卸载原CAMSS/SG，临时insmod新SG，再modprobe磁盘原CAMSS。没有覆盖原模块文件。native、pipeline两个子worker均通过并终态；测试后恢复原SG/CAMSS，核对原文件和加载note，再做已安装链路四摄回归，最后恢复服务。

|最终用例|结果|
|---|---|
|关闭视频FD，保留导出DMA-BUF FD和mmap|users0、jobs0，owner_refs1|
|再关闭DMA-BUF FD，只保留mmap|owner_refs仍1，内容可读|
|最后munmap|owner_refs归0，平台可正常卸载|
|原生MMAP NV12|6帧，stride640|
|导出／导入DMABUF NV21|4帧，stride672、source offset16|
|两个并发MMAP上下文|NV12/NV21各4帧|
|四摄libcamera→IPE|imx471/imx319/s5k3m5/s5kgw1各12帧|
|主摄RAW+NV12 / RAW-only|各6请求；原始IFE SOF/时间戳保留；RAW-only IPE0|
|隔离IPA主摄|27帧、5控制阶段、Gamma ACK1，独立统计进程|
|原框架恢复后的已安装四摄|各12帧，无GStreamer bus错误|

最终候选共99个IPE作业，direct99、copy0、cancel0、failed0。原生最后一次双会话运行8帧；管线最后一次单会话运行27帧，正常PC/WFI，watchdog/protocol错误0，导入引用回到0。[最终像素复核](framework-pixels-validation.json)独立核对18帧输入CRC、客户端每帧有效Y相同、各组末帧全图CRC与UV误差；UV MAE仍0.203125。直接DMA保留调用方padding0xa7，旧bounce填0xa5。这里的去复制结论限于原生m2m／候选libcamera到核心的图像路径，不表示全部应用与显示链路都无复制。

## 失败记录与当前状态

最初native-r1读取导入SG页字段，在DMABUF_DEBUG配置下不适用，未提交图像即失败；握手已完成但当时具体返回码未记录，不能反称已实测某个errno。改为查询自有IOMMU域后native-r2与pipeline-r2通过，核心二进制与最终版相同；这两次早期结果不作为最终导出owner修复的证明。

pipeline-r1上传中断，事务目录、manifest、worker均未创建；孤立stdin接收进程经pidfd核对身份后终止，[审计](staging-r1-validation.json)保留。改为校验并复用远端缓存，避免重复上传大库。

中间导出wrapper原型只构建，未上机；因包装内层文件的deferred fput／全局observer不能保证释放先后，已revert，最终直接指定原始导出文件owner。首次close-current核对器误将普通unified diff与git diff格式作字节比较，修正为同格式再核对；没有改变源码或重跑硬件。[汇总审计](attempts-validation.json)。

[当前状态](current-state-validation.json)：同一378恢复boot，所有本轮worker/client/collector终态；原SG/CAMSS加载note和磁盘文件恢复，临时模块／节点／FW移除，taint0、CAMSS和双CCI休眠、九路相机电源disabled/users0，PW/WP各一实例。Image363/boot366/DT365及已安装软件保持，SSC旧问题未修。

接续优先正式平台所有者／板级启用、实际在途取消／硬件异常并发，再接原厂Gamma/LTM/CCM完整IQ和[全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。第五2MP身份、多模式、动态帧时长／防频闪、几何／多摄同步、连续AF等尚待。低照度黑场／噪点不单独判链路失败，照明相关光学／颜色校准后做。FW/HAL/反汇编/CDM/完整日志/图像/个体校准仅private；公共镜像只本地提交，不push或PR。
