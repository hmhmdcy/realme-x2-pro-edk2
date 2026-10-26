"""Record the actual recovered baseline and preserve failed ICP evidence."""
from pathlib import Path
import json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=lambda p:json.loads(p.read_text())
final=read(HERE/'final-state-validation.json');camera=read(HERE/'camera-runtime-validation.json');boot=read(HERE/'postboot-validation.json')
assert final['passed'] and camera['passed'] and boot['new_boot_verified']
failure=read(HERE.parent/'kernel366/boot-runtime-r1-validation.json');assert not failure['passed'] and failure['a5_cpu_release_attempted']
source=read(HERE.parent/'kernel365/source-state.json');built=read(HERE.parent/'kernel363/source-state.json')
built.update(installed=True,installed_evidence='reference/kernel363/postboot-validation.json',current_image_still_deployed=True)
(HERE.parent/'kernel363/source-state.json').write_text(json.dumps(built,indent=2)+'\n')
source.update(installed=True,installed_as_dt_stage=365,firmware_packaging_stage=366,installed_evidence='reference/kernel366/postboot-validation.json',icp_default_disabled=True)
(HERE.parent/'kernel365/source-state.json').write_text(json.dumps(source,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/rel;old=read(p);archive=ROOT/'archive'/('camera-'+p.stem+'-through362-2026-10-20.json')
 if not archive.exists():shutil.copyfile(p,archive)
 old.update(stage=367,kernel_boot_stage=366,current_boot_guard_stage=367,kernel_image_stage=363,
  actual_kernel_image_stage=363,actual_kernel_release=final['kernel'],boot_stage=366,current_dt_stage=365,
  device_current_kernel=final['kernel'],current_camss_module_stage=363,unified_gamma_driver_source_stage=348,
  current_camss_module_note_sha256=final['camss_note_sha256'],current_camss_source=built['source'],
  current_camss_source_branch='samurai-iommu-node-lifetime357',current_camss_source_commit=built['commit'],
  maintained_branch=source['branch'],maintained_commit=source['commit'],actual_kernel_image_source_commit=built['commit'],
  actual_board_dt_source_commit=source['commit'],current_camera_evidence=prefix+'reference/kernel367/README.md',
  current_camera_userspace_stage=362,current_camera_configuration_stage=362,framework_version='99990.7.2-r29',configuration_version='0.1.0-r24',
  current_device_runtime_state_verified=True,deployed_snapshot_is_historical=False,device_current_taint=0,
  device_closeout_evidence=prefix+'reference/kernel367/final-state-validation.json',current_boot_guard_evidence=prefix+'reference/kernel367/postboot-validation.json',
  device_current_ssh_status='strict_original_key_usb',device_current_usb_mode='NCM',device_force_restart_currently_needed=False,
  iommu_node_lifetime_fix_installed=True,iommu_node_lifetime_runtime_evidence=prefix+'reference/kernel364/memory-runtime-r1-validation.json',
  a5_icp_candidate_source_commit=source['commit'],corrected_board_carveout_runtime_tested=True,
  corrected_board_carveout_evidence=prefix+'reference/kernel366/boot-runtime-r1-validation.json',
  icp_firmware_boot_verified=False,icp_hardware_backend_installed=False,icp_static_dt_default_disabled=True,
  icp_latest_hfi_response=3,icp_latest_attempt_normal_terminal=False,icp_latest_attempt_followed_by_modem_watchdog=True,
  icp_latest_attempt_evidence=prefix+'reference/kernel366/boot-runtime-r1-validation.json',
  icp_latest_attempt_recovery_evidence=prefix+'reference/kernel367/postboot-validation.json',
  icp_next_step='Offline firmware CSR/response-3 and power-down analysis before another CPU release',
  current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False,
  confirmed_physical_camera_count=4,portrait_2mp_identity_verified=False,
  remaining_camera_scope_evidence=prefix+'reference/kernel363/REMAINING-CAMERA-SCOPE.md',
  in_progress_stage=367,in_progress_installed=True,in_progress_evidence=prefix+'reference/kernel367/README.md')
 if 'deployed_camera_modules' in old:old['deployed_camera_modules']=final['deployed_camera_modules']
 p.write_text(json.dumps(old,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through362-2026-10-20.md'
if not archive.exists():shutil.copyfile(ROOT/'NEXT-SESSION.md',archive)
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：367（基线恢复，完整多摄／ISP目标 active）

2026-10-20。先读WORKING-BOUNDARIES.md。原密钥USB SSH，当前boot guard `/var/lib/samurai/k367-work/boot-id-private.txt`，reference/kernel367/host.py为入口。Image/778模块363、boot固件366、静态DT来源365；libcamera五运行包99990.7.2-r29，config/stack0.1.0-r24，四份私有完整Preview默认保持362。全部相机/ISP目标尚未完成。

## 实际新结果

363统一Image固定ba61a62293e0f6bc5838c06f2e85e033e3d702a8，包含348 Gamma和357公共OF/IOMMU节点引用修正。42 CAMSS组件W1/Werror无诊断，778模块匹配，实际内嵌BT模块核对。四颗已确认传感器和隔离IPA回归通过。364实机映射/核对/回收1280页；实验模块/节点可完整卸载，无OF引用故障。

364首次正确板级启动在resources返回-22；精确诊断确认overlay给已有无phandle预留节点加标签不能实时解析。365增加默认disabled的SoC ICP资源和板级camera_mem引用，既有固件9ab00000/5MiB/no-map不变。207个引用数字重排但目标路径均保持。只改logdump FAT中的DT没有生效；实际EDK2用固件卷DT。366重建固件，逐FFS证明只有DTB变化，实际boot读回和静态引用通过。不能再把FAT DT文件正确当Linux已采用它。

366一次A5实验已到固件/共享IOVA映射、资源上电和CPU释放；HFI响应持续3，500ms超时，日志记录block reset asserted，约1秒后modem watchdog并自动重启。无完整SYS_INIT/PING/PC_ACK，原worker没有正常终态。ramoops和原状态私存保留；不能把旧terminal=false改成功，不能把watchdog原因归结为某单行代码。恢复启动ICP模块/节点不在、17时钟0、taint0，临时固件副本按哈希清理，原厂和事务副本均保留。

恢复启动SSC file server exit4导致SensorProxy/桌面未起；367执行正常停服务和一次bootloader/reboot，不刷分区、不重试A5，恢复后实际状态/采集见reference/kernel367各验证JSON。完整目标继续active。

## 维护源／工具与回退

完整内核源/mnt/samurai-full282/source354，分支samurai-icp-board-dt365，提交e217016006e609333a715c10f2f3e442dc4da95f；含精确HFI ready364与诊断1947eb7，但实际Image固定ba61，静态DT来自e217。临时ICP模块按k363构建，没有永久加载。libcamera源/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2，正式r29/r24配方已保存。进入ext4先用reference/kernel284/storage.py::mounted_build()，SDK bind串行。

私存E:/edk2-samurai-out/kernel363～367。boot366候选c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924；logdump365 aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da。boot276和logdump363可组合回退DT；原k298模块树/logdump和362事务的r27/r22包＋338模块＋344私有配置也保留。NV/OTP/工厂备份未写，原厂固件、校准、认证日志及密钥不进公共Git。

## 下一步

优先复用已取得的原厂CAMERA_ICP.elf、AndroidR固定源码及352上游原型，离线查响应3的写入者、CSR/共享地址语义和停机顺序；当前不安排重复A5 CPU释放。363 ELF入口和命令路径指令测试是局部证据，平台/OS等为桩，不能外推整固件状态。IPE图像会话与IO/IQ、后级Gamma/LTM/CCM尚未打通。

四颗已测为三后摄＋前摄；官方还有2MP人像摄像头，vendor的OV02A1B仅库名证据，实际身份未确认。AndroidR cam-sensor@4与现前摄共享PHY2/MCLK2/reset12，GPIO29选择关系待解，不能直接加冲突GPIO节点或当OV02A10。见reference/kernel363/REMAINING-CAMERA-SCOPE.md。

动态FrameDurationLimits、自动防频闪、其它模式、绝对颜色/黑电平/阴影、几何/多摄同步和连续AF仍开放，延期纯色/遮光可后做。不要把已取流与现有个体WB/LSC/CCM/default Gamma集成称为完整校准。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从367恢复检查点继续多摄/ISP active目标。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel366/README.md和367/README.md。现机Image363/boot366/DT365、r29/r24，host367当前guard；A5响应3超时后modem watchdog自动重启，原事务无终态、日志保留。367正常重启无分区写入，先看最终健康与采集。下一步优先离线原厂固件CSR/response3/停机次序分析，不重复CPU释放；IPE、未知2MP、更多模式和光学同步/连续AF未完。私有固件/校准/密钥不上Git，storage284先挂ext4。\n')
note='367当前：Image363统一内核、boot366/静态DT365和r29/r24已用；四颗传感器回归。A5实际释放后响应3超时并出现modem watchdog，完整ICP握手未通过，正常基线恢复及后续离线分析继续。'
entries={'linux-port/camera/README.md':'../../','linux-port/camera/kernel/README.md':'../../../','linux-port/docs/HARDWARE-STATUS.md':'../../'}
for rel,prefix in entries.items():
 p=ROOT/rel;s=p.read_text();p.write_text(note+' [367状态]('+prefix+'reference/kernel367/README.md)。\n\n'+s.split('\n\n',1)[1] if s.startswith('362已部署') else note+' [367状态]('+prefix+'reference/kernel367/README.md)。\n\n'+s)
for rel in ['sessions/INDEX.md','DOCS-INDEX.md']:
 p=ROOT/rel;s=p.read_text()
 if rel.startswith('sessions') and '367基线恢复' not in s:s=s.replace('## 最新交接\n','## 最新交接\n\n- [367基线恢复及363～366 ICP/DT实测](../reference/kernel367/README.md)\n',1)
 if rel.startswith('DOCS'):s=s.replace('[362隔离请求及默认调校部署](reference/kernel362/README.md)','[367基线恢复与ICP/DT实测](reference/kernel367/README.md)')
 p.write_text(s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for n in range(363,368) for p in (ROOT/'reference'/('kernel'+str(n))).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/r for r in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/INDEX.md','DOCS-INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',*entries]]
paths += [archive,*ROOT.glob('archive/camera-*-through362-2026-10-20.json')]
for p in paths:
 dest=mirror/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
print('367 checkpoint and selected public sources mirrored; goal remains active.')
