"""Install the single-IFE routing/scaling backends on the verified 286 tree."""
from pathlib import Path
import json,subprocess

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
SOURCE=TREE/'drivers/media/platform/qcom/camss'
BASE='209d1ea0f0a53e9a725ad288c159baddbc83aef7'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==BASE and not git('status','--porcelain')
assert json.loads((ROOT.parent/'kernel286/depth-gamma-full-build-validation.json').read_text())['terminal']
assert subprocess.run(['git','-C',str(TREE),'show-ref','--verify','--quiet','refs/heads/samurai-vfe175-demux-mnds287']).returncode==1
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-vfe175-demux-mnds287'],check=True,capture_output=True)
for name in ['camss-vfe-175-demux.c','camss-vfe-175-demux.h','camss-vfe-175-mnds.c','camss-vfe-175-mnds.h']:
    target=SOURCE/name;assert not target.exists();target.write_bytes((ROOT/'source'/name).read_bytes())
p=SOURCE/'camss-vfe-175-camif.c';s=p.read_text();old='static int vfe_175_bayer_pattern(u32 code)';assert s.count(old)==1;p.write_text(s.replace(old,old[7:]))
p=SOURCE/'camss-vfe-175-camif.h';s=p.read_text();needle='int vfe_175_camif_prepare';assert s.count(needle)==1;p.write_text(s.replace(needle,'int vfe_175_bayer_pattern(u32 code);\n'+needle))
p=SOURCE/'Makefile';s=p.read_text();needle='\t\tcamss-vfe-175-gamma.o \\\n';assert s.count(needle)==1
p.write_text(s.replace(needle,needle+'\t\tcamss-vfe-175-demux.o \\\n\t\tcamss-vfe-175-mnds.o \\\n'))
p=SOURCE/'camss-vfe-175-pixel.c';s=p.read_text();needle='#include "camss-vfe-175-gamma.h"\n';assert s.count(needle)==1
s=s.replace(needle,needle+'#include "camss-vfe-175-demux.h"\n#include "camss-vfe-175-mnds.h"\n')
needle='\tstruct vfe_175_gamma_config gamma;\n';assert s.count(needle)==1
s=s.replace(needle,needle+'\tstruct vfe_175_demux_config demux;\n\tstruct vfe_175_mnds_config mnds;\n')
needle='''	ret = vfe_175_demosaic_prepare(line);
''';assert s.count(needle)==1
s=s.replace(needle,'''	ret = vfe_175_demux_from_code(line->fmt[MSM_VFE_PAD_SINK].code, &demux);
	if (ret)
		return ret;
	ret = vfe_175_mnds_from_line(line, &mnds);
	if (ret)
		return ret;
	ret = vfe_175_demux_configure(vfe, &demux);
	if (ret)
		return ret;
'''+needle)
old='''	ret = vfe_175_demosaic_prepare(line);
	if (ret)
		return ret;''';new=old.replace('return ret;','goto error;');assert s.count(old)==1;s=s.replace(old,new)
needle='\tret = vfe_175_round_prepare(line);\n';assert s.count(needle)==1
s=s.replace(needle,'\tret = vfe_175_mnds_configure(vfe, &mnds);\n\tif (ret)\n\t\tgoto error;\n'+needle)
needle='\tvfe_175_round_stop(vfe);\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\tvfe_175_mnds_stop(vfe);\n')
needle='\tvfe_175_demosaic_stop(vfe);\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\tvfe_175_demux_stop(vfe);\n')
p.write_text(s)
print(git('status','--short'))
