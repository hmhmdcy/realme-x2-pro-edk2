"""Adapt the actual transfer harness to both legacy and typed-colour entry points."""
from pathlib import Path
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=(HERE.parent/'kernel393/check-transfer.py').read_text().replace('stage=393','stage=397')
s=s.replace("ipe=strip(P/'camss-icp-a5-ipe.h.proposed')", "ipe=strip(P/'camss-icp-a5-colour.h.proposed')+strip(P/'camss-icp-a5-ipe.h.proposed')\nprovider=provider.replace('typedef uint8_t u8;', 'typedef uint8_t u8;')\ndma=dma.replace('typedef uint8_t u8;', 'typedef int16_t s16;typedef uint8_t u8;')\ncolour=strip(P/'camss-icp-a5-colour.c.proposed')")
s=s.replace("'camss_a5_ipe_run_status','camss_a5_ipe_run'", "'run_colour_status','camss_a5_ipe_run_status','camss_a5_ipe_run_colour_status','camss_a5_ipe_run'")
s=s.replace("code=dma+provider+ipe+encoder+body+cases", """cases=cases.replace(' for(unsigned scenario=0;scenario<=17;++scenario){',' for(unsigned colour_mode=0;colour_mode<2;++colour_mode)for(unsigned scenario=0;scenario<=17;++scenario){')
cases=cases.replace('  int ret=camss_a5_ipe_run_status(&a,&session,&job,&result);','''  use_colour=colour_mode;
  struct camss_a5_ipe_cc cc={.matrix={128,0,0,0,128,0,0,0,128}};
  int ret=use_colour?camss_a5_ipe_run_colour_status(&a,&session,&job,&cc,&result):camss_a5_ipe_run_status(&a,&session,&job,&result);''')
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
provider=provider.replace('static struct camss_a5 *active;','static struct camss_a5 *active;static bool use_colour;')
provider=provider.replace('(void)packet;(void)ack;assert(bytes==40', '''(void)packet;(void)ack;
 if(use_colour){
  u32 base,post;memcpy(&base,a->request.cpu+40,4);memcpy(&post,a->request.cpu+48,4);assert(base>=REQUEST_IOVA && post==32);
  u32 off=base-REQUEST_IOVA;assert(off+108<=a->request.bytes);u8 *arr=a->request.cpu+off;u32 v;
  memcpy(&v,arr+36,4);assert(v==1);memcpy(&v,arr+40,4);assert(v==base+64);
  memcpy(&v,arr+64,4);assert(v==0x03000009);memcpy(&v,arr+68,4);assert(v==0x5e68);
  memcpy(&v,arr-2592+2188,4);assert(v==1);
 }
 assert(bytes==40''')
code=dma+provider+ipe+encoder+colour+body+cases""")
s=s.replace("hardware_error_concurrency_not_claimed=True,passed=True", "hardware_error_concurrency_not_claimed=True,legacy_and_colour_transfer_paths=True,colour_region_same_retained_request_parcel=True,invalid_colour_rejected_before_allocation=True,passed=True")
(HERE/'check-transfer.py').write_text(s)
print('Prepared actual transfer ownership checks for legacy and colour calls.')
