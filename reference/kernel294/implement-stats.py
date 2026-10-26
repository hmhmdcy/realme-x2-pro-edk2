"""Add VFE175 BHIST transport using fixed protocol facts and existing typed UAPI."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel');D=TREE/'drivers/media/platform/qcom/camss'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='1aa1955077c977b611c722eca0bc467c3bf052ed' and not git('status','--porcelain')
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-stats294'],check=True,capture_output=True)
def edit(name,old,new):
 p=D/name;s=p.read_text();assert s.count(old)==1,(name,old);p.write_text(s.replace(old,new))
edit('camss-video.h','\tint (*prepare_dma_buffer)(struct camss_video *vid, struct camss_buffer *buf);','''	int (*prepare_dma_buffer)(struct camss_video *vid, struct camss_buffer *buf);
	/* Optional: start/stop a metadata output without restarting its image. */
	int (*start_metadata)(struct camss_video *vid);
	void (*stop_metadata)(struct camss_video *vid);''')
edit('camss-video.c','''static int video_meta_start_streaming(struct vb2_queue *q, unsigned int count)
{
	return 0;
}''','''static int video_meta_start_streaming(struct vb2_queue *q, unsigned int count)
{
	struct camss_video *video = vb2_get_drv_priv(q);
	int ret = 0;

	if (video->ops->start_metadata)
		ret = video->ops->start_metadata(video);
	if (ret)
		video->ops->flush_buffers(video, VB2_BUF_STATE_QUEUED);

	return ret;
}''')
edit('camss-video.c','''static void video_meta_stop_streaming(struct vb2_queue *q)
{
	struct camss_video *video = vb2_get_drv_priv(q);

	video->ops->flush_buffers(video, VB2_BUF_STATE_ERROR);
}''','''static void video_meta_stop_streaming(struct vb2_queue *q)
{
	struct camss_video *video = vb2_get_drv_priv(q);

	if (video->ops->stop_metadata)
		video->ops->stop_metadata(video);
	video->ops->flush_buffers(video, VB2_BUF_STATE_ERROR);
}''')
edit('camss-vfe.h','int vfe_params_prepare(struct camss_video *vid, struct camss_buffer *buf);','''int vfe_params_prepare(struct camss_video *vid, struct camss_buffer *buf);
int vfe_start_metadata_v2(struct camss_video *vid);
void vfe_stop_metadata_v2(struct camss_video *vid);''')
edit('camss-vfe.c','''int vfe_enable_output_v2(struct vfe_line *line)''','''/* The image owns the line; metadata controls only its own DMA output. */
int vfe_start_metadata_v2(struct camss_video *vid)
{
	struct vfe_output *output = container_of(vid, struct vfe_output, video_out);
	struct vfe_line *line = output->line;
	struct vfe_device *vfe = to_vfe(line);
	unsigned long flags;
	int ret = 0;

	if (output->pad != MSM_VFE_PAD_SRC_STATS || !output->wm_num)
		return 0;

	spin_lock_irqsave(&vfe->output_lock, flags);
	if (line->output[0].state == VFE_OUTPUT_ON) {
		ret = vfe_enable_one_output(line, output);
		if (!ret) {
			output->sequence = line->output[0].sequence;
			vfe->res->hw_ops->reg_update(vfe, line->id);
		}
	}
	spin_unlock_irqrestore(&vfe->output_lock, flags);

	return ret;
}

void vfe_stop_metadata_v2(struct camss_video *vid)
{
	struct vfe_output *output = container_of(vid, struct vfe_output, video_out);
	struct vfe_line *line = output->line;
	struct vfe_device *vfe = to_vfe(line);
	const struct vfe_hw_ops *ops = vfe->res->hw_ops;
	unsigned long flags;
	unsigned int i;

	if (output->pad != MSM_VFE_PAD_SRC_STATS || !output->wm_num)
		return;

	spin_lock_irqsave(&vfe->output_lock, flags);
	if (output->state == VFE_OUTPUT_ON) {
		if (ops->vfe_output_stop)
			ops->vfe_output_stop(vfe, output);
		else
			for (i = 0; i < output->wm_num; i++)
				ops->vfe_wm_stop(vfe, output->wm[i].bus_client, line);
		output->state = VFE_OUTPUT_OFF;
		ops->reg_update(vfe, line->id);
	}
	spin_unlock_irqrestore(&vfe->output_lock, flags);
}

int vfe_enable_output_v2(struct vfe_line *line)''')
edit('camss-vfe.c','''		if (output->pad == MSM_VFE_PAD_SRC_STATS && output->wm_num) {
			video->type''','''		if (output->pad == MSM_VFE_PAD_SRC_STATS && output->wm_num) {
			/* Backends may declare statistics before allocating their DMA. */
			if (!output->dma_vaddr) {
				ret = vfe_alloc_stats(vfe, output);
				if (ret)
					return ret;
			}
			video->type''')
edit('camss-vfe.c','''error_link:
	msm_video_unregister(video_out);''','''error_link:
	/* Registration may already have published an earlier metadata node. */
	vfe_unregister_meta_nodes(&vfe->line[i]);
	msm_video_unregister(video_out);''')
header='''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef CAMSS_VFE_175_STATS_H
#define CAMSS_VFE_175_STATS_H

#include <linux/types.h>

struct device;
struct camss_video;
struct camss_buffer;
struct vfe_device;
struct vfe_line;
struct vfe_output;
struct v4l2_isp_block_header;

struct vfe_175_stats_state {
	u16 left, top, width, height;
	bool enabled;
};

int vfe_175_bhist_validate(struct device *dev,
			   const struct v4l2_isp_block_header *block);
int vfe_175_stats_validate_output(const struct vfe_output *output);
int vfe_175_stats_prepare(struct vfe_line *line);
int vfe_175_start_metadata(struct camss_video *vid);
void vfe_175_stats_params(struct vfe_device *vfe, struct vfe_line *line,
			  const struct v4l2_isp_block_header *block);
void vfe_175_stats_start(struct vfe_device *vfe, struct vfe_output *output);
void vfe_175_stats_stop(struct vfe_device *vfe, struct vfe_output *output);
void vfe_175_stats_update(struct vfe_device *vfe, struct vfe_output *output);

#endif /* CAMSS_VFE_175_STATS_H */
'''
(D/'camss-vfe-175-stats.h').write_text(header)
src='''// SPDX-License-Identifier: GPL-2.0-only
/* Qualcomm SM8150 VFE175 linear luma Bayer histogram. */

#include <linux/bitfield.h>
#include <linux/io.h>
#include <linux/limits.h>
#include <linux/qcom-camss-config.h>

#include "camss.h"
#include "camss-vfe.h"
#include "camss-vfe-175-stats.h"

#define VFE_175_STATS_ENABLE             0x044
#define VFE_175_BHIST_ENABLE             BIT(5)
#define VFE_175_STATS_CONFIG             0xaac
#define VFE_175_BHIST_UNIFORM            BIT(4)
#define VFE_175_BHIST_CHANNEL            GENMASK(23, 21)
#define VFE_175_BHIST_OFFSET             0xbe4
#define VFE_175_BHIST_REGIONS            0xbe8
#define VFE_175_BHIST_MAX_WIDTH          8192
#define VFE_175_BHIST_MAX_HEIGHT         16384
#define VFE_175_BHIST_CLIENT             16
#define VFE_175_BHIST_GROUP              1
#define VFE_175_BHIST_BYTES              (CAMSS_STATS_BHIST_BINS * sizeof(u32))
#define VFE_175_BUS_CGC                  0x200c
#define VFE_175_BUS_COMP(n)              (0x2010 + (n) * 4)
#define VFE_175_BUS_NO_SYNC              0x2084
#define VFE_175_WM(n, r)                 (0x2200 + (n) * 0x100 + (r))

static struct vfe_output *vfe_175_stats_output(struct vfe_line *line)
{
	unsigned int i;

	for (i = 1; i < line->num_outputs; i++)
		if (line->output[i].pad == MSM_VFE_PAD_SRC_STATS)
			return &line->output[i];

	return NULL;
}

static void vfe_175_bhist_write(struct vfe_device *vfe, struct vfe_line *line)
{
	const struct vfe_175_stats_state *s = &vfe->pixel175.stats;
	struct vfe_output *output = vfe_175_stats_output(line);
	u32 value;

	/* Region offsets are pixels; sizes count 2x2 quads minus one. */
	writel_relaxed(s->left | ((u32)s->top << 16),
		       vfe->base + VFE_175_BHIST_OFFSET);
	writel_relaxed((s->width / 2 - 1) | ((s->height / 2 - 1) << 16),
		       vfe->base + VFE_175_BHIST_REGIONS);
	value = readl_relaxed(vfe->base + VFE_175_STATS_CONFIG);
	/* Channel zero is Y. Uniform bins shift the 14-bit data down to 10. */
	value = (value & ~VFE_175_BHIST_CHANNEL) | VFE_175_BHIST_UNIFORM;
	writel_relaxed(value, vfe->base + VFE_175_STATS_CONFIG);
	value = readl_relaxed(vfe->base + VFE_175_STATS_ENABLE);
	value &= ~VFE_175_BHIST_ENABLE;
	if (s->enabled && output && output->state == VFE_OUTPUT_ON)
		value |= VFE_175_BHIST_ENABLE;
	writel_relaxed(value, vfe->base + VFE_175_STATS_ENABLE);
}

int vfe_175_bhist_validate(struct device *dev,
			   const struct v4l2_isp_block_header *block)
{
	const struct camss_params_aec_bhist *r;

	if (block->flags & ~(V4L2_ISP_PARAMS_FL_BLOCK_ENABLE |
			     V4L2_ISP_PARAMS_FL_BLOCK_DISABLE) ||
	    block->flags == (V4L2_ISP_PARAMS_FL_BLOCK_ENABLE |
			     V4L2_ISP_PARAMS_FL_BLOCK_DISABLE))
		return -EINVAL;
	if (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE)
		return 0;

	r = container_of(block, struct camss_params_aec_bhist, header);
	/* Horizontal region count has a minimum of two quads on this IFE. */
	if ((r->left | r->top | r->width | r->height) & 1 ||
	    r->width < 4 || r->height < 2 ||
	    r->left >= VFE_175_BHIST_MAX_WIDTH ||
	    r->top >= VFE_175_BHIST_MAX_HEIGHT ||
	    r->width > VFE_175_BHIST_MAX_WIDTH ||
	    r->height > VFE_175_BHIST_MAX_HEIGHT)
		return -EINVAL;

	return 0;
}

int vfe_175_stats_validate_output(const struct vfe_output *output)
{
	if (output->pad != MSM_VFE_PAD_SRC_STATS || output->wm_num != 1 ||
	    output->wm[0].bus_client != VFE_175_BHIST_CLIENT ||
	    output->wm[0].plane || output->comp_group != VFE_175_BHIST_GROUP ||
	    output->dma_size != VFE_175_BHIST_BYTES || !output->dma_vaddr)
		return -EINVAL;
	if (output->dma_addr > U32_MAX ||
	    VFE_175_BHIST_BYTES - 1 > U32_MAX - output->dma_addr ||
	    !IS_ALIGNED(output->dma_addr, 256))
		return -ERANGE;

	return 0;
}

int vfe_175_stats_prepare(struct vfe_line *line)
{
	struct vfe_device *vfe = to_vfe(line);
	struct vfe_output *output = vfe_175_stats_output(line);
	u32 width = line->fmt[MSM_VFE_PAD_SINK].width & ~1U;
	u32 height = line->fmt[MSM_VFE_PAD_SINK].height & ~1U;
	bool valid = width >= 4 && height >= 2 &&
		     width <= VFE_175_BHIST_MAX_WIDTH &&
		     height <= VFE_175_BHIST_MAX_HEIGHT;

	if (output && vb2_is_streaming(&output->video_out.vb2_q) && !valid)
		return -EINVAL;
	vfe->pixel175.stats = (struct vfe_175_stats_state) {
		.width = valid ? width : 0,
		.height = valid ? height : 0,
		.enabled = valid,
	};
	if (valid)
		vfe_175_bhist_write(vfe, line);

	return 0;
}

void vfe_175_stats_params(struct vfe_device *vfe, struct vfe_line *line,
			  const struct v4l2_isp_block_header *block)
{
	struct vfe_175_stats_state *s = &vfe->pixel175.stats;
	u32 w = line->fmt[MSM_VFE_PAD_SINK].width & ~1U;
	u32 h = line->fmt[MSM_VFE_PAD_SINK].height & ~1U;
	const struct camss_params_aec_bhist *r;

	if (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE) {
		s->enabled = false;
	} else {
		if (w < 4 || h < 2)
			return;
		r = container_of(block, struct camss_params_aec_bhist, header);
		s->left = min_t(u32, r->left, w - 4);
		s->top = min_t(u32, r->top, h - 2);
		s->width = min_t(u32, r->width, w - s->left);
		s->height = min_t(u32, r->height, h - s->top);
		if (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_ENABLE)
			s->enabled = true;
	}
	if (s->width && s->height)
		vfe_175_bhist_write(vfe, line);
}

int vfe_175_start_metadata(struct camss_video *vid)
{
	struct vfe_output *output = container_of(vid, struct vfe_output, video_out);
	struct vfe_device *vfe = to_vfe(output->line);

	if (output->pad == MSM_VFE_PAD_SRC_STATS &&
	    output->line->output[0].state == VFE_OUTPUT_ON &&
	    (!vfe->pixel175.stats.width || !vfe->pixel175.stats.height))
		return -EINVAL;

	return vfe_start_metadata_v2(vid);
}

void vfe_175_stats_start(struct vfe_device *vfe, struct vfe_output *output)
{
	u32 wm = output->wm[0].bus_client;
	u32 value;

	memset(output->dma_vaddr, 0, output->dma_size);
	value = readl_relaxed(vfe->base + VFE_175_BUS_CGC);
	writel_relaxed(value | BIT(wm), vfe->base + VFE_175_BUS_CGC);
	value = readl_relaxed(vfe->base + VFE_175_BUS_NO_SYNC);
	writel_relaxed(value | BIT(wm), vfe->base + VFE_175_BUS_NO_SYNC);
	value = readl_relaxed(vfe->base + VFE_175_BUS_COMP(output->comp_group));
	writel_relaxed(value | BIT(wm),
		       vfe->base + VFE_175_BUS_COMP(output->comp_group));
	/* Statistics are a self-sized PLAIN64 packet, not a strided image. */
	writel_relaxed(0, vfe->base + VFE_175_WM(wm, 0x18));
	writel_relaxed(0, vfe->base + VFE_175_WM(wm, 0x1c));
	writel_relaxed(0, vfe->base + VFE_175_WM(wm, 0x20));
	writel_relaxed(0xa, vfe->base + VFE_175_WM(wm, 0x24));
	writel_relaxed(1, vfe->base + VFE_175_WM(wm, 0x28));
	writel_relaxed(0, vfe->base + VFE_175_WM(wm, 0x48));
	writel_relaxed(1, vfe->base + VFE_175_WM(wm, 0x4c));
	writel_relaxed(0, vfe->base + VFE_175_WM(wm, 0x50));
	writel_relaxed(1, vfe->base + VFE_175_WM(wm, 0x54));
	writel_relaxed(VFE_175_BHIST_BYTES, vfe->base + VFE_175_WM(wm, 0x58));
	writel_relaxed(0xf, vfe->base + VFE_175_WM(wm, 0x5c));
	writel_relaxed(3, vfe->base + VFE_175_WM(wm, 0x08));
	vfe_175_bhist_write(vfe, output->line);
}

void vfe_175_stats_update(struct vfe_device *vfe, struct vfe_output *output)
{
	writel_relaxed(output->dma_addr,
		       vfe->base + VFE_175_WM(output->wm[0].bus_client, 0x14));
}

void vfe_175_stats_stop(struct vfe_device *vfe, struct vfe_output *output)
{
	u32 value = readl_relaxed(vfe->base + VFE_175_STATS_ENABLE);
	u32 wm = output->wm[0].bus_client;

	writel_relaxed(value & ~VFE_175_BHIST_ENABLE,
		       vfe->base + VFE_175_STATS_ENABLE);
	writel_relaxed(0, vfe->base + VFE_175_WM(wm, 0x08));
	/* Complete the stop before metadata buffers can be returned. */
	readl(vfe->base + VFE_175_WM(wm, 0x08));
	value = readl_relaxed(vfe->base + VFE_175_BUS_COMP(output->comp_group));
	writel_relaxed(value & ~BIT(wm),
		       vfe->base + VFE_175_BUS_COMP(output->comp_group));
}
'''
(D/'camss-vfe-175-stats.c').write_text(src)
edit('Makefile','\t\tcamss-vfe-175-pixel.o \\','\t\tcamss-vfe-175-pixel.o \\\n\t\tcamss-vfe-175-stats.o \\')
edit('camss-vfe-175-pixel.h','#include <media/v4l2-isp.h>','#include <media/v4l2-isp.h>\n#include "camss-vfe-175-stats.h"')
edit('camss-vfe-175-pixel.h','\tbool wb_enabled;','\tbool wb_enabled;\n\tstruct vfe_175_stats_state stats;')
edit('camss-vfe-175-pixel.h','vfe_175_params_info[2]','vfe_175_params_info[6]')
edit('camss-vfe-175-pixel.c','vfe_175_params_info[2]','vfe_175_params_info[6]')
needle='''	[CAMSS_PARAMS_WB_GAIN] = {
		.size = sizeof(struct camss_params_wb_gain),
		.block_validate = vfe_175_wb_validate,
	},'''
edit('camss-vfe-175-pixel.c',needle,needle+'''
	[CAMSS_PARAMS_CHROMA_ENHAN] = {
		.size = sizeof(struct camss_params_chroma_enhan),
		.block_validate = vfe_175_params_unsupported,
	},
	[CAMSS_PARAMS_COLOR_CORRECT] = {
		.size = sizeof(struct camss_params_color_correct),
		.block_validate = vfe_175_params_unsupported,
	},
	[CAMSS_PARAMS_GAMMA] = {
		.size = sizeof(struct camss_params_gamma),
		.block_validate = vfe_175_params_unsupported,
	},
	[CAMSS_PARAMS_AEC_BHIST] = {
		.size = sizeof(struct camss_params_aec_bhist),
		.block_validate = vfe_175_bhist_validate,
	},''')
edit('camss-vfe-175-pixel.c','\tvfe_175_wb_write(vfe);\n\n\treturn 0;','\tvfe_175_wb_write(vfe);\n\tret = vfe_175_stats_prepare(line);\n\tif (ret)\n\t\tgoto error;\n\n\treturn 0;')
edit('camss-vfe-175-pixel.c','''		const struct camss_params_wb_gain *wb;

		if (block->flags''','''		const struct camss_params_wb_gain *wb;

		if (block->type == CAMSS_PARAMS_AEC_BHIST) {
			vfe_175_stats_params(vfe, line, block);
			offset += block->size;
			continue;
		}
		if (block->flags''')
edit('camss-vfe-17x.c','''	.prepare_buffer = vfe_params_prepare,
};''','''	.prepare_buffer = vfe_params_prepare,
	.start_metadata = vfe_175_start_metadata,
	.stop_metadata = vfe_stop_metadata_v2,
};''')
edit('camss-vfe-17x.c','''		/* Keep shared pad indices; undeclared DS/stats reject formats. */
		vfe_set_pix(pix, 2);''','''		vfe_add_stats(&pix->output[2], 16, 1);
		/* Keep shared pad indices; undeclared DS outputs reject formats. */
		vfe_set_pix(pix, 3);''')
for signature,call in [('start','vfe_175_stats_start(vfe, output)'),('stop','vfe_175_stats_stop(vfe, output)'),('update','vfe_175_stats_update(vfe, output)')]:
 p=D/'camss-vfe-17x.c';s=p.read_text();start=s.index('static void vfe_output_'+signature+'_175(');end=s.index('\n}',start);fragment=s[start:end];needle='\tif (output->line->is_pix)';assert needle in fragment
 fragment=fragment.replace(needle,'\tif (output->pad == MSM_VFE_PAD_SRC_STATS)\n\t\t'+call+';\n\telse if (output->line->is_pix)',1);p.write_text(s[:start]+fragment+s[end:])
edit('camss-vfe-175-output.c','#include "camss-vfe-175-output.h"','#include "camss-vfe-175-output.h"\n#include "camss-vfe-175-stats.h"')
edit('camss-vfe-175-output.c','''	} else if (output->line->num_outputs != 1) {
		return -EINVAL;
	}''','''	} else if (output->line->num_outputs == 3) {
		const struct vfe_output *params = &output->line->output[1];

		if (params->pad != MSM_VFE_PAD_SINK_PARAMS || params->wm_num ||
		    vfe_175_stats_validate_output(&output->line->output[2]))
			return -EINVAL;
	} else if (output->line->num_outputs != 1) {
		return -EINVAL;
	}''')
subprocess.run(['git','-C',str(TREE),'diff','--check'],check=True,capture_output=True)
patch=subprocess.check_output(['git','-C',str(TREE),'diff']);(ROOT/'vfe175-stats-candidate.patch').write_bytes(patch)
# New files are separately copied until the full staged diff is saved after testing.
for name in ['camss-vfe-175-stats.c','camss-vfe-175-stats.h']:(ROOT/name).write_bytes((D/name).read_bytes())
report=dict(stage=294,parent=git('rev-parse','HEAD'),branch=git('branch','--show-current'),modified_files=git('status','--porcelain').splitlines(),same_typed_uapi=True,stats_client=16,stats_comp_group=1,stats_bins=1024,no_dt_firmware_or_product_userspace_changes=True,not_compiled_or_deployed=True)
(ROOT/'stats-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
