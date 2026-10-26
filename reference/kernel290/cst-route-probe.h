/* SPDX-License-Identifier: GPL-2.0-only */
/* Fixed development experiment: no arbitrary register arguments or sensor tuning. */
#define RESPONSE_PHASES 15
static uint32_t response_saved[12],response_full_saved[2],response_frame_saved;
static bool response_saved_valid;
static void response_mask(unsigned reg,uint32_t mask,uint32_t value)
{
 mmio_write(gamma_base,reg,(mmio_read(gamma_base,reg)&~mask)|(value&mask));
}
static void response_set(unsigned phase)
{
 static const unsigned values[4]={128,256,512,1023};
 if(!response_saved_valid){
  for(unsigned i=0;i<12;i++)response_saved[i]=mmio_read(gamma_base,0xf30+i*4);
  response_full_saved[0]=mmio_read(gamma_base,0xe18);response_full_saved[1]=mmio_read(gamma_base,0xe38);response_frame_saved=mmio_read(gamma_base,0x4c);response_saved_valid=true;
 }
 for(unsigned i=0;i<12;i++)mmio_write(gamma_base,0xf30+i*4,response_saved[i]);
 mmio_write(gamma_base,0xe18,response_full_saved[0]);mmio_write(gamma_base,0xe38,response_full_saved[1]);
 const char *kind="original";unsigned value=0;
 if(phase>=1&&phase<=11){
  for(unsigned row=0;row<3;row++){
   response_mask(0xf30+16*row,0x1fff1fffu,0);response_mask(0xf34+16*row,0x1fffu,0);
   response_mask(0xf38+16*row,0x07ff07ffu,0);response_mask(0xf3c+16*row,0x03ff03ffu,1023u<<16);
  }
 }
 if(phase>=1&&phase<=8){
  bool high=phase<=4;value=values[(phase-1)%4];kind=high?"cst_offset_high":"cst_offset_low";
  for(unsigned row=0;row<3;row++)response_mask(0xf38+16*row,0x07ff07ffu,high?value<<16:value);
 }else if(phase>=9&&phase<=11){
  value=phase==9?512:phase==10?128:256;kind="cst_clamp_constant";
  for(unsigned row=0;row<3;row++)response_mask(0xf3c+16*row,0x03ff03ffu,(value<<16)|value);
 }else if(phase>=12){
  value=phase==12?128:phase==13?64:0;kind="full_clamp_constant";
  response_mask(0xe18,0x3ff003ffu,(value<<20)|value);response_mask(0xe38,0x3ff003ffu,(value<<20)|value);
 }
 mmio_write(gamma_base,0x4c,response_frame_saved|16u);
 mmio_write(gamma_base,0x4ac,1);
 printf("RESPONSE_CONFIG phase=%u kind=%s value=%u cst_offset=%08x cst_clamp=%08x full_y=%08x full_c=%08x\n",phase,kind,value,mmio_read(gamma_base,0xf38),mmio_read(gamma_base,0xf3c),mmio_read(gamma_base,0xe18),mmio_read(gamma_base,0xe38));fflush(stdout);
}
static void response_measure(unsigned phase,const unsigned char *data,unsigned stride)
{
 uint64_t sum[3]={0};unsigned minimum[3]={255,255,255},maximum[3]={0};
 for(unsigned y=0;y<360;y++)for(unsigned x=0;x<320;x++){
  unsigned ch=y<240?0:1+(x&1),value=data[(size_t)y*stride+x];
  sum[ch]+=value;if(value<minimum[ch])minimum[ch]=value;if(value>maximum[ch])maximum[ch]=value;
 }
 printf("RESPONSE_MEASURE phase=%u y_sum=%" PRIu64 " y_min=%u y_max=%u u_sum=%" PRIu64 " u_min=%u u_max=%u v_sum=%" PRIu64 " v_min=%u v_max=%u\n",phase,sum[0],minimum[0],maximum[0],sum[1],minimum[1],maximum[1],sum[2],minimum[2],maximum[2]);fflush(stdout);
}
static void response_restore(void)
{
 if(!response_saved_valid||!gamma_base)return;
 for(unsigned i=0;i<12;i++)mmio_write(gamma_base,0xf30+i*4,response_saved[i]);
 mmio_write(gamma_base,0xe18,response_full_saved[0]);mmio_write(gamma_base,0xe38,response_full_saved[1]);mmio_write(gamma_base,0x4c,response_frame_saved);mmio_write(gamma_base,0x4ac,1);
 bool equal=mmio_read(gamma_base,0x4c)==response_frame_saved&&mmio_read(gamma_base,0xe18)==response_full_saved[0]&&mmio_read(gamma_base,0xe38)==response_full_saved[1];
 for(unsigned i=0;i<12;i++)equal&=mmio_read(gamma_base,0xf30+i*4)==response_saved[i];
 printf("RESPONSE_RESTORE registers=%d\n",equal);response_saved_valid=false;
}
