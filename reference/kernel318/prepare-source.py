"""Add optional LSC to the shared-streams CAMSS source; no board changes."""
from pathlib import Path
import json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera318-lsc-kernel')
base='afad7bde625bbf7bf58c145bde1f977b806da986'
assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==base
assert not subprocess.check_output(['git','-C',str(TREE),'diff','HEAD'])
subdir=Path('drivers/media/platform/qcom/camss')
for source in (HERE/'kernel').glob('*.h'):shutil.copyfile(source,TREE/subdir/source.name)
for source in (HERE/'kernel').glob('*.c'):shutil.copyfile(source,TREE/subdir/source.name)
def edit(relative,old,new):
 p=TREE/relative;s=p.read_text();assert s.count(old)==1,(relative,old)
 p.write_text(s.replace(old,new))
uapi=Path('include/uapi/linux/qcom-camss-config.h')
edit(uapi,'\tCAMSS_PARAMS_AEC_BHIST = 5,','\tCAMSS_PARAMS_AEC_BHIST = 5,\n\tCAMSS_PARAMS_LSC = 6,')
edit(uapi,' * @CAMSS_PARAMS_AEC_BHIST: region of the AEC Bayer histogram statistics,',
 ' * @CAMSS_PARAMS_LSC: regular lens shading mesh, &struct camss_params_lsc\n * @CAMSS_PARAMS_AEC_BHIST: region of the AEC Bayer histogram statistics,')
edit(uapi,'/**\n * enum camss_stats_block_type', (HERE/'lsc-uapi.txt').read_text()+'/**\n * enum camss_stats_block_type')
edit(subdir/'Makefile','\t\tcamss-vfe-175-pixel.o \\\n','\t\tcamss-vfe-175-pixel.o \\\n\t\tcamss-vfe-175-lsc.o \\\n')
edit(subdir/'camss-vfe-175-pixel.h','\tbool wb_enabled;','\tbool wb_enabled;\n\tbool lsc_enabled;\n\tu8 lsc_bank;')
edit(subdir/'camss-vfe-175-pixel.h','vfe_175_params_info[6]','vfe_175_params_info[7]')
edit(subdir/'camss-vfe-175-pixel.c','#include "camss-vfe-175-gamma.h"','#include "camss-vfe-175-gamma.h"\n#include "camss-vfe-175-lsc.h"')
edit(subdir/'camss-vfe-175-pixel.c','vfe_175_params_info[6]','vfe_175_params_info[7]')
edit(subdir/'camss-vfe-175-pixel.c','\t[CAMSS_PARAMS_AEC_BHIST] = {','\t[CAMSS_PARAMS_LSC] = {\n\t\t.size = sizeof(struct camss_params_lsc),\n\t\t.block_validate = vfe_175_lsc_validate,\n\t},\n\t[CAMSS_PARAMS_AEC_BHIST] = {')
edit(subdir/'camss-vfe-175-pixel.c','\tvfe_175_wb_write(vfe);\n\tret = vfe_175_stats_prepare(line);','\tvfe_175_wb_write(vfe);\n\tvfe_175_lsc_init(vfe);\n\tret = vfe_175_stats_prepare(line);')
edit(subdir/'camss-vfe-175-pixel.c','\tvfe_175_blc_enable(vfe, false);','\tvfe_175_blc_enable(vfe, false);\n\tvfe_175_lsc_stop(vfe);')
edit(subdir/'camss-vfe-175-pixel.c','\t\tif (block->type == CAMSS_PARAMS_AEC_BHIST) {','\t\tif (block->type == CAMSS_PARAMS_LSC) {\n\t\t\tvfe_175_lsc_params(vfe, block);\n\t\t\toffset += block->size;\n\t\t\tcontinue;\n\t\t}\n\t\tif (block->type == CAMSS_PARAMS_AEC_BHIST) {')
edit(subdir/'camss-vfe.h','\tconst struct v4l2_isp_params_block_type_info *params_info;',
 '\tunsigned int params_max_payload;\n\tint (*params_validate)(struct vfe_line *line,\n\t\t\t       const struct v4l2_isp_buffer *params);\n\tconst struct v4l2_isp_params_block_type_info *params_info;')
edit(subdir/'camss-vfe.c','\treturn v4l2_isp_params_validate_buffer(vfe->camss->dev, vb, buf->meta,\n\t\t\t\t\t       ops->params_info,\n\t\t\t\t\t       ops->params_num_types);',
 '\tret = v4l2_isp_params_validate_buffer(vfe->camss->dev, vb, buf->meta,\n\t\t\t\t\t      ops->params_info,\n\t\t\t\t\t      ops->params_num_types);\n\tif (ret)\n\t\treturn ret;\n\treturn ops->params_validate ? ops->params_validate(output->line, buf->meta) : 0;')
edit(subdir/'camss-vfe.c','v4l2_isp_buffer_size(CAMSS_PARAMS_IFE_MAX_PAYLOAD);',
 'v4l2_isp_buffer_size(vfe->res->hw_ops->params_max_payload ?: \n\t\t\t\t\t     CAMSS_PARAMS_IFE_MAX_PAYLOAD);')
edit(subdir/'camss-vfe-17x.c','#include "camss-vfe-175-camif.h"','#include "camss-vfe-175-camif.h"\n#include "camss-vfe-175-lsc.h"')
edit(subdir/'camss-vfe-17x.c','\t.params_info = vfe_175_params_info,',
 '\t.params_max_payload = CAMSS_PARAMS_IFE_LSC_MAX_PAYLOAD,\n\t.params_validate = vfe_175_params_validate_line,\n\t.params_info = vfe_175_params_info,')
subprocess.run(['git','-C',str(TREE),'add','-N',str(subdir/'camss-vfe-175-lsc.c'),str(subdir/'camss-vfe-175-lsc.h')],check=True)
patch=subprocess.check_output(['git','-C',str(TREE),'diff','HEAD'])
(HERE/'lsc-driver.patch').write_bytes(patch)
for relative in [uapi,*[subdir/name for name in ['camss-vfe.h','camss-vfe.c','camss-vfe-17x.c','camss-vfe-175-pixel.h','camss-vfe-175-pixel.c','Makefile']]]:
 dest=HERE/'kernel'/relative.name;shutil.copyfile(TREE/relative,dest)
print('Prepared optional LSC parameters, intrinsic/frame validation, inactive-bank DMI upload and normal lifecycle.')
