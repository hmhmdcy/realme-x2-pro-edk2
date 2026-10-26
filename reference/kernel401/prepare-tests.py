"""Extend actual lifetime tests to copied typed Gamma and the larger IQ page."""
from pathlib import Path
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel399/check-transfer.py').read_text().replace('stage=399','stage=401').replace('colour_mode<3','colour_mode<4')
s=s.replace("'camss_a5_ipe_run_colour_chain_status','camss_a5_ipe_run'","'camss_a5_ipe_run_colour_chain_status','camss_a5_ipe_run_gamma_status','camss_a5_ipe_run'")
s=s.replace('  int ret=use_colour==2?camss_a5_ipe_run_colour_chain_status', '''  struct camss_a5_ipe_gamma gamma={0};for(unsigned bank=0;bank<3;bank++)for(unsigned i=0;i<256;i++){gamma.base[bank][i]=4*i;gamma.delta[bank][i]=4;}
  int ret=use_colour==3?camss_a5_ipe_run_gamma_status(&a,&session,&job,&chain,&gamma,&result):use_colour==2?camss_a5_ipe_run_colour_chain_status''')
s=s.replace('  assert(ret==expected);','  assert(ret==expected && !gamma_live);')
s=s.replace(' assert(bytes==40', ''' if(use_colour==3){
  u32 base,pre,post,v;memcpy(&base,a->request.cpu+40,4);memcpy(&pre,a->request.cpu+44,4);memcpy(&post,a->request.cpu+48,4);assert(base>=REQUEST_IOVA && pre==32 && post==64);
  u32 off=base-REQUEST_IOVA;assert(off+3424<=a->request.bytes);u8 *arr=a->request.cpu+off;
  memcpy(&v,arr+36,4);assert(v==1);memcpy(&v,arr+40,4);assert(v==base+160);memcpy(&v,arr+48,4);assert(v==20);
  memcpy(&v,arr+68,4);assert(v==3);memcpy(&v,arr+72,4);assert(v==base+216);memcpy(&v,arr+96,4);assert(v==base+260);memcpy(&v,arr+120,4);assert(v==base+304);memcpy(&v,arr+128,4);assert(v==12);
  memcpy(&v,arr+304,4);assert(v==0x0a0003ff);memcpy(&v,arr+308,4);assert(v==base+352);memcpy(&v,arr+312,4);assert(v==0x01006008);
  memcpy(&v,arr+352,4);assert(v==0x1000);memcpy(&v,arr+3420,4);assert(v==0x13fc);memcpy(&v,arr-2592+2192,4);assert(v==1);
 }
 assert(bytes==40''')
needle='code=dma+provider+ipe+encoder+colour+body+cases'
s=s.replace(needle,"""provider+='''
static unsigned gamma_allocations,gamma_live;static bool fail_gamma_alloc;static void *gamma_storage;
static void *kmemdup(const void *p,size_t bytes,unsigned flags){(void)flags;assert(bytes==3072 && !gamma_live && !bo_allocations);++gamma_allocations;if(fail_gamma_alloc)return NULL;gamma_storage=malloc(bytes);assert(gamma_storage);memcpy(gamma_storage,p,bytes);memset((void*)p,0xff,bytes);gamma_live=1;return gamma_storage;}
static void kfree(void *p){if(!p)return;assert(gamma_live && p==gamma_storage);free(p);gamma_live=0;gamma_storage=NULL;}
'''
cases=cases.replace(' clean_provider();printf(',''' for(unsigned invalid=0;invalid<3;invalid++){
 clean_provider();mode=0;bo_allocations=bo_live=hw_frames=gamma_allocations=0;fail_gamma_alloc=invalid==2;
 struct iommu_domain domain={true};struct device device={&domain};struct camss_a5 a={.dev=&device,.initialized=true,.cpu_enabled=true,.irq_enabled=true,.engine_dma_capable=true};active=&a;
 struct camss_a5_session session={.a5=&a,.handle=1,.configured=true};struct camss_a5_ipe_job job={0};struct camss_a5_ipe_gamma gamma={0};
 if(!invalid)gamma.base[1][255]=1024;else if(invalid==1)gamma.delta[2][0]=-513;
 enum camss_a5_ipe_result result=CAMSS_A5_IPE_COMPLETE;
 assert(camss_a5_ipe_run_gamma_status(&a,&session,&job,NULL,&gamma,&result)==(invalid==2?-ENOMEM:-ERANGE));
 assert(result==CAMSS_A5_IPE_REJECTED && !bo_allocations && !hw_frames && !gamma_live && gamma_allocations==1 && !camss_a5_backing_owned(&a));cases++;fail_gamma_alloc=false;
 }
 clean_provider();printf(''')
code=dma+provider+ipe+encoder+colour+body+cases""")
s=s.replace('legacy_cc_and_conversion_transfer_paths=True','legacy_cc_conversion_and_gamma_transfer_paths=True,gamma_cpu_copy_precedes_coherent_allocation=True,gamma_caller_mutation_after_copy_does_not_change_wire=True,gamma_cpu_copy_freed_even_when_dma_request_retained=True')
(HERE/'check-transfer.py').write_text(s)
print('Prepared actual Gamma lifetime/CPU-copy/DMA-retention checks.')
