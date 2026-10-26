"""Connect an explicit PD10 image output and calibrated WM5 runtime."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
kernel=m.mounted_build().parent/'source354';directory=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True)
base='dbefc5bdd8de8da07128171423f098a38d6e45b0';assert git('rev-parse','HEAD').strip()==base and not git('status','--porcelain')
for path in [kernel,*kernel.parents]:assert not (path/'AGENTS.md').exists()
subprocess.run(['git','-C',str(kernel),'switch','-c','samurai-vfe175-ds4-dma427'],check=True,capture_output=True)
changed=[]
def write(name,text):
 path=Path(name) if name.startswith('include/') else directory/name
 (kernel/path).write_text(text);changed.append(path)
def read(name):return (kernel/directory/name).read_text()
def replace(text,old,new,count=1):
 assert text.count(old)==count,(old,text.count(old),count)
 return text.replace(old,new)

path='include/uapi/linux/qcom-camss-config.h';text=(kernel/path).read_text()
text=replace(text,'\tCAMSS_PARAMS_IFE_GAMMA = 7,','\tCAMSS_PARAMS_IFE_GAMMA = 7,\n\tCAMSS_PARAMS_IFE_DS4 = 8,')
text=replace(text,'#include <linux/types.h>','#include <linux/types.h>\n#include <linux/videodev2.h>')
text=replace(text,'/* Number of entries in each gamma channel LUT. */','''/* Local experimental identifier, not reserved upstream. Single-plane PD10:
 * each 2x2 YUV420 block occupies eight bytes. SM8150 rows are aligned to
 * 192 bytes and the packed row count to four; bpl describes packed rows. */
#define V4L2_PIX_FMT_QCOM_PD10_LOCAL v4l2_fourcc('Q', 'P', '1', '0')

/* DS4 configuration only. Flags and reserved must be zero. Stream lifetime
 * controls the hardware enable; coefficients come from selected tuning. */
struct camss_params_ife_ds4 {
	struct v4l2_isp_block_header header;
	__u16 coefficient[3];
	__u16 reserved;
} __attribute__((aligned(8)));

/* Number of entries in each gamma channel LUT. */''')
write(path,text)

text=read('camss-format.h');text=replace(text,'struct camss_formats {','''struct camss_pd10_layout {
	u32 stride, slice_height, bytes;
};
int camss_format_pd10_layout(u32 width, u32 height,
			     struct camss_pd10_layout *layout);

struct camss_formats {''');write('camss-format.h',text)
text=read('camss-format.c');text=replace(text,'#include <linux/lcm.h>','#include <linux/lcm.h>\n#include <linux/math.h>')
write('camss-format.c',text+'\n'+(HERE/'pd10-layout.c').read_text())
text=read('camss-video.h');text=replace(text,'\tunsigned int line_based;','\tunsigned int line_based;\n\t/* Auxiliary image DMA follows the primary line without restarting it. */\n\tbool auxiliary;');write('camss-video.h',text)
text=read('camss-video.c');text=replace(text,'#include <linux/slab.h>','#include <linux/slab.h>\n#include <linux/qcom-camss-config.h>')
text=replace(text,'#include "camss-video.h"','#include "camss-video.h"\n#include "camss-format.h"')
special='''	if (pix->pixelformat == V4L2_PIX_FMT_QCOM_PD10_LOCAL) {
		struct camss_pd10_layout layout;
		int ret = camss_format_pd10_layout(pix->width, pix->height, &layout);

		if (ret)
			return ret;
		pix->plane_fmt[0].bytesperline = layout.stride;
		pix->plane_fmt[0].sizeimage = layout.bytes;
	}
'''
start=text.index('static int video_mbus_to_pix_mp(');end=text.index('static struct v4l2_subdev *video_remote_subdev',start)
part=text[start:end];part=replace(part,'\n\treturn 0;','\n'+special+'\n\treturn 0;');text=text[:start]+part+text[end:]
start=text.index('static int __video_try_fmt(');end=text.index('static int video_try_fmt(',start)
part=text[start:end];part=replace(part,'\n\treturn 0;','\n'+special.replace('pix->','pix_mp->')+'\n\treturn 0;');text=text[:start]+part+text[end:]
needle='\tret = video_device_pipeline_alloc_start(vdev);'
text=replace(text,needle,'''	if (video->auxiliary) {
		ret = video_check_format(video);
		if (!ret)
			ret = video->ops->start_metadata ?
				video->ops->start_metadata(video) : -EINVAL;
		if (ret)
			video->ops->flush_buffers(video, VB2_BUF_STATE_QUEUED);
		return ret;
	}

'''+needle)
start=text.index('static void video_stop_streaming(');end=text.index('static void video_unprepare_streaming(',start)
part=text[start:end];part=replace(part,'\n\tif (subdev &&','''
	if (video->auxiliary) {
		if (video->ops->stop_metadata)
			video->ops->stop_metadata(video);
		video->ops->flush_buffers(video, VB2_BUF_STATE_ERROR);
		return;
	}

	if (subdev &&''');text=text[:start]+part+text[end:];write('camss-video.c',text)

text=read('camss-vfe-175-ds4.h');text=replace(text,'#endif /* CAMSS_VFE_175_DS4_H */','''struct device;
struct vfe_device;
struct vfe_line;
struct vfe_output;
struct camss_buffer;
struct v4l2_isp_block_header;
struct v4l2_isp_buffer;
struct camss_formats;
struct v4l2_frmsize_stepwise;
extern const struct camss_formats vfe_formats_ds4_175;
extern const struct v4l2_frmsize_stepwise vfe_frame_sizes_ds4_175;
int vfe_175_ds4_validate(struct device *dev, const struct v4l2_isp_block_header *block);
int vfe_175_ds4_validate_line(struct vfe_line *line, const struct v4l2_isp_buffer *params);
void vfe_175_ds4_params(struct vfe_device *vfe, struct vfe_line *line,
			const struct v4l2_isp_block_header *block);
int vfe_175_ds4_validate_output(const struct vfe_output *output);
int vfe_175_ds4_validate_buffer(const struct vfe_output *output, const struct camss_buffer *buffer);
void vfe_175_ds4_start(struct vfe_device *vfe, struct vfe_output *output);
void vfe_175_ds4_update(struct vfe_device *vfe, struct vfe_output *output, const struct camss_buffer *buffer);
void vfe_175_ds4_stop(struct vfe_device *vfe, struct vfe_output *output);

#endif /* CAMSS_VFE_175_DS4_H */''');write('camss-vfe-175-ds4.h',text)
text=read('camss-vfe-175-ds4.c');text=replace(text,'#include <linux/string.h>','''#include <linux/string.h>
#include <linux/io.h>
#include <linux/limits.h>
#include <linux/media-bus-format.h>
#include <linux/qcom-camss-config.h>
#include "camss.h"
#include "camss-format.h"
#include "camss-vfe.h"''')
text+='''
static const struct camss_format_info formats_ds4_175[] = {
	{ MEDIA_BUS_FMT_UYYVYY10_0_5X30, 15, V4L2_PIX_FMT_QCOM_PD10_LOCAL, 1,
	  PER_PLANE_DATA(0, 1, 1, 2, 1, 32) },
};
const struct camss_formats vfe_formats_ds4_175 = {
	.nformats = ARRAY_SIZE(formats_ds4_175), .formats = formats_ds4_175,
};
const struct v4l2_frmsize_stepwise vfe_frame_sizes_ds4_175 = {
	.min_width = 4, .max_width = 1024, .step_width = 2,
	.min_height = 2, .max_height = 1024, .step_height = 2,
};

'''+(HERE/'ds4-runtime.c').read_text();write('camss-vfe-175-ds4.c',text)
text=read('camss-vfe-175-pixel.h');text=replace(text,'\tbool gamma_enabled;','\tbool gamma_enabled;\n\tbool ds4_configured, ds4_running;\n\tu16 ds4_coefficient[3];');text=text.replace('vfe_175_params_info[8]','vfe_175_params_info[9]');write('camss-vfe-175-pixel.h',text)
text=read('camss-vfe-175-pixel.c');text=replace(text,'#include "camss-vfe-175-mnds.h"','#include "camss-vfe-175-mnds.h"\n#include "camss-vfe-175-ds4.h"')
text=text.replace('vfe_175_params_info[8]','vfe_175_params_info[9]');text=replace(text,'\t[CAMSS_PARAMS_WB_GAIN] = {','''	[CAMSS_PARAMS_IFE_DS4] = {
		.size = sizeof(struct camss_params_ife_ds4),
		.block_validate = vfe_175_ds4_validate,
	},
	[CAMSS_PARAMS_WB_GAIN] = {''')
text=replace(text,'\t\tif (block->type == CAMSS_PARAMS_IFE_GAMMA) {','''		if (block->type == CAMSS_PARAMS_IFE_DS4) {
			vfe_175_ds4_params(vfe, line, block);
			offset += block->size;
			continue;
		}
		if (block->type == CAMSS_PARAMS_IFE_GAMMA) {''');write('camss-vfe-175-pixel.c',text)

text=read('camss-vfe-175-output.c');text=replace(text,'} else if (output->line->num_outputs == 3) {','} else if (output->line->num_outputs == 3 ||\n\t\t   output->line->num_outputs == 4) {')
text=replace(text,'\tif (pix->pixelformat != V4L2_PIX_FMT_NV12','''	if (output->line->num_outputs == 4) {
		const struct vfe_output *ds4 = &output->line->output[3];

		if (ds4->pad != MSM_VFE_PAD_SRC_DS4 || ds4->wm_num != 1 ||
		    ds4->wm[0].bus_client != 5 || ds4->wm[0].plane || ds4->comp_group != 1)
			return -EINVAL;
	}
	if (pix->pixelformat != V4L2_PIX_FMT_NV12''');write('camss-vfe-175-output.c',text)

text=read('camss-vfe-17x.c');text=replace(text,'#include "camss-vfe-175-output.h"','#include "camss-vfe-175-output.h"\n#include "camss-vfe-175-ds4.h"')
text=replace(text,'\treturn vfe_175_validate_buffer(output, buf);','''	if (output->pad == MSM_VFE_PAD_SRC_DS4)
		return vfe_175_ds4_validate_buffer(output, buf);
	return vfe_175_validate_buffer(output, buf);''')
text=replace(text,'\t\t/* Keep shared pad indices; undeclared DS outputs reject formats. */\n\t\tvfe_set_pix(pix, 3);','\t\tvfe_add_ds(&pix->output[3], MSM_VFE_PAD_SRC_DS4, 5, 1);\n\t\tvfe_set_pix(pix, 4);')
text=replace(text,'\tif (output->line->is_pix)\n\t\treturn vfe_175_validate_output(output);','''	if (output->pad == MSM_VFE_PAD_SRC_DS4) {
		ret = vfe_175_ds4_validate_output(output);
		return ret ?: (vfe->pixel175.ds4_configured ? 0 : -ENODATA);
	}
	if (output->line->is_pix)
		return vfe_175_validate_output(output);''')
text=replace(text,'\telse if (output->line->is_pix)\n\t\tvfe_175_full_start','\telse if (output->pad == MSM_VFE_PAD_SRC_DS4)\n\t\tvfe_175_ds4_start(vfe, output);\n\telse if (output->line->is_pix)\n\t\tvfe_175_full_start')
text=replace(text,'\telse if (output->line->is_pix) {\n\t\tvfe_175_full_stop','\telse if (output->pad == MSM_VFE_PAD_SRC_DS4)\n\t\tvfe_175_ds4_stop(vfe, output);\n\telse if (output->line->is_pix) {\n\t\tvfe_175_full_stop')
text=replace(text,'\telse if (output->line->is_pix)\n\t\tvfe_175_full_update','\telse if (output->pad == MSM_VFE_PAD_SRC_DS4)\n\t\tvfe_175_ds4_update(vfe, output, buf);\n\telse if (output->line->is_pix)\n\t\tvfe_175_full_update')
needle='/* SM8150 full IFE: shared RDI transport, matched CAMIF and FULL DMA. */'
text=replace(text,needle,'''static int vfe_175_validate_all_params(struct vfe_line *line,
				       const struct v4l2_isp_buffer *params)
{
	int ret = vfe_175_params_validate_line(line, params);

	return ret ?: vfe_175_ds4_validate_line(line, params);
}

'''+needle)
text=replace(text,'.params_validate = vfe_175_params_validate_line,','.params_validate = vfe_175_validate_all_params,')
text=replace(text,'.params_max_payload = CAMSS_PARAMS_IFE_GAMMA_MAX_PAYLOAD,','.params_max_payload = CAMSS_PARAMS_IFE_GAMMA_MAX_PAYLOAD +\n\t\t\t      sizeof(struct camss_params_ife_ds4),');write('camss-vfe-17x.c',text)

text=read('camss-vfe.c');text=replace(text,'#include "camss-vfe.h"','#include "camss-vfe.h"\n#include "camss-vfe-175-ds4.h"')
text=replace(text,'\t\t*fmt = *src;\n\t\tfmt->width = w;','''		*fmt = *src;
		if (pad == MSM_VFE_PAD_SRC_DS4 &&
		    to_vfe(line)->camss->res->version == CAMSS_8150)
			fmt->code = MEDIA_BUS_FMT_UYYVYY10_0_5X30;
		fmt->width = w;''')
text=replace(text,'code->which)->code;','''code->which)->code;
		if (code->pad == MSM_VFE_PAD_SRC_DS4 &&
		    to_vfe(line)->camss->res->version == CAMSS_8150)
			code->code = MEDIA_BUS_FMT_UYYVYY10_0_5X30;''')
text=replace(text,'\t\t} else {\n\t\t\tcontinue;\n\t\t}\n\n\t\tvideo->ops = &vfe->video_ops;','''		} else if (output->pad == MSM_VFE_PAD_SRC_DS4 &&
			   vfe->res->hw_ops == &vfe_ops_175) {
			video->type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
			video->auxiliary = true;
			video->formats = vfe_formats_ds4_175.formats;
			video->nformats = vfe_formats_ds4_175.nformats;
			video->frame_sizes = &vfe_frame_sizes_ds4_175;
			video->bpl_alignment = 192;
			suffix = "ds4";
		} else {
			continue;
		}

		video->ops = &vfe->video_ops;''')
text=text.replace('if (output->pad != MSM_VFE_PAD_SRC_STATS || !output->wm_num)','if ((!vid->auxiliary && output->pad != MSM_VFE_PAD_SRC_STATS) ||\n\t    !output->wm_num)')
text=replace(text,'\tif (ops->vfe_output_start)\n\t\tops->vfe_output_start(vfe, output);\n\telse\n\t\tops->vfe_wm_start(vfe, output->wm[0].bus_client, line);','''	if (!output->video_out.auxiliary) {
		if (ops->vfe_output_start)
			ops->vfe_output_start(vfe, output);
		else
			ops->vfe_wm_start(vfe, output->wm[0].bus_client, line);
	}''')
start=text.index('static int vfe_enable_one_output(');end=text.index('/* The image owns the line;',start);part=text[start:end]
part=replace(part,'\t\tops->reg_update(vfe, line->id);','\t\tif (!output->video_out.auxiliary)\n\t\t\tops->reg_update(vfe, line->id);')
part=replace(part,'\n\treturn 0;','''
	if (output->video_out.auxiliary && output->gen2.active_num) {
		ops->vfe_output_start(vfe, output);
		ops->reg_update(vfe, line->id);
	}
	return 0;''');text=text[:start]+part+text[end:]
start=text.index('int vfe_queue_buffer_v2(');end=text.index('/*\n * vfe_enable_v2',start);part=text[start:end]
part=replace(part,'\t\tops->reg_update(vfe, line->id);','''		if (vid->auxiliary && output->gen2.active_num == 1)
			ops->vfe_output_start(vfe, output);
		ops->reg_update(vfe, line->id);''');text=text[:start]+part+text[end:]
text=replace(text,'\t\toutput->gen2.active_num--;\n\t}\n\n\treturn ready_buf;','''		output->gen2.active_num--;
		if (output->video_out.auxiliary && !output->gen2.active_num) {
			ops->vfe_output_stop(vfe, output);
			ops->reg_update(vfe, line->id);
		}
	}

	return ready_buf;''')
text=replace(text,'if (o && output->video_out.type == V4L2_BUF_TYPE_META_CAPTURE)','if (o && (output->video_out.type == V4L2_BUF_TYPE_META_CAPTURE ||\n\t\t\t  output->video_out.auxiliary))');write('camss-vfe.c',text)

subprocess.run(['git','-C',str(kernel),'diff','--check'],check=True)
subprocess.run(['git','-C',str(kernel),'add','--',*map(str,changed)],check=True)
(HERE/'ds4-dma.patch').write_text(git('diff','--cached','--binary'))
subprocess.run(['git','-C',str(kernel),'commit','-m','media: camss: connect calibrated VFE175 PD10 auxiliary capture'],check=True)
rows=[dict(path=str(p),sha256=hashlib.sha256((kernel/p).read_bytes()).hexdigest()) for p in changed]
r=dict(stage=427,parent_commit=base,commit=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),source_hashes=rows,
 local_pd10_fourcc_not_reserved_upstream=True,ds4_param_block_flags_must_be_zero=True,ds4_wm5_group1_independent=True,
 ds4_image_auxiliary_queue_not_metadata=True,format_and_dma_candidate_connected=True,hardware_validated=False,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
