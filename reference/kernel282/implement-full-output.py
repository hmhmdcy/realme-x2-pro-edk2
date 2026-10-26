"""Implement the matched single-IFE VFE175 FULL transport behind the unopened PIX path."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE='2985ef200e4ae28d567f5919a4d8657ac0559b65'
git=lambda *args:subprocess.check_output(['git','-C',str(TREE),*args],text=True)
assert git('rev-parse','HEAD').strip()==BASE and not git('status','--porcelain')
D=TREE/'drivers/media/platform/qcom/camss'


def replace(name,old,new):
    p=D/name;s=p.read_text();assert s.count(old)==1,(name,old)
    p.write_text(s.replace(old,new))


replace('Makefile','\t\tcamss-vfe-175-camif.o \\\n','\t\tcamss-vfe-175-camif.o \\\n\t\tcamss-vfe-175-output.o \\\n')
replace('camss-video.h','\tint (*prepare_buffer)(struct camss_video *vid, struct camss_buffer *buf);',
    '''\tint (*prepare_buffer)(struct camss_video *vid, struct camss_buffer *buf);
\t/* Optional: validate capture DMA layout after its SG mappings are checked. */
\tint (*prepare_dma_buffer)(struct camss_video *vid, struct camss_buffer *buf);''')
path=D/'camss-video.c';source=path.read_text()
start=source.index('static int video_buf_prepare(');end=source.index('\n}\n',start)+3
prepare=source[start:end]
old='\tvbuf->field = V4L2_FIELD_NONE;\n\n\treturn 0;\n}'
assert prepare.count(old)==1
new='''\tif (video->ops->prepare_dma_buffer) {
\t\tret = video->ops->prepare_dma_buffer(video,
\t\t\t\tcontainer_of(vbuf, struct camss_buffer, vb));
\t\tif (ret)
\t\t\treturn ret;
\t}

\tvbuf->field = V4L2_FIELD_NONE;

\treturn 0;
}'''
path.write_text(source[:start]+prepare.replace(old,new)+source[end:])
replace('camss-vfe-17x.c','#include "camss-vfe-175-camif.h"',
    '#include "camss-vfe-175-camif.h"\n#include "camss-vfe-175-output.h"')
replace('camss-vfe-17x.c','#define VFE_BUS_IRQ_MASK(n)',
    '#define VFE_17X_COMPOSITE_IRQ_NUM\t\t6\n\n#define VFE_BUS_IRQ_MASK(n)')
replace('camss-vfe-17x.c','for (i = 0; i < MSM_VFE_COMPOSITE_IRQ_NUM; i++)',
    'for (i = 0; i < VFE_17X_COMPOSITE_IRQ_NUM; i++)')
replace('camss-vfe-17x.c','''\tfor (wm = 0; wm < MSM_VFE_IMAGE_MASTERS_NUM; wm++)
\t\tif (vfe_bus_status[1] & STATUS1_WM_CLIENT_BUF_DONE(wm))
\t\t\tvfe->isr_ops.wm_done(vfe, wm);''', '''\t/* PIX planes complete together through their composite group above. */
\tfor (wm = 0; wm < vfe->res->line_num; wm++)
\t\tif (!vfe->line[wm].is_pix &&
\t\t    (vfe_bus_status[1] & STATUS1_WM_CLIENT_BUF_DONE(wm)))
\t\t\tvfe->isr_ops.wm_done(vfe, wm);''')
path=D/'camss-vfe-17x.c';source=path.read_text()
start=source.index('/* SM8150 full IFE: shared RDI transport, matched CAMIF preparation. */')
source=source[:start]+'''static int vfe_prepare_dma_175(struct camss_video *video,
\t\t\t       struct camss_buffer *buf)
{
\tstruct vfe_output *output = container_of(video, struct vfe_output, video_out);

\tif (!output->line->is_pix)
\t\treturn 0;

\treturn vfe_175_validate_buffer(output, buf);
}

static const struct camss_video_ops vfe_video_ops_175 = {
\t.queue_buffer = vfe_queue_buffer_v2,
\t.flush_buffers = vfe_flush_buffers,
\t.prepare_dma_buffer = vfe_prepare_dma_175,
};

static void vfe_subdev_init_175(struct device *dev, struct vfe_device *vfe)
{
\tvfe_subdev_init(dev, vfe);
\tvfe->video_ops = vfe_video_ops_175;
\tvfe->isr_ops.comp_done = vfe_175_comp_done;
}

static int vfe_line_prepare_175(struct vfe_line *line)
{
\tint ret;

\tif (line->is_pix) {
\t\tret = vfe_175_validate_output(&line->output[0]);
\t\tif (ret)
\t\t\treturn ret;
\t}

\treturn vfe_175_camif_prepare(line);
}

static void vfe_output_start_175(struct vfe_device *vfe,
\t\t\t\t struct vfe_output *output)
{
\tif (output->line->is_pix)
\t\tvfe_175_full_start(vfe, output);
\telse
\t\tvfe_wm_start(vfe, output->wm[0].bus_client, output->line);
}

static void vfe_output_stop_175(struct vfe_device *vfe,
\t\t\t\tstruct vfe_output *output)
{
\tif (output->line->is_pix)
\t\tvfe_175_full_stop(vfe, output);
\telse
\t\tvfe_wm_stop(vfe, output->wm[0].bus_client, output->line);
}

static void vfe_output_update_175(struct vfe_device *vfe,
\t\t\t\t  struct vfe_output *output,
\t\t\t\t  struct camss_buffer *buf)
{
\tif (output->line->is_pix)
\t\tvfe_175_full_update(vfe, output, buf);
\telse
\t\tvfe_wm_update(vfe, output->wm[0].bus_client, buf->addr[0],
\t\t\t      output->line);
}

/* SM8150 full IFE: shared RDI transport, matched CAMIF and FULL DMA. */
const struct vfe_hw_ops vfe_ops_175 = {
\t.vfe_line_prepare = vfe_line_prepare_175,
\t.global_reset = vfe_global_reset,
\t.hw_version = vfe_hw_version,
\t.isr_read = vfe_isr_read,
\t.isr = vfe_isr,
\t.pm_domain_off = vfe_pm_domain_off,
\t.pm_domain_on = vfe_pm_domain_on,
\t.reg_update_clear = vfe_reg_update_clear,
\t.reg_update = vfe_reg_update,
\t.subdev_init = vfe_subdev_init_175,
\t.vfe_disable = vfe_disable,
\t.vfe_enable = vfe_enable,
\t.vfe_halt = vfe_halt,
\t.violation_read = vfe_violation_read,
\t.vfe_output_start = vfe_output_start_175,
\t.vfe_output_stop = vfe_output_stop_175,
\t.vfe_output_update = vfe_output_update_175,
};
'''
path.write_text(source)

(D/'camss-vfe-175-output.h').write_text('''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef CAMSS_VFE_175_OUTPUT_H
#define CAMSS_VFE_175_OUTPUT_H

#include <linux/types.h>

struct vfe_device;
struct vfe_output;
struct camss_buffer;

int vfe_175_validate_output(const struct vfe_output *output);
int vfe_175_validate_buffer(const struct vfe_output *output,
\t\t\t    const struct camss_buffer *buf);
void vfe_175_full_start(struct vfe_device *vfe, struct vfe_output *output);
void vfe_175_full_stop(struct vfe_device *vfe, struct vfe_output *output);
void vfe_175_full_update(struct vfe_device *vfe, struct vfe_output *output,
\t\t\t const struct camss_buffer *buf);
void vfe_175_comp_done(struct vfe_device *vfe, u8 comp);

#endif /* CAMSS_VFE_175_OUTPUT_H */
''')
(D/'camss-vfe-175-output.c').write_text('''// SPDX-License-Identifier: GPL-2.0-only
/* Qualcomm VFE175 single-IFE FULL NV12 write-master transport. */

#include <linux/io.h>
#include <linux/limits.h>

#include "camss.h"
#include "camss-vfe.h"
#include "camss-vfe-175-output.h"

#define VFE_175_FULL_MAX_WIDTH               4096
#define VFE_175_FULL_MAX_HEIGHT              4096
#define VFE_175_FULL_Y                       3
#define VFE_175_FULL_C                       4
#define VFE_175_FULL_MASK                    (BIT(3) | BIT(4))
#define VFE_175_BUS_CGC_OVERRIDE             0x200c
#define VFE_175_BUS_COMP_MASK                0x2010
#define VFE_175_BUS_ADDR_NO_SYNC             0x2084
#define VFE_175_WM_CFG(n)                    (0x2208 + (n) * 0x100)
#define VFE_175_WM_IMAGE_ADDR(n)             (0x2214 + (n) * 0x100)
#define VFE_175_WM_IMAGE_OFFSET(n)           (0x2218 + (n) * 0x100)
#define VFE_175_WM_WIDTH(n)                  (0x221c + (n) * 0x100)
#define VFE_175_WM_HEIGHT(n)                 (0x2220 + (n) * 0x100)
#define VFE_175_WM_PACKER(n)                 (0x2224 + (n) * 0x100)
#define VFE_175_WM_STRIDE(n)                 (0x2228 + (n) * 0x100)
#define VFE_175_WM_UBWC_MODE(n)              (0x2244 + (n) * 0x100)
#define VFE_175_WM_IRQ_PERIOD(n)             (0x2248 + (n) * 0x100)
#define VFE_175_WM_IRQ_PATTERN(n)            (0x224c + (n) * 0x100)
#define VFE_175_WM_DROP_PERIOD(n)            (0x2250 + (n) * 0x100)
#define VFE_175_WM_DROP_PATTERN(n)           (0x2254 + (n) * 0x100)
#define VFE_175_WM_FRAME_INC(n)              (0x2258 + (n) * 0x100)
#define VFE_175_WM_BURST_LIMIT(n)            (0x225c + (n) * 0x100)
#define VFE_175_PACKER_NV12                  0xe

int vfe_175_validate_output(const struct vfe_output *output)
{
\tconst struct v4l2_pix_format_mplane *pix = &output->video_out.active_fmt.fmt.pix_mp;
\tu32 stride = pix->plane_fmt[0].bytesperline;
\tu64 required;

\t/* One single-IFE FULL image, fixed Y/C clients and composite group zero. */
\tif (!output->line->is_pix || output->pad != MSM_VFE_PAD_SRC ||
\t    output != &output->line->output[0] || output->wm_num != 2 ||
\t    output->comp_group != 0 || output->line->num_outputs != 1 ||
\t    output->wm[0].bus_client != VFE_175_FULL_Y || output->wm[0].plane != 0 ||
\t    output->wm[1].bus_client != VFE_175_FULL_C || output->wm[1].plane != 1)
\t\treturn -EINVAL;
\tif (pix->pixelformat != V4L2_PIX_FMT_NV12 || pix->num_planes != 1 ||
\t    !pix->width || !pix->height || (pix->width & 1) || (pix->height & 1) ||
\t    pix->width > VFE_175_FULL_MAX_WIDTH ||
\t    pix->height > VFE_175_FULL_MAX_HEIGHT ||
\t    stride < pix->width || !IS_ALIGNED(stride, 16) || stride > U16_MAX)
\t\treturn -EINVAL;

\trequired = (u64)stride * pix->height * 3 / 2;
\tif (required > pix->plane_fmt[0].sizeimage)
\t\treturn -EINVAL;

\treturn 0;
}

int vfe_175_validate_buffer(const struct vfe_output *output,
\t\t\t    const struct camss_buffer *buf)
{
\tconst struct v4l2_pix_format_mplane *pix = &output->video_out.active_fmt.fmt.pix_mp;
\tu64 luma = (u64)pix->plane_fmt[0].bytesperline * pix->height;
\tu64 size = luma * 3 / 2;
\tu64 address = buf->addr[0];
\tint ret;

\tret = vfe_175_validate_output(output);
\tif (ret)
\t\treturn ret;
\tif (address > U32_MAX || size - 1 > U32_MAX - address)
\t\treturn -ERANGE;
\tif (!IS_ALIGNED(address, 16) || buf->addr[1] != address + luma)
\t\treturn -EINVAL;

\treturn 0;
}

/* Called only after line format and capture DMA preparation succeeded. */
void vfe_175_full_start(struct vfe_device *vfe, struct vfe_output *output)
{
\tconst struct v4l2_pix_format_mplane *pix = &output->video_out.active_fmt.fmt.pix_mp;
\tu32 stride = pix->plane_fmt[0].bytesperline;
\tu32 value;
\tunsigned int i;

\tvalue = readl_relaxed(vfe->base + VFE_175_BUS_CGC_OVERRIDE);
\twritel_relaxed(value | VFE_175_FULL_MASK, vfe->base + VFE_175_BUS_CGC_OVERRIDE);
\t/* Single IFE: no cross-core address synchronization. */
\tvalue = readl_relaxed(vfe->base + VFE_175_BUS_ADDR_NO_SYNC);
\twritel_relaxed(value | VFE_175_FULL_MASK, vfe->base + VFE_175_BUS_ADDR_NO_SYNC);
\tvalue = readl_relaxed(vfe->base + VFE_175_BUS_COMP_MASK);
\twritel_relaxed(value | VFE_175_FULL_MASK, vfe->base + VFE_175_BUS_COMP_MASK);

\tfor (i = 0; i < output->wm_num; i++) {
\t\tu8 wm = output->wm[i].bus_client;
\t\tu32 height = pix->height >> output->wm[i].plane;

\t\twritel_relaxed(0, vfe->base + VFE_175_WM_IMAGE_OFFSET(wm));
\t\twritel_relaxed(pix->width, vfe->base + VFE_175_WM_WIDTH(wm));
\t\twritel_relaxed(height, vfe->base + VFE_175_WM_HEIGHT(wm));
\t\twritel_relaxed(VFE_175_PACKER_NV12, vfe->base + VFE_175_WM_PACKER(wm));
\t\twritel_relaxed(stride, vfe->base + VFE_175_WM_STRIDE(wm));
\t\twritel_relaxed(stride * height, vfe->base + VFE_175_WM_FRAME_INC(wm));
\t\twritel_relaxed(0xf, vfe->base + VFE_175_WM_BURST_LIMIT(wm));
\t\twritel_relaxed(0, vfe->base + VFE_175_WM_IRQ_PERIOD(wm));
\t\twritel_relaxed(1, vfe->base + VFE_175_WM_IRQ_PATTERN(wm));
\t\twritel_relaxed(0, vfe->base + VFE_175_WM_DROP_PERIOD(wm));
\t\twritel_relaxed(1, vfe->base + VFE_175_WM_DROP_PATTERN(wm));
\t\tvalue = readl_relaxed(vfe->base + VFE_175_WM_UBWC_MODE(wm));
\t\twritel_relaxed(value & ~BIT(0), vfe->base + VFE_175_WM_UBWC_MODE(wm));
\t\twritel_relaxed(1, vfe->base + VFE_175_WM_CFG(wm));
\t}
}

void vfe_175_full_update(struct vfe_device *vfe, struct vfe_output *output,
\t\t\t const struct camss_buffer *buf)
{
\tunsigned int i;

\t/* 175 uses byte addresses; newer IFE address>>8 programming is different. */
\tfor (i = 0; i < output->wm_num; i++)
\t\twritel_relaxed(buf->addr[output->wm[i].plane],
\t\t\t       vfe->base + VFE_175_WM_IMAGE_ADDR(output->wm[i].bus_client));
}

void vfe_175_full_stop(struct vfe_device *vfe, struct vfe_output *output)
{
\tu32 value;
\tunsigned int i;

\tfor (i = 0; i < output->wm_num; i++)
\t\twritel_relaxed(0, vfe->base + VFE_175_WM_CFG(output->wm[i].bus_client));
\tvalue = readl_relaxed(vfe->base + VFE_175_BUS_COMP_MASK);
\twritel_relaxed(value & ~VFE_175_FULL_MASK, vfe->base + VFE_175_BUS_COMP_MASK);
}

void vfe_175_comp_done(struct vfe_device *vfe, u8 comp)
{
\tstruct camss_buf_done_info info = { };

\tif (comp >= 6 || vfe->res->line_num <= VFE_LINE_PIX ||
\t    !vfe->line[VFE_LINE_PIX].is_pix)
\t\treturn;

\tinfo.status = BIT(comp);
\t/* One image completion for the group, never one per Y/C client. */
\tvfe_buf_done(vfe, VFE_LINE_PIX, &info);
}
''')
git('diff','--check')
report=dict(stage=282,parent=BASE,source_candidate_only=True,full_dimensions_max=[4096,4096],
    fixed_full_clients=[3,4],nv12_packer=14,unshifted_byte_addresses=True,
    composite_groups=6,standard_capture_dma_validation=True,
    pix_line_still_not_exposed=True,no_board_or_userspace_change=True,not_deployed=True)
(ROOT/'output-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
