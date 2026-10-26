from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['firmware-session','session','owner','dispatch','worker','intree-build','boot-runtime','session-runtime','final-state']:
 assert read(HERE/(name+'-validation.json'))['passed']
runtime=read(HERE/'boot-runtime-validation.json');assert runtime['same_boot'] and runtime['ipe_session_lifecycle_passed']
source=read(HERE/'source-state.json')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p)
 d.update(stage=376,latest_work_stage=376,current_boot_guard_stage=374,current_boot_guard_path='/var/lib/samurai/k374-recovered/boot-id-private.txt',
  current_camera_evidence=prefix+'reference/kernel376/README.md',current_device_revalidated_stage=376,current_device_runtime_state_verified=True,
  device_closeout_evidence=prefix+'reference/kernel376/final-state-validation.json',in_progress_stage=376,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel376/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_attempt_evidence=prefix+'reference/kernel376/boot-runtime-r1-validation.json',icp_latest_attempt_recovery_evidence=None,
  icp_latest_attempt_normal_terminal=True,icp_latest_attempt_followed_by_system_reboot=False,icp_latest_attempt_followed_by_modem_watchdog=False,
  icp_latest_hfi_response_latency_ms=read(HERE/'session-runtime-validation.json')['ready_response_latency_ms'],
  icp_sys_init_evidence=prefix+'reference/kernel376/boot-runtime-r1-validation.json',icp_full_hfi_lifecycle_verified=True,
  icp_full_hfi_lifecycle_evidence=prefix+'reference/kernel376/session-runtime-validation.json',icp_hardware_cleanup_verified=True,
  icp_latest_device_experiment_stage=376,icp_image_sessions_hardware_tested=2,ipe_sessions_created_destroyed_hardware_verified=True,
  ipe_sessions_hardware_evidence=prefix+'reference/kernel376/session-runtime-validation.json',ipe_max_simultaneous_sessions_tested=2,
  ipe_image_frames_submitted=0,ipe_image_processing_hardware_verified=False,icp_hardware_backend_installed=False,
  icp_next_step='Implement IPE CONFIG_IO and IQ/command buffers from retained OEM ABI and firmware; verify A5 and engine SMMU SID/buffer ownership, frame completion and libcamera m2m. Session lifecycle alone is not image processing.',
  current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：376（两IPE会话并存/创建/销毁实机通过；图像IO/IQ/帧处理未接，目标active）

2026-10-20。先读WORKING-BOUNDARIES.md和reference/kernel376/README.md。前轮375完整HFI启停、本轮376两个IPE上下文真实通过，均为实质进展；完整多摄/ISP校准目标仍active。禁止把会话成功当作已经处理图像。

## 当前设备与维护源

当前仍374恢复后的同一启动，guard `/var/lib/samurai/k374-recovered/boot-id-private.txt`；使用reference/kernel376/host.py，strict原密钥USB/known_hosts不变。375与376没有重启，没有375/376-recovered启动。376-boot-r1 worker8198与collector均已结束，state finished/terminal/passed；旧失败事务保留。

实际Image363／7.3.0-rc6-rmx1931-samurai-k363+，boot366嵌入DT365、libcamera五包r29、config/stack r24及362四份私有Preview保持。原厂曝光/手动频闪、IFE Gamma、已有unit WB/CCT与动态LSC/CCM保持。候选未永久安装，静态ICP disabled。

376终态CPU/IRQ/PM/backing/mapped/时钟组/电源域/会话均0，17个ICP/BPS/IPE时钟enable0、临时core/test/固件/overlay无残留、CAMSS/双CCI休眠、9相机电源disabled/users0、taint0、故障0。桌面、PW/WP、SSC、SensorProxy和adsp/slpi/modem均正常。本轮复用375同启动四摄各12帧与主摄隔离27帧/5阶段/Gamma ACK，不重复未改动相机组件扫描/采集。证据376/boot-runtime-validation.json、session-runtime-validation.json、final-state-validation.json。

维护源 `/mnt/samurai-full282/source354`，分支samurai-a5-ipe-session376，最终b6c779010ec222c6f70a4912e3d3205fd6414b5c；初始2630955b62106204ed708bbb8e96a4237406beeb，父375 94a92da1da7d6e5418e284b4a0c858100fa74fd9。实际Image源码ba61a62293e0f6bc5838c06f2e85e033e3d702a8、静态DT e217016006e609333a715c10f2f3e442dc4da95f未变。实际候选r2 core SHAa4f426c8af9f484a2c831f63d3957485323c749935a95f0324411dbf365a985e，test SHA847b38b1de2bdce468ce668cffc24780643e3b5893ff0a4584b42acd190f4e22，均in-treeY/W1/Werror无诊断。

访问ext4先调用reference/kernel284/storage.py::mounted_build()，返回/mnt/samurai-full282/build、source354在旁；WSL退出会卸载，不重建/格式化镜像。libcamera源 /mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2；SDK /home/cy122/x2pro-linux/libcamera214-root，work bind串行。

## 必须保留的底层修正

372已取原厂故障现场并纠正异常context解码，详见372/README；真正context由arch_coredump_ptr取得，ABT SP+0x58，旧SP+32槽被C handler覆盖，不能当故障PC。373 reset→wake→10个HFI参数编程+读回→INIT_REQUEST修正真实启动错误；未测得旧CSR复位前后数值，不宣称reset清零机制已证实。

374已证明资源probe、普通BUS_BOUND及overlayapply返回后显式启动，三个ACK俱全仍在块复位后重启，排除“仅probe内运行”解释。375对照原厂正常停机，PC/WFI/CONTROL关闭读回成功后不额外assert全局ICP/AHB reset，DMA退映射后释放PM；runtime_suspend同样不额外assert。失败/未初始化/未清enable仍强制reset，失败保留CPU/RAM/PM，IRQ已关重试跳过PC。375完整启停真实通过；旧重启内部总线/看门狗机制仍未直接测定。不要回退这些修正或重新重演旧失败启动。

## 376实现与实际证据

优先复用352固定CAMSS原型ebd1e440...与Realme GPL9668fcdc.../355管理器；再次检索未取得可直接替代本机A5的实现，不代表所有仓库都没有。原型async比A5多一字段，且原固定树缺会话函数定义，不能直接套用。

原厂完整create handler指令与destroy caller片段/分配器callback/释放指令已在Unicorn执行，OS/流/分配/cache/log/postMessage为桩。create命令28/ACK32；destroy命令44/**实际ACK48**，其payload16字节而原头文件packed声明12。两个64位头token回显；destroy payload不保证回显token，ACK无handle字段。证据376/firmware-session-validation.json，所有原始汇编/回包私存。

SoC核心新增camss_a5_ipe_create(a5,session,type2/3)、destroy及会话list，多个独立对象/命令mutex串行。对象首次需清零，并活到成功destroy或stop，不得跨owner并发复用。唯一递增双64token关联实际handle与命令，拒绝错误类型/长度/token/opcode/返回状态；duplicate handle、序号溢出也处理。排队后超时或不可信应答导致session_uncertain阻止新命令；明确FW拒绝的销毁保留handle可重试；stop先销毁已知会话，失败/未知状态走强制复位，复位失败保留会话/CPU/DMA/PM。无图像IO或frame命令，后续必须单独管理图像DMA活跃状态。

扩展generic send_packet供SYS与会话复用，清expected后synchronize_irq，pending状态复用前加入IRQ解析。成功ACK不再覆盖同批hardIRQ watchdog/protocol错误，join期间错误在返回前重读；旧函数体25/26反例失败，新代码27路径ASAN/UBSAN通过。owner23路径、worker分发与清理模型也通过；提供者均是桩，不与硬件证据混同。

唯一376实际实验：INIT/PING→createRT(type2/active1)→create非RT(type3/active2)→destroy非RT(active1)→destroyRT(active0)→PC/WFI→正常停机/全释放/卸载。两个handle不同（core重复检测），7msgs/8IRQs/1debug、watchdog/protocol0；队列CMD读写44word、MSG61word，按INIT56/PING16/create32×2/destroy48×2/PC12精确对应，提供实际ABI长度佐证。session_creates2/destroys2/peak2/remaining0；image_frames0。还没有IPE处理图像、引擎DMA、输出画质或多摄同步证据。

## 下一步

进入IPE CONFIG_IO、IQ/命令buffer布局和内存归属、SMMU SID与帧完成，再接libcamera m2m和已提取的Gamma/LTM/CCM。原厂头文件私存352/oem/hfi_session_defs.h中image_info约423、ipe_frame_process_data479、hfi_cmd_ipe_config507；355/oem/cam_icp_hw_mgr.c create4555、destroy2731、ACK1758/1875/2084，配置IO和patchbuffer查相关函数。优先复用已有源，必要时只按固定路径取文件，禁止partial clone全目录git grep触发海量lazyfetch。

当前temp overlay只使用A5 SID0x2222（SM8150v2），A5、BPS、IPE引擎的DMA权限/共享域与SID不能直接等同，必须核对原厂DT和当前主线绑定，避免抢现有CAMSS的stream。HFI IO区域从0x10c00000起，已加载的firmware/shared/heap有固定别名；新增图像/IO配置buffer应走现有内核DMA/IOMMU API并落实寿命/缓存/错误回滚，不能用户空间MMIO或盲写地址。两个会话的创建成功未验证这些数据面。

第五2MP身份仍未知（OV02A1B库名非硬件识别，前摄共享PHY2/MCLK2/reset12，GPIO29选择待解）；更多模式、动态FrameDurationLimits、自动防频闪、光学/几何/同步/连续AF仍待，见363/REMAINING-CAMERA-SCOPE.md。延期纯色遮光可后做。整体goal继续active。

## 私存与回退

公共Git /home/cy122/edk2-samurai/repo，范围Platform/Realme/sm8150；根目录不是Git。私存E:/edk2-samurai-out/kernel376含模型/模块/成功实验完整日志和原厂ABI回包。原厂ELF kernel352/CAMERA_ICP.elf-private，3,630,392 bytes SHA a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。objdump -m armv7；Unicorn /home/cy122/x2pro-linux/private-k329-venv/bin/python。原固件、完整日志/异常现场、个体校准与密钥仅私存。

boot366 SHA c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924，logdump365 aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da，374恢复读回保持；375/376无刷写。boot276+logdump363、旧k298模块/logdump、362 r27/r22+338module+344private组合保留。原厂9ab00000/5MiB保留区证据356可复用。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标，读NEXT-SESSION.md、WORKING-BOUNDARIES.md与reference/kernel376/README.md。376已实机两个不同IPE RT/非RT handle并存后分别销毁，7msgs/8IRQ、完整INIT/PING/PC/WFI/全释放与卸载通过，same boot故障/taint0；尚无图像IO或帧。guard仍374-recovered，用host376；Image363/boot366/DT365/r29/r24保持，候选未永久安装。源source354/b6c779010分支samurai-a5-ipe-session376，父37594a92da。保留373启动顺序/读回及375协作停机，376原厂指令证实create28/ACK32、destroy44/实际ACK48、双64token；IRQ错误不能被成功ACK或join竞态覆盖。下一步直接做IPE CONFIG_IO、IQ/命令buffer、引擎SMMU SID/缓冲区寿命和frame完成，再接libcamera m2m/Gamma/LTM/CCM；A5 SID2222不能直接当IPE DMA已验。375同启动四摄/隔离Gamma可复用，勿重复无关扫描。第五摄/模式/光学/几何/同步/AF仍未完成。raw固件/回包/异常/校准/完整日志仅私存。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text().replace('## 最新交接\n','## 最新交接\n\n- [376两IPE会话创建/并存/销毁](../reference/kernel376/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[375原厂A5/HFI完整启停](reference/kernel375/README.md)','[376两IPE会话实机生命周期](reference/kernel376/README.md)');p.write_text(s)
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;s=p.read_text();first,rest=s.split('\n',1);assert first.startswith('375当前：')
 p.write_text('376当前：两个IPE RT/非RT独立会话实机并存后分别销毁，完整HFI/停机/卸载通过，同启动故障/taint0；尚未配置IO或处理图像。Image363/boot366/DT365/r29/r24保持，候选未永久安装；四摄证据复用375同启动结果。完整目标active。[376证据]('+prefix+'reference/kernel376/README.md)。以下为历史。\n'+rest)
print(json.dumps(dict(stage=376,current_boot_guard_stage=374,ipe_session_lifecycle_verified=True,ipe_images_verified=False,goal_status='active')))
