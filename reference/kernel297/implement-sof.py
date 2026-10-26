"""Use the existing CAMIF SOF tags for every SM8150 PIX capture output."""
from pathlib import Path
import subprocess
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git = lambda *a: subprocess.check_output(['git', '-C', str(TREE), *a], text=True).strip()
assert git('rev-parse', 'HEAD') == 'f86906688666c0ebaabaeeec96c28d5741257f50'
assert not git('status', '--porcelain')
subprocess.run(['git', '-C', str(TREE), 'switch', '-c', 'samurai-sof297'], check=True)
d = TREE / 'drivers/media/platform/qcom/camss'
p = d / 'camss-vfe-17x.c'
s = p.read_text()
start = s.index('static void vfe_isr_sof(')
end = s.index('\n}\n', start) + 3
s = s[:start] + '''static void vfe_isr_sof(struct vfe_device *vfe, enum vfe_line_id line_id)
{
	struct v4l2_event event = { .type = V4L2_EVENT_FRAME_SYNC };
	struct vfe_line *line = &vfe->line[line_id];
	struct vfe_output *output;
	unsigned long flags;
	unsigned int i, o;

	if (vfe->camss->res->version != CAMSS_8150)
		return;

	spin_lock_irqsave(&vfe->output_lock, flags);
	output = &line->output[0];
	if (output->state != VFE_OUTPUT_ON) {
		spin_unlock_irqrestore(&vfe->output_lock, flags);
		return;
	}
	event.u.frame_sync.frame_sequence = output->sof_sequence++;
	/* All outputs observe the same input frame, even if DONE is delayed. */
	for (o = 0; o < line->num_outputs; o++) {
		output = &line->output[o];
		if (output->state != VFE_OUTPUT_ON || !output->wm_num)
			continue;
		for (i = 0; i < CAMSS_INIT_BUF_COUNT; i++) {
			struct camss_buffer *buf = output->buf[i];

			if (buf && !buf->sof_valid) {
				buf->vb.sequence = event.u.frame_sync.frame_sequence;
				buf->sof_valid = true;
				break;
			}
		}
	}
	spin_unlock_irqrestore(&vfe->output_lock, flags);

	v4l2_subdev_notify_event(&line->subdev, &event);
}
''' + s[end:]
p.write_text(s)
p = d / 'camss-vfe.c'
s = p.read_text()
old = '\tready_buf->vb.vb2_buf.timestamp = ts;\n\tready_buf->vb.sequence = output->sequence++;'
assert s.count(old) == 1
s = s.replace(old, '''	ready_buf->vb.vb2_buf.timestamp = ts;
	if (line->is_pix && vfe->camss->res->version == CAMSS_8150) {
		if (ready_buf->sof_valid)
			output->sequence = ready_buf->vb.sequence + 1;
		else
			dev_err_ratelimited(vfe->camss->dev,
					    "Missing SOF tag for completed PIX buffer\\n");
	} else {
		ready_buf->vb.sequence = output->sequence++;
	}''')
start = s.index('void vfe_buf_done(')
end = s.index('\n}\n', start) + 3
part = s[start:end]
part = part.replace('\tunsigned int o;\n', '\tunsigned int o;\n\tbool sof_tracking = false;\n')
old = '\tline = &vfe->line[vfe->wm_output_map[wm]];'
assert part.count(old) == 1
part = part.replace(old, old + '\n\tsof_tracking = line->is_pix && vfe->camss->res->version == CAMSS_8150;')
old = '''		if (ready[0]) {
			params = vfe_params_apply_next(vfe, line,
						       line->output[0].sequence);'''
assert old in part
part = part.replace(old, '''		if (ready[0]) {
			u32 sequence = sof_tracking ? line->output[0].sof_sequence :
						      line->output[0].sequence;

			params = vfe_params_apply_next(vfe, line, sequence);''')
old = '''	for (o = 0; o < MSM_VFE_NUM_OUTPUTS; o++)
		if (ready[o])
			vb2_buffer_done(&ready[o]->vb.vb2_buf,
					VB2_BUF_STATE_DONE);'''
assert old in part
part = part.replace(old, '''	for (o = 0; o < MSM_VFE_NUM_OUTPUTS; o++) {
		if (!ready[o])
			continue;
		/* A completion counter cannot establish an input-frame identity. */
		vb2_buffer_done(&ready[o]->vb.vb2_buf,
				sof_tracking && !ready[o]->sof_valid ?
				VB2_BUF_STATE_ERROR : VB2_BUF_STATE_DONE);
	}''')
s = s[:start] + part + s[end:]
p.write_text(s)
subprocess.run(['git', '-C', str(TREE), 'diff', '--check'], check=True)
print(git('diff', '--stat'))
