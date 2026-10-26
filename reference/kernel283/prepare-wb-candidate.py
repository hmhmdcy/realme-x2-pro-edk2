"""Stage a VFE175 WB backend without changing the running full-build source."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel283')
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE = '18b48939788bc7f95fb2999ea986846a67f0c62c'
SOURCE = TREE / 'drivers/media/platform/qcom/camss'
STAGE = PRIVATE / 'wb-candidate'
assert subprocess.check_output(['git', '-C', str(TREE), 'rev-parse', 'HEAD'], text=True).strip() == BASE
assert not subprocess.check_output(['git', '-C', str(TREE), 'status', '--porcelain'], text=True)
assert not STAGE.exists(), 'Inspect the existing candidate instead of replaying preparation'
STAGE.mkdir()
for source in SOURCE.iterdir():
    if source.suffix in ['.c', '.h'] or source.name == 'Makefile':
        (STAGE / source.name).write_bytes(source.read_bytes())

header = '''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef CAMSS_VFE_175_PIXEL_H
#define CAMSS_VFE_175_PIXEL_H

#include <linux/types.h>
#include <media/v4l2-isp.h>

struct vfe_device;
struct vfe_line;
struct v4l2_isp_buffer;
struct v4l2_isp_params_block_type_info;

/* Cached configuration survives parameter updates while WB is bypassed. */
struct vfe_175_pixel_state {
	u16 g_gain;
	u16 b_gain;
	u16 r_gain;
	bool wb_enabled;
};

extern const struct v4l2_isp_params_block_type_info vfe_175_params_info[2];
void vfe_175_pixel_prepare(struct vfe_line *line);
void vfe_175_params_apply(struct vfe_device *vfe, struct vfe_line *line,
			  const struct v4l2_isp_buffer *params);

#endif /* CAMSS_VFE_175_PIXEL_H */
'''
source = '''// SPDX-License-Identifier: GPL-2.0-only
/* Qualcomm SM8150 full VFE175 pixel module programming. */

#include <linux/bitfield.h>
#include <linux/io.h>
#include <linux/qcom-camss-config.h>

#include "camss.h"
#include "camss-vfe.h"
#include "camss-vfe-175-pixel.h"

#define VFE_175_WB_GAIN_0		0x6fc
#define VFE_175_WB_GAIN_1		0x700
#define VFE_175_WB_OFFSET_0	0x704
#define VFE_175_WB_OFFSET_1	0x708
#define VFE_175_WB_GREEN		GENMASK(11, 0)
#define VFE_175_WB_BLUE		GENMASK(27, 16)
#define VFE_175_WB_RED		GENMASK(11, 0)
#define VFE_175_WB_OFFSET_GB	(GENMASK(14, 0) | GENMASK(30, 16))
#define VFE_175_WB_OFFSET_R	GENMASK(14, 0)
#define VFE_175_WB_UNITY		128

static u32 vfe_175_wb_q7(u16 gain)
{
	/* The common block uses U15Q10; this hardware uses U12Q7. */
	return min_t(u32, ((u32)gain + 4) >> 3, 4095);
}

static void vfe_175_wb_write(struct vfe_device *vfe)
{
	const struct vfe_175_pixel_state *state = &vfe->pixel175;
	u32 g = VFE_175_WB_UNITY, b = g, r = g;
	u32 value;

	if (state->wb_enabled) {
		g = vfe_175_wb_q7(state->g_gain);
		b = vfe_175_wb_q7(state->b_gain);
		r = vfe_175_wb_q7(state->r_gain);
	}

	value = readl_relaxed(vfe->base + VFE_175_WB_GAIN_0);
	value &= ~(VFE_175_WB_GREEN | VFE_175_WB_BLUE);
	value |= FIELD_PREP(VFE_175_WB_GREEN, g) |
		 FIELD_PREP(VFE_175_WB_BLUE, b);
	writel_relaxed(value, vfe->base + VFE_175_WB_GAIN_0);
	value = readl_relaxed(vfe->base + VFE_175_WB_GAIN_1);
	value &= ~VFE_175_WB_RED;
	writel_relaxed(value | FIELD_PREP(VFE_175_WB_RED, r),
		       vfe->base + VFE_175_WB_GAIN_1);

	/* No offset conversion is advertised: only zero offsets are accepted. */
	value = readl_relaxed(vfe->base + VFE_175_WB_OFFSET_0);
	writel_relaxed(value & ~VFE_175_WB_OFFSET_GB,
		       vfe->base + VFE_175_WB_OFFSET_0);
	value = readl_relaxed(vfe->base + VFE_175_WB_OFFSET_1);
	writel_relaxed(value & ~VFE_175_WB_OFFSET_R,
		       vfe->base + VFE_175_WB_OFFSET_1);
}

static int vfe_175_wb_validate(struct device *dev,
			       const struct v4l2_isp_block_header *block)
{
	const struct camss_params_wb_gain *wb;

	if (block->flags & ~(V4L2_ISP_PARAMS_FL_BLOCK_ENABLE |
			     V4L2_ISP_PARAMS_FL_BLOCK_DISABLE) ||
	    block->flags == (V4L2_ISP_PARAMS_FL_BLOCK_ENABLE |
			     V4L2_ISP_PARAMS_FL_BLOCK_DISABLE))
		return -EINVAL;
	/* A DISABLE block may contain only the header. Never read its payload. */
	if (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE)
		return 0;

	wb = container_of(block, struct camss_params_wb_gain, header);
	if (wb->g_gain > 32767 || wb->b_gain > 32767 || wb->r_gain > 32767 ||
	    wb->g_sub || wb->b_sub || wb->r_sub ||
	    wb->g_add || wb->b_add || wb->r_add ||
	    wb->_pad[0] || wb->_pad[1] || wb->_pad[2])
		return -EINVAL;

	return 0;
}

static int vfe_175_params_unsupported(struct device *dev,
				      const struct v4l2_isp_block_header *block)
{
	return -EINVAL;
}

const struct v4l2_isp_params_block_type_info vfe_175_params_info[2] = {
	[0] = {
		.size = sizeof(struct v4l2_isp_block_header),
		.block_validate = vfe_175_params_unsupported,
	},
	[CAMSS_PARAMS_WB_GAIN] = {
		.size = sizeof(struct camss_params_wb_gain),
		.block_validate = vfe_175_wb_validate,
	},
};

void vfe_175_pixel_prepare(struct vfe_line *line)
{
	struct vfe_device *vfe = to_vfe(line);

	if (!line->is_pix)
		return;
	/* Reopening a line starts from neutral gains, then queued params apply. */
	vfe->pixel175 = (struct vfe_175_pixel_state) {
		.g_gain = 1024,
		.b_gain = 1024,
		.r_gain = 1024,
		.wb_enabled = true,
	};
	vfe_175_wb_write(vfe);
}

void vfe_175_params_apply(struct vfe_device *vfe, struct vfe_line *line,
			  const struct v4l2_isp_buffer *params)
{
	size_t offset = 0;

	if (!line->is_pix)
		return;
	/* The common parser checked sizes, types and payloads before queueing. */
	while (offset < params->data_size) {
		const struct v4l2_isp_block_header *block =
			(const void *)&params->data[offset];
		const struct camss_params_wb_gain *wb;

		if (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE) {
			vfe->pixel175.wb_enabled = false;
		} else {
			wb = container_of(block, struct camss_params_wb_gain, header);
			vfe->pixel175.g_gain = wb->g_gain;
			vfe->pixel175.b_gain = wb->b_gain;
			vfe->pixel175.r_gain = wb->r_gain;
			if (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_ENABLE)
				vfe->pixel175.wb_enabled = true;
		}
		vfe_175_wb_write(vfe);
		offset += block->size;
	}
}
'''
(STAGE / 'camss-vfe-175-pixel.h').write_text(header)
(STAGE / 'camss-vfe-175-pixel.c').write_text(source)

def replace(name, old, new):
    path = STAGE / name
    text = path.read_text()
    assert text.count(old) == 1, (name, old)
    path.write_text(text.replace(old, new))

replace('Makefile', '\t\tcamss-vfe-175-output.o \\\n', '\t\tcamss-vfe-175-output.o \\\n\t\tcamss-vfe-175-pixel.o \\\n')
replace('camss-vfe.h', '#include "camss-vfe-gen1.h"', '#include "camss-vfe-gen1.h"\n#include "camss-vfe-175-pixel.h"')
replace('camss-vfe.h', 'struct vfe_device {\n', 'struct vfe_device {\n\tstruct vfe_175_pixel_state pixel175;\n')
replace('camss-vfe-17x.c', '\t.prepare_dma_buffer = vfe_prepare_dma_175,', '\t.prepare_dma_buffer = vfe_prepare_dma_175,\n\t.prepare_buffer = vfe_params_prepare,')
replace('camss-vfe-17x.c', '\treturn vfe_175_camif_prepare(line);', '\tret = vfe_175_camif_prepare(line);\n\tif (ret)\n\t\treturn ret;\n\tvfe_175_pixel_prepare(line);\n\n\treturn 0;')
replace('camss-vfe-17x.c', 'const struct vfe_hw_ops vfe_ops_175 = {', 'const struct vfe_hw_ops vfe_ops_175 = {\n\t.params_info = vfe_175_params_info,\n\t.params_num_types = ARRAY_SIZE(vfe_175_params_info),\n\t.vfe_params_apply = vfe_175_params_apply,')
replace('camss-vfe.c', 'static void vfe_params_apply_queued(', 'void vfe_params_apply_queued(')
replace('camss-vfe.h', 'int vfe_enable_v2(struct vfe_line *line);', 'int vfe_enable_v2(struct vfe_line *line);\nvoid vfe_params_apply_queued(struct vfe_device *vfe, struct vfe_line *line);')
replace('camss-vfe-17x.c', '\tret = vfe_enable_output_v2(line);', '\t/* Queued PIX parameters must override defaults before the first frame. */\n\tif (line->is_pix)\n\t\tvfe_params_apply_queued(vfe, line);\n\n\tret = vfe_enable_output_v2(line);')

uapi = PRIVATE / 'wb-uapi/linux/qcom-camss-config.h'
uapi.parent.mkdir(parents=True)
text = (TREE/'include/uapi/linux/qcom-camss-config.h').read_text()
old = '#define CAMSS_PARAMS_IFE_MAX_PAYLOAD\t\t\\\n\tsizeof(struct camss_params_aec_bhist)'
assert text.count(old) == 1
uapi.write_text(text.replace(old, '#define CAMSS_PARAMS_IFE_MAX_PAYLOAD\t\t\\\n\t(sizeof(struct camss_params_aec_bhist) +\t\\\n\t sizeof(struct camss_params_wb_gain))'))

changed = [p.name for p in STAGE.iterdir() if not (SOURCE / p.name).exists() or p.read_bytes() != (SOURCE / p.name).read_bytes()]
report = dict(stage=283, base=BASE, changed=sorted(changed),
              sha256={n:hashlib.sha256((STAGE/n).read_bytes()).hexdigest() for n in sorted(changed)},
              original_tree_unchanged=True, not_deployed=True, no_hardware_isp_claim=True)
(PRIVATE / 'wb-stage-private.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
