"""Install independently written 175 output-depth and Gamma16 backends once."""
from pathlib import Path
import hashlib,json,math,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel286')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
SOURCE=TREE/'drivers/media/platform/qcom/camss'
BASE='d1a5f84405cfa774765e9b8ffabd6d1533dec2b6'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==BASE and not git('status','--porcelain')
assert subprocess.run(['git','-C',str(TREE),'show-ref','--verify','--quiet','refs/heads/samurai-vfe175-depth-gamma286']).returncode==1
assert json.loads((ROOT.parent/'kernel285/cst-full-build-validation.json').read_text())['terminal']
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-vfe175-depth-gamma286'],check=True,capture_output=True)
tables={}
for kind in ['srgb','709']:
    def curve(x):
        if kind=='srgb':return 12.92*x if x<=0.0031308 else 1.055*x**(1/2.4)-0.055
        return 4.5*x if x<0.018 else 1.099*x**0.45-0.099
    tables[kind]=[math.floor(curve(i/64)*1024+0.5) for i in range(65)]
    assert tables[kind][0]==0 and tables[kind][-1]==1024 and max(tables[kind][:-1])<=1023
text='/* Standard transfer functions sampled at x=i/64, rounded to 10-bit knots. */\n'
for kind,values in tables.items():
    text+='static const u16 vfe_175_gamma_'+kind+'[VFE_175_GAMMA_POINTS] = {\n'
    for start in range(0,65,8):text+='\t'+', '.join(str(v) for v in values[start:start+8])+',\n'
    text+='};\n\n'
for name in ['camss-vfe-175-round.c','camss-vfe-175-round.h','camss-vfe-175-gamma.c','camss-vfe-175-gamma.h']:
    p=SOURCE/name;assert not p.exists();s=(ROOT/'source'/name).read_text()
    if name.endswith('gamma.c'):
        assert s.count('/* STANDARD_TRANSFER_TABLES */')==1
        s=s.replace('/* STANDARD_TRANSFER_TABLES */',text.rstrip())
    p.write_text(s)
path=SOURCE/'Makefile';s=path.read_text();needle='\t\tcamss-vfe-175-cst.o \\\n';assert s.count(needle)==1
path.write_text(s.replace(needle,needle+'\t\tcamss-vfe-175-round.o \\\n\t\tcamss-vfe-175-gamma.o \\\n'))
path=SOURCE/'camss-vfe-175-pixel.c';s=path.read_text();needle='#include "camss-vfe-175-cst.h"\n';assert s.count(needle)==1
s=s.replace(needle,needle+'#include "camss-vfe-175-round.h"\n#include "camss-vfe-175-gamma.h"\n')
needle='\tstruct vfe_175_cst_config cst;\n';assert s.count(needle)==1
s=s.replace(needle,needle+'\tstruct vfe_175_gamma_config gamma;\n')
old='''	ret = vfe_175_demosaic_prepare(line);
	if (ret)
		return ret;
	ret = vfe_175_cst_configure(vfe, &cst);
	if (ret) {
		vfe_175_demosaic_stop(vfe);
		return ret;
	}
'''
new='''	ret = vfe_175_gamma_from_format(&line->output[0].video_out.active_fmt.fmt.pix_mp,
					&gamma);
	if (ret)
		return ret;
	ret = vfe_175_demosaic_prepare(line);
	if (ret)
		return ret;
	ret = vfe_175_gamma_configure(vfe, &gamma);
	if (ret)
		goto error;
	ret = vfe_175_cst_configure(vfe, &cst);
	if (ret)
		goto error;
	ret = vfe_175_round_prepare(line);
	if (ret)
		goto error;
'''
assert s.count(old)==1;s=s.replace(old,new)
old='''	vfe_175_wb_write(vfe);

	return 0;
}

void vfe_175_pixel_stop'''
new='''	vfe_175_wb_write(vfe);

	return 0;

error:
	vfe_175_pixel_stop(vfe);
	return ret;
}

void vfe_175_pixel_stop'''
assert s.count(old)==1;s=s.replace(old,new)
needle='''void vfe_175_pixel_stop(struct vfe_device *vfe)
{
''';assert s.count(needle)==1
s=s.replace(needle,needle+'\tvfe_175_round_stop(vfe);\n\tvfe_175_gamma_stop(vfe);\n')
path.write_text(s)
(PRIVATE/'transfer-table-generation-private.json').write_text(json.dumps(tables,indent=2)+'\n')
print(git('status','--short'))
