"""Finish the interrupted include/ops wiring, then publish the actual source."""
from pathlib import Path
import shutil,subprocess
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera318-lsc-kernel')
subdir=Path('drivers/media/platform/qcom/camss')
p=TREE/subdir/'camss-vfe-17x.c';s=p.read_text()
old='#include "camss-vfe-175-camif.h"'
assert '#include "camss-vfe-175-lsc.h"' not in s
s=s.replace(old,old+'\n#include "camss-vfe-175-lsc.h"')
old='\t.params_info = vfe_175_params_info,';assert s.count(old)==1
s=s.replace(old,'\t.params_max_payload = CAMSS_PARAMS_IFE_LSC_MAX_PAYLOAD,\n\t.params_validate = vfe_175_params_validate_line,\n'+old);p.write_text(s)
p=TREE/subdir/'camss-vfe.c';s=p.read_text().replace('params_max_payload ?: \n','params_max_payload ?: \n'.replace(' \n','\n'));p.write_text(s)
subprocess.run(['git','-C',str(TREE),'add','-N',str(subdir/'camss-vfe-175-lsc.c'),str(subdir/'camss-vfe-175-lsc.h')],check=True)
(HERE/'lsc-driver.patch').write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','HEAD']))
for relative in [Path('include/uapi/linux/qcom-camss-config.h'),*[subdir/name for name in ['camss-vfe.h','camss-vfe.c','camss-vfe-17x.c','camss-vfe-175-pixel.h','camss-vfe-175-pixel.c','Makefile']]]:
 shutil.copyfile(TREE/relative,HERE/'kernel'/relative.name)
print('Finished318 source integration and published exact cumulative diff.')
