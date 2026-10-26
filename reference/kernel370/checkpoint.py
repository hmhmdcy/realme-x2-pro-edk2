"""Record offline candidate progress without promoting it to device evidence."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=lambda p:json.loads(p.read_text())
for label in ['firmware-mapping','exception-layout','lifecycle','snapshot','owner','intree-build']:
 assert read(HERE/(label+'-validation.json'))['passed']
source=read(HERE/'source-state.json');assert source['applied'] and not source['installed'] and not source['firmware_cpu_started']
source.update(hardware_exercised=False,hardware_boot_verified=False,hardware_cleanup_verified=False,
 latest_actual_device_experiment_stage=369,actual_device_guard_stage=369)
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p)
 assert d['current_boot_guard_stage']==369
 d.update(stage=370,latest_work_stage=370,current_camera_evidence=prefix+'reference/kernel369/README.md',
  current_device_revalidated_stage=369,in_progress_stage=370,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel370/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_quiesced_failure_candidate_evidence=prefix+'reference/kernel370/README.md',icp_quiesced_failure_hardware_verified=False,
  icp_static_mmu_instruction_evidence=prefix+'reference/kernel370/firmware-mapping-validation.json',
  icp_exception_layout_instruction_evidence=prefix+'reference/kernel370/exception-layout-validation.json',
  icp_latest_device_experiment_stage=369,
  icp_next_step='Prepare and fixture a guarded held-failure snapshot worker; collect owned firmware exception state before DMA/PM teardown, then observe cleanup separately; no identical369 replay',
  current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text()
s=s.replace('# 当前检查点：369（真实故障快照已取回，设备恢复，完整目标active）', '# 当前检查点：370（离线quiesce窗口候选通过构建；设备证据仍369，目标active）',1)
s=s.replace('先读WORKING-BOUNDARIES.md及reference/kernel369/README.md。','先读WORKING-BOUNDARIES.md及reference/kernel370/README.md；最近真实设备证据在369。',1)
a=s.index('## 下一步\n');b=s.index('\n大目录git grep',a)
s=s[:a]+'''## 370离线新增

同一原厂ELF的vmm_preinit/program_section_entries实际指令执行，只有L1 memset桩：代码／异常字段／页表／CSR样本为恒等映射，共享区／SFR／堆静态未映射，需后续动态VMM。原始页表／静态表只私存。初始化请求等待块4例确认请求=1才写01000100版本，结合369已读版本可推断通过等待点；不是完整RTOS、CP15或硬件SMMU验证。原始data/prefetch abort入口4例确认FAR/FSR/type偏移1099a0/1099a4/1099a8、type3/1，CP15值合成且core-save为桩，没有本机异常解码。

驱动分开quiesce_locked与stop_locked：start失败仅quiesce，保留RAM/映射/已持有PM，由owner最终stop。原先devcoredump仍先发布。临时test默认关闭hold_start_failure；显式开启且CPU/IRQ已停、块复位成功、完整固件映射和PM仍有归属时才failed-held并pin模块。root0400二进制firmware视图受两层锁／实际分配边界保护，cleanup后不可读。纯诊断接口，非正式相机ABI；DDR可能不含A5脏cache，零值不能证明没有异常。

实际start13／quiesce-stop9／旧负例2、reader15、hold-pin13的ASAN/UBSAN模型通过；MMIO/复位/DMA/PM/调度仍为桩。针对实际k363的两个in-tree W=1/-Werror模块构建通过，无诊断，未安装／加载。core232976 SHA513e25fe2ecdf77c20e28f97792be48bd9139e169501c5244bd371fbbb6d2b4e；test73320 SHA147caba4cb3b6ca2c1511442423d12de82489a1c0fcb9b47bba1ad8949e925c0。配置和既有CAMSS输出恢复。本轮无手机操作，复用369验证，没有重新宣称基线测试。

## 下一步

先准备并夹具验证独立held-failure收集／清理worker，使用369当前guard和显式hold_start_failure=1。不能直接跑369默认自动清理launcher，也不能在新worker未准备好时再启动CPU。结果确认failed-held且归属完整后，先对照原厂ELF核实固件首4KiB代码页；匹配才读109000异常页和必要页表，只私存，快照落盘后再分别观察DMA和PM释放。页不匹配／复位失败／归属不全停止读取，不读重启后旧DDR来解释新故障。最近真实实验仍369的3／2.711ms／SFR空／自动重启／无清理终态；不能称本轮修好了故障或完成握手。
''' + s[b:]
s=s.replace('samurai-a5-sfr-diagnostic369／f9e1ce02537f9a28f02c471888203e59c0bff794；父368 core9c60745372258f2f37374862a06c9fd09eeaf240。', 'samurai-a5-quiesced-failure370／e79613d477deee2a55726cc2e05c7789057395ba；父369 f9e1ce02537f9a28f02c471888203e59c0bff794。',1)
s=s.replace('候选临时加载后已由重启消失，默认ICP仍disabled。', '369旧候选已随恢复重启消失，370新候选未加载，默认ICP仍disabled。',1)
s=s.replace('私存E:/edk2-samurai-out/kernel369含collected-r1/raw', '私存E:/edk2-samurai-out/kernel370含离线模型／页表／新模块；kernel369含collected-r1/raw',1)
s=s.replace('本轮已取消该自有grep/fetch并确认进程结束','369已取消其自有grep/fetch并确认进程结束',1)
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从370离线检查点继续active多摄/ISP目标。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel370/README.md。现机证据和guard仍369/host369严格Wi-Fi，Image363/boot366/DT365/r29/r24；本轮无手机操作。维护源source354/e79613d477分开start失败quiesce和stop资源释放，默认false临时hold_start_failure及root0400受界固件视图；actual函数模型和in-tree W1/Werror两模块构建通过但未加载。原厂静态MMU/请求等待/异常入口指令证据已补，CP15/cache/RTOS不模拟。最近真实369响应3仅2.711ms、SFR空、重启无终态。下一步先准备并夹具验证使用369guard、hold_start_failure=1的新worker，窗口内先核对原厂代码页才读109000异常页/页表并私存，再分开观察DMA/PM释放；不能直接重跑369launcher。原始固件/内存/校准/认证日志私存。完整HFI/IPE、第五摄身份、更多模式和光学同步/AF未完。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text();s=s.replace('## 最新交接\n','## 最新交接\n\n- [370离线A5故障窗口与MMU证据](../reference/kernel370/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[369真实故障快照与恢复基线](reference/kernel369/README.md)','[370离线A5故障窗口与MMU证据](reference/kernel370/README.md)');p.write_text(s)
print(json.dumps(dict(stage=370,offline_candidate_verified=True,new_phone_operations=False,current_guard_stage=369,goal_status='active')))
