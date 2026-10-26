"""Extend the actual transfer lifetime model to the typed conversion chain."""
from pathlib import Path
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel397/check-transfer.py').read_text().replace('stage=397','stage=399')
s=s.replace('typedef int16_t s16;typedef uint8_t u8;','typedef uint16_t u16;typedef int16_t s16;typedef uint8_t u8;')
s=s.replace("'camss_a5_ipe_run_colour_status','camss_a5_ipe_run'","'camss_a5_ipe_run_colour_status','camss_a5_ipe_run_colour_chain_status','camss_a5_ipe_run'")
s=s.replace('colour_mode<2','colour_mode<3')
s=s.replace('static bool use_colour;','static unsigned use_colour;')
s=s.replace(' if(use_colour){',' if(use_colour==1){')
s=s.replace('  int ret=use_colour?camss_a5_ipe_run_colour_status(&a,&session,&job,&cc,&result):camss_a5_ipe_run_status(&a,&session,&job,&result);','''  struct camss_a5_ipe_colour chain={.modules=7,.cst={.maximum={1023,1023,1023}}};
  int ret=use_colour==2?camss_a5_ipe_run_colour_chain_status(&a,&session,&job,&chain,&result):use_colour?camss_a5_ipe_run_colour_status(&a,&session,&job,&cc,&result):camss_a5_ipe_run_status(&a,&session,&job,&result);''')
s=s.replace(' assert(bytes==40', ''' if(use_colour==2){
  u32 base,pre,post;memcpy(&base,a->request.cpu+40,4);memcpy(&pre,a->request.cpu+44,4);memcpy(&post,a->request.cpu+48,4);assert(base>=REQUEST_IOVA && pre==32 && post==64);
  u32 off=base-REQUEST_IOVA;assert(off+268<=a->request.bytes);u8 *arr=a->request.cpu+off;u32 v;
  memcpy(&v,arr+36,4);assert(v==1);memcpy(&v,arr+40,4);assert(v==base+128);
  memcpy(&v,arr+68,4);assert(v==2);memcpy(&v,arr+72,4);assert(v==base+184);memcpy(&v,arr+96,4);assert(v==base+228);
  memcpy(&v,arr+128,4);assert(v==0x0300000c);memcpy(&v,arr+132,4);assert(v==0x5a68);
  memcpy(&v,arr+184,4);assert(v==0x03000009);memcpy(&v,arr+188,4);assert(v==0x5e68);
  memcpy(&v,arr+228,4);assert(v==0x03000008);memcpy(&v,arr+232,4);assert(v==0x6468);
  memcpy(&v,arr-2592+2092,4);assert(v==1);memcpy(&v,arr-2592+2188,4);assert(v==1);memcpy(&v,arr-2592+2200,4);assert(v==1);
 }
 assert(bytes==40''')
# This replacement runs while generating C, after the earlier three rejection
# cases have already been appended. Their original evidence is retained.
needle="code=dma+provider+ipe+encoder+colour+body+cases"
s=s.replace(needle,"""cases=cases.replace(' clean_provider();printf(',''' for(unsigned invalid=0;invalid<7;invalid++){
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
code=dma+provider+ipe+encoder+colour+body+cases""")
s=s.replace('legacy_and_colour_transfer_paths=True','legacy_cc_and_conversion_transfer_paths=True,conversion_region_same_retained_request_parcel=True,invalid_conversion_rejected_before_allocation=True')
(HERE/'check-transfer.py').write_text(s)
print('Prepared lifetime tests for legacy, standalone CC and conversion chain APIs.')
