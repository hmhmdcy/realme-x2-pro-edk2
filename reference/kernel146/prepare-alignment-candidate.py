from pathlib import Path
import difflib, hashlib, json, subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel147'); out.mkdir(exist_ok=False)
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147'); ref.mkdir(exist_ok=False)
old=out.parent / 'kernel146'
names=['drivers/gpu/drm/msm/adreno/a6xx_gpu.c','drivers/gpu/drm/msm/msm_gem.h','drivers/gpu/drm/msm/msm_gem_vma.c']
a=k / names[0]
assert a.read_bytes()==(old / 'a6xx-candidate-private.c').read_bytes()
(out / 'source146-before-private.patch').write_bytes(subprocess.check_output(['git','-C',str(k),'diff','--binary']))
a.write_bytes((old / 'a6xx-before-private.c').read_bytes())
before={n:(k / n).read_text() for n in names}
(out / 'source145-restored-before-private.patch').write_bytes(subprocess.check_output(['git','-C',str(k),'diff','--binary']))
s=before[names[0]]
start=s.index('static struct drm_gpuvm *\na6xx_create_private_vm(')
end=s.index('\nstatic uint32_t a6xx_get_rptr',start)
chunk=s[start:end]
chunk=chunk.replace('\tstruct msm_mmu *mmu;','\tstruct adreno_gpu *adreno_gpu = to_adreno_gpu(gpu);\n\tstruct drm_gpuvm *vm;\n\tstruct msm_mmu *mmu;')
chunk=chunk.replace('\treturn msm_gem_vm_create(gpu->dev, mmu, "gpu", ADRENO_VM_START,\n\t\t\t\t adreno_private_vm_size(gpu), kernel_managed);',
'''\tvm = msm_gem_vm_create(gpu->dev, mmu, "gpu", ADRENO_VM_START,
\t\t\t       adreno_private_vm_size(gpu), kernel_managed);

\t/* Diagnostic candidate: test A640 GMEM resolve address granularity. */
\tif (!IS_ERR(vm) && kernel_managed && adreno_is_a640(adreno_gpu))
\t\tto_msm_vm(vm)->iova_alignment = SZ_64K;

\treturn vm;''')
assert 'iova_alignment' in chunk
after={names[0]:s[:start]+chunk+s[end:]}
after[names[1]]=before[names[1]].replace('\tbool managed;','\tbool managed;\n\n\t/** @iova_alignment: Address alignment for kernel managed allocations. */\n\tu64 iova_alignment;')
after[names[2]]=before[names[2]].replace('obj->size, PAGE_SIZE, 0,','obj->size, vm->iova_alignment, 0,').replace('\tvm->managed = managed;','\tvm->managed = managed;\n\tvm->iova_alignment = PAGE_SIZE;')
patch=''
for n in names:
    assert after[n]!=before[n]
    (out / (Path(n).name+'-before-private')).write_text(before[n])
    (k / n).write_text(after[n])
    patch+='diff --git a/'+n+' b/'+n+'\n'+''.join(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref / 'a640-managed-iova-alignment-diagnostic.patch').write_text(patch)
subprocess.run(['git','-C',str(k),'diff','--check','--',*names],check=True)
(out / 'config-before-private').write_bytes((k / '.config').read_bytes())
report=dict(stage=147,baseline=145,previous_failed_candidate=146,failed_ccu_invalidation_reverted=True,a640_kernel_managed_only=True,alignment_bytes=65536,obj_size_and_mapping_extent_unchanged=True,candidate_diagnostic_only=True,device_fix_accepted=False)
(ref / 'candidate-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
build=(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel146/apply-build-package.py')).read_text()
start=build.index("name = 'drivers/"); end=build.index('env = os.environ.copy()')
build=build[:start]+"assert not (out / 'align-full-build-private.log').exists()\nassert shutil.disk_usage('/mnt/c').free > 4 * 1024**3\n"+build[end:]
build=build.replace('kernel146','kernel147').replace("'146'","'147'").replace('K146','K147').replace('#146','#147').replace('modules-root146','modules-root147').replace('Image-k146-ccu-retire-private','Image-k147-iova-align-private').replace('logdump-k146-ccu-retire.img','logdump-k147-iova-align.img').replace("'ccu-'","'align-'")
build=build.replace('stage=146,kernel_build=146','stage=147,kernel_build=147').replace('a640_only_ccu_invalidation_moved=True','a640_managed_iova_alignment_64k=True,ccu_invalidation_restored=True').replace('submit_order_cases=20','diagnostic_candidate=True')
(ref / 'build-package.py').write_text(build)
print('K147_A640_ALIGNMENT_CANDIDATE_PREPARED_AND_CCU_ORDER_RESTORED')
