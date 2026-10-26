from pathlib import Path
import json,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=lambda p:json.loads(p.read_text())
final=read(HERE/'final-state-validation.json');camera=read(HERE/'camera-runtime-validation.json');failed=read(HERE/'boot-runtime-r1-validation.json');cleanup=read(HERE/'recovery-cleanup-validation.json')
assert final['passed'] and camera['passed'] and cleanup['new_boot_verified']
assert failed['raw_standard_devcoredump_recovered'] and not failed['firmware_handshake_passed'] and not failed['sfr_text_recovered']
source=read(HERE/'source-state.json');source.pop('firmware_cpu_started',None);source.update(temporary_runtime_exercised=True,firmware_cpu_release_attempted=True,hardware_boot_verified=False,
    installed=False,runtime_evidence='reference/kernel369/boot-runtime-r1-validation.json',current_device_recovered=True)
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
core_path=HERE.parent/'kernel368/source-state.json';core=read(core_path);core.update(temporary_runtime_exercised_stage=369,hardware_boot_verified=False,hardware_cleanup_verified=False,runtime_evidence='reference/kernel369/boot-runtime-r1-validation.json');core_path.write_text(json.dumps(core,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/rel;d=read(p)
 d.update(stage=369,latest_work_stage=369,current_boot_guard_stage=369,current_camera_evidence=prefix+'reference/kernel369/README.md',
  current_device_runtime_state_verified=True,device_current_taint=0,device_current_ssh_status='strict_original_key_wifi',device_force_restart_currently_needed=False,
  current_boot_guard_evidence=prefix+'reference/kernel369/recovery-cleanup-validation.json',device_closeout_evidence=prefix+'reference/kernel369/final-state-validation.json',
  device_recovered_boot_evidence=prefix+'reference/kernel369/recovered-boot-validation.json',device_recovered_baseline_capture_evidence=prefix+'reference/kernel369/camera-runtime-validation.json',
  device_recovered_camera_count=4,in_progress_stage=369,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel369/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_attempt_evidence=prefix+'reference/kernel369/boot-runtime-r1-validation.json',icp_latest_attempt_recovery_evidence=prefix+'reference/kernel369/recovery-cleanup-validation.json',
  icp_latest_attempt_normal_terminal=False,icp_latest_attempt_followed_by_modem_watchdog=None,icp_latest_attempt_followed_by_system_reboot=True,
  icp_latest_hfi_response=3,icp_latest_hfi_response_latency_ms=failed['fatal_response_latency_ms'],icp_latest_deadline_expired=False,
  icp_standard_devcoredump_runtime_recovered=True,icp_standard_devcoredump_bytes=568,icp_actual_sfr_text_recovered=False,
  icp_hardware_cleanup_verified=False,icp_firmware_boot_verified=False,icp_hardware_backend_installed=False,
  icp_memory_page_allocation_evidence=prefix+'reference/kernel369/firmware-reservation-validation.json',
  icp_next_step='Offline A5 MMU/SFR/CSR audit, then separate CPU quiesce from DMA/power teardown for a bounded firmware-state diagnostic; do not repeat369',
  current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 if 'deployed_camera_modules' in d:d['deployed_camera_modules']=final['deployed_camera_modules']
 p.write_text(json.dumps(d,indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：369（真实故障快照已取回，设备恢复，完整目标active）

2026-10-20。先读WORKING-BOUNDARIES.md及reference/kernel369/README.md。当前是369独立恢复启动，guard `/var/lib/samurai/k369-recovered/boot-id-private.txt`；用reference/kernel369/host.py，既有原密钥／known_hosts严格Wi-Fi端点私存kernel369/current-transport-private.json，不能用旧367guard发写操作。

## 当前设备与已验证功能

Image363（7.3.0-rc6-rmx1931-samurai-k363+）、778模块；boot固件366、实际静态DT来源365。libcamera五运行包99990.7.2-r29、config/stack0.1.0-r24，四份私有完整Preview默认保持362：已映射模式的原厂曝光／手动防频闪、IFE Gamma及既有个体WB/CCT、动态LSC、CCM。没有永久安装ICP模块或改变用户空间／个体配置。

恢复后四颗传感器各12帧GStreamer硬件采集，主摄隔离IPA另28帧／5阶段／Gamma ACK通过；故障增量0。SSC、SensorProxy、greetd、Phoc/Phosh、PW/WP正常，无需额外重启；最后taint0、十个相机模块loaded note与磁盘一致、CAMSS/双CCI休眠、九相机电源disabled/users0，无活动worker／ICP模块／临时固件／动态节点。实际结果见369/camera-runtime-validation.json和final-state-validation.json。不能外推为绝对光学校准或本机全部相机。

## 最新ICP事实（均非完整握手通过）

363完整Image含348 Gamma与357公共OF/IOMMU节点引用修正；364真实1280页映射／撤销及动态节点回收通过。365修正实时overlay不能给已有无phandle节点建引用的问题，将禁用SoC ICP与板级9ab00000/5MiB/no-map固件区建立静态联系。FAT中的DT文件不被当前EDK2采用，366已将同一DT装进实际固件卷，逐FFS仅DTB变化，运行引用验证通过。

366 A5响应3在500ms超时，记录block reset后modem watchdog并新启动，无正常终态。368优先反编译已提取原厂ELF：完整SendSfrMessage 348字节实际指令执行11路径，先处理SFR再写3；3是已证实的故障路径，不能发SYS_INIT。cache/log/format/power为明确桩，不模拟整RTOS。

368新core直接拒绝3并在清理前发布标准568字节LE devcoredump，SFR受声明/分配大小双边界限制；DMA映射回收移到PM供电释放前，unmap失败保留PM引用。实际start13／stop7和诊断helper/decoder模型通过，in-tree k363 W1/Werror构建通过，但没有真实成功清理证明。

369给临时诊断模块增加残留时钟/域时的module pin，8组实际条件模型通过；core与368产物逐字节同一。独立collector先就绪才加载test模块；只匹配新A5 failing_device/OF节点，计划先fsync再确认消费，夹具通过。一次新实验仍造成重启。原worker停在load-boot-test、terminal=false，没有改写旧记录。

实际取回568字节raw标准dump，SHA b3ca6c91f52aefee242e46efba0c5c02b7f6e46f08b18d9564fd998139a3f7bd；响应3、fw版本寄存器1000100、队列索引全0、interrupt/watchdog/protocol计数0、SFR正文空。ramoops记录CPU release后2.711ms读3、expired0、block reset asserted。collector仅raw文件落盘，decoded/result/确认消费未完成；离线解码完成。重启原因仍未证明，不能将366的modem watchdog直接当这次结论，也不能称DMA顺序调整修好了异常。

恢复boot/logdump读回正确；临时firmware副本与原厂和事务副本哈希一致后删除，原件和原state均保留。重启后代码页不匹配，停止未读异常页；同5MiB范围1280页的只读内核分配元数据均保留／mapcount0，无slab/buddy/匿名/页表占用。它只排除所观察启动的Linux普通页分配，不能证明安全世界所有权或A5权限。

## 下一步

不要重复369的CPU启动／清理序列，也不要把空SFR解释为没有故障。先离线核查A5 MMU、共享区/SFR和CSR读回语义，确认初值／指针／size及CPU访问属性。设计把CPU quiesce与DMA撤销/断电分开的诊断窗口，在已停CPU且仍拥有的固件RAM中保全异常状态，之后再做新针对性硬件实验。不能靠再调超时或允许3发SYS_INIT绕过错误。

大目录git grep会触发AndroidR partial clone补取，本轮已取消该自有grep/fetch并确认进程结束；优先复用kernel352/oem与356已保存的19781相关证据，只定点读取必要文件，别重启目录级补取。

## 源码、工具、回退

内核维护源/mnt/samurai-full282/source354，samurai-a5-sfr-diagnostic369／f9e1ce02537f9a28f02c471888203e59c0bff794；父368 core9c60745372258f2f37374862a06c9fd09eeaf240。实际Image固定ba61a62293e0f6bc5838c06f2e85e033e3d702a8，DT固定e217016006e609333a715c10f2f3e442dc4da95f。候选临时加载后已由重启消失，默认ICP仍disabled。libcamera源/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2，r29/r24正式配方保持。

Git公共镜像/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150。私存E:/edk2-samurai-out/kernel369含collected-r1/raw、私有ramoops、当前guard/transport和构建；原厂ELF在kernel352。host369严格密钥，全部原始固件、SFR、内存页、认证/内核日志和校准不进公共Git。进入ext4先调用reference/kernel284/storage.py::mounted_build()，SDK bind串行。无活动构建或实验worker。

boot366 c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924，logdump365 aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da。boot276＋logdump363可回退DT；k298旧模块树/logdump和362事务的r27/r22＋338模块＋344私有配置组合回退保留。NV、OTP、个体校准和工厂备份未写。

## 完整目标剩余

完整SYS_INIT/PING/PC_ACK、IPE图像会话与IO/IQ及后级Gamma/LTM/CCM尚未打通。已确认三后摄＋前摄，另有官方2MP人像摄像头；vendor OV02A1B只有库名证据，实际身份未确认。原厂19781 cam-sensor@4与前摄共享PHY2/MCLK2/reset12，GPIO29选择关系待解，不加冲突GPIO节点或等同OV02A10。见363/REMAINING-CAMERA-SCOPE.md。

动态FrameDurationLimits、自动防频闪、其它模式、绝对颜色／黑电平／阴影、几何／多摄同步及连续AF仍开放；用户延期的纯色／遮光可后做。整体goal保持active。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从369恢复检查点继续active多摄/ISP目标。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel369/README.md。新core真实devcoredump568已取回，但HFI3仅2.711ms出现、SFR空、随后重启无终态；DMA先退后断电未获成功清理证明。现机恢复369 guard（host369，严格Wi-Fi）、Image363/boot366/DT365/r29/r24，四颗相机及隔离回归、SSC桌面健康通过，无需重启。维护源source354/f9e1ce0253，核心父9c60745372。下一步离线MMU/SFR/CSR audit及将CPU quiesce与DMA/PM清理分开的诊断窗口，不重放同序列。1280页均kernel reserved；DDR代码页不匹配不读异常页。所有raw/dump/固件/校准/密钥只私存，partial repo目录grep已取消，复用保存的定点原厂源。完整HFI/IPE、2MP身份、其它模式和光学同步/AF未完。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text().replace('## 最新交接\n','## 最新交接\n\n- [369真实A5故障快照与恢复基线](../reference/kernel369/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[368SFR错误诊断与回收候选](reference/kernel368/README.md)','[369真实故障快照与恢复基线](reference/kernel369/README.md)');p.write_text(s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[core_path]+[ROOT/r for r in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/INDEX.md','DOCS-INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for p in paths:
 assert 'private' not in p.name.lower();dest=mirror/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
print('369 real-dump failure and recovered healthy baseline recorded; full goal remains active.')
