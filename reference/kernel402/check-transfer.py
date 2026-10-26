from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;OLD=HERE.parent/'kernel388'
strip=lambda p:'\n'.join(l for l in p.read_text().splitlines() if not l.startswith('#include'))+'\n'
source=(P/'camss-icp-a5-boot.c.proposed').read_text()
def function(name):
 m=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert m,name;return m.group()
dma=(OLD/'dma-model-provider.h').read_text()+strip(OLD/'camss-icp-a5-dma.h')+strip(OLD/'camss-icp-a5-dma.c')
provider=(OLD/'transfer-model-provider.h').read_text().replace('bool initialized,cpu_enabled,','bool irq_enabled,config_fw_mapped;u32 watchdogs,protocol_errors;\n bool initialized,cpu_enabled,')
provider=provider.replace('a->command_queued=mode!=9;','a->command_queued=mode!=9;\n if(mode==13)return -EINVAL;\n if(mode==14){a->session_reply=true;return -EREMOTEIO;}')
provider=provider.replace('m->mapped=0;return 0;}','if(mode==17)return -EIO;m->mapped=0;return 0;}',1)
ipe=strip(P/'camss-icp-a5-colour.h.proposed')+strip(P/'camss-icp-a5-ipe.h.proposed')
provider=provider.replace('typedef uint8_t u8;', 'typedef uint8_t u8;')
dma=dma.replace('typedef uint8_t u8;', 'typedef uint16_t u16;typedef int16_t s16;typedef uint8_t u8;')
colour=strip(P/'camss-icp-a5-colour.c.proposed')
tests=(OLD/'transfer-model-cases.c').read_text();split=tests.index('int main(void)');encoder=tests[:split].replace('static int camss_a5_ipe_','int camss_a5_ipe_').replace('mode==5?-EINVAL:0','mode==5 || mode==17?-EINVAL:0');cases=tests[split:]
cases=cases.replace('scenario<=12','scenario<=17').replace('.initialized=true,.cpu_enabled=true,','.initialized=true,.cpu_enabled=true,.irq_enabled=true,')
cases=cases.replace('  int ret=camss_a5_ipe_run(&a,&session,&job);','''  if(scenario==15)a.irq_enabled=false;
  if(scenario==16)a.protocol_errors=1;
  enum camss_a5_ipe_result result=CAMSS_A5_IPE_COMPLETE;
  int ret=camss_a5_ipe_run_status(&a,&session,&job,&result);''')
cases=cases.replace('scenario==10?-EOVERFLOW:-EINVAL','scenario==10?-EOVERFLOW:scenario==14?-EREMOTEIO:scenario==15?-ENODEV:scenario==16?-EBUSY:-EINVAL')
cases=cases.replace('  assert(ret==expected && !gamma_live);','''  assert(ret==expected && !gamma_live);
  enum camss_a5_ipe_result wanted=scenario==0 || scenario==11?CAMSS_A5_IPE_COMPLETE:
   (scenario>=1 && scenario<=5) || scenario==12?CAMSS_A5_IPE_REJECTED:CAMSS_A5_IPE_RESET_REQUIRED;
  assert(result==wanted);''')
cases=cases.replace('scenario==6 || scenario==7 || scenario==8;','scenario==6 || scenario==7 || scenario==8 || scenario==13 || scenario==14;')
cases=cases.replace('  if(retained){','''  if(scenario==17){
   assert(result==CAMSS_A5_IPE_RESET_REQUIRED && !hw_frames && a.request.cpu && bo_live==1);
   /* Cleanup failed before any firmware MAP; classify conservatively. */
   mode=0;a.cpu_enabled=false;assert(!free_memory(&a));
  }else if(retained){''')
body='\n'.join(function(n) for n in ['nv12_layout_valid','camss_a5_backing_owned','free_imported_images','free_memory','free_transfer_memory','transfer_region_locked','transfer_alloc','transfer_released','run_colour_status','camss_a5_ipe_run_status','camss_a5_ipe_run_colour_status','camss_a5_ipe_run_colour_chain_status','camss_a5_ipe_run_gamma_status','camss_a5_ipe_run'])
cases=cases.replace(' for(unsigned scenario=0;scenario<=17;++scenario){',' for(unsigned colour_mode=0;colour_mode<4;++colour_mode)for(unsigned scenario=0;scenario<=17;++scenario){')
cases=cases.replace('  int ret=camss_a5_ipe_run_status(&a,&session,&job,&result);','''  use_colour=colour_mode;
  struct camss_a5_ipe_cc cc={.matrix={128,0,0,0,128,0,0,0,128}};
  struct camss_a5_ipe_colour chain={.modules=7,.cst={.maximum={1023,1023,1023}}};
  struct camss_a5_ipe_gamma gamma={0};for(unsigned bank=0;bank<3;bank++)for(unsigned i=0;i<256;i++){gamma.base[bank][i]=4*i;gamma.delta[bank][i]=4;}
  int ret=use_colour==3?camss_a5_ipe_run_gamma_status(&a,&session,&job,&chain,&gamma,&result):use_colour==2?camss_a5_ipe_run_colour_chain_status(&a,&session,&job,&chain,&result):use_colour?camss_a5_ipe_run_colour_status(&a,&session,&job,&cc,&result):camss_a5_ipe_run_status(&a,&session,&job,&result);''')
cases=cases.replace(' clean_provider();printf(',''' for(unsigned invalid=0;invalid<3;invalid++){
  clean_provider();mode=0;bo_allocations=bo_live=hw_frames=0;
  struct iommu_domain domain={true};struct device device={&domain};
  struct camss_a5 a={.dev=&device,.initialized=true,.cpu_enabled=true,.irq_enabled=true,.engine_dma_capable=true};active=&a;
  struct camss_a5_session session={.a5=&a,.handle=1,.configured=true};struct camss_a5_ipe_job job={0};
  struct camss_a5_ipe_cc cc={0};if(!invalid)cc.shift=4;else if(invalid==1)cc.matrix[4]=2048;else cc.offset[1]=-4097;
  enum camss_a5_ipe_result result=CAMSS_A5_IPE_COMPLETE;
  assert(camss_a5_ipe_run_colour_status(&a,&session,&job,&cc,&result)==(invalid?-ERANGE:-EINVAL));
  assert(result==CAMSS_A5_IPE_REJECTED && !bo_allocations && !hw_frames && !camss_a5_backing_owned(&a));cases++;
 }
 clean_provider();printf(''')
provider=provider.replace('static struct camss_a5 *active;','static struct camss_a5 *active;static unsigned use_colour;')
provider=provider.replace('(void)packet;(void)ack;assert(bytes==40', '''(void)packet;(void)ack;
 if(use_colour==1){
  u32 base,post;memcpy(&base,a->request.cpu+40,4);memcpy(&post,a->request.cpu+48,4);assert(base>=REQUEST_IOVA && post==32);
  u32 off=base-REQUEST_IOVA;assert(off+108<=a->request.bytes);u8 *arr=a->request.cpu+off;u32 v;
  memcpy(&v,arr+36,4);assert(v==1);memcpy(&v,arr+40,4);assert(v==base+64);
  memcpy(&v,arr+64,4);assert(v==0x03000009);memcpy(&v,arr+68,4);assert(v==0x5e68);
  memcpy(&v,arr-2592+2188,4);assert(v==1);
 }
 if(use_colour==2){
  u32 base,pre,post;memcpy(&base,a->request.cpu+40,4);memcpy(&pre,a->request.cpu+44,4);memcpy(&post,a->request.cpu+48,4);assert(base>=REQUEST_IOVA && pre==32 && post==64);
  u32 off=base-REQUEST_IOVA;assert(off+268<=a->request.bytes);u8 *arr=a->request.cpu+off;u32 v;
  memcpy(&v,arr+36,4);assert(v==1);memcpy(&v,arr+40,4);assert(v==base+128);
  memcpy(&v,arr+68,4);assert(v==2);memcpy(&v,arr+72,4);assert(v==base+184);memcpy(&v,arr+96,4);assert(v==base+228);
  memcpy(&v,arr+128,4);assert(v==0x0300000c);memcpy(&v,arr+132,4);assert(v==0x5a68);
  memcpy(&v,arr+184,4);assert(v==0x03000009);memcpy(&v,arr+188,4);assert(v==0x5e68);
  memcpy(&v,arr+228,4);assert(v==0x03000008);memcpy(&v,arr+232,4);assert(v==0x6468);
  memcpy(&v,arr-2592+2092,4);assert(v==1);memcpy(&v,arr-2592+2188,4);assert(v==1);memcpy(&v,arr-2592+2200,4);assert(v==1);
 }
 if(use_colour==3){
  u32 base,pre,post,v;memcpy(&base,a->request.cpu+40,4);memcpy(&pre,a->request.cpu+44,4);memcpy(&post,a->request.cpu+48,4);assert(base>=REQUEST_IOVA && pre==32 && post==64);
  u32 off=base-REQUEST_IOVA;assert(off+3424<=a->request.bytes);u8 *arr=a->request.cpu+off;
  memcpy(&v,arr+36,4);assert(v==1);memcpy(&v,arr+40,4);assert(v==base+160);memcpy(&v,arr+48,4);assert(v==20);
  memcpy(&v,arr+68,4);assert(v==3);memcpy(&v,arr+72,4);assert(v==base+216);memcpy(&v,arr+96,4);assert(v==base+260);memcpy(&v,arr+120,4);assert(v==base+304);memcpy(&v,arr+128,4);assert(v==12);
  memcpy(&v,arr+304,4);assert(v==0x010003ff);memcpy(&v,arr+308,4);assert(v==base+352);memcpy(&v,arr+312,4);assert(v==0x01006008);
  memcpy(&v,arr+352,4);assert(v==0x1000);memcpy(&v,arr+3420,4);assert(v==0x13fc);memcpy(&v,arr-2592+2192,4);assert(v==1);
 }
 assert(bytes==40''')
cases=cases.replace(' clean_provider();printf(',''' for(unsigned invalid=0;invalid<7;invalid++){
  clean_provider();mode=0;bo_allocations=bo_live=hw_frames=0;
  struct iommu_domain domain={true};struct device device={&domain};
  struct camss_a5 a={.dev=&device,.initialized=true,.cpu_enabled=true,.irq_enabled=true,.engine_dma_capable=true};active=&a;
  struct camss_a5_session session={.a5=&a,.handle=1,.configured=true};struct camss_a5_ipe_job job={0};
  struct camss_a5_ipe_colour chain={.modules=7,.cst={.maximum={1023,1023,1023}}};
  switch(invalid){case 0:chain.modules=8;break;case 1:chain.cst.matrix[4]=4096;break;case 2:chain.cst.minimum[0]=1024;break;case 3:chain.cst.minimum[0]=1;chain.cst.maximum[0]=0;break;case 4:chain.cv.y_offset=1024;break;case 5:chain.cv.chroma[7]=-2049;break;case 6:chain.cc.offset[0]=-1025;break;}
  enum camss_a5_ipe_result result=CAMSS_A5_IPE_COMPLETE;
  assert(camss_a5_ipe_run_colour_chain_status(&a,&session,&job,&chain,&result)==(invalid?-ERANGE:-EINVAL));
  assert(result==CAMSS_A5_IPE_REJECTED && !bo_allocations && !hw_frames && !camss_a5_backing_owned(&a));cases++;
 }
 clean_provider();printf(''')
provider+='''
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
code=dma+provider+ipe+encoder+colour+body+cases
model=P/'transfer-model.c';model.write_text(code)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-no-pie',str(model),'-o',str(P/'transfer-model')],capture_output=True)
(P/'transfer-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-5000:]
q=subprocess.run([str(P/'transfer-model')],capture_output=True);(P/'transfer-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-5000:]
match=re.fullmatch(r'TRANSFER_MODEL cases=(\d+) passed=1\n',q.stdout.decode());assert match
r=dict(stage=402,actual_core_and_dma_functions=True,asan_ubsan=True,cases=int(match[1]),same_errno_preflight_and_submitted_failures_distinguished=True,preflight_fence_timeout_local=True,failed_cleanup_not_local=True,missing_irq_or_protocol_error_not_local=True,unknown_map_frame_unmap_refs_retained=True,old_pointer_fixture_and_mixed_rejection_kept=True,hardware_error_concurrency_not_claimed=True,legacy_cc_conversion_and_gamma_transfer_paths=True,gamma_cpu_copy_precedes_coherent_allocation=True,gamma_caller_mutation_after_copy_does_not_change_wire=True,gamma_cpu_copy_freed_even_when_dma_request_retained=True,conversion_region_same_retained_request_parcel=True,invalid_conversion_rejected_before_allocation=True,colour_region_same_retained_request_parcel=True,invalid_colour_rejected_before_allocation=True,passed=True)
(HERE/'transfer-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
