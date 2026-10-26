from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['memory-validation.json','intree-build-validation.json','memory-runtime-validation.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
state=json.loads((HERE/'source-state.json').read_text());assert state['tracked_clean'] and not state['installed']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text());d.update(current_camera_evidence=prefix+'reference/kernel354/README.md',in_progress_stage=354,
  in_progress_evidence=prefix+'reference/kernel354/README.md',in_progress_installed=False,
  a5_icp_dma_memory_backend_implemented=True,a5_icp_dma_memory_backend_evidence=prefix+'reference/kernel354/memory-validation.json',
  a5_icp_dma_memory_actual_smmu_tested=True,a5_icp_dma_memory_runtime_evidence=prefix+'reference/kernel354/memory-runtime-r2-validation.json',
  icp_hardware_backend_installed=False,icp_firmware_boot_verified=False,factory_final_tone_default_pending=True,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
entry='''354最新：新增实际A5 memory backend（reference/kernel354/kernel/camss-icp-a5-memory.c/.h）alloc/map/unmap/free四API。需要defaultDMA域+0..5MiB明确RESV_RESERVED，coherentRAM原DMAIOVA在窗口外且32bit，逐页iommu_iova_to_phys→alias0，不假定PA连续/32bit。已有外来映射拒绝覆盖；map失败rollback前缀，unmap倒序保留准确prefix，失败不free、可重试；domain切换拒绝。host/ARM各25场景PAGES1280，离散PA>4GiB/cache属性/错误resv和domain/坏DMA/分配map失败/缺失PA/外来map/unmap失败保RAM+retry/domain change均过。初测试工具stdio变量/缩进和桩生命周期问题已修，kernelbackend未改弱。353未改的HFI/ELF检查复用。

354真实内核集成source /mnt/samurai-full282/source354，branch samurai-icp-a5-core354，parent34830086bae...，commit ea71fa4fd8375502d73231dfb749cbd3a23920eb，8文件trackedclean，patch26039bytes。coreHFI/fw/memory+hiddenKconfig/Makefile+memorytest C，privateDTBO头仅build未提交。in-tree W1/Werror r2 13.85sec无诊断，core122976 SHA9ee2275a6e984011c0c3c10b0c71d2b755254fd8961e913ee6f8698015b64f33（R1相同），test73464 SHA764b3299461908c8b1222c1642f81cccf234829db682b784f6656c573b12b216，Kbuild intreeY/vermagic匹配。shared camera目录+config/关键gen files恢复，hosttools/vdso等prepare输出可能刷新，不称全部build字节不变。没有改/重编旧CAMSS/Image/sensor或安装。

354实际prereq bootguardmatch/7.3rc6-k298，OF_OVERLAY/DYNAMIC y，SMMU /soc@0/iommu@15000000 phandle44/iommucells2，ICPclk/ICPahb enable0。内存诊断临时overlay /reserved-memory/samurai-icp354-fw-iova（无physicalreg, iommu-addresses指新dev 0..5MiB）+/soc@0/samurai-icp354-memory（SID2222 mask0+memory-region），probe group只有自身才DMAallocate，未A5 MMIO/clockFWboot。

354 R1 /var/lib/samurai/k354-memory-r1 worker4528终态failed：core加载成功但test覆盖EINVAL，日志“symbols in overlay, but not in live tree”；基础DT无__symbols__，-@多导出符号导致，未映射；模块/节点清理taint0/fault0。failed报告与private logs保留。修fixture为plugin不带-@，无__symbols__/__fixups__而保留__local_fixups__，外部SMMU用实测phandle；944→778byteDTBO。只重建本次相关两个模块，core bytes相同，没改内存逻辑或gate。

354 R2 /var/lib/samurai/k354-memory-r2 worker4723终态passed/PID不存在。真SMMU group1，5MiB1280pages alias与原DMA PA逐页一致/CPU模式匹配，alias存在时额外DMA分配避窗口；全部1280页撤销确认，mapped0/backingfalse。临时core/test模块和两DT节点全移除，taint0→0/新相关fault0，未停PW/WP或改persistentDT/安装module/重启/NV。private354 runtime observation含DMA地址，public已去除。不是A5取指/DMA/cache一致性/固件boot证明。无活动build/probe/SDKbind。

354所有通用源/脱敏证据已镜像，vendor/blob/原始logs/模块私存。下一步355结合原厂A5+ICPmgr核对BPS/IPE资源上电顺序，实现platform power/clock/IRQ/HFI握手，再实际启动firmware。纯IOVA运行时overlay验证不等于永久DT schema/早期扫描已完成。kernel core内存路径已实机，完整IPE会话/IOIQ/libcamera m2m及350～352LTM/CCM/Gamma默认仍待。当前deployed仍349最后观察338+r27/r22+344etc；AE防频闪/模式/光学/同步/连续AF等全目标active未完成。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：353','# 当前检查点：354',1);at=s.index('\n\n',s.index('\n\n')+2)+2;s=s[:at]+entry+s[at:];path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goalactive。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel354/README。354实际A5 coherentDMA/IOVAalias内存backend已实现，host/ARM25错误回滚场景过；真实SMMU临时overlay R2 group1/1280pages全map验证全unmap释放，taint0fault0/临时module与DTnodes全移除，无FWboot。R1 -@导出symbols而base无symbols导致覆盖EINVAL，未映射且清理；R2 plugin不用-@保留localfixups、numericSMMUphandle44，修fixture不改core。source354 fullkernel commit ea71fa4... parent34830086bae，8files clean/patch保存；in-treecore9ee2275a...122976,test764b3299...73464，W1Werror。build camera/config关键输出已恢复但hosttools准备输出可能刷新。当前phone仍338+r27/r22+344etc，无worker/bind。下一步355读原厂A5/ICPmgr核对BPS/IPE上电先后，实际接platform GDSC/clocks/IRQ/HFI握手boot；内存已经可用，不回到仅源码inventory。无physicalreg的纯IOVA reservation运行时已验证，永久DTschema/早期扫描待。private352原ICP ELF+353core+350Gamma/351LTM/CCM数据保留，全部固件/vendor/原始数据不镜像。full goal还包括IPE会话/IOIQ/libcamera m2m、AE/防频闪/模式/光学/同步/AF等，勿缩为本轮完成。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('354当前：ICP DMA内存后端与IOVA0..5MiB真实SMMU探测通过，1280页全部撤销释放；继续A5平台资源与启动，默认未改。[354详情](../../reference/kernel354/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded354 actual memory backend and successful live SMMU mapping/cleanup; firmware boot still pending; goal active.')
