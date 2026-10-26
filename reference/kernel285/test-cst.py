"""Test actual CST/Demosaic/WB and 17x lifecycle functions with MMIO mocked."""
from pathlib import Path
import ast,hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel285')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
SOURCE=TREE/'drivers/media/platform/qcom/camss'
# Export the current UAPI with the kernel's own header-install tool.
export=PRIVATE/'host-uapi';(export/'scripts').mkdir(parents=True,exist_ok=True)
(export/'include/linux').mkdir(parents=True,exist_ok=True)
if not (export/'scripts/unifdef').exists():
    subprocess.run(['gcc',str(TREE/'scripts/unifdef.c'),'-o',str(export/'scripts/unifdef')],check=True)
subprocess.run(['sh',str(TREE/'scripts/headers_install.sh'),str(TREE/'include/uapi/linux/videodev2.h'),
                str(export/'include/linux/videodev2.h')],cwd=export,check=True)
for name in ['cst-host-compile-private.log','cst-host-tests-private.log']:
    p=PRIVATE/name
    if p.exists():
        i=1
        while (PRIVATE/(name+f'.attempt{i}')).exists():i+=1
        p.rename(PRIVATE/(name+f'.attempt{i}'))
old=ast.parse((ROOT.parent/'kernel284/test-demosaic.py').read_text())
variables={}
for node in old.body:
    if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
        for target in node.targets:
            if isinstance(target,ast.Name):variables[target.id]=node.value.value
prelude=variables['prelude'].replace('#include <errno.h>','#include <errno.h>\n#include <math.h>\n#include <linux/videodev2.h>')
prelude=prelude.replace('#define __counted_by(x)\n','')
mocks=variables['mocks'].replace('struct vfe_line { bool is_pix; struct vfe_device *owner; };','''struct camss_video { struct v4l2_format active_fmt; };
struct test_line_output { struct camss_video video_out; };
struct vfe_line { bool is_pix; struct vfe_device *owner; struct test_line_output output[1]; };''')
structs=[]
for name,tag in [('camss-vfe-175-cst.h','vfe_175_cst_config'),('camss-vfe-175-demosaic.h','vfe_175_demosaic_config'),('camss-vfe-175-pixel.h','vfe_175_pixel_state')]:
    structs.append(re.search(r'struct '+tag+r' \{.*?\};',(SOURCE/name).read_text(),re.S)[0])
transport=(SOURCE/'camss-vfe-17x.c').read_text()
def function(name,ret):
    m=re.search(r'static '+ret+' '+name+r'\(',transport);assert m
    return transport[m.start():transport.index('\n}',m.start())+2]
cst_tests=r'''
static int signed13(unsigned int x) { return (x&4096)?(int)(x&8191)-8192:(int)(x&8191); }
static void test_cst(struct vfe_device *v)
{
 struct v4l2_pix_format_mplane pix={.pixelformat=V4L2_PIX_FMT_NV12,.colorspace=V4L2_COLORSPACE_SRGB};
 struct vfe_175_cst_config c={.matrix={{1024,0,0},{0,1024,0},{0,0,1024}},.clamp_max={1023,1023,1023},.enabled=true};
 struct vfe_175_cst_config base=c,sentinel;
 for(unsigned int row=0;row<3;row++)for(unsigned int col=0;col<3;col++) {
  for(int n=-32768;n<=32767;n++) {
   c=base;c.matrix[row][col]=n;reset_trace();int r=vfe_175_cst_configure(v,&c);
   if(n < -4096 || n > 4095)assert(r==-EINVAL && !reads && !writes && !barriers);
   else {
    assert(!r && writes==13 && barriers==1);
    unsigned int word=col==0?get(0xf34+16*row):get(0xf30+16*row);
    if(col==2)word>>=16;
    assert(signed13(word)==n);
   }
  }
 }
 for(unsigned int row=0;row<3;row++)for(unsigned int n=0;n<=65535;n++) {
  c=base;c.offset[row]=n;reset_trace();int r=vfe_175_cst_configure(v,&c);
  if(n>1023)assert(r==-EINVAL && !reads && !writes);
  else assert(!r && ((get(0xf38+16*row)>>16)&2047)==n && !(get(0xf38+16*row)&2047));
  c=base;c.clamp_max[row]=n;reset_trace();r=vfe_175_cst_configure(v,&c);
  if(n>1023)assert(r==-EINVAL && !reads && !writes);
  else assert(!r && ((get(0xf3c+16*row)>>16)&1023)==n);
  c=base;c.clamp_min[row]=n;reset_trace();r=vfe_175_cst_configure(v,&c);
  if(n>1023)assert(r==-EINVAL && !reads && !writes);
  else assert(!r && (get(0xf3c+16*row)&1023)==n);
 }
 for(unsigned int row=0;row<3;row++) {
  c=base;c.clamp_min[row]=701;c.clamp_max[row]=700;reset_trace();
  assert(vfe_175_cst_configure(v,&c)==-EINVAL && !reads && !writes);
 }
 for(unsigned int on=0;on<2;on++) {
  c=base;c.enabled=on;c.matrix[0][0]=-4096;c.matrix[1][1]=4095;
  memset(bank,0xa5,sizeof(bank));reset_trace();assert(!vfe_175_cst_configure(v,&c));
  assert(nt==14 && trace[12]==0xffff && trace[13]==0x4c && writes==13 && barriers==1);
  for(unsigned int row=0;row<3;row++) {
   for(unsigned int word=0;word<4;word++)assert(trace[row*4+word]==0xf30+row*16+word*4);
   assert((get(0xf30+row*16)&~0x1fff1fffU)==(0xa5a5a5a5U&~0x1fff1fffU));
   assert((get(0xf34+row*16)&~0x1fffU)==(0xa5a5a5a5U&~0x1fffU));
   assert((get(0xf38+row*16)&~0x07ff07ffU)==(0xa5a5a5a5U&~0x07ff07ffU));
   assert((get(0xf3c+row*16)&~0x03ff03ffU)==(0xa5a5a5a5U&~0x03ff03ffU));
  }
  assert(get(0x4c)==((0xa5a5a5a5U&~1U)|on));
  reset_trace();vfe_175_cst_stop(v);assert(writes==1 && get(0x4c)==(0xa5a5a5a5U&~1U));
 }
 reset_trace();assert(vfe_175_cst_configure(v,NULL)==-EINVAL && !reads && !writes);
 v->res->is_lite=true;assert(vfe_175_cst_configure(v,&base)==-EINVAL);vfe_175_cst_stop(v);assert(!reads && !writes);
 v->res->is_lite=false;v->camss->res->version=CAMSS_8650;
 assert(vfe_175_cst_configure(v,&base)==-EINVAL);vfe_175_cst_stop(v);assert(!reads && !writes);
 v->camss->res->version=CAMSS_8150;
 /* Independent normalized ITU equations, not an expected integer table. */
 double max_error=0;
 for(unsigned int profile=0;profile<2;profile++)for(unsigned int limited=0;limited<2;limited++) {
  pix.ycbcr_enc=profile?V4L2_YCBCR_ENC_709:V4L2_YCBCR_ENC_601;
  pix.quantization=limited?V4L2_QUANTIZATION_LIM_RANGE:V4L2_QUANTIZATION_FULL_RANGE;
  assert(!vfe_175_cst_from_format(&pix,&c));
  reset_trace();assert(!vfe_175_cst_configure(v,&c));
  double kr=profile?0.2126:0.299,kb=profile?0.0722:0.114,kg=1-kr-kb;
  int matrix[3][3];
  for(unsigned int row=0;row<3;row++) {
   matrix[row][0]=signed13(get(0xf34+16*row));
   matrix[row][1]=signed13(get(0xf30+16*row));
   matrix[row][2]=signed13(get(0xf30+16*row)>>16);
  }
  for(unsigned int r=0;r<=32;r++)for(unsigned int g=0;g<=32;g++)for(unsigned int b=0;b<=32;b++) {
   double rgb[]={r*1023.0/32,g*1023.0/32,b*1023.0/32};
   double y=(kr*rgb[0]+kg*rgb[1]+kb*rgb[2])/1023;
   double expected[]={y,(rgb[2]/1023-y)/(2*(1-kb)),(rgb[0]/1023-y)/(2*(1-kr))};
   for(unsigned int row=0;row<3;row++) {
    double actual=c.offset[row];for(unsigned int col=0;col<3;col++)actual+=matrix[row][col]*rgb[col]/1024;
    double target=row?512+expected[row]*(limited?896:1024):(limited?64+876*expected[0]:1023*expected[0]);
    if(actual<c.clamp_min[row])actual=c.clamp_min[row];if(actual>c.clamp_max[row])actual=c.clamp_max[row];
    if(target<c.clamp_min[row])target=c.clamp_min[row];if(target>c.clamp_max[row])target=c.clamp_max[row];
    double err=fabs(actual-target);if(err>max_error)max_error=err;
    assert(err<1.1);
   }
  }
  for(unsigned int n=0;n<1024;n++)for(unsigned int row=1;row<3;row++)
   assert(matrix[row][0]*n+matrix[row][1]*n+matrix[row][2]*n==0);
  assert(c.offset[0]==(limited?64:0) && c.offset[1]==512 && c.offset[2]==512);
 }
 printf("CST max coefficient approximation error %.6f / 1023 (pre-hardware rounding)\n",max_error);
 pix.ycbcr_enc=0;pix.quantization=0;
 assert(!vfe_175_cst_from_format(&pix,&c) && c.offset[0]==64);
 pix.colorspace=V4L2_COLORSPACE_JPEG;assert(!vfe_175_cst_from_format(&pix,&c) && !c.offset[0]);
 pix.colorspace=V4L2_COLORSPACE_REC709;assert(!vfe_175_cst_from_format(&pix,&c) && c.matrix[0][0]==186);
 for(unsigned int enc=0;enc<256;enc++) {
  pix.ycbcr_enc=enc;memset(&c,0x5a,sizeof(c));sentinel=c;
  int r=vfe_175_cst_from_format(&pix,&c);
  if(enc!=0 && enc!=V4L2_YCBCR_ENC_601 && enc!=V4L2_YCBCR_ENC_709)assert(r==-EINVAL && !memcmp(&c,&sentinel,sizeof(c)));
  else assert(!r);
 }
 pix.ycbcr_enc=V4L2_YCBCR_ENC_601;
 for(unsigned int q=0;q<256;q++) {
  pix.quantization=q;int r=vfe_175_cst_from_format(&pix,&c);assert(q<=2?!r:r==-EINVAL);
 }
 pix.quantization=0;pix.ycbcr_enc=0;pix.colorspace=V4L2_COLORSPACE_BT2020;
 assert(vfe_175_cst_from_format(&pix,&c)==-EINVAL);
 pix.colorspace=V4L2_COLORSPACE_SMPTE240M;assert(vfe_175_cst_from_format(&pix,&c)==-EINVAL);
 pix.pixelformat=V4L2_PIX_FMT_SRGGB10;assert(vfe_175_cst_from_format(&pix,&c)==-EINVAL);
 assert(vfe_175_cst_from_format(NULL,&c)==-EINVAL && vfe_175_cst_from_format(&pix,NULL)==-EINVAL);
 reset_trace();memset(bank,0,sizeof(bank));
}
'''
tests=variables['tests']
tests=tests.replace('struct vfe_line pix={true,&v},rdi={false,&v};','''struct vfe_line pix={.is_pix=true,.owner=&v},rdi={.is_pix=false,.owner=&v};
 struct v4l2_pix_format_mplane *format=&pix.output[0].video_out.active_fmt.fmt.pix_mp;
 *format=(struct v4l2_pix_format_mplane){.pixelformat=V4L2_PIX_FMT_NV12,.colorspace=V4L2_COLORSPACE_SRGB,.ycbcr_enc=V4L2_YCBCR_ENC_601,.quantization=V4L2_QUANTIZATION_FULL_RANGE};
 test_cst(&v);''')
tests=tests.replace('writes==8 && v.pixel175.wb_enabled','writes==21 && v.pixel175.wb_enabled && (get(0x4c)&1)')
tests=tests.replace('vfe_175_pixel_stop(&v);assert(!(get(0x40)&1024));','''vfe_175_pixel_stop(&v);assert(!(get(0x40)&1024) && !(get(0x4c)&1));
 reset_trace();format->ycbcr_enc=V4L2_YCBCR_ENC_BT2020;
 assert(vfe_175_pixel_prepare(&pix)==-EINVAL && !reads && !writes);
 format->ycbcr_enc=V4L2_YCBCR_ENC_601;''')
tests=tests.replace('puts_count==1 && queued==1 && !(get(0x40)&1024)','puts_count==1 && queued==1 && !(get(0x40)&1024) && !(get(0x4c)&1)')
tests=tests.replace('full_stops==1 && !(get(0x40)&1024)','full_stops==1 && !(get(0x40)&1024) && !(get(0x4c)&1)')
tests=tests.replace('assert(vfe_175_demosaic_prepare(&pix)==0);full.pad=5;','assert(vfe_175_pixel_prepare(&pix)==0);full.pad=5;')
tests=tests.replace('full_stops==2 && (get(0x40)&1024)','full_stops==2 && (get(0x40)&1024) && (get(0x4c)&1)')
tests=tests.replace('PASS: Demosaic36 fields, exhaustive classifier bounds, masks/order, RDI isolation and actual enable/stop rollback','PASS: CST12 matrix/fields/ranges, Demosaic36, RDI isolation and actual 17x enable/stop rollback')
names=['camss-vfe-175-cst.c','camss-vfe-175-demosaic.c','camss-vfe-175-pixel.c']
texts={n:(SOURCE/n).read_text() for n in names}
code=prelude+'\n'.join(structs)+mocks
code+='\n'.join('\n'.join(l for l in texts[n].splitlines() if not l.startswith('#include')) for n in names)
code+=function('vfe_enable','int')+'\n'+function('vfe_output_stop_175','void')
code+='\nstatic u32 get(unsigned int address);\nstatic void reset_trace(void);\n'+cst_tests+tests
path=PRIVATE/'cst-host-tests-private.c';path.write_text(code)
command=['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-D__EXPORTED_HEADERS__',
         '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-I'+str(export/'include'),'-I'+str(TREE/'include/uapi'),str(path),'-lm','-o',str(PRIVATE/'cst-host-tests-private')]
result=subprocess.run(command,text=True,capture_output=True)
(PRIVATE/'cst-host-compile-private.log').write_text(result.stdout+result.stderr)
assert result.returncode==0,result.stderr
result=subprocess.run([str(PRIVATE/'cst-host-tests-private')],text=True,capture_output=True)
(PRIVATE/'cst-host-tests-private.log').write_text(result.stdout+result.stderr)
assert result.returncode==0,result.stdout+result.stderr
report=dict(stage=285,exit=0,asan_ubsan=True,source_sha256={n:hashlib.sha256(t.encode()).hexdigest() for n,t in texts.items()},
            harness_sha256=hashlib.sha256(code.encode()).hexdigest(),signed_coefficient_inputs=9*65536,
            offset_and_clamp_inputs=9*65536,independent_color_cube_points=4*33**3,neutral_chroma_exact=True,
            masks_and_configuration_order=True,actual_enable_and_stop_functions_tested=True,
            hardware_mmio_simulated=True,hardware_color_validation_pending=True,not_deployed=True,output=result.stdout.strip())
(ROOT/'cst-host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
