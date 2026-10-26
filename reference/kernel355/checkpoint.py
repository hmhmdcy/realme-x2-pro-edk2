from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['resources-validation.json','intree-build-validation.json','power-runtime-r2-validation.json']:assert json.loads((HERE/name).read_text())['passed'],name
state=json.loads((HERE/'source-state.json').read_text());assert state['tracked_clean'] and not state['installed']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text());d.update(current_camera_evidence=prefix+'reference/kernel355/README.md',in_progress_stage=355,
  in_progress_evidence=prefix+'reference/kernel355/README.md',in_progress_installed=False,
  a5_icp_resources_implemented=True,a5_icp_resources_evidence=prefix+'reference/kernel355/resources-validation.json',
  a5_icp_resources_hardware_tested=True,a5_icp_resources_runtime_evidence=prefix+'reference/kernel355/power-runtime-r2-validation.json',
  a5_icp_candidate_source_commit=state['commit'],icp_hardware_backend_installed=False,icp_firmware_boot_verified=False,
  factory_final_tone_default_pending=True,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
entry='''355最新：实现SM8150 A5/BPS/IPE0/IPE1平台资源后端，实际上电/读取A5版本/释放通过。原厂ICPmgr确认顺序A5→BPS→IPE0→IPE1，退出反序；HFI/CPU/IRQ实际传入A5_SIERRA_BASE 0x0ac10000 size8000，不是旁边CSR2 0x0ac18000。353/354未写A5寄存器，不存在已写错地址。355原厂GPL提交9668fcdc...提取7files200795bytes，索引在reference/kernel355，原始源码private355/oem；复用private352/oem。

355 camss-icp-a5-resources.c/.h采用qcom,camss phandle supplier runtimePM link，复用现有CAMSS338 CPAS/MMCX/公共clock/ICC，不重复CPAS所有权。独管19clock refs/3PD，NO_DEV_LINK手动按次序PDget+clockbulk，逆序释放/部分失败rollback。原厂SVS fastAHB200M、ICP400M、BPS400M、IPE475M（共源）；四组bitmask15/PD7。生命周期由owner串行且停A5后才断电。16项实际resume/suspend体hostmock测试过，4rate失败/4bulk失败/3PDget失败/3PDput错误/顺序/忙/invalid，未改353/354复用其证据。

355沿用 /mnt/samurai-full282/source354 目录新branch samurai-icp-a5-resources355；354旧提交仍在。父ea71fa4...，本轮commit 0a23a25f34723a9d6fddb3a7c4e94080d0e92b7c，5filesclean/patch12364bytes。Kconfig Makefile及generic资源/测试C提交；privateoverlayheader仅BUILD。W1/Werror实际in-tree构建13.66sec无诊断，core155312 SHA85f212be67b273ca9270337ebd86fd41b2a9229a6509ea6ca87a8e9ebae36a38，test65904 SHA2957ccfb129cbb017e41991cf57ec5602af1674a2960c6fb158b43b219fb9484，intreeY/currentvermagic。构建后只补Kconfig OF/PM_GENERIC_DOMAINS依赖，当前配置均已启用，未变module对象。共享camera/config关键输出恢复，hosttools准备可能刷新。

355手机strictkeyUSB正常，bootguardmatch，实测CAMSSphandle38/CAMCC206/SMMU44。测试临时node /soc@0/samurai-icp355-power@ac10000，19clockrefs对应ICP/BPS/IPE17实际objects（IPE共源，fastAHB另计）。R1 worker5761 preflight对象数误18而实测17，终止于insmod前，模块/节点全无，无上电，失败保留。辅助脚本修17，不改kernel/gate。

355 R2 /var/lib/samurai/k355-power-r2 worker5811终态passed/PID不存在。全部4groups/3PD启，A5version0x10010000/control0x3000（ENbit9=0）/status0x200，ICP400M/BPS400M/IPE475000048Hz，已读19rates。随后groups0/domains0/consumer suspended；test/core卸载/临时node移除，17objects enable0，CAMSS suspended，taint0→0/fault0。未写控制/复位/启动FW、未DMA或IPE处理验证；已门控时钟rate设置保留，不声称寄存器全还原。不停PW/WP/不换已安装module/不重启/NV。无活动worker/build/bind。

355通用源与脱敏报告已镜像。下一步356实现同一ICP设备上354memory+355resources+IRQ/HFI固件boot/SYS_INIT/响应/停止。352 private原ELF3630392bytes SHAa22bc8ad...59e63，3LOAD span384000，需要0..5MiBalias。原厂HFI固定shared07400000len09600000，secondaryheap10a00000len00100000（实际allocator取DT1MiB，不是header2MiB），SFRalloc8KiB，QDSS10b00000len1MiB→phys16790000，IO10c00000len0xcf300000。需接共享/heap内存及QDSS条件。原厂enableCPU/control200+nsecreset10再拷贝ELF，HFIinitcontrol1210+qtbl/sfr/shared/heap/qdss/IO/initreq1后pollresp1，IRQenable3，再SYS_INIT。应先保证内存完整并核实reset语义，别盲启；stop原厂先PC_PREP/WFI，再clearEN|WAKE/read-write nsecreset/initreq0/irq0，关clock后才unmap/free。actualHFIqueue体/ELF/IOVA memory已经完成，继续boot不可倒回纯inventory。full goal IPE IO/IQ/libcamera m2m、AE防频闪/模式/光学/同步/连续AF等仍未完成。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：354','# 当前检查点：355',1);at=s.index('\n\n',s.index('\n\n')+2)+2;s=s[:at]+entry+s[at:];path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goalactive。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel355/README。355已完成实际A5/BPS/IPE资源上电/版本读取/释放；16错误回滚mock检查+in-treeW1Werror+phoneR2 passed，taint0fault0/临时module和DTnode已移除；无FWboot。HFI寄存器正确基址Sierra0xac10000非CSR2 0xac18000。资源复用现有CAMSS PM supplier管理公共CPAS/MMCX/ICC，独管19clockrefs/3PD，顺序A5/BPS/IPE0/IPE1。source354同路径已新branch samurai-icp-a5-resources355，commit0a23a25f...父ea71fa4...，5filesclean；355module私存未安装。实测CAMSSphandle38/CAMCC206/SMMU44，17实际clockobjects enable0/CAMSS suspended，PW不变。下一步356将354已实际验证的FW alias内存与355资源接同一设备，补shared/heap布置/IRQ/HFI boot/SYS_INIT及stop。原FW private352 ELF a22bc8...、OEM各HFI头/管理器在352/355，shared07400000len09600000，heap10a00000实际1MiB，SFR8KiB，QDSS10b00000→phys16790000，条件待；固件需正确停止再断电/unmap。勿回到仅源码inventory。完整IPE会话/IOIQ/libcamera、350-352Gamma/LTM/CCM默认、AE/防频闪/模式/光学/同步/AF均待，勿将一阶段视为目标完成。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('355当前：A5/BPS/双IPE资源后端已完成真实上电、A5版本读取与释放；继续原厂固件HFI启动，默认未改。[355详情](../../reference/kernel355/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded355 real A5/BPS/IPE power lifecycle; firmware boot pending; goal remains active.')
