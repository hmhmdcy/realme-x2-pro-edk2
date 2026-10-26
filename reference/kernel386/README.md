# 386：V4L2 m2m入口及实际18帧队列验证

新增SoC队列适配模块，在已验证A5/IPE核心上提供V4L2多平面API、单连续内存平面的NV12/NV21、MMAP和DMABUF导入导出，以及标准媒体拓扑。实际客户端完成18帧和两个并发上下文。完整多摄／ISP目标仍active，libcamera管线、零拷贝与完整IQ尚未完成。

## 实现层次与来源

新增[camss-icp-a5-m2m.c](camss-icp-a5-m2m.c)和[头文件](camss-icp-a5-m2m.h)，Kconfig/Makefile接入；临时平台诊断所有者增加可选enable_m2m注册、只读状态与清理入口。平台资源、七组SID及固件加载由原A5核心和已验证临时覆盖提供，持久DT、Image、传感器和已安装libcamera未改。下一步应收敛正式平台所有者与板级启用，临时所有者不是最终部署形态。

先复核[维护者固定原型](https://kernel.googlesource.com/pub/scm/linux/kernel/git/bod/linux/+/ebd1e440443121d18f730ab2aeea5586a754f36f/drivers/media/platform/qcom/camss/camss-ipe.c)及352的[复用评估](../kernel352/icp-reuse-assessment.json)。其会话接口缺定义、构建文件不全、命令缓冲尚为占位，不能直接部署到本机。队列/媒体框架按当前内核vim2m、v4l2-mem2mem和vb2实现核对，未移植X1E80100的MDT/PAS或重复实现通用m2m调度器。

使用原厂提取A5固件和384原生条带/IQ，不加载外部条带或用CPU近似替代硬件处理。当前图像仍经过核心自有DMA缓冲的CPU复制；DMABUF可用不等于零拷贝，不能这样宣传。

维护源分支samurai-a5-ipe-m2m386，提交ab58f554a7b9f886bd43b9c3f47d52761d9bf982，父3856fb4806e219998f5d06919a9b0266ff7b08867b0，源码干净且与验证提案一致。[补丁](m2m-adapter.patch)、[状态](source-state.json)。

## 生命周期

注册只暴露节点，排队后才启动原FW。平台bound回调防止绑定完成前运行。工作队列调用睡眠式SoC核心；V4L2的取消等待通过job_finish完成，STREAMOFF和close会join工作再释放队列/会话。视频IOCTL锁不被硬件工作反向获取，避免退出等待锁住工作。

DMABUF CPU访问显式begin/end及vmap/vunmap，拒绝I/O映射；检查plane容量、payload和data_offset溢出。统一全帧1:1几何，S_FMT在任一队列有缓冲时返回EBUSY。当前使用显示端口8、max_cores2、RT会话，未暴露任意IQ或外部命令。

文件和保留的硬件所有权分别pin平台所有者。失败停机时仍被核心引用的已关闭会话保留为orphan，成功quiesce清除核心引用后才释放。错误状态不会把未确认释放的DMA/PM当作可卸载；显式cleanup可在没有用户时重试。

## 构建与模型

[m2m-validation.json](m2m-validation.json)：实际C函数体、ASAN/UBSAN、162组格式边界，offset/payload溢出、DMABUF begin/vmap/IOMEM/null/end失败配对、停机失败保留所有者/闭合会话及成功重试回收通过。框架/IRQ/硬件是模型provider，不是完整内核并发证明。

[worker-validation.json](worker-validation.json)：实际回收语句，活动客户端、其它用户、失败cleanup、未确认快照和未知核心所有权均保留；只按依赖顺序移除本事务模块。[ready-validation.json](ready-validation.json)验证实时刷新仍保持原有空闲门槛。

[intree-build-validation.json](intree-build-validation.json)：实际k363配置in-tree/W1/-Werror，最终r2无诊断。首轮C编译通过但modpost缺少未包含的vb2模块导出；随后把四个标准vb2依赖纳入局部构建，未改框架源码或强行忽略符号。原vb2部署不替换，构建后恢复相关输出/config/symvers。

运行模块：核心317008B SHA256 b429dc7b37fb22d9a5628a90eb3e27b780e4df3da568750f815ac7ae09a3b56d（与385相同）；标准m2m helper201296B SHA256 a00c9410b34755c68bdf9c925ce92a9f509e91590fc76ecb443448d35ab411d9；适配器115032B SHA256 bdd8669addb3a747aaaf76dc9fd833873e2baf83edc1755b243168886de2854b；诊断114568B SHA256 6e447d0a3cce74a59363387c20645580b1c8b98357946fdf17a865c6590450c3。客户端为静态AArch64程序，[构建结果](client-build-validation.json)。

## 实机结果与失败审计

[m2m-runtime-r4-validation.json](m2m-runtime-r4-validation.json)：唯一/var/lib/samurai/k386-m2m-r4，worker18051，实际video12/media1临时节点；客户端/worker/collector都终态退出。节点编号动态分配，后续不能硬编码。媒体设备从/sys/bus/media/devices发现。

|用例|格式/stride|缓冲方式|帧数|退出|
|---|---|---|---:|---|
|0|NV12/640|MMAP|6|显式STREAMOFF|
|1|NV21/672|导出/导入DMABUF，源offset16|4|直接关闭仍streaming的文件|
|2、3|NV12及NV21/640|两个同时streaming的MMAP上下文|4+4|显式STREAMOFF|

三个FW运行期合计jobs18/completed18/failed0，最后运行期双会话峰值2、8帧MAP/FRAME/UNMAP、双destroy及PC/WFI正常停止。最后CMD420/MSG449words、36消息/36中断/1debug、watchdog/protocol0。m2m路径未发PING，ping_done=false是未调用，不冒称本轮PING验证；test诊断的scratch数组与image_bytes也不用于m2m数据证明。

[pixels-validation.json](pixels-validation.json)：18帧的输入CRC独立主机重建、活跃Y像素均由实际客户端逐帧比较相等，每组末帧完整像素/CRC/UV误差由主机复核；源缓冲未被修改，导出目标尾部保护不变，timestamp/sequence与S_FMT-EBUSY检查通过。首MMAP帧CRC吻合384基线。UV MAE0.203125，仍有滤波差异，非全平面identity。

[attempts-validation.json](attempts-validation.json)保留r1～r3失败，三次均未启动FW/提交图像且已回收。r1观察器误用不存在的media class；实际是media bus。r2/r3使用了探测时保存的静态ready结果，r3中group/domain3；r4同样旧快照3，经过只读状态刷新得到0、runtime suspended后才通过原门槛。没有放宽资源释放条件，内核模块未因此重建或修改。未测出该瞬时资源状态的完整内核触发链。

[current-state-validation.json](current-state-validation.json)：同一378恢复启动guard，taint0、CAMSS/双CCI休眠、9电源disabled/users0；所有临时模块、video/media节点和FW移除，四次worker/collector/client均不活跃，17相关时钟回到0。无新相关fault。没有永久安装、刷写或重启，四摄普通采集仍381证据，Image363/DT365/boot366/r29/r24及362私有Preview保持，SSC旧问题未修。

## 尚待

接入libcamera实际管线并验证真实相机帧、metadata与延迟/取消；补在途DMA取消等异常并发验证，推进SG/DMABUF直接DMA以去掉复制，再接原厂Gamma/LTM/CCM完整IQ和全部[剩余校准范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。临时m2m入口通过不是完整目标完成。

现场继续按低照度解释，不以黑/噪点单独判故障。原FW/HAL/汇编/CDM/完整日志/图像/个体校准仅私存/mnt/e/edk2-samurai-out/kernel386；公共目录只含自有源码、工具和脱敏结果，本地提交不push/PR。
