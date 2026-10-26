/* Host-only independent tests; appended after the actual driver functions. */
static void test_round(struct vfe_device *v)
{
 struct vfe_175_round_config base={.y_max=255,.c_max=255,.output_bits=8,.enabled=true},c;
 for(unsigned int depth=8;depth<=10;depth+=2) {
  base.output_bits=depth;base.y_max=base.c_max=(1U<<depth)-1;
  for(unsigned int member=0;member<4;member++)for(unsigned int n=0;n<=65535;n++) {
   c=base;
   if(member==0)c.y_min=n;if(member==1)c.y_max=n;if(member==2)c.c_min=n;if(member==3)c.c_max=n;
   reset_trace();int ret=vfe_175_round_configure(v,&c);
   if(n>((1U<<depth)-1))assert(ret==-EINVAL && !reads && !writes && !barriers);
   else {
    assert(!ret && writes==6 && barriers==1);
    unsigned int val=get(member<2?0xe18:0xe38);
    assert((member%2?val>>20:val&1023)==n);
    assert(get(0xe1c)==((10-depth)*8+6) && get(0xe3c)==((10-depth)*8+7));
   }
  }
 }
 for(unsigned int bits=0;bits<256;bits++) {
  c=base;c.output_bits=bits;reset_trace();int ret=vfe_175_round_configure(v,&c);
  if(bits!=8 && bits!=10)assert(ret==-EINVAL && !reads && !writes);
 }
 c=base;c.y_min=7;c.y_max=6;reset_trace();assert(vfe_175_round_configure(v,&c)==-EINVAL && !reads);
 c=base;c.c_min=15;c.c_max=14;assert(vfe_175_round_configure(v,&c)==-EINVAL && !reads);
 for(unsigned int on=0;on<2;on++) {
  c=base;c.enabled=on;memset(bank,0xa5,sizeof(bank));reset_trace();
  assert(!vfe_175_round_configure(v,&c));
  assert(nt==7 && trace[0]==0xe18 && trace[1]==0xe1c && trace[2]==0xe38 && trace[3]==0xe3c);
  assert(trace[4]==0xffff && trace[5]==0xe0c && trace[6]==0xe2c);
  assert((get(0xe18)&~0x3ff003ffU)==(0xa5a5a5a5U&~0x3ff003ffU));
  assert((get(0xe38)&~0x3ff003ffU)==(0xa5a5a5a5U&~0x3ff003ffU));
  assert((get(0xe1c)&~63U)==(0xa5a5a5a5U&~63U) && (get(0xe3c)&~63U)==(0xa5a5a5a5U&~63U));
  assert(get(0xe0c)==((0xa5a5a5a5U&~0xc00U)|(on?0xc00:0)));
  assert(get(0xe2c)==((0xa5a5a5a5U&~0xc00U)|(on?0xc00:0)));
  reset_trace();vfe_175_round_stop(v);assert(writes==2 && !(get(0xe0c)&0xc00) && !(get(0xe2c)&0xc00));
 }
 reset_trace();assert(vfe_175_round_configure(v,NULL)==-EINVAL && !reads);
 v->res->is_lite=true;assert(vfe_175_round_configure(v,&base)==-EINVAL);vfe_175_round_stop(v);assert(!reads && !writes);
 v->res->is_lite=false;v->camss->res->version=CAMSS_8650;
 assert(vfe_175_round_configure(v,&base)==-EINVAL);vfe_175_round_stop(v);assert(!reads && !writes);
 v->camss->res->version=CAMSS_8150;
 struct vfe_line raw={.owner=v},pix={.is_pix=true,.owner=v};
 assert(!vfe_175_round_prepare(&raw) && !writes);
 assert(vfe_175_round_prepare(&pix)==-EINVAL && !writes);
 pix.output[0].video_out.active_fmt.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_NV12;
 memset(bank,0,sizeof(bank));assert(!vfe_175_round_prepare(&pix) && (get(0xe18)>>20)==255);
 memset(bank,0,sizeof(bank));reset_trace();
}

static bool valid_gamma(const struct vfe_175_gamma_config *c)
{
 for(unsigned int ch=0;ch<3;ch++) {
  if(c->points[ch][64]>1024)return false;
  for(unsigned int i=0;i<64;i++) {
   int delta=(int)c->points[ch][i+1]-(int)c->points[ch][i];
   if(c->points[ch][i]>1023 || delta < -512 || delta > 511)return false;
  }
 }
 return true;
}

static void test_gamma(struct vfe_device *v)
{
 struct vfe_175_gamma_config c,base,sentinel;
 struct v4l2_pix_format_mplane pix={.pixelformat=V4L2_PIX_FMT_NV12,.colorspace=V4L2_COLORSPACE_SRGB};
 u32 packed[3][64];
 /* All adjacent 10-bit knot pairs, including the asymmetric signed delta. */
 memset(&c,0,sizeof(c));
 for(unsigned int next=0;next<1024;next++) {
  for(unsigned int i=1;i<65;i++)c.points[0][i]=next;
  for(unsigned int first=0;first<1024;first++) {
   c.points[0][0]=first;int delta=(int)next-(int)first;
   int ret=vfe_175_gamma_pack(&c,packed);
   if(delta < -512 || delta > 511)assert(ret==-EINVAL);
   else {
    assert(!ret && (packed[0][0]&1023)==first);
    unsigned int word=(packed[0][0]>>10)&1023;
    assert((word&512?(int)word-1024:(int)word)==delta);
    assert(!(packed[0][0]&0xfff00000U));
   }
  }
 }
 assert(vfe_175_gamma_pack(NULL,packed)==-EINVAL);
 assert(!vfe_175_gamma_from_format(&pix,&base));
 const unsigned int probes[]={0,1,511,512,1023,1024,1025,65535};
 for(unsigned int ch=0;ch<3;ch++)for(unsigned int i=0;i<65;i++)for(unsigned int p=0;p<sizeof(probes)/sizeof(probes[0]);p++) {
  c=base;c.points[ch][i]=probes[p];reset_trace();
  int ret=vfe_175_gamma_configure(v,&c);
  if(valid_gamma(&c))assert(!ret);
  else assert(ret==-EINVAL && !reads && !writes && !barriers);
 }
 for(unsigned int n=0;n<=65535;n++) {
  c=base;c.points[0][0]=n;reset_trace();int ret=vfe_175_gamma_pack(&c,packed);
  assert(valid_gamma(&c)?ret==0:ret==-EINVAL);
 }
 double error[3]={0,0,0};
 for(unsigned int transfer=0;transfer<3;transfer++) {
  pix.xfer_func=transfer==0?V4L2_XFER_FUNC_SRGB:transfer==1?V4L2_XFER_FUNC_709:V4L2_XFER_FUNC_NONE;
  assert(!vfe_175_gamma_from_format(&pix,&c) && !vfe_175_gamma_pack(&c,packed));
  for(unsigned int n=0;n<=16384;n++) {
   double x=n/16384.0,target=transfer==0?(x<=0.0031308?12.92*x:1.055*pow(x,1.0/2.4)-0.055):transfer==1?(x<0.018?4.5*x:1.099*pow(x,0.45)-0.099):x;
   if(n%256==0)assert(fabs(c.points[0][n/256]-target*1024)<=0.5000001);
   unsigned int seg=n==16384?63:n/256;double frac=(n-seg*256)/256.0;
   double modeled=c.points[0][seg]*(1-frac)+c.points[0][seg+1]*frac;
   double err=fabs(modeled-target*1024);if(err>error[transfer])error[transfer]=err;
  }
  for(unsigned int ch=1;ch<3;ch++)assert(!memcmp(c.points[0],c.points[ch],sizeof(c.points[0])));
 }
 assert(error[0]<22 && error[1]<7 && error[2]==0);
 printf("64-segment transfer interpolation error: sRGB %.6f, 709 %.6f, linear %.6f (10-bit codes, no hardware rounding)\n",error[0],error[1],error[2]);
 pix.xfer_func=0;pix.colorspace=V4L2_COLORSPACE_SRGB;assert(!vfe_175_gamma_from_format(&pix,&c) && c.points[0][1]==vfe_175_gamma_srgb[1]);
 pix.colorspace=V4L2_COLORSPACE_REC709;assert(!vfe_175_gamma_from_format(&pix,&c) && c.points[0][1]==vfe_175_gamma_709[1]);
 for(unsigned int f=0;f<256;f++) {
  pix.xfer_func=f;memset(&c,0x5a,sizeof(c));sentinel=c;int ret=vfe_175_gamma_from_format(&pix,&c);
  if(f!=0 && f!=V4L2_XFER_FUNC_SRGB && f!=V4L2_XFER_FUNC_709 && f!=V4L2_XFER_FUNC_NONE)
   assert(ret==-EINVAL && !memcmp(&c,&sentinel,sizeof(c)));
  else assert(!ret);
 }
 pix.pixelformat=V4L2_PIX_FMT_SRGGB10;assert(vfe_175_gamma_from_format(&pix,&c)==-EINVAL);
 assert(vfe_175_gamma_from_format(NULL,&c)==-EINVAL && vfe_175_gamma_from_format(&pix,NULL)==-EINVAL);
 /* Distinct R/G/B tables, all current bank combinations, auto-increment on/off. */
 for(unsigned int ch=0;ch<3;ch++)for(unsigned int i=0;i<65;i++)
  base.points[ch][i]=ch==0?i*16:ch==1?(i*i+2)/4:512;
 base.enabled=true;assert(!vfe_175_gamma_pack(&base,packed));
 for(unsigned int old=0;old<8;old++)for(unsigned int automatic=0;automatic<2;automatic++) {
  memset(bank,0xa5,sizeof(bank));memset(dmi_ram,0xef,sizeof(dmi_ram));
  u32 cfg=(0xa5a5a455U&~256U)|(automatic?256U:0),lut=0x5a5a5a58U|old,addr=123;
  memcpy(bank+0xc24,&cfg,4);memcpy(bank+0x798,&lut,4);memcpy(bank+0xc28,&addr,4);
  reset_trace();dmi_writes=0;assert(!vfe_175_gamma_configure(v,&base));
  assert(writes==391 && barriers==2 && nt==393 && dmi_writes==192);
  assert(get(0xc24)==cfg && get(0xc28)==addr && get(0x798)==(lut^7) && (get(0x48)&8));
  assert((get(0x48)&~8U)==(0xa5a5a5a5U&~8U));
  const unsigned int selector[]={30,26,28};
  for(unsigned int ch=0;ch<3;ch++) {
   unsigned int active=(old>>ch)&1,inactive=1-active;
   for(unsigned int i=0;i<64;i++) {
    assert(dmi_ram[selector[ch]+inactive][i]==packed[ch][i]);
    assert(dmi_ram[selector[ch]+active][i]==0xefefefefU);
    assert(trace[ch*129+1+i*2]==0xc28 && trace[ch*129+2+i*2]==0xc30);
   }
  }
  assert(trace[387]==0xc24 && trace[388]==0xc28 && trace[389]==0xffff && trace[390]==0x798 && trace[391]==0xffff && trace[392]==0x48);
  vfe_175_gamma_stop(v);assert(!(get(0x48)&8));
 }
 c=base;c.enabled=false;reset_trace();dmi_writes=0;assert(!vfe_175_gamma_configure(v,&c) && writes==1 && !dmi_writes && !(get(0x48)&8));
 reset_trace();assert(vfe_175_gamma_configure(v,NULL)==-EINVAL && !reads && !writes);
 v->res->is_lite=true;assert(vfe_175_gamma_configure(v,&base)==-EINVAL);vfe_175_gamma_stop(v);assert(!reads && !writes);
 v->res->is_lite=false;v->camss->res->version=CAMSS_8650;
 assert(vfe_175_gamma_configure(v,&base)==-EINVAL);vfe_175_gamma_stop(v);assert(!reads && !writes);
 v->camss->res->version=CAMSS_8150;memset(bank,0,sizeof(bank));reset_trace();
}
