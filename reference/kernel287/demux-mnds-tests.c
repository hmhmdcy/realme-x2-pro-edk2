/* Host-only boundary, packing and mathematical invariant tests. */
static void test_demux(struct vfe_device *v)
{
 struct vfe_175_demux_config base={.gr_gain=100,.gb_gain=200,.r_gain=300,.b_gain=400,.enabled=true},c,sentinel;
 for(unsigned int member=0;member<4;member++)for(unsigned int n=0;n<=65535;n++) {
  c=base;if(member==0)c.gr_gain=n;if(member==1)c.gb_gain=n;if(member==2)c.r_gain=n;if(member==3)c.b_gain=n;
  reset_trace();int r=vfe_175_demux_configure(v,&c);
  if(n>32767)assert(r==-EINVAL && !reads && !writes && !barriers);
  else {
   assert(!r && writes==8 && barriers==1);
   unsigned int val=get(member<2?0x564:0x568);
   if(member==1 || member==2)val>>=16;
   assert((val&32767)==n);
   assert(get(0x564)==get(0x56c) && get(0x568)==get(0x570));
  }
 }
 for(unsigned int member=0;member<2;member++)for(unsigned int n=0;n<=65535;n++) {
  c=base;if(member)c.black_out=n;else c.black_in=n;reset_trace();int r=vfe_175_demux_configure(v,&c);
  if(n>4095)assert(r==-EINVAL && !reads && !writes);
  else assert(!r && ((get(0x560)>>(member?20:4))&4095)==n);
 }
 const unsigned int even[]={201,156,202,172},odd[]={172,202,156,201};
 for(unsigned int pattern=0;pattern<256;pattern++) {
  c=base;c.pattern=pattern;memset(bank,0xa5,sizeof(bank));reset_trace();int r=vfe_175_demux_configure(v,&c);
  if(pattern>3)assert(r==-EINVAL && !reads && !writes);
  else {
   assert(!r && nt==9 && trace[7]==0xffff && trace[8]==0x40);
   assert(get(0x574)==even[pattern] && get(0x578)==odd[pattern]);
   assert((get(0x564)&32767)==(pattern<2?100:200));
   assert(((get(0x564)>>16)&32767)==(pattern<2?200:100));
   assert((get(0x564)&0x80008000U)==(0xa5a5a5a5U&0x80008000U));
   assert((get(0x568)&0x80008000U)==(0xa5a5a5a5U&0x80008000U));
   assert((get(0x560)&0x000f0000)==(0xa5a5a5a5U&0x000f0000));
   assert((get(0x560)&15)==1 && get(0x40)==(0xa5a5a5a5U|4U));
   vfe_175_demux_stop(v);assert(get(0x40)==(0xa5a5a5a5U&~4U));
  }
 }
 const unsigned int codes[4][4]={
  {MEDIA_BUS_FMT_SRGGB8_1X8,MEDIA_BUS_FMT_SRGGB10_1X10,MEDIA_BUS_FMT_SRGGB12_1X12,MEDIA_BUS_FMT_SRGGB14_1X14},
  {MEDIA_BUS_FMT_SGRBG8_1X8,MEDIA_BUS_FMT_SGRBG10_1X10,MEDIA_BUS_FMT_SGRBG12_1X12,MEDIA_BUS_FMT_SGRBG14_1X14},
  {MEDIA_BUS_FMT_SBGGR8_1X8,MEDIA_BUS_FMT_SBGGR10_1X10,MEDIA_BUS_FMT_SBGGR12_1X12,MEDIA_BUS_FMT_SBGGR14_1X14},
  {MEDIA_BUS_FMT_SGBRG8_1X8,MEDIA_BUS_FMT_SGBRG10_1X10,MEDIA_BUS_FMT_SGBRG12_1X12,MEDIA_BUS_FMT_SGBRG14_1X14}};
 for(unsigned int p=0;p<4;p++)for(unsigned int depth=0;depth<4;depth++) {
  assert(!vfe_175_demux_from_code(codes[p][depth],&c));
  assert(c.pattern==p && c.gr_gain==1024 && c.gb_gain==1024 && c.r_gain==1024 && c.b_gain==1024 && !c.black_in && !c.black_out);
 }
 memset(&c,0x5a,sizeof(c));sentinel=c;
 assert(vfe_175_demux_from_code(MEDIA_BUS_FMT_RGB888_1X24,&c)==-EINVAL && !memcmp(&c,&sentinel,sizeof(c)));
 assert(vfe_175_demux_from_code(0,&c)==-EINVAL && vfe_175_demux_from_code(codes[0][0],NULL)==-EINVAL);
 reset_trace();assert(vfe_175_demux_configure(v,NULL)==-EINVAL && !reads && !writes);
 v->res->is_lite=true;assert(vfe_175_demux_configure(v,&base)==-EINVAL);vfe_175_demux_stop(v);assert(!reads && !writes);
 v->res->is_lite=false;v->camss->res->version=CAMSS_8650;
 assert(vfe_175_demux_configure(v,&base)==-EINVAL);vfe_175_demux_stop(v);assert(!reads && !writes);
 v->camss->res->version=CAMSS_8150;memset(bank,0,sizeof(bank));reset_trace();
}

static void verify_axis(unsigned int input,unsigned int output)
{
 struct vfe_175_mnds_axis a;int r=vfe_175_mnds_axis(input,output,&a);
 if(!input || !output || input>16384 || output>input)assert(r==-EINVAL);
 else if((uint64_t)input>=(uint64_t)output*64)assert(r==-ERANGE);
 else {
  assert(!r && a.input==input && a.output==output);
  unsigned int res=input<output*4?3:input<output*8?2:input<output*16?1:0;
  assert(a.resolution==res);
  uint64_t numerator=(uint64_t)input*(1ULL<<(14+res));
  assert((uint64_t)a.phase*output<=numerator && (uint64_t)(a.phase+1)*output>numerator && a.phase<(1U<<22));
 }
}

static void test_mnds(struct vfe_device *v)
{
 for(unsigned int input=1;input<=16384;input++) {
  for(unsigned int output=1;output<=128;output++)verify_axis(input,output);
  verify_axis(input,input);verify_axis(input,input/2);verify_axis(input,input/4);verify_axis(input,input/8);
  verify_axis(input,input/16);verify_axis(input,input/32);verify_axis(input,input/64);
 }
 verify_axis(0,0);verify_axis(0,1);verify_axis(16385,1);verify_axis(UINT32_MAX,UINT32_MAX);
 struct vfe_175_mnds_config c={.input_width=1280,.input_height=720,.output_width=640,.output_height=360,.enabled=true},base=c,sentinel;
 const unsigned int dimensions[][4]={{640,480,640,480},{1280,720,640,360},{4032,3024,1920,1080},{16384,16384,4096,4096},{62,62,2,2},{64,64,2,2}};
 for(unsigned int n=0;n<sizeof(dimensions)/sizeof(dimensions[0]);n++) {
  c=base;c.input_width=dimensions[n][0];c.input_height=dimensions[n][1];c.output_width=dimensions[n][2];c.output_height=dimensions[n][3];
  memset(bank,0xa5,sizeof(bank));reset_trace();int r=vfe_175_mnds_configure(v,&c);
  if(n==5) { assert(r==-ERANGE && !reads && !writes);continue; }
  assert(!r && writes==23 && barriers==1 && nt==24 && trace[20]==0xffff && trace[21]==0xa3c && trace[22]==0xa68 && trace[23]==0x4c);
  const unsigned int offset[]={0xa40,0xa54,0xa6c,0xa80};
  for(unsigned int axis=0;axis<4;axis++) {
   unsigned int in=axis%2?c.input_height:c.input_width;
   unsigned int out=(axis%2?c.output_height:c.output_width)/(axis>=2?2:1);
   unsigned int mask=axis>=2?0xffffffffU:0x3fff3fffU,old=0xa5a5a5a5U;
   assert(get(offset[axis])==((old&~mask)|((in-1)|((out-1)<<16))));
   unsigned int res=in<out*4?3:in<out*8?2:in<out*16?1:0;
   unsigned int phase=(uint64_t)in*(1ULL<<(14+res))/out;
   assert(get(offset[axis]+4)==((old&~0x303fffffU)|(res<<28)|phase));
   assert(get(offset[axis]+8)==(old&~0x3fffU));
   assert(get(offset[axis]+12)==(old&~0x3fffffU));
   assert(get(offset[axis]+16)==((old&0x40000000U)|(in-1)));
  }
  assert((get(0xa3c)&3)==3 && (get(0xa68)&3)==3 && get(0x4c)==(0xa5a5a5a5U|8U));
  vfe_175_mnds_stop(v);assert(!(get(0xa3c)&3) && !(get(0xa68)&3) && get(0x4c)==(0xa5a5a5a5U&~8U));
 }
 const unsigned int bad[]={0,1,3,16385,UINT32_MAX};
 for(unsigned int member=0;member<4;member++)for(unsigned int b=0;b<sizeof(bad)/sizeof(bad[0]);b++) {
  c=base;if(member==0)c.input_width=bad[b];if(member==1)c.input_height=bad[b];if(member==2)c.output_width=bad[b];if(member==3)c.output_height=bad[b];
  reset_trace();assert(vfe_175_mnds_configure(v,&c)<0 && !reads && !writes);
 }
 c=base;c.output_width=1282;reset_trace();assert(vfe_175_mnds_configure(v,&c)==-EINVAL && !reads && !writes);
 c=base;c.enabled=false;memset(bank,0,sizeof(bank));assert(!vfe_175_mnds_configure(v,&c) && !(get(0x4c)&8));
 reset_trace();assert(vfe_175_mnds_configure(v,NULL)==-EINVAL && !reads);
 v->res->is_lite=true;assert(vfe_175_mnds_configure(v,&base)==-EINVAL);vfe_175_mnds_stop(v);assert(!reads && !writes);
 v->res->is_lite=false;v->camss->res->version=CAMSS_8650;
 assert(vfe_175_mnds_configure(v,&base)==-EINVAL);vfe_175_mnds_stop(v);assert(!reads && !writes);
 v->camss->res->version=CAMSS_8150;
 struct vfe_line line={.is_pix=true,.owner=v,.compose={.width=640,.height=360},.crop={.width=640,.height=360}};
 line.fmt[0]=(struct v4l2_mbus_framefmt){.width=1280,.height=720};line.fmt[1]=(struct v4l2_mbus_framefmt){.width=640,.height=360};
 line.output[0].video_out.active_fmt.fmt.pix_mp=(struct v4l2_pix_format_mplane){.pixelformat=V4L2_PIX_FMT_NV12,.width=640,.height=360};
 assert(!vfe_175_mnds_from_line(&line,&c) && c.input_width==1280 && c.output_width==640);
 memset(&c,0x5a,sizeof(c));sentinel=c;line.crop.left=2;
 assert(vfe_175_mnds_from_line(&line,&c)==-EINVAL && !memcmp(&c,&sentinel,sizeof(c)));line.crop.left=0;
 line.compose.width=638;assert(vfe_175_mnds_from_line(&line,&c)==-EINVAL);line.compose.width=640;
 line.fmt[1].height=358;assert(vfe_175_mnds_from_line(&line,&c)==-EINVAL);line.fmt[1].height=360;
 line.is_pix=false;assert(vfe_175_mnds_from_line(&line,&c)==-EINVAL);
 assert(vfe_175_mnds_from_line(NULL,&c)==-EINVAL && vfe_175_mnds_from_line(&line,NULL)==-EINVAL);
 memset(bank,0,sizeof(bank));reset_trace();
}
