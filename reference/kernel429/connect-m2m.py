"""Queue FULL and PD10 together through standard two-plane DMA-BUF ownership."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
root=m.mounted_build().parent/'source354';d=root/'drivers/media/platform/qcom/camss'
git=lambda *a:subprocess.check_output(['git','-C',str(root),*a],text=True)
assert git('rev-parse','HEAD').strip()=='17a47d707376c0d45d97f96242ecf73673ad2748' and not git('status','--porcelain')
def rep(t,a,b,n=1):
 assert t.count(a)==n,(a[:90],t.count(a),n)
 return t.replace(a,b)
p=root/'include/uapi/linux/qcom-ipe-a5.h';t=p.read_text();t=rep(t,'#include <linux/v4l2-controls.h>','''#include <linux/v4l2-controls.h>
#include <linux/videodev2.h>

/* Experimental local OUTPUT bundle, not an upstream-reserved FourCC.
 * Plane 0: one contiguous NV12 image. Plane 1: native quarter-size PD10.
 * Both planes must belong to the same completed IFE SOF and remain owned
 * by this queue until DQBUF. CAPTURE remains ordinary single-plane NV12.
 */
#define V4L2_PIX_FMT_QCOM_NV12_PD10 v4l2_fourcc('Q', 'N', '1', '0')''');p.write_text(t)
p=d/'camss-icp-a5-m2m.c';t=p.read_text()
t=rep(t,'#include <linux/dma-buf.h>','#include <linux/crc32.h>\n#include <linux/dma-buf.h>\n#include <linux/unaligned.h>\n#include <linux/vmalloc.h>')
t=rep(t,'bool aborting, closed;','bool aborting, closed, coarse;')
t=rep(t,'\tu64 jobs, completed, direct_completed, cancelled, failed, starts, stops;','\tu64 jobs, completed, direct_completed, cancelled, failed, starts, stops;\n\tu8 *dc_snapshot;\n\tu32 dc_snapshot_bytes;')
t=rep(t,'\t\t\t    const struct qcom_ipe_a5_frame_params *params,','\t\t\t    const struct camss_a5_ipe_coarse_input *coarse,\n\t\t\t    const struct qcom_ipe_a5_frame_params *params,')
t=rep(t,'\tif (!params || !params->version)\n\t\treturn','\tif (coarse && (!params || !params->version || !(params->flags & QCOM_IPE_A5_LTM)))\n\t\treturn -EINVAL;\n\tif (!params || !params->version)\n\t\treturn')
t=rep(t,'\treturn camss_a5_ipe_run_ltm_status(ctx->dev->a5,','\tif (coarse)\n\t\treturn camss_a5_ipe_run_ltm_pd10_status(ctx->dev->a5, &ctx->session, job,\n\t\t\t\t\t\t      colour, gamma, ltm, coarse, result);\n\treturn camss_a5_ipe_run_ltm_status(ctx->dev->a5,')
t=rep(t,'static struct dma_buf *image_buffer(struct vb2_buffer *vb)','static struct dma_buf *image_buffer(struct vb2_buffer *vb, unsigned int plane)')
t=rep(t,'vb->planes[0].dbuf','vb->planes[plane].dbuf')
t=rep(t,'vb->planes[0].mem_priv, O_RDWR','vb->planes[plane].mem_priv, O_RDWR')
t=rep(t,'\tint ret;\n\n\tret = start_backend(dev);','\tstruct camss_a5_pd10_layout coarse;\n\tint ret;\n\n\tret = start_backend(dev);')
t=rep(t,'\tif (!ret)\n\t\tret = camss_a5_ipe_configure_nv12(dev->a5, &ctx->session, &io);','''	if (!ret && ctx->coarse) {
		ret = camss_a5_ipe_pd10_quarter(&io.input, &coarse);
		if (!ret)
			ret = camss_a5_ipe_configure_nv12_pd10(dev->a5, &ctx->session, &io, &coarse);
	} else if (!ret) {
		ret = camss_a5_ipe_configure_nv12(dev->a5, &ctx->session, &io);
	}''')
t=rep(t,'a5->dma_input.buffer || a5->dma_output.buffer;','a5->dma_input.buffer || a5->dma_output.buffer || a5->dma_coarse.buffer;')
t=rep(t,'struct dma_buf *input = NULL, *output = NULL;','struct dma_buf *input = NULL, *output = NULL, *coarse_buffer = NULL;\n\tstruct camss_a5_ipe_coarse_input coarse = {};')
t=rep(t,'image_buffer(&src->vb2_buf);','image_buffer(&src->vb2_buf, 0);')
t=rep(t,'image_buffer(&dst->vb2_buf);','image_buffer(&dst->vb2_buf, 0);')
t=rep(t,'\tjob.input_dma = input;','''	if (ctx->coarse) {
		coarse_buffer = image_buffer(&src->vb2_buf, 1);
		if (IS_ERR(coarse_buffer)) {
			ret = PTR_ERR(coarse_buffer);
			coarse_buffer = NULL;
			goto finish;
		}
		if (!dev->dc_snapshot)
			dev->dc_snapshot = kvzalloc(0x40000 + 16, GFP_KERNEL);
		if (!dev->dc_snapshot) {
			ret = -ENOMEM;
			goto finish;
		}
		dev->dc_snapshot_bytes = 0;
		coarse.dma = coarse_buffer;
		coarse.offset = src->vb2_buf.planes[1].data_offset;
		coarse.bytes = 46080;
		coarse.scratch_output = dev->dc_snapshot + 16;
		coarse.scratch_capacity = 0x40000;
	}
	job.input_dma = input;''')
t=rep(t,'\tret = frame_params_run(ctx, &job, params, &result);','''	ret = frame_params_run(ctx, &job, ctx->coarse ? &coarse : NULL, params, &result);
	if (!ret && ctx->coarse) {
		u32 i, changed = 0, bytes = ctx->session.scratch_bytes;
		u8 *data = dev->dc_snapshot + 16;

		for (i = 0; i < bytes; i++)
			changed += data[i] != 0xa7;
		put_unaligned_le32(job.request_id, dev->dc_snapshot);
		put_unaligned_le32(bytes, dev->dc_snapshot + 4);
		put_unaligned_le32(crc32_le(~0U, data, bytes) ^ ~0U, dev->dc_snapshot + 8);
		put_unaligned_le32(changed, dev->dc_snapshot + 12);
		dev->dc_snapshot_bytes = bytes + 16;
	}''')
t=rep(t,'finish:\n\tkfree(params);','finish:\n\tif (coarse_buffer)\n\t\tdma_buf_put(coarse_buffer);\n\tkfree(params);')
a=t.index('static int queue_setup(');z=t.index('static int buffer_output_validate(',a)
t=t[:a]+'''/* Common geometry is stored as NV12. Only the OUTPUT queue gains PD10. */
static int queue_format(struct ipe_context *ctx, unsigned int type,
			struct v4l2_pix_format_mplane *format)
{
	struct camss_a5_nv12_layout full;
	struct camss_a5_pd10_layout coarse;
	int ret;

	*format = ctx->format;
	if (!V4L2_TYPE_IS_OUTPUT(type) || !ctx->coarse)
		return 0;
	full = (struct camss_a5_nv12_layout){ format->width, format->height,
		format->plane_fmt[0].bytesperline, format->height, false };
	ret = camss_a5_ipe_pd10_quarter(&full, &coarse);
	if (ret)
		return ret;
	format->pixelformat = V4L2_PIX_FMT_QCOM_NV12_PD10;
	format->num_planes = 2;
	format->plane_fmt[1].bytesperline = coarse.stride;
	format->plane_fmt[1].sizeimage = coarse.bytes;
	return 0;
}

static int queue_setup(struct vb2_queue *q, unsigned int *buffers,
		       unsigned int *planes, unsigned int sizes[],
		       struct device *alloc_devs[])
{
	struct ipe_context *ctx = vb2_get_drv_priv(q);
	struct v4l2_pix_format_mplane f;
	unsigned int i;
	int ret = queue_format(ctx, q->type, &f);

	if (ret)
		return ret;
	if (*planes && *planes != f.num_planes)
		return -EINVAL;
	for (i = 0; i < f.num_planes; i++) {
		if (*planes && sizes[i] < f.plane_fmt[i].sizeimage)
			return -EINVAL;
		sizes[i] = f.plane_fmt[i].sizeimage;
	}
	*planes = f.num_planes;
	return 0;
}

static int buffer_prepare(struct vb2_buffer *vb)
{
	struct ipe_context *ctx = vb2_get_drv_priv(vb->vb2_queue);
	struct v4l2_pix_format_mplane f;
	unsigned int i;
	int ret = queue_format(ctx, vb->type, &f);

	if (ret)
		return ret;
	if (vb->num_planes != f.num_planes)
		return -EINVAL;
	for (i = 0; i < f.num_planes; i++) {
		u32 bytes = f.plane_fmt[i].sizeimage;
		u32 offset = vb->planes[i].data_offset;
		unsigned long size = vb2_plane_size(vb, i);

		if (offset > size || bytes > size - offset || (u64)offset + bytes > U32_MAX)
			return -EINVAL;
		if (V4L2_TYPE_IS_OUTPUT(vb->type)) {
			if (vb2_get_plane_payload(vb, i) < offset + bytes)
				return -EINVAL;
		} else {
			vb2_set_plane_payload(vb, i, offset + bytes);
		}
	}
	return 0;
}

'''+t[z:]
t=rep(t,'\tif (f->index > 1)\n\t\treturn -EINVAL;\n\tf->pixelformat =', '''	if (f->index == 2 && V4L2_TYPE_IS_OUTPUT(f->type)) {
		f->pixelformat = V4L2_PIX_FMT_QCOM_NV12_PD10;
		strscpy(f->description, "NV12 + native PD10 (local)", sizeof(f->description));
		return 0;
	}
	if (f->index > 1)
		return -EINVAL;
	f->pixelformat =''')
t=rep(t,'\tu64 stride, max_stride;','\tu64 stride, max_stride;\n\tbool coarse = V4L2_TYPE_IS_OUTPUT(f->type) &&\n\t\tp->pixelformat == V4L2_PIX_FMT_QCOM_NV12_PD10;')
t=rep(t,'if (p->pixelformat != V4L2_PIX_FMT_NV12 && p->pixelformat != V4L2_PIX_FMT_NV21)','if (!coarse && p->pixelformat != V4L2_PIX_FMT_NV12 && p->pixelformat != V4L2_PIX_FMT_NV21)')
t=rep(t,'\tp->field = V4L2_FIELD_NONE;','\tif (coarse && (p->width != 640 || p->height != 480))\n\t\treturn -EOPNOTSUPP;\n\tp->field = V4L2_FIELD_NONE;')
t=rep(t,'\tp->plane_fmt[0].sizeimage = stride * p->height * 3 / 2;','''	p->plane_fmt[0].sizeimage = stride * p->height * 3 / 2;
	if (coarse) {
		p->num_planes = 2;
		p->plane_fmt[1].bytesperline = 768;
		p->plane_fmt[1].sizeimage = 46080;
	}''')
t=rep(t,'\tf->fmt.pix_mp = file_context(file)->format;\n\treturn 0;','\treturn queue_format(file_context(file), f->type, &f->fmt.pix_mp);')
t=rep(t,'\tif (!ret)\n\t\tctx->format = f->fmt.pix_mp; /* bypass has a single shared geometry */','''	if (!ret) {
		bool output = V4L2_TYPE_IS_OUTPUT(f->type);
		bool coarse = f->fmt.pix_mp.pixelformat == V4L2_PIX_FMT_QCOM_NV12_PD10;

		if (!output && ctx->coarse && (f->fmt.pix_mp.width != 640 ||
		    f->fmt.pix_mp.height != 480 || f->fmt.pix_mp.pixelformat != V4L2_PIX_FMT_NV12))
			return -EINVAL;
		ctx->format = f->fmt.pix_mp;
		if (output)
			ctx->coarse = coarse;
		if (coarse) {
			ctx->format.pixelformat = V4L2_PIX_FMT_NV12;
			ctx->format.num_planes = 1;
			memset(&ctx->format.plane_fmt[1], 0, sizeof(ctx->format.plane_fmt[1]));
		}
	}''')
t=rep(t,'\tkfree(dev->firmware);\n\tkfree(dev);\n}', '\tkvfree(dev->dc_snapshot);\n\tkfree(dev->firmware);\n\tkfree(dev);\n}')
t+='''
/* Temporary bounded root-only diagnostic; header is request/bytes/CRC/changed.
 * Snapshot is published only after a completed job and never aliases DMA RAM.
 */
ssize_t camss_a5_m2m_dc_snapshot(struct camss_a5_m2m *dev, char *buffer,
				loff_t offset, size_t count)
{
	ssize_t ret = 0;

	if (!dev || offset < 0)
		return -EINVAL;
	mutex_lock(&dev->hw_lock);
	if (offset < dev->dc_snapshot_bytes) {
		count = min_t(size_t, count, dev->dc_snapshot_bytes - offset);
		memcpy(buffer, dev->dc_snapshot + offset, count);
		ret = count;
	}
	mutex_unlock(&dev->hw_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(camss_a5_m2m_dc_snapshot);
''';p.write_text(t)
p=d/'camss-icp-a5-m2m.h';t=p.read_text();t=rep(t,'#endif','''ssize_t camss_a5_m2m_dc_snapshot(struct camss_a5_m2m *dev, char *buffer,
				loff_t offset, size_t count);
#endif''');p.write_text(t)
p=d/'camss-icp-platform.c';t=p.read_text()
t=rep(t,'!!a5->dma_input.buffer + !!a5->dma_output.buffer,','!!a5->dma_input.buffer + !!a5->dma_output.buffer + !!a5->dma_coarse.buffer,')
t=rep(t,'(unsigned long long)a5->dma_input.bytes + a5->dma_output.bytes,','(unsigned long long)a5->dma_input.bytes + a5->dma_output.bytes + a5->dma_coarse.bytes,')
t=rep(t,'ATTRIBUTE_GROUPS(icp);','''static ssize_t ltm_scratch_read(struct file *file, struct kobject *kobject,
				const struct bin_attribute *attribute,
				char *buffer, loff_t offset, size_t count)
{
	struct camss_icp *icp = dev_get_drvdata(kobj_to_dev(kobject));
	ssize_t ret;

	mutex_lock(&icp->lock);
	ret = camss_a5_m2m_dc_snapshot(icp->m2m, buffer, offset, count);
	mutex_unlock(&icp->lock);
	return ret;
}
static const struct bin_attribute bin_attr_ltm_scratch =
	__BIN_ATTR(ltm_scratch, 0400, ltm_scratch_read, NULL, 0x40000 + 16);
static const struct bin_attribute *const icp_bin_attrs[] = {
	&bin_attr_ltm_scratch, NULL
};
static const struct attribute_group icp_group = {
	.attrs = icp_attrs, .bin_attrs = icp_bin_attrs,
};
static const struct attribute_group *icp_groups[] = { &icp_group, NULL };''');p.write_text(t)
subprocess.run(['git','-C',str(root),'diff','--check'],check=True)
subprocess.run(['git','-C',str(root),'add','--',str(root/'include/uapi/linux/qcom-ipe-a5.h'),*[str(d/n) for n in ['camss-icp-a5-m2m.c','camss-icp-a5-m2m.h','camss-icp-platform.c']]],check=True)
subprocess.run(['git','-C',str(root),'commit','-m','media: camss: queue paired NV12 and PD10 planes through IPE m2m'],check=True)
state=json.loads((HERE/'source-state.json').read_text());state.update(commit=git('rev-parse','HEAD').strip(),m2m_and_ipa_not_yet_connected=False,
 m2m_paired_source_connected=True,ipa_not_yet_connected=True,experimental_local_fourcc='QN10',
 legacy_6008_byte_parameters_unchanged=True,root_only_bounded_temporary_scratch_snapshot=True)
paths=[row['path'] for row in state['source_hashes']]+['include/uapi/linux/qcom-ipe-a5.h']+['drivers/media/platform/qcom/camss/'+n for n in ['camss-icp-a5-m2m.c','camss-icp-a5-m2m.h','camss-icp-platform.c']]
state['source_hashes']=[dict(path=n,sha256=hashlib.sha256((root/n).read_bytes()).hexdigest()) for n in paths]
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'pd10-runtime.patch').write_text(git('diff',state['parent_commit'],'HEAD'))
print(json.dumps(state,indent=2))
