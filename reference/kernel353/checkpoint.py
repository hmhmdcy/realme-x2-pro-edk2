from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['kernel-build-validation.json','core-validation.json','iommu-planning-evidence.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
state=dict(stage=353,scope='A5 HFI queue and ELF RAM-loading kernel core helpers',
 source_files=[dict(path=p.relative_to(HERE).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((HERE/'kernel').iterdir()) if p.is_file()],
 original_source_manifest='../kernel352/oem-icp-sources.json',build_evidence='kernel-build-validation.json',test_evidence='core-validation.json',
 platform_probe_and_iommu_and_hfi_boot_not_implemented=True,installed=False,phone_changed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text());d.update(current_camera_evidence=prefix+'reference/kernel353/README.md',in_progress_stage=353,
  in_progress_evidence=prefix+'reference/kernel353/README.md',in_progress_installed=False,
  a5_icp_kernel_core_helpers_built=True,a5_icp_kernel_core_evidence=prefix+'reference/kernel353/core-validation.json',
  a5_icp_iommu_reservation_plan_evidence=prefix+'reference/kernel353/iommu-planning-evidence.json',
  icp_hardware_backend_installed=False,factory_final_tone_default_pending=True,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
entry='''353最新：实际新增kernel/camss-icp-a5-{hfi,fw,core}.c/.h+externalMakefile，导出qtable_init/ring_init/write/read/fw_inspect/load核心库，无platformprobe/MMIO/IOMMU/固件boot/V4L2。真实内核W=1/-Werror r2成功1.98sec/无诊断，qcom-camss-icp-a5-core.ko88408bytes SHA d6ccd241513a718d88a3d460ba7ea468b7312d712e8d896071f02cdcb6b3cf8f，release7.3.0-rc6-rmx1931-samurai-k298+。外部工作/mnt/samurai-full282/icp353-core，build/source实际/home/cy122/x2pro-linux/camera305-sensor-kernel；未改已有Image/CAMSS/sourcebranch/安装。早r1可编译但table语义修正前，不作最终通过。

353核心合同：qhdr956，liveword前pad60、尾pad60；table预留4slots/active3，total3848。初按3slot2892被原厂Cstruct sizeof比较拒绝，core-r1-failure记录；352原固件lookup只证明24header/956stride，controlled3-slotfixture不等于原host完整qtblsize。INTR_MODE初始化full3848bytes与原hfi.c原代码一致，DbgTxWatermark1024。host writes1584组与编译原hfi_write_cmd完整buffer+header0diff，每arch16single-read与原hfi_read_message0diff。新read按packetlength保留后续包，short/incomplete/invalid不推进；原readbulk不直接照搬。2producer+1consumer2000packets各host/ARM通过，仅hostmutex模型非真实fwconcurrency。coherentRAM/dma_rmb/wmb/mb，实际kernelobj 5个dmb oshld/oshst/osh；DBG原fw可能overwrite，尽力日志非MSG guarantee。

353ELF loader先全部header/PTLOAD检查再zero span/copy，ARM32LE/entry0原固件，BSS+gaps与独立Python5MiBexpected逐字节一致，guard/span外unchanged。17malformed ELF每arch拒绝且RAM/layout不改。host/ARM Cgnu11/O2/WallWextraWerror actualfunctionbodies+pthread，source oracle仅privately compiled GPL hfi functions/init，非HAL binaryoracle。publiccore-validation passed。tests E ext4 /mnt/samurai-full282/icp353-tests，SDK/private/camss353-core临时bind已卸载，避免C拷大数据；private353含日志/模块/ASM，不镜像厂商表/固件/参考代码。

353 IOMMU规划实查：of_iommu.c无物理reg时iommu-addresses对应RESV_RESERVED；get_resv(core ops)->ARM_SMMU get_resv->iommu_dma_get_resv->OF；DMA iova_reserve_iommu_regions reserve所有非SW_MSI，包括纯IOVA。可在DT memory-region引用无reg的纯IOVA窗口0..5MiB，先预留防DMAallocator碰撞，别处分配coherentRAM，再用domain页面PA映射alias0给A5，不强依赖固定physical camera carveout。还没DT/实际domain/group/map验证，不直接启动。iommu_get_dma_domain未模块导出，需iommu_get_domain_for_dev（已export）并checkDMA type；map/unmap/iova_to_phys/get/put_resv已export。iommu-planning-evidence含5源码hash/确切调用链/exports。一次无mount读symvers失败已修，后续脚本都284 mounted_build先挂E镜像。

353源码与脱敏证据已镜像，无活动build/SDKbind/phoneworker，无手机操作，仍349最后观察338+r27/r22+344etc。下一步354实际实现一致性RAM+保留IOVA确认+逐页alias/失败回滚/释放，随后A5 platformresource/boot HFI握手和IPE IOIQ/libcamera m2m。不能把本轮corelibrary当整hardwarebackend已完成。全goalactive，Gamma候选348/349未装、LTM核心/frontCCM/ADRC、AE防频闪/模式/光学/多摄几何同步/连续AF等仍待。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：352','# 当前检查点：353',1);at=s.index('\n\n',s.index('\n\n')+2)+2;s=s[:at]+entry+s[at:];path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goalactive。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel353/README。353实际kernel A5 HFI+ELF core helpers built W1/Werror module r2成功，host/ARM actualbodies1584原write+16原read comparisons/full3848qtbl初始化一致，2000host并发packet/17坏ELF+原固件BSSzero/guards通过；不是MMIO/IOMMU/boot/平台driver。初table3slots错，原厂预留4/active3total3848已修，failed保留。新的关键354路线：standard OF memory-region/iommu-addresses无physicalreg→RESV_RESERVED，ARM_SMMU/core/DMA实际链支持保留0..5MiBIOVA不让DMAcookie碰撞；coherentRAM别处分配，逐page取得原DMA phys再映射alias0，后续unmap/free。无固定physicalcarveout不必阻塞。iommu_get_dma_domain不导出，get_domain_for_dev/map/unmap/iova_to_phys/get_put_resv已导出；checkdomainDMA与group再动。下一步实现memorybackend+rollback，再platformresource/boot HFI和IPE会话+libcamera。source353核心在reference/kernel353/kernel；external工作E ext4 icp353-core，testsicp353-tests，SDK bind已卸；build/source实际camera305-sensor-kernel/release7.3rc6-k298。352已取原厂ARM32ICP ELF并Thumb lookup ABI核对；351LTM/CCM树/front25矩阵/flags，350Gamma树/编码插值均保留。phone未动，仍349最后观察338+r27/r22+344etc；完整goalactive未完成AE/光学/同步/AF等。所有厂商表/固件/asm/源码oracle私存不镜像。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('353当前：A5/HFI队列与ELF内核核心已构建并完成主机/ARM对照；继续实现IOVA映射和硬件启动，手机默认未改。[353详情](../../reference/kernel353/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded353 actual A5 core implementation/build/tests and next IOMMU mapping plan; goal active.')
