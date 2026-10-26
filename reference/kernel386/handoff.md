# 当前检查点：386（V4L2 m2m实际18帧通过，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel386/README.md。385完整交接归档archive/NEXT-SESSION-through385-2026-10-21.md，384及更早归档保留。现场低照度继续按用户关灯条件解释，黑/噪点本身不是链路故障；不为光照校准打断其它适配。

## 新源与层次

维护源/mnt/samurai-full282/source354，branch samurai-a5-ipe-m2m386，HEADab58f554a7b9f886bd43b9c3f47d52761d9bf982，父3856fb4806e219998f5d06919a9b0266ff7b08867b0；干净且等于验证提案。新增camss-icp-a5-m2m.c/h、Makefile/Kconfig接入、boot-test可选enable_m2m注册和status/cleanup。A5核心/条带/IQ/DMA回收未改，核心二进制仍317008B/b429dc7b37fb22d9a5628a90eb3e27b780e4df3da568750f815ac7ae09a3b56d。

新适配器提供标准VIDEO_M2M_MPLANE、NV12/NV21单连续内存平面、MMAP/DMABUF、媒体ISP拓扑。video IOCTL/queue共用video_lock，硬件work只hw_lock→core锁，避免STREAMOFF等待工作反向抢video_lock。bound回调防绑定未完成启动；排队才加载原FW/启动A5。核心仍CPU复制到自有DMA，不是零拷贝，不接受外部IQ/striping。端口固定8/max_cores2/RT会话，几何仍全帧1:1/IQ关闭，偶宽高128..8192/实际image≤64MiB，有效偶stride，统一输入输出格式；不冒称缩放/完整IQ。

DMABUF显式begin/end CPUaccess和vmap/vunmap，拒绝IOMEM/null，校验plane/payload/offset溢出。文件和持有硬件分别pin平台所有者，停机失败时closed ctx的session仍被核心引用就保留orphan，quiesce成功清除引用后才free。原有381核心DMA retain及reset回收机制保持。临时平台所有者/覆盖是验证环境，正式板级启用和平台owner仍待，持久DT/Image未改。

## 构建与运行

386/build-intree.py构建core、标准v4l2-mem2mem helper、adapter、test，以及仅供modpost符号的四个vb2依赖（不上传替换现有vb2）。首次C编译通过但modpost缺vb2模块导出；加入四依赖目标后r2 in-tree k363 W1/-Werror无诊断。备份/恢复camss、v4l2-core、videobuf2输出和config/symvers；没有改主线框架源码。

helper201296B SHAa00c9410b34755c68bdf9c925ce92a9f509e91590fc76ecb443448d35ab411d9；adapter115032B SHAbdd8669addb3a747aaaf76dc9fd833873e2baf83edc1755b243168886de2854b；test114568B SHA6e447d0a3cce74a59363387c20645580b1c8b98357946fdf17a865c6590450c3；静态AArch64客户端824408B SHA55b1505ecc211f9678b9a9da317e6fe9d3bddf0f5cdaaa011d76ad915c57d4f7。未永久安装。

同一378恢复启动guard /var/lib/samurai/k378-recovered/boot-id-private.txt，host386委托385→...→378，严格原USBkey/known_hosts。唯一成功/var/lib/samurai/k386-m2m-r4 worker18051；实际临时video12/media1，不硬编码节点号；client/worker/collector均终态退出。r1 worker17446、r2 17665、r3 17854也终态并清理，三次未启动FW/提交图像。

成功客户端四用例：MMAP NV12 stride640六帧；导出/导入DMABUF NV21 stride672四帧、源offset16、直接close仍streaming文件；双线程同时streaming的MMAP NV12/NV21各四帧。共jobs18/completed18/failed0、FWstarts3；18帧输入CRC主机独立重建，实际C客户端逐帧Y活跃像素全等、timestamp/sequence正确、S_FMT-EBUSY、源缓冲不变、目标尾部保护通过，各组末帧全图/CRC/UV误差主机复核。UV MAE均0.203125仍滤波差，不是全平面identity/完整IQ；首MMAP帧CRC与384基线一致，不声称首帧全图另作逐字节对照。

最后一次FW运行双会话create/destroy/peak2、IOconfigs2、frames8、MAP/UNMAP8、CMD420/MSG449words、messages36/IRQs36/debug1、wd/protocol0，PC/WFI正常停止。m2m未发PING，ping_done=false是未调用；test的scratch数组[0,0]/image_bytes0是旧synthetic诊断字段，不拿来判m2m数据。客户端实际像素证据见pixels-validation.json，最后核心计数不是整个18帧的累计数。

r1失败：观察器错误使用/sys/class/media；正确/sys/bus/media/devices/mediaN，且不存在device symlink，用p.resolve().parents匹配平台。r2/r3失败：探测保存静态ready快照group/domain3，未发FW；r4同样旧3，读m2m_status刷新core结果后group/domain0、runtime suspended才通过原idle门槛。没有放宽资源检查，也没有为此重建模块。具体资源瞬时触发链未测，勿把推断写成根因。失败日志/private observation均保留，attempts-validation.json正式审计。

check-m2m.py：实际C体ASAN/UBSAN/162格式边界、CPU映射失败配对、offset溢出、停机失败留pin/orphan和成功retry回收。check-worker.py覆盖真实finally语句，活跃client/其它user/cleanup失败/未确认snapshot/未知coreowned不盲卸载；check-ready.py覆盖真实只读刷新循环，永不idle/CPU或job意外活动被拒绝。模型不是完整并发/硬件故障证明；在途DMA取消等异常还待实测。

## 当前设备与接续

close-current：源干净，taint0、CAMSS/双CCI休眠、9rails disabled/users0，静态ICPdisabled，临时core/adapter/test/helper和video/media/FW全部消失；r1..r4三类进程都不活跃，17相关clk归零，无新相关fault。本轮无真摄像头采集/刷写/重启/永久安装。四摄仍381每摄12帧640、主摄IPA27帧5阶段/GammaACK1；Image363/7.3.0-rc6-rmx1931-samurai-k363+、boot366 DT365、五libcamera r29/config-stackr24、362四私有Preview保持。SSC旧EPERM/daemon4/SLPIoffline/SensorProxystopped未修、379desktop恢复保持，不宣称全平台健康。

下一步接libcamera实际管线，先核对已有CAMSS NV12缓冲布局、import/export、metadata/请求完成时序和取消，复用库的V4L2M2MDevice。inspect-integration确认实际库有该类，camss-video.c对NV12/NV21用addr0+stride*height派生UV地址；不要凭旧prototype的NV12 num_planes2直接假定本机布局。库源/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2，SDK/home/cy122/x2pro-linux/libcamera214-root，work bind串行。当前M2M只由真实V4L2客户端验证，不能写libcamera已接入或整相机pipeline已完成。

之后推进SG/DMABUF直接DMA去复制、正式平台owner/板级启用和原厂Gamma/LTM/CCM完整IQ。第五2MP身份（OV02A1B库名非ID、front共PHY2/MCLK2/reset12、GPIO29mux未解）、多模式、动态帧长/自动频闪、光学/几何/同步/连续AF仍按363/REMAINING-CAMERA-SCOPE.md。目标active，无预算，未pause。

## 历史与操作

访问ext4前reference/kernel284/storage.py::mounted_build()返回/mnt/samurai-full282/build和旁置source354，不格式化/重建镜像。所有exec session已同handle终态，无正在跑的build或client。公共mirror/home/cy122/edk2-samurai/repo仅Platform/Realme/sm8150，本地commit不push/PR、保留无关staged。rawFW/HAL/asm/CDM/图像/完整日志/校准/auth仅/mnt/e/edk2-samurai-out/kernelNNN。

381 SID2222/0、2080/20、20a0/20、2100/20、2120/20、20c0/0、2140/0，images20000000+08000000仅IOVA、每image64MiB；parcel07800000≤1MiB/shared内，config07600000/4KiB。未知完成保留BO/PM，A5停机IRQjoin后两IPE CDMresetf/TOP3新ACK且清除再free，失败明确retry。373先reset/wake后HFI参数；375正常PC/WFI/CPUoff不额外全局BCR；376双token/IRQjoin/错误锁存；379MAP/UNMAPACK44尾12无效、CONFIGACK56scratch36/DESTROYACK48/FRAMEACK72。377/378失败/自动重启审计不重演、不改成功；372ABTSP+58、EUD377retired保留。

383 Unicorn2.1.4全局MEM_READ破坏ThumbIT/SP，限定观察必须整CDM/job对无观察一致；384默认无读hook。HAL CPUwrite mask不含provider uc.mem_write，不当全初始化mask。模型chip10705非新设备读。HAL281/camera.qcom.so-private，350debug仅符号；FW352/CAMERA_ICP.elf-private，asm370-marmv7；Unicorn/home/cy122/x2pro-linux/private-k329-venv/bin/python。fixedGPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6、CamxChi9f17f1b568626b393e785b369c5dc94543774d7a、原型ebd1e440443121d18f730ab2aeea5586a754f36f缺文件；partialclone不全树gitgrep/lazyfetch。383stats/paramsRFC仍draft无目标条带算法。boot366 SHAc3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924、logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da及旧rollback保持。
