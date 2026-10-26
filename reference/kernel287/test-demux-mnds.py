"""Run actual Demux/MNDS, existing processing and 17x lifecycle code under sanitizers."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
previous=ROOT.parent/'kernel286/test-depth-gamma.py'
s=previous.read_text()
s=s.replace("'/mnt/e/edk2-samurai-out/kernel286'","'/mnt/e/edk2-samurai-out/kernel287'")
s=s.replace("tests=(ROOT/'depth-gamma-tests.c').read_text()", "tests=(ROOT.parent/'kernel286/depth-gamma-tests.c').read_text()+'\\n'+(ROOT/'demux-mnds-tests.c').read_text()")
at=s.index("exec(compile(s,str(base),'exec'),globals())")
extra=r"""
s=s.replace('depth-gamma-host-','demux-mnds-host-').replace('stage=286','stage=287')
s=s.replace("('camss-vfe-175-round.h','vfe_175_round_config'),", "('camss-vfe-175-demux.h','vfe_175_demux_config'),('camss-vfe-175-mnds.h','vfe_175_mnds_config'),('camss-vfe-175-round.h','vfe_175_round_config'),")
s=s.replace("names=['camss-vfe-175-round.c'", "names=['camss-vfe-175-camif.c','camss-vfe-175-demux.c','camss-vfe-175-mnds.c','camss-vfe-175-round.c'")
at=s.index('structs=[]')
s=s[:at]+"prelude += '\\n#include <linux/media-bus-format.h>\\n#include <linux/v4l2-mediabus.h>\\ntypedef uint64_t u64;\\n#define FIELD_MAX(mask) ((mask) >> __builtin_ctz(mask))\\n#define div_u64(n,d) ((uint64_t)(n)/(d))\\n#define MSM_VFE_PAD_SINK 0\\n'\n"+s[at:]
needle='struct test_line_output output[1]; };'
assert needle in s
s=s.replace(needle,'struct test_line_output output[1]; struct v4l2_mbus_framefmt fmt[2]; struct v4l2_rect compose,crop; };')
s=s.replace('test_cst(&v);test_round(&v);test_gamma(&v);', '''format->width=640;format->height=480;
 pix.fmt[0]=(struct v4l2_mbus_framefmt){.code=MEDIA_BUS_FMT_SRGGB10_1X10,.width=640,.height=480};
 pix.fmt[1]=pix.fmt[0];pix.compose=(struct v4l2_rect){.width=640,.height=480};pix.crop=pix.compose;
 test_cst(&v);test_round(&v);test_gamma(&v);test_demux(&v);test_mnds(&v);''')
s=s.replace('writes==418 && v.pixel175.wb_enabled','writes==449 && v.pixel175.wb_enabled')
s=s.replace('!(get(0x4c)&1)', '!(get(0x4c)&9)')
needle='format->xfer_func=V4L2_XFER_FUNC_DEFAULT;'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
 reset_trace();pix.crop.left=2;
 assert(vfe_175_pixel_prepare(&pix)==-EINVAL && !reads && !writes);pix.crop.left=0;
 reset_trace();pix.fmt[0].code=MEDIA_BUS_FMT_RGB888_1X24;
 assert(vfe_175_pixel_prepare(&pix)==-EINVAL && !reads && !writes);pix.fmt[0].code=MEDIA_BUS_FMT_SRGGB10_1X10;''')
s=s.replace('not_deployed=True,output=result.stdout.strip()',
            'demux_gain_inputs=4*65536,demux_black_inputs=2*65536,mnds_axis_pairs_at_least=16000*128,unsupported_roi_rejected_before_processing_mmio=True,not_deployed=True,output=result.stdout.strip()')
s=s.replace('PASS: FULL output depth, Gamma16 banked DMI, CST12, Demosaic36, RDI isolation and actual 17x lifecycle',
            'PASS: Bayer Demux, MNDS16 NV12 axes/geometry, FULL depth, Gamma/CST/Demosaic and actual 17x lifecycle')
"""
# Insert after the 286 wrapper has finished its transformations of the old harness.
pos=s.index("exec(compile(s,str(base),'exec'),globals())")
s=s[:pos]+extra+'\n'+s[pos:]
exec(compile(s,str(previous),'exec'),globals())
