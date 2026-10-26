"""Pair CAMIF setup with its distinct PIX reg-update and interrupt bits."""
from pathlib import Path
import subprocess

TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
path = TREE / 'drivers/media/platform/qcom/camss/camss-vfe-17x.c'
source = path.read_text()


def replace(old, new):
    global source
    assert source.count(old) == 1, old
    source = source.replace(old, new)


replace('#define\t\tSTATUS_0_CAMIF_SOF\t\t\tBIT(0)',
        '#define\t\tSTATUS_0_CAMIF_SOF\t\t\tBIT(0)\n#define\t\tSTATUS_0_CAMIF_REG_UPDATE\t\tBIT(4)')
replace('static void vfe_reg_update(struct vfe_device *vfe, enum vfe_line_id line_id)\n{\n\tvfe->reg_update |= REG_UPDATE_RDI(line_id);',
        '''static u32 vfe_reg_update_mask(struct vfe_device *vfe,
\t\t\t       enum vfe_line_id line_id)
{
\treturn vfe->line[line_id].is_pix ? BIT(0) : REG_UPDATE_RDI(line_id);
}

static void vfe_reg_update(struct vfe_device *vfe, enum vfe_line_id line_id)
{
\tvfe->reg_update |= vfe_reg_update_mask(vfe, line_id);''')
replace('vfe->reg_update &= ~REG_UPDATE_RDI(line_id);',
        'vfe->reg_update &= ~vfe_reg_update_mask(vfe, line_id);')
replace('''\tfor (i = VFE_LINE_RDI0; i < vfe->res->line_num; i++)
\t\tif (status0 & STATUS_0_RDI_REG_UPDATE(i))
\t\t\tvfe->isr_ops.reg_update(vfe, i);

\tfor (i = VFE_LINE_RDI0; i < vfe->res->line_num; i++)
\t\tif (status0 & STATUS_1_RDI_SOF(i))
\t\t\tvfe->isr_ops.sof(vfe, i);''', '''\tfor (i = VFE_LINE_RDI0; i < vfe->res->line_num; i++) {
\t\tu32 update = vfe->line[i].is_pix ? STATUS_0_CAMIF_REG_UPDATE :
\t\t\t\t\t\tSTATUS_0_RDI_REG_UPDATE(i);
\t\tu32 sof = vfe->line[i].is_pix ? STATUS_0_CAMIF_SOF :
\t\t\t\t\t     STATUS_1_RDI_SOF(i);

\t\tif (status0 & update)
\t\t\tvfe->isr_ops.reg_update(vfe, i);
\t\tif (status0 & sof)
\t\t\tvfe->isr_ops.sof(vfe, i);
\t}''')
path.write_text(source)
subprocess.run(['git', '-C', str(TREE), 'diff', '--check'], check=True)
print('PIX uses reg-update command bit0 / ACK bit4 / SOF bit0; RDI bits unchanged.')
