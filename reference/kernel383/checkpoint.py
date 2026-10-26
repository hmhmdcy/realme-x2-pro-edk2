from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['observer','preparation','partitions','intree-build','current-state']:assert read(HERE/(name+'-validation.json'))['passed']
source=read(HERE/'source-state.json')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==382
 d.update(stage=383,latest_work_stage=383,current_camera_evidence=prefix+'reference/kernel383/README.md',current_device_revalidated_stage=383,
  device_closeout_evidence=prefix+'reference/kernel383/current-state-validation.json',in_progress_stage=383,
  in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel383/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  ipe_native_bypass_partitions_available=True,ipe_native_bypass_partitions_evidence=prefix+'reference/kernel383/partitions-validation.json',
  ipe_native_complete_striping_available=False,ipe_original_frame_preparation_differential_evidence=prefix+'reference/kernel383/preparation-validation.json',
  icp_next_step='Serialize native bypass pass/stripe geometry using the new partition component; compare complete OEM-generated CDM/job data, then real pixels. The runtime still needs the private striping fixture. Continue sizes/ports/cores/frames, V4L2 m2m/libcamera and full IQ/calibration.',
  latest_stage_device_mutated=False,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through382-2026-10-20.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：383（内核原生分区组件与原厂CDM差分；完整striping未完成，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel383/README.md。本轮增加SoC分区算法并构建，建立完整原固件准备差分验证器，属于progress；未改设备。382完整交接保存在archive/NEXT-SESSION-through382-2026-10-20.md，381/380旧交接也保留，具体DMA/复位修正不能丢。

## 当前源、设备和实机范围

维护源 /mnt/samurai-full282/source354，分支samurai-a5-ipe-partitions383，HEADa9f823f210344ab551e4859b4889358916345fbb，父38247475238dc6a0d4b28a5db22b0c1af223dc50297，干净。383核心304424字节SHA c80e564872f5c9cbfe376c6da77a48a9494dd067f14d36dbe71d17c02eceedb2；测试100104字节SHA2281097c4c94e17a643a0bc15880ae903a3e08c6da42dc563d5d017688fe5a98，与382相同。真实k363配置in-tree/W1/-Werror无诊断，未安装。

仍是378恢复启动，guard `/var/lib/samurai/k378-recovered/boot-id-private.txt`；用reference/kernel383/host.py委托382→381→380→379→378动态guard，严格原密钥USB/known_hosts不变。383只读确认taint0、CAMSS/双CCI休眠、ICP模块与临时固件无残留、静态ICPdisabled。未启动新候选、刷写、重启或相机重采。

最近实机仍是382 /var/lib/samurai/k382-boot-r1 worker11416，collector均finished/terminal/passed退出。INIT/PING，两RT/非RT handle并存各CONFIG_IO（scratch48/48），RT一帧640×480、FRAME40/ACK72、图像MAP/UNMAP、双destroy、PC/WFI/cooperative stop、全部DMA/PM/模块回收；CMD158/MSG173words、16msgs/17IRQ/1debug、wd/protocol0。Y307200字节全等输入，UV MAE0.203125，仅U阶跃4亮度横向像素内/V阶跃2色度行内有差，实际滤波/舍入未推导。完整IQ/光学校准未验，不能叫全平面identity。实际输入输出只私存382。

最近四摄仍381同启动imx471/imx319/s5k3m5/s5kgw1各12帧640×480、主摄隔离IPA27帧/5阶段/GammaACK1；未重复未改组件。382收尾9rails disabled/users0、17ICP/BPS/IPEclk enable0等保持为最近完整资源证据；383只读复核相关PM/残留。SSC旧attach失败/daemon exit4、SLPIoffline/SensorProxystopped未修复，桌面379恢复后保持，不宣称全平台健康。

实际Image363/7.3.0-rc6-rmx1931-samurai-k363+、boot366嵌入DT365、libcamera五包r29、config/stack r24与362四份私有Preview保持。原厂曝光/手动频闪、IFE Gamma、unitWB/CCT与动态LSC/CCM保留。实际Image源码ba61a62293e0f6bc5838c06f2e85e033e3d702a8、DT源码e217016006e609333a715c10f2f3e442dc4da95f不变。

## 383新增可复用代码

camss_a5_ipe_bypass_partitions(width,cores,output,capacity,count)写u16 inclusive fetch/output范围，从右到左；仅模块关闭、全帧1:1、8位NV12/NV21。width偶数128..8192，core1/2，分区数量ceil(width/328)再向core倍数取整，边界floor(width*i/count)向下对齐2，fetch边界向外4像素并限幅。非法参数/容量不足先拒绝，输出/count不改。不是固定320宽：328单核1条、330两条、656两条、658三条，双核再取偶数。

76组与完整原HAL算法一致，含临界邻域、不同高度、端口8/9、NV12/NV21；ASAN/UBSAN，无空洞/重叠/fetch越界，真实内核构建通过。函数只是范围组件，尚未接入run，不生成全striping blob、不消除私存文件依赖。下一步必须完成序列化再实机，不把该组件当完整后端。

原厂stripe布局显示输出范围在每stripe+20，视频输出在+24；fetch在+4/+6。最初额外port9比较错用+20，修正oracle读偏移后通过，未改原生算法来迎合错误fixture。完整metadata字段和closed模块语义仍须继续推导。

## 新原厂验证器与观察器陷阱

reference/kernel383/engine_model.py::prepare执行原FW DoFirstRead0x7998、完整CONFIG_IO0x16534、FRAME_PROCESS准备0x17f30，停在HardwareDriver_EnqueueJob入口0x220a2。模型版本寄存器0xe0040000=0x10705，原函数得到chip3/info100664；不是从手机新读出的版本值。OS分配器、日志、流句柄/私有上下文与命令回收建模；几何/拓扑/FE/WE/ICA/CDM原函数并未替换为桩。没有执行硬件enqueue、engine或pixelDMA。

原HAL完整striping×原FW准备验证12组640×480/1920×1080/4608×3456 ×port8/9 ×core1/2。限定striping范围的MEM_READ观察和完全无观察生成的整512KiB CDM缓冲+32B job逐字节相等。读取stripe字节数534、1330、3121/3320。HAL分配器和输出区分别填0xa5/0x5a，取两结果不变bits、将其余bits清零的canonical stripe，以上12组CDM/job仍逐字节相等；两dirtyseed本身CDM也同。不能将该证据扩到开启高级IQ后的语义。

私存383/{width}x{height}-p{port}-c{core}-canonical-stripe-private.bin、-defined-bits-private.bin、-original-cdm-private.bin、-canonical-cdm-private.bin、-reads-private.json；prep报告脱敏。后续native serializer可调用该验证器比较整CDM/job，不必强行复制未初始化输出padding。注意原HALCPU写轨迹mask不包含libc provider中uc.mem_write，不是完整初始化mask；用互补seed与实际消费差分验证。

全局UC_HOOK_MEM_READ在当前Unicorn2.1.4中会破坏Thumb IT返回：原始FreeCdmProgramArray0xf21e空数组，无钩子或钩子限定无关区间正常SP0；全局空callback却跳过f274正常返回序列，SP差-32。该问题导致初版full模型栈错乱，不是设备故障；已用check-observer.py最小复现。改限定读范围并对12组整个生成CDM/job与无观察运行一致后才采用轨迹。既有reference内未发现383之前使用该读取钩子的脚本。禁止为了观察而直接加全局READ钩子后信任输出。

probe-engine.py --full也只停到0x220a2，不是完整引擎执行；--no-reads可对照。probe-free.py是诊断工具，check-observer.py为正式回归。前期失败日志保留私存engine-full-failure/engine-unobserved-private.log等。没有新增手机失败事务。

## 下一步与范围

先将原生partition接上pass纵向几何、各端口裁剪与FE/WE/ICA启用字段，形成完整内核striping序列化；与本轮原厂CDM/job verifier差分并实机验证像素，再扩连续帧和V4L2m2m/libcamera、原厂Gamma/LTM/CCM。当前仍加载samurai-ipe382-stripe.bin才能运行，不能称独立通用后端。不用用户空间近似替代硬件目标。

380 HAL入口144348create、1448f0execute、144988destroy，hal-machine.py可复用；params五Q+I分别IQ、ICA1、ICA2、zoom、previousZoom、cores。383/trace-striping.py::execute可设dirty与uv_swap，完整原算法非桩。原FWpayload frame3816/IQ2584/header92/frameSet232、14ports×2plane，batch最多16、单帧copy324，userArg3808，BL内部扣32。条带使用2268+624Σstripe，passCount20、每pass412、stripeCount428+412*i。striping数组按原包装顺序是右到左。

382内核已自行生成IQ默认：清零2584后u32偏移52/68/244/260=1（ICA1/2 invalidPixel interpolation/eightBit alignment），job已移除外部iq/iq_bytes；raw数据与383 helper scope保持模块关闭，不接受任意IQ/CDM。本次未改该运行路径。完整原HAL request/原FW engine未在模型执行。

第五2MP身份未明（OV02A1B库名非识别，front共享PHY2/MCLK2/reset12，GPIO29mux待解）、更多模式、动态帧时长/自动防频闪、光学/几何/同步/连续AF与完整校准仍待，363/REMAINING-CAMERA-SCOPE.md保留；延期纯色/遮光可后做。目标active。

## 资源修正、来源与私存

保留381临时组合SID2222/0、2080/20、20a0/20、2100/20、2120/20、20c0/0、2140/0（与CAMSS mask无交）、images IOVA20000000+08000000仅地址名字空间，不新增RAMcarveout；input20000000/output24000000各≤64MiB，parcel07800000≤1MiB在既有共享预留内，config07600000/4KiB。三BO由核心拥有，未知/错误完成retain pending/BO/PM，A5停机IRQjoin后两IPE CDM reset0xf/TOP3新ACK且清除都成功才能free；失败保留供明确重试。启动前ACK[3,3]已实机验证。未猜测写IRQmask/CORE_EN/CPASQoS。

保留373 reset/wake后HFI参数编程/readback，375正常PC/WFI/CONTROL确认关CPU后避免额外全局ICP/AHB复位，376双token/IRQjoin/错误锁存，379MAP/UNMAP56命令/ACK44仅header状态有效（尾12未初始化分配器内容）。CONFIG40/ACK56 scratch36、DESTROY44/ACK48有效payload状态，FRAME40/ACK72。377/378失败/自动重启事务不能重演或改称成功，内部机制未测，审计保留。372context解码纠正保留，EUD9505被动capture377已retire/com-off。

访问ext4前用reference/kernel284/storage.py::mounted_build()，/mnt/samurai-full282/build与source354旁置，不重建/格式化镜像。libcamera源/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2，SDK/home/cy122/x2pro-linux/libcamera214-root，work bind串行。exec session须等同一handle终态再依赖操作。

固定Realme GPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6，CamxChi9f17f1b568626b393e785b369c5dc94543774d7a，原型ebd1e440443121d18f730ab2aeea5586a754f36f不完整/旧async多字段；ipe_data.h外部定义未取得。383另查维护者2026 CAMSS stats/params RFC（README链接），仍draft，未提供本机条带算法，暂未改UAPI。避免partial clone全树gitgrep触发lazyfetch。

HAL281/camera.qcom.so-private SHAe2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde；350debugELF仅符号，objdump原HAL。FW352/CAMERA_ICP.elf-private SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63，armv7完整asm370，objdump -m armv7。Unicorn/home/cy122/x2pro-linux/private-k329-venv/bin/python。原固件/HAL/源码/生成blob/CDM/图像/完整日志/校准/密钥仅/mnt/e/edk2-samurai-out/kernelNNN，不入公共Git。

公共Git/home/cy122/edk2-samurai/repo，Platform/Realme/sm8150范围，本地提交不push/PR。boot366 SHAc3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924、logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da保持，378恢复读回已核；旧回退均保留。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel383/README.md。383新增内核bypass分区函数：128..8192偶宽，ceil(W/328)向core1/2倍数取整，内部对齐2，4px fetch halo，右到左；76组原HAL完整算法对照/ASAN通过，in-tree W1/-Werror无诊断。完整striping serializer仍未做、run仍依赖私存文件；下一步接pass纵向/裁剪/FE/WE/ICA并差分整个原厂CDM/job，再实机。原FW DoFirstRead+CONFIG_IO+完整frame准备已执行至220a2硬件enqueue前，12组3尺寸×port8/9×core1/2；限定观察与无观察整512KiB CDM/32Bjob全等，互补dirtyseed canonical stripe也全等。全局MEM_READ钩子会破坏本环境Thumb IT/SP，最小复现已存，只用限定观察且比较无观察结果。source a9f823f210344ab551e4859b4889358916345fbb branch samurai-a5-ipe-partitions383，未安装/设备仅只读；最近实机382幅度修复，四摄381复用；guard378-recovered用host383，Image363/boot366/DT365/r29/r24保持，SSC旧故障未修。保留DMA/复位retain和373/375/376/379修正与377/378失败审计，完整IQ/多摄校准goal active。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text();anchor='## 最新交接\n';assert anchor in s;p.write_text(s.replace(anchor,anchor+'\n- [383原生分区与原厂CDM差分](../reference/kernel383/README.md)\n',1))
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[382内核ICA默认配置与幅度修复](reference/kernel382/README.md)','[383原生分区与原厂CDM差分](reference/kernel383/README.md)'))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;s=p.read_text();first,rest=s.split('\n',1);assert first.startswith('382当前：')
 p.write_text('383当前：内核原生分区组件76组原算法差分并构建，原厂帧准备/CDM验证器12组通过；完整striping序列化和运行文件依赖仍待收敛。本轮设备只读，最近实机382幅度修复/四摄381证据保留，完整IQ与多摄目标active。[383证据]('+prefix+'reference/kernel383/README.md)。以下为历史。\n'+rest)
print(json.dumps(dict(stage=383,native_partition_component=True,complete_native_striping=False,last_hardware_experiment=382,goal_status='active')))
