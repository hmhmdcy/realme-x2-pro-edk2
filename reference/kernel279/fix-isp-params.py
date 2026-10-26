"""Respect header-only DISABLE and apply module enable/disable explicitly."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
report = json.loads((ROOT / 'params-before-fix-validation.json').read_text())
assert report['heap_buffer_overflow'] and report['exit'] != 0
prefix = 'drivers/media/platform/qcom/camss/'
changes = []


def replace(name, old, new):
    path = TREE / prefix / name
    text = path.read_text()
    assert text.count(old) == 1, name
    updated = text.replace(old, new)
    changes.append(dict(path=prefix + name, before_sha256=hashlib.sha256(text.encode()).hexdigest(),
                        after_sha256=hashlib.sha256(updated.encode()).hexdigest()))
    path.write_text(updated)


replace('camss-vfe-780.c',
        '\tif ((bhist->left | bhist->top | bhist->width | bhist->height) & 1 ||',
        '\tif (block->flags & ~(V4L2_ISP_PARAMS_FL_BLOCK_ENABLE |\n'
        '\t\t\t     V4L2_ISP_PARAMS_FL_BLOCK_DISABLE))\n\t\treturn -EINVAL;\n\n'
        '\t/* The common ABI permits a header-only DISABLE block. */\n'
        '\tif (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE)\n\t\treturn 0;\n\n'
        '\tif ((bhist->left | bhist->top | bhist->width | bhist->height) & 1 ||')
replace('camss-vfe-780.c',
        '\t\tif (block->type == CAMSS_PARAMS_AEC_BHIST &&\n'
        '\t\t    !(block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE))\n'
        '\t\t\tvfe_params_aec_bhist(vfe, line,\n'
        '\t\t\t\t\t     container_of(block,\n'
        '\t\t\t\t\t\t\t  struct camss_params_aec_bhist,\n'
        '\t\t\t\t\t\t\t  header));',
        '\t\tif (block->type == CAMSS_PARAMS_AEC_BHIST) {\n'
        '\t\t\tif (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE) {\n'
        '\t\t\t\tvfe_880_enable_aec_bhist(vfe, false);\n'
        '\t\t\t} else {\n'
        '\t\t\t\tvfe_params_aec_bhist(vfe, line,\n'
        '\t\t\t\t\tcontainer_of(block, struct camss_params_aec_bhist, header));\n'
        '\t\t\t\tif (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_ENABLE)\n'
        '\t\t\t\t\tvfe_880_enable_aec_bhist(vfe, true);\n'
        '\t\t\t}\n\t\t}')
replace('camss-vfe-880-pp.h',
        'void vfe_880_setup_pixel_pipe(struct vfe_device *vfe, u32 width, u32 height);',
        'void vfe_880_setup_pixel_pipe(struct vfe_device *vfe, u32 width, u32 height);\n'
        'void vfe_880_enable_aec_bhist(struct vfe_device *vfe, bool enable);')
replace('camss-vfe-880-pp.c',
        '/*\n * vfe_880_set_aec_bhist_region - Select the region the AEC BHIST counts',
        'void vfe_880_enable_aec_bhist(struct vfe_device *vfe, bool enable)\n'
        '{\n\tu32 value = readl_relaxed(vfe->base + IFE_STATS_AEC_BHIST_MODULE_CFG);\n\n'
        '\tif (enable)\n\t\tvalue |= BIT(0);\n\telse\n\t\tvalue &= ~BIT(0);\n\n'
        '\twritel_relaxed(value, vfe->base + IFE_STATS_AEC_BHIST_MODULE_CFG);\n}\n\n'
        '/*\n * vfe_880_set_aec_bhist_region - Select the region the AEC BHIST counts')
(ROOT / 'params-fix-source-validation.json').write_text(json.dumps(dict(
    stage=279, changes=changes, header_only_disable_no_payload_reads=True,
    reserved_flags_rejected=True, module_enable_disable_applied=True,
    hardware_not_tested=True, phone_unchanged=True), indent=2) + '\n')
print('Updated actual backend validation and module flag handling')
