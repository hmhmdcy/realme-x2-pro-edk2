from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel354/memory-test.c').read_text()
s=s.replace('#define IOMMU_CACHE 4', '#define IOMMU_CACHE 4\n#define IOMMU_PRIV 8')
s=s.replace('static bool absent_region,fail_alloc;', 'static bool absent_region,fail_alloc,expected_privileged;')
s=s.replace('absent_region=fail_alloc=false;', 'absent_region=fail_alloc=false;expected_privileged=true;')
s=s.replace('IOMMU_READ|IOMMU_WRITE|(device.coherent?IOMMU_CACHE:0)', 'IOMMU_READ|IOMMU_WRITE|(device.coherent?IOMMU_CACHE:0)|(expected_privileged?IOMMU_PRIV:0)')
s=s.replace('static dma_addr_t dma_address;', 'static dma_addr_t dma_address;static u32 alias_base,expected_bytes;')
s=s.replace('dma_address=0x20000000;', 'dma_address=0x20000000;alias_base=0;expected_bytes=CAMSS_A5_FW_WINDOW;')
s=s.replace('assert(bytes==CAMSS_A5_FW_WINDOW)', 'assert(bytes==expected_bytes)')
s=s.replace('bytes==CAMSS_A5_FW_WINDOW&&dma==dma_address', 'bytes==expected_bytes&&dma==dma_address')
s=s.replace('if(iova<CAMSS_A5_FW_WINDOW)return alias[iova/PAGE_SIZE]+(alias[iova/PAGE_SIZE]?iova%PAGE_SIZE:0);', 'if(iova>=alias_base&&iova-alias_base<expected_bytes){unsigned int i=(iova-alias_base)/PAGE_SIZE;return alias[i]+(alias[i]?iova%PAGE_SIZE:0);}')
s=s.replace('iova-dma_address<CAMSS_A5_FW_WINDOW', 'iova-dma_address<expected_bytes')
s=s.replace('iova<CAMSS_A5_FW_WINDOW&&iova%PAGE_SIZE==0', 'iova>=alias_base&&iova-alias_base<expected_bytes&&iova%PAGE_SIZE==0')
s=s.replace('unsigned int i=iova/PAGE_SIZE;', 'unsigned int i=(iova-alias_base)/PAGE_SIZE;')
helpers=r'''
#define MEMREMAP_WC 1
static void *memremap(phys_addr_t physical,size_t bytes,unsigned flags) {
 assert(physical==0x9ab00000&&bytes==CAMSS_A5_FW_WINDOW&&flags==MEMREMAP_WC);allocs++;
 if(fail_alloc){return NULL;}
 void *cpu=malloc(bytes);assert(cpu);memset(cpu,0xa5,bytes);return cpu;
}
static void memunmap(void *cpu) {
 for(unsigned i=0;i<PAGES;i++)assert(!alias[i]||alias[i]==0xdead0000);
 frees++;free(cpu);
}
'''
s=s.replace('#include "actual-memory-private.c"',helpers+'\n#include "actual-memory-private.c"')
extra=r'''
 const u32 bases[]={0x07400000,0x10a00000,0xfff00000};
 const u32 sizes[]={0x1e000,0x100000,0x100000};
 for(unsigned int k=0;k<3;k++)for(unsigned int failure=0;failure<3;failure++) {
  reset();m=(struct camss_a5_fw_memory){};expected_privileged=false;alias_base=bases[k];expected_bytes=sizes[k];region.start=alias_base;region.length=expected_bytes;
  assert(!camss_a5_iova_memory_alloc(&device,&m,alias_base,expected_bytes));assert(m.iova==alias_base&&m.bytes==expected_bytes&&!m.privileged);
  if(failure==1)fail_map=expected_bytes/PAGE_SIZE/2;
  if(failure==2)alias[expected_bytes/PAGE_SIZE-1]=0xdead0000;
  int r=camss_a5_fw_memory_map(&m);
  assert(r==(failure==1?-ENOMEM:failure==2?-EBUSY:0));
  if(!failure)assert(m.mapped==expected_bytes);
  released(&m);
 }
 const u32 invalid_base[]={1,0,0xfffff000};const u32 invalid_size[]={PAGE_SIZE,1,PAGE_SIZE*2};
 for(unsigned int k=0;k<3;k++) {
  reset();m=(struct camss_a5_fw_memory){};
  assert(camss_a5_iova_memory_alloc(&device,&m,invalid_base[k],invalid_size[k])==-EINVAL&&!allocs);
 }
 reset();m=(struct camss_a5_fw_memory){};assert(camss_a5_iova_memory_alloc(&device,&m,0x7400000,PAGE_SIZE)==-EINVAL&&!allocs);
 reset();m=(struct camss_a5_fw_memory){};alias_base=0x7400000;expected_bytes=PAGE_SIZE*2;region.start=alias_base;region.length=expected_bytes;dma_address=alias_base-PAGE_SIZE;
 assert(camss_a5_iova_memory_alloc(&device,&m,alias_base,expected_bytes)==-ERANGE&&!m.cpu&&frees==1);
 for(unsigned kind=0;kind<4;kind++) {
  reset();m=(struct camss_a5_fw_memory){};for(unsigned i=0;i<PAGES;i++)pages[i]=0x9ab00000ULL+(u64)i*PAGE_SIZE;
  assert(!camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW));assert(m.carveout&&m.privileged&&m.physical==0x9ab00000);
  if(kind==1){fail_map=PAGES/2;}
  if(kind==3){alias[PAGES-1]=0xdead0000;}
  int ret=camss_a5_fw_memory_map(&m);assert(ret==(kind==1?-ENOMEM:kind==3?-EBUSY:0));
  if(kind==2){fail_unmap=PAGES/2;assert(camss_a5_fw_memory_unmap(&m)==-EIO&&m.mapped&&m.cpu&&!frees);assert(camss_a5_fw_memory_free(&m)==-EBUSY);fail_unmap=-1;}
  released(&m);
 }
 const u64 bad_physical[]={0,0x9ab00001,0xfffffffffffff000ULL};
 for(unsigned k=0;k<3;k++){reset();m=(struct camss_a5_fw_memory){};assert(camss_a5_fw_carveout_alloc(&device,&m,bad_physical[k],CAMSS_A5_FW_WINDOW)==-EINVAL&&!allocs);}
 reset();m=(struct camss_a5_fw_memory){};assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,PAGE_SIZE)==-EINVAL&&!allocs);
 reset();m=(struct camss_a5_fw_memory){};absent_region=true;assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW)==-EINVAL&&!allocs);
 reset();m=(struct camss_a5_fw_memory){};fail_alloc=true;assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW)==-ENOMEM&&allocs==1&&!frees);
 reset();m=(struct camss_a5_fw_memory){};device.domain=NULL;assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW)==-ENODEV&&!allocs);
 reset();m=(struct camss_a5_fw_memory){.bytes=PAGE_SIZE};assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW)==-EBUSY&&!allocs);
'''
s=s.replace('\tprintf("MEMORY_PASS',extra+'\n\tprintf("MEMORY_PASS')
(HERE/'memory-test.c').write_text(s)
s=(HERE.parent/'kernel354/check-memory.py').read_text().replace('icp354-tests','icp356-tests').replace('camss354-memory','camss356-memory').replace('stage=354','stage=356')
s=s.replace('actual_memory_backend_compiled=True,','actual_memory_backend_compiled=True,carveout_map_unmap_and_error_preserves_backing_tested=True,firmware_privileged_and_shared_heap_unprivileged_verified=True,nonzero_shared_heap_and_32bit_end_aliases_tested=True,')
(HERE/'check-memory.py').write_text(s)
print('Prepared generalized alias tests including the previous firmware cases.')
