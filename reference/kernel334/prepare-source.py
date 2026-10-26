from pathlib import Path
import json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;parent=Path('/home/cy122/x2pro-linux/camera325-gw1-tpg-kernel');tree=Path('/home/cy122/x2pro-linux/camera334-ccm-kernel')
base='4318dd1c2f7b8971b267cc50d9129e86e99bccdb'
assert subprocess.check_output(['git','-C',str(parent),'rev-parse','HEAD'],text=True).strip()==base
assert not subprocess.check_output(['git','-C',str(parent),'diff','HEAD'])
assert not tree.exists()
subprocess.run(['git','-C',str(parent),'worktree','add','-b','samurai-ccm334',str(tree),base],check=True)
directory=Path('drivers/media/platform/qcom/camss')
for source in (HERE/'kernel').glob('camss-vfe-175-ccm.*'):shutil.copyfile(source,tree/directory/source.name)
def edit(relative,before,after):
 p=tree/relative;s=p.read_text();assert s.count(before)==1,(str(relative),before);p.write_text(s.replace(before,after))
edit(directory/'Makefile','\t\tcamss-vfe-175-lsc.o \\\n','\t\tcamss-vfe-175-lsc.o \\\n\t\tcamss-vfe-175-ccm.o \\\n')
edit(directory/'camss-vfe-175-pixel.c','#include "camss-vfe-175-lsc.h"','#include "camss-vfe-175-lsc.h"\n#include "camss-vfe-175-ccm.h"')
edit(directory/'camss-vfe-175-pixel.c','[CAMSS_PARAMS_COLOR_CORRECT] = {\n\t\t.size = sizeof(struct camss_params_color_correct),\n\t\t.block_validate = vfe_175_params_unsupported,',
 '[CAMSS_PARAMS_COLOR_CORRECT] = {\n\t\t.size = sizeof(struct camss_params_color_correct),\n\t\t.block_validate = vfe_175_ccm_validate,')
edit(directory/'camss-vfe-175-pixel.c','\tvfe_175_lsc_init(vfe);','\tvfe_175_lsc_init(vfe);\n\tvfe_175_ccm_init(vfe);')
edit(directory/'camss-vfe-175-pixel.c','\tvfe_175_lsc_stop(vfe);','\tvfe_175_lsc_stop(vfe);\n\tvfe_175_ccm_stop(vfe);')
edit(directory/'camss-vfe-175-pixel.c','\t\tif (block->type == CAMSS_PARAMS_LSC) {',
 '\t\tif (block->type == CAMSS_PARAMS_COLOR_CORRECT) {\n\t\t\tvfe_175_ccm_params(vfe, block);\n\t\t\toffset += block->size;\n\t\t\tcontinue;\n\t\t}\n\t\tif (block->type == CAMSS_PARAMS_LSC) {')
edit(directory/'camss-vfe-17x.c','\t.params_max_payload = CAMSS_PARAMS_IFE_LSC_MAX_PAYLOAD,','\t.params_max_payload = CAMSS_PARAMS_IFE_COLOR_MAX_PAYLOAD,')
uapi=Path('include/uapi/linux/qcom-camss-config.h')
edit(uapi,' * @k:       per-output-channel offsets (typically 9s effective)',' * @k:       per-output-channel offsets (VFE175 uses 11 signed bits)')
needle='#define CAMSS_PARAMS_IFE_LSC_MAX_PAYLOAD \\\n\t(CAMSS_PARAMS_IFE_MAX_PAYLOAD + sizeof(struct camss_params_lsc))'
edit(uapi,needle,needle+'\n\n#define CAMSS_PARAMS_IFE_COLOR_MAX_PAYLOAD \\\n\t(CAMSS_PARAMS_IFE_LSC_MAX_PAYLOAD + sizeof(struct camss_params_color_correct))')
subprocess.run(['git','-C',str(tree),'add','-N',str(directory/'camss-vfe-175-ccm.c'),str(directory/'camss-vfe-175-ccm.h')],check=True)
(HERE/'ccm-driver.patch').write_bytes(subprocess.check_output(['git','-C',str(tree),'diff','HEAD']))
for relative in [directory/'Makefile',directory/'camss-vfe-175-pixel.c',directory/'camss-vfe-17x.c',uapi]:shutil.copyfile(tree/relative,HERE/'kernel'/relative.name)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=334,source=str(tree),base_commit=base,branch='samurai-ccm334',installed=False,board_and_sensor_changes=False,
 changes=['VFE175 CCM validation/GBR register programming/enable/lifecycle','parameter capacity includes CCM with WB/BHIST/LSC','backend-specific signed offset documentation']),indent=2)+'\n')
print('Prepared VFE175 CCM backend; no board, sensor, queue ABI or installed-module change.')
