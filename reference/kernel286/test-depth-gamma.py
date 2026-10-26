"""Extend the actual CST/Demosaic/WB lifecycle harness with depth and Gamma16."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
base=ROOT.parent/'kernel285/test-cst.py'
s=base.read_text().replace("PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel285')","PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel286')")
s=s.replace('cst-host-','depth-gamma-host-').replace("ROOT/'cst-host-tests-validation.json'","ROOT/'depth-gamma-host-tests-validation.json'")
s=s.replace("('camss-vfe-175-cst.h','vfe_175_cst_config'),", "('camss-vfe-175-round.h','vfe_175_round_config'),('camss-vfe-175-gamma.h','vfe_175_gamma_config'),('camss-vfe-175-cst.h','vfe_175_cst_config'),")
s=s.replace("names=['camss-vfe-175-cst.c'", "names=['camss-vfe-175-round.c','camss-vfe-175-gamma.c','camss-vfe-175-cst.c'")
at=s.index('structs=[]')
s=s[:at]+'''prelude += '\\ntypedef uint8_t u8;\\n#define VFE_175_GAMMA_ENTRIES 64\\n#define VFE_175_GAMMA_POINTS 65\\n'
mocks=mocks.replace('trace[32]','trace[4096]').replace('if(nt<32)','if(nt<4096)')
mocks += r"""
void vfe_175_pixel_stop(struct vfe_device *);
static u32 dmi_ram[32][64];
static unsigned int dmi_writes;
static void writel(u32 value,void *p)
{
 unsigned int reg=(unsigned char *)p-bank;
 writel_relaxed(value,p);
 if(reg==0xc30) {
  u32 cfg,index;memcpy(&cfg,bank+0xc24,4);memcpy(&index,bank+0xc28,4);
  assert((cfg&255)>=26 && (cfg&255)<=31 && index<64);
  dmi_ram[cfg&255][index]=value;dmi_writes++;
  if(cfg&256) { index++;memcpy(bank+0xc28,&index,4); }
 }
}
"""
''' + s[at:]
tests=(ROOT/'depth-gamma-tests.c').read_text()
needle="tests=variables['tests']";assert s.count(needle)==1
s=s.replace(needle,'cst_tests += '+repr(tests)+'\n'+needle)
s=s.replace('test_cst(&v);','test_cst(&v);test_round(&v);test_gamma(&v);')
s=s.replace('writes==21 && v.pixel175.wb_enabled','writes==418 && v.pixel175.wb_enabled')
s=s.replace('format->ycbcr_enc=V4L2_YCBCR_ENC_601;\'\'\')', """format->ycbcr_enc=V4L2_YCBCR_ENC_601;
 reset_trace();format->xfer_func=V4L2_XFER_FUNC_SMPTE2084;
 assert(vfe_175_pixel_prepare(&pix)==-EINVAL && !reads && !writes);
 format->xfer_func=V4L2_XFER_FUNC_DEFAULT;''')""")
s=s.replace('!(get(0x4c)&1)', '!(get(0x4c)&1) && !(get(0x48)&8) && !(get(0xe0c)&0xc00) && !(get(0xe2c)&0xc00)')
s=s.replace('(get(0x4c)&1));', '(get(0x4c)&1) && (get(0x48)&8) && (get(0xe0c)&0xc00)==0xc00 && (get(0xe2c)&0xc00)==0xc00);')
s=s.replace('stage=285','stage=286')
s=s.replace('hardware_color_validation_pending=True,not_deployed=True,',
            'hardware_color_validation_pending=True,round_field_inputs=8*65536,gamma_adjacent_knot_pairs=1024*1024,gamma_all_knots_checked=True,inactive_banks_and_shared_dmi_state=True,not_deployed=True,')
s=s.replace('PASS: CST12 matrix/fields/ranges, Demosaic36, RDI isolation and actual 17x enable/stop rollback',
            'PASS: FULL output depth, Gamma16 banked DMI, CST12, Demosaic36, RDI isolation and actual 17x lifecycle')
exec(compile(s,str(base),'exec'),globals())
