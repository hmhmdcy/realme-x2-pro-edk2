"""Build a scoped diagnostic candidate, preserving the same-build baseline."""
from pathlib import Path
import difflib,tarfile,hashlib,json,shutil,os
os.umask(0o077);base=Path('/var/lib/samurai/k148-mesa');source=base/'mesa-26.2.4'
rel='src/freedreno/vulkan/tu_knl_drm.cc';p=source/rel;old=p.read_text()
with tarfile.open('/var/lib/samurai/k148-sdk-apks/mesa-26.2.4.tar.xz') as t:
    assert t.extractfile('mesa-26.2.4/'+rel).read()==p.read_bytes()
library=base/'build/src/freedreno/vulkan/libvulkan_freedreno.so';assert library.exists()
baseline=base/'baseline-build';baseline.mkdir(mode=0o755)
shutil.copy2(library,baseline/library.name);(baseline/'tu_knl_drm.cc.original').write_text(old)
prefix='''   *iova = 0;

   /* Match the A640 kernel-managed address alignment for automatic VM_BIND
    * allocations. Mapping sizes and explicit capture/replay addresses retain
    * their original granularity.
    */
   uint64_t alignment = os_page_size;
   if (dev->physical_device->has_vm_bind &&
       dev->physical_device->dev_id.gpu_id == 640)
      alignment = MAX2(alignment, UINT64_C(0x10000));
'''
assert old.count('   *iova = 0;\n')==1
new=old.replace('   *iova = 0;\n',prefix)
assert new.count('util_vma_heap_alloc(&dev->vma, size, os_page_size)')==2
new=new.replace('util_vma_heap_alloc(&dev->vma, size, os_page_size)','util_vma_heap_alloc(&dev->vma, size, alignment)')
p.write_text(new)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(base/'a640-vm-bind-iova-alignment-diagnostic.patch').write_text(patch)
for folder in [baseline,base/'candidate-build']:
    folder.mkdir(mode=0o755,exist_ok=True)
    icd=dict(file_format_version='1.0.1',ICD=dict(api_version='1.4.354',library_arch='64',library_path=str(folder/library.name)))
    (folder/'freedreno_icd.aarch64.json').write_text(json.dumps(icd,indent=2)+'\n')
report=dict(diagnostic_candidate=True,promoted=False,source_archive_sha256='bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9',
    modified_file=rel,original_sha256=hashlib.sha256(old.encode()).hexdigest(),candidate_sha256=hashlib.sha256(new.encode()).hexdigest(),
    same_build_baseline_library_sha256=hashlib.sha256((baseline/library.name).read_bytes()).hexdigest(),
    scope='Automatic A640 VM_BIND IOVA allocation only',explicit_capture_replay_preserved=True,mapping_sizes_preserved=True)
(base/'candidate-preparation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
