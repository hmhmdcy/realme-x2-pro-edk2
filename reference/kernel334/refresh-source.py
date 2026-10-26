from pathlib import Path
import json,shutil,subprocess
HERE=Path(__file__).resolve().parent;state=json.loads((HERE/'source-state.json').read_text());tree=Path(state['source']);directory=Path('drivers/media/platform/qcom/camss')
for name in ['camss-vfe-175-ccm.c','camss-vfe-175-ccm.h']:shutil.copyfile(HERE/'kernel'/name,tree/directory/name)
p=tree/'include/uapi/linux/qcom-camss-config.h';s=p.read_text().replace('VFE175 uses 11s; typically 9s on OPE','VFE175 uses 11 signed bits');p.write_text(s)
for relative in [directory/'Makefile',directory/'camss-vfe-175-pixel.c',directory/'camss-vfe-17x.c',Path('include/uapi/linux/qcom-camss-config.h')]:shutil.copyfile(tree/relative,HERE/'kernel'/relative.name)
subprocess.run(['git','-C',str(tree),'diff','--check'],check=True)
(HERE/'ccm-driver.patch').write_bytes(subprocess.check_output(['git','-C',str(tree),'diff','HEAD']))
print('Synced focused CCM source and checked patch whitespace.')
