"""Exercise current request ownership, including LTM/Gamma copy failures."""
from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
old=(P.parent/'kernel402/transfer-model.c').read_text();source=(P/'camss-icp-a5-boot.c.proposed').read_text()
strip=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
def function(name):
 match=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert match,name;return match[0]
provider=old[:old.index('#ifndef CAMSS_A5_IPE_COLOUR_H')]
provider=provider.replace('typedef uint8_t u8;', 'typedef int32_t s32;typedef uint8_t u8;')
provider+='#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))\n'
provider=provider.replace('if(use_colour==3){','if(use_colour==3 || use_colour==6){')
needle=' assert(bytes==40';assert needle in provider
provider=provider.replace(needle,r'''
 if(use_colour==4 || use_colour==5){
  u32 base,pre,post,v;memcpy(&base,a->request.cpu+40,4);memcpy(&pre,a->request.cpu+44,4);memcpy(&post,a->request.cpu+48,4);assert(base>=REQUEST_IOVA && pre==32 && post==96);
  u32 off=base-REQUEST_IOVA;assert(off+6352<=a->request.bytes);u8 *arr=a->request.cpu+off;
  memcpy(&v,arr+36,4);assert(v==2);memcpy(&v,arr+40,4);assert(v==base+192);memcpy(&v,arr+64,4);assert(v==base+3456);memcpy(&v,arr+72,4);assert(v==11);
  memcpy(&v,arr+100,4);assert(v==(use_colour==5?3u:2u));memcpy(&v,arr+104,4);assert(v==base+248);memcpy(&v,arr+128,4);assert(v==base+292);
  memcpy(&v,arr+3456,4);assert(v==0x0100002f);memcpy(&v,arr+3460,4);assert(v==base+3616);memcpy(&v,arr+3464,4);assert(v==0x01005c08);
  memcpy(&v,arr+3616,4);assert(v==0xabcd);memcpy(&v,arr+3616+304+252,4);assert(v==0xffffff);memcpy(&v,arr+3616+2480+252,4);assert(v==0xfffffff);
  memcpy(&v,arr-2592+2096,4);assert(v==1);memcpy(&v,arr-2592+2108,4);assert(v==1);memcpy(&v,arr-2592+2180,4);assert(v==1);memcpy(&v,arr-2592+2184,4);assert(v==1);
  if(use_colour==5){memcpy(&v,arr+152,4);assert(v==base+336);memcpy(&v,arr+160,4);assert(v==12);memcpy(&v,arr+336,4);assert(v==0x010003ff);}
 }
'''+needle,1)
start=provider.index('static void *kmemdup(');end=provider.index('\n',provider.index('static void kfree(',start))
provider=provider[:start]+r'''
static unsigned ltm_live,ltm_allocations;static bool fail_ltm_alloc;static void *ltm_storage;
static void *kmemdup(const void *p,size_t bytes,unsigned flags){(void)flags;assert(!bo_allocations);
 if(bytes==3072){assert(!gamma_live);++gamma_allocations;if(fail_gamma_alloc)return NULL;gamma_storage=malloc(bytes);assert(gamma_storage);memcpy(gamma_storage,p,bytes);memset((void*)p,0xff,bytes);gamma_live=1;return gamma_storage;}
 assert(bytes==2800 && !ltm_live);++ltm_allocations;if(fail_ltm_alloc)return NULL;ltm_storage=malloc(bytes);assert(ltm_storage);memcpy(ltm_storage,p,bytes);memset((void*)p,0xff,bytes);ltm_live=1;return ltm_storage;}
static void kfree(void *p){if(!p)return;if(p==ltm_storage){assert(ltm_live);free(p);ltm_storage=NULL;ltm_live=0;}else{assert(gamma_live && p==gamma_storage);free(p);gamma_live=0;gamma_storage=NULL;}}
'''+provider[end:]
headers=strip((P/'camss-icp-a5-colour.h.proposed').read_text())+strip((P/'camss-icp-a5-ipe.h.proposed').read_text())
a=old.index('int camss_a5_ipe_bypass_size(const struct camss_a5_ipe_io *io,u32 cores,u32 *bytes)');b=old.index('// SPDX-License-Identifier:',a);encoders=old[a:b]
encoders+='''int camss_a5_ipe_ltm_size(const struct camss_a5_ipe_io *io,u32 cores,const struct camss_a5_ipe_ltm_geometry *g,u32 *bytes){assert(g && g->data_collection && g->image_processing && g->mask_filter && !bo_allocations);return camss_a5_ipe_bypass_size(io,cores,bytes);}
int camss_a5_ipe_encode_ltm_striping(void *p,u32 cap,const struct camss_a5_ipe_io *io,u32 cores,const struct camss_a5_ipe_ltm_geometry *g,u32 *used){assert(g && g->data_collection && g->image_processing && g->mask_filter);return camss_a5_ipe_encode_bypass_striping(p,cap,io,cores,used);}
'''
body='\n'.join(function(n) for n in ['nv12_layout_valid','camss_a5_backing_owned','free_imported_images','free_memory','free_transfer_memory','transfer_region_locked','transfer_alloc','transfer_released','run_colour_status','camss_a5_ipe_run_status','camss_a5_ipe_run_colour_status','camss_a5_ipe_run_colour_chain_status','camss_a5_ipe_run_gamma_status','camss_a5_ipe_run_ltm_status','camss_a5_ipe_run'])
cases=old[old.index('int main(void)'):].replace('colour_mode<4','colour_mode<7')
needle='  int ret=use_colour==3?';assert needle in cases
cases=cases.replace(needle,'''  struct camss_a5_ipe_ltm ltm={.iq={.reverse_gamma=1,.local_adaptation=1,.mask_filter=1,.data_collection=1,.image_processing=1},.weight={0xabcd}};
  ltm.la[1][63]=(struct camss_a5_ipe_ltm_unsigned){4095,-1};ltm.reverse_gamma[4][63]=(struct camss_a5_ipe_ltm_unsigned){16383,-1};
  int ret=use_colour>=4?camss_a5_ipe_run_ltm_status(&a,&session,&job,&chain,use_colour>=5?&gamma:NULL,use_colour==6?NULL:&ltm,&result):use_colour==3?''',1)
cases=cases.replace('  assert(ret==expected);','''  assert(ret==expected && !gamma_live && !ltm_live);
  enum camss_a5_ipe_result wanted=scenario==0 || scenario==11?CAMSS_A5_IPE_COMPLETE:
   ((scenario>=1 && scenario<=5) || scenario==12)?CAMSS_A5_IPE_REJECTED:CAMSS_A5_IPE_RESET_REQUIRED;
  assert(result==wanted);''',1)
needle=' clean_provider();printf(';assert needle in cases
cases=cases.replace(needle,r'''
 for(unsigned invalid=0;invalid<6;invalid++){
  clean_provider();mode=0;bo_allocations=bo_live=hw_frames=gamma_allocations=ltm_allocations=0;fail_ltm_alloc=invalid>=4;
  struct iommu_domain domain={true};struct device device={&domain};struct camss_a5 a={.dev=&device,.initialized=true,.cpu_enabled=true,.irq_enabled=true,.engine_dma_capable=true};active=&a;
  struct camss_a5_session session={.a5=&a,.handle=1,.configured=true};struct camss_a5_ipe_job job={0};struct camss_a5_ipe_ltm ltm={0};struct camss_a5_ipe_gamma gamma={0};
  if(!invalid)ltm.iq.mask_filter=2;else if(invalid==1)ltm.iq.rgb2y[3]=128;else if(invalid==2)ltm.scale[63].base=2048;else if(invalid==3)ltm.reverse_gamma[4][63].delta=-8193;
  enum camss_a5_ipe_result result=CAMSS_A5_IPE_COMPLETE;
  assert(camss_a5_ipe_run_ltm_status(&a,&session,&job,NULL,invalid==5?&gamma:NULL,&ltm,&result)==(invalid>=4?-ENOMEM:-ERANGE));
  assert(result==CAMSS_A5_IPE_REJECTED && !bo_allocations && !hw_frames && !ltm_live && !gamma_live && ltm_allocations==1 && gamma_allocations==(invalid==5) && !camss_a5_backing_owned(&a));cases++;fail_ltm_alloc=false;
 }
'''+needle,1)
code=provider+headers+encoders+strip((P/'camss-icp-a5-colour.c.proposed').read_text())+body+cases
(P/'transfer-model.c').write_text(code)
q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-no-pie',str(P/'transfer-model.c'),'-o',str(P/'transfer-model')],capture_output=True);(P/'transfer-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-6000:]
q=subprocess.run([str(P/'transfer-model')],capture_output=True);(P/'transfer-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-5000:]
match=re.fullmatch(r'TRANSFER_MODEL cases=(\d+) passed=1\n',q.stdout.decode());assert match
report=dict(stage=405,cases=int(match[1]),host_asan_ubsan=True,actual_current_core_dma_and_colour_functions=True,ltm_geometry_provider_checks_copied_flags=True,geometry_math_separately_verified404=True,existing_paths_and_null_ltm_fallback=True,ltm_and_gamma_mutated_caller_after_copy=True,copies_precede_coherent_allocation_and_map=True,cpu_copies_freed_on_all_exits=True,unknown_map_frame_unmap_retains_request_and_image_refs=True,retained_request_contains_ltm_iq_dmi_luts=True,pre32_post96_max2and3=True,local_failure_vs_reset_required_checked=True,ltm_and_second_copy_alloc_failures_checked=True,hardware_concurrency_or_fault_recovery_not_claimed=True,phone_accessed=False,passed=True)
(HERE/'transfer-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
