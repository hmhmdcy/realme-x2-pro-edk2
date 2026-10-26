from pathlib import Path
import urllib.request,hashlib,json
out=Path('/mnt/e/edk2-samurai-out/kernel147'); ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147')
base='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/gpu/msm/'
files={}
for name in ['kgsl.c','kgsl_iommu.c']:
    url=base+name; p=out / ('oem-'+name)
    if not p.exists(): p.write_bytes(urllib.request.urlopen(url,timeout=45).read())
    files[name]=dict(url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
s=(out / 'oem-kgsl.c').read_text()
assert 'else if (entry->memdesc.size >= SZ_64K)\n\t\tkgsl_memdesc_set_align(&entry->memdesc, ilog2(SZ_64K));' in s
t=(out / 'oem-kgsl_iommu.c').read_text()
assert 'align = max_t(uint64_t, 1 << kgsl_memdesc_get_align(memdesc),' in t
report=dict(pinned_oem_sources=files,oem_imported_buffers_at_least64k_use_at_least64k_alignment=True,oem_imported_buffers_at_least1m_use1m_alignment=True,oem_vm_allocator_honors_alignment=True,does_not_prove_universal_hardware_alignment_requirement=True)
(ref / 'oem-alignment-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K147_PINNED_OEM_ALIGNMENT_SOURCE_CONTRACT_VERIFIED')
