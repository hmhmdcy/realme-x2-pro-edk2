"""Preserve independently streaming statistics buffers and unwind partial output starts."""
from pathlib import Path
import json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel');p=TREE/'drivers/media/platform/qcom/camss/camss-vfe.c'
assert json.loads((host.PRIVATE/'boot-build-state-private.json').read_text())['terminal']
assert json.loads((ROOT/'parent-restart-metadata-validation.json').read_text())['expected_failure_observed']
assert json.loads((ROOT/'parent-partial-metadata-validation.json').read_text())['expected_failure_observed']
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='4757a0f15c1e0439eef2fdddf6043d65635f1c90' and not git('status','--porcelain')
s=p.read_text();needle='static int vfe_enable_one_output('
i=s.index(needle)
helpers='''/* Keep active auxiliary buffers queued while only the image stream stops. */
static void vfe_requeue_active_buffers(struct vfe_output *output)
{
	int i;

	for (i = CAMSS_INIT_BUF_COUNT - 1; i >= 0; i--) {
		struct camss_buffer *buf = output->buf[i];

		if (!buf)
			continue;
		buf->sof_valid = false;
		list_add(&buf->queue, &output->pending_bufs);
		output->buf[i] = NULL;
	}
	output->gen2.active_num = 0;
}

/* Called with output_lock held, before any owned buffers can be recycled. */
static void vfe_stop_one_output(struct vfe_line *line, struct vfe_output *output)
{
	struct vfe_device *vfe = to_vfe(line);
	const struct vfe_hw_ops *ops = vfe->res->hw_ops;
	unsigned int i;

	if (ops->vfe_output_stop)
		ops->vfe_output_stop(vfe, output);
	else
		for (i = 0; i < output->wm_num; i++)
			ops->vfe_wm_stop(vfe, output->wm[i].bus_client, line);
}

'''
s=s[:i]+helpers+s[i:]
start=s.index('int vfe_enable_output_v2(');end=s.index('\n}',start);frag=s[start:end]
assert '\tint ret;' in frag;frag=frag.replace('\tint ret;','\tint ret = 0;')
needle='\n\tspin_unlock_irqrestore(&vfe->output_lock, flags);'
assert frag.count(needle)==1
frag=frag.replace(needle,'''
	if (ret) {
		bool stopped = false;

		while (i--) {
			struct vfe_output *output = &line->output[i];

			if (output->state != VFE_OUTPUT_ON)
				continue;
			vfe_stop_one_output(line, output);
			vfe_requeue_active_buffers(output);
			output->state = VFE_OUTPUT_OFF;
			stopped = true;
		}
		if (stopped)
			ops->reg_update(vfe, line->id);
	}
'''+needle)
s=s[:start]+frag+s[end:]
start=s.index('static void vfe_disable_output(');end=s.index('\n}',start);frag=s[start:end]
frag=frag.replace('\tconst struct vfe_hw_ops *ops = vfe->res->hw_ops;\n','').replace('\tunsigned int i, o;','\tunsigned int o;')
old='''		if (ops->vfe_output_stop)
			ops->vfe_output_stop(vfe, output);
		else
			for (i = 0; i < output->wm_num; i++)
				ops->vfe_wm_stop(vfe, output->wm[i].bus_client, line);
		output->gen2.active_num = 0;'''
assert old in frag
frag=frag.replace(old,'''		vfe_stop_one_output(line, output);
		if (o && output->video_out.type == V4L2_BUF_TYPE_META_CAPTURE)
			vfe_requeue_active_buffers(output);
		else
			output->gen2.active_num = 0;
		output->state = VFE_OUTPUT_OFF;''')
s=s[:start]+frag+s[end:];p.write_text(s)
subprocess.run(['git','-C',str(TREE),'diff','--check'],check=True,capture_output=True)
(ROOT/'metadata-restart-candidate.patch').write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff']))
print('Added buffer-preserving image stop and partial-output rollback; not compiled or deployed.')
