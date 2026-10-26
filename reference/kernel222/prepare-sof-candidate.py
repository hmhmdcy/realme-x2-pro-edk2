from pathlib import Path
import difflib,hashlib,json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel222');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
observed=json.loads((here/'request-gap-r7-validation.json').read_text());frames=observed['frames']
assert not observed['frame_start_emitter_observed'] and any(f['buffer_sequence']!=f['request_sequence'] for f in frames)
parent='drivers/media/platform/qcom/camss/';changes={}
def edit(name,replacements):
 original=(kernel/(parent+name)).read_text();text=original
 for old,new in replacements:
  assert text.count(old)==1,(name,old,text.count(old));text=text.replace(old,new)
 changes[parent+name]=(original,text)
edit('camss-vfe.h',[("\tunsigned int sequence;\n","\tunsigned int sequence;\n\tunsigned int sof_sequence;\n")])
edit('camss-vfe.c',[
 ('#include <media/v4l2-device.h>\n','#include <media/v4l2-device.h>\n#include <media/v4l2-event.h>\n'),
 ('\toutput->sequence = 0;\n','\toutput->sequence = 0;\n\toutput->sof_sequence = 0;\n'),
 ('static const struct v4l2_subdev_core_ops vfe_core_ops = {\n', '''static int vfe_subscribe_event(struct v4l2_subdev *sd, struct v4l2_fh *fh,
			       struct v4l2_event_subscription *sub)
{
	struct vfe_line *line = v4l2_get_subdevdata(sd);
	struct vfe_device *vfe = to_vfe(line);

	if (vfe->camss->res->version != CAMSS_8150 ||
	    sub->type != V4L2_EVENT_FRAME_SYNC || sub->id)
		return -EINVAL;

	return v4l2_event_subscribe(fh, sub, 16, NULL);
}

static const struct v4l2_subdev_core_ops vfe_core_ops = {
	.subscribe_event = vfe_subscribe_event,
	.unsubscribe_event = v4l2_event_subdev_unsubscribe,
'''),
 ('\t\tsd->flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;\n','\t\tsd->flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;\n\t\tif (vfe->camss->res->version == CAMSS_8150)\n\t\t\tsd->flags |= V4L2_SUBDEV_FL_HAS_EVENTS;\n'),
])
edit('camss-vfe-17x.c',[
 ('#include <linux/iopoll.h>\n','#include <linux/iopoll.h>\n\n#include <media/v4l2-event.h>\n'),
 ('static void vfe_isr_sof(struct vfe_device *vfe, enum vfe_line_id line_id)\n{\n\t/* nop */\n}', '''static void vfe_isr_sof(struct vfe_device *vfe, enum vfe_line_id line_id)
{
	struct v4l2_event event = { .type = V4L2_EVENT_FRAME_SYNC };
	struct vfe_output *output;
	unsigned long flags;

	if (vfe->camss->res->version != CAMSS_8150)
		return;

	spin_lock_irqsave(&vfe->output_lock, flags);
	output = &vfe->line[line_id].output;
	if (output->state != VFE_OUTPUT_ON) {
		spin_unlock_irqrestore(&vfe->output_lock, flags);
		return;
	}
	event.u.frame_sync.frame_sequence = output->sof_sequence++;
	spin_unlock_irqrestore(&vfe->output_lock, flags);

	v4l2_subdev_notify_event(&vfe->line[line_id].subdev, &event);
}'''),
])
out=private/'sof-candidate-source';assert not out.exists();out.mkdir(mode=0o700)
patch='Subject: [PATCH] media: camss: expose SM8150 VFE start-of-frame events\n\nProvide the existing RDI SOF interrupt to userspace through the standard\nsubdevice FRAME_SYNC event. Keep the SOF sequence independent of completed\nbuffers, reset it at stream start, and retain all IRQ masks and power policy.\n\nThis is a development prerequisite for truthful delayed control association.\nBuffer sequence mapping and the userspace pairing still require validation.\n\n---\n'
for name,(old,new) in changes.items():
 p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(new)
 patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
patch=patch.replace('buffers, reset it at stream start, and retain all IRQ masks and power policy.','buffers and reset it at stream start. Retain all IRQ masks and power\npolicy.')
patch=patch.replace('This is a development prerequisite for truthful delayed control association.\nBuffer sequence mapping and the userspace pairing still require validation.','This is a development prerequisite for truthful delayed control\nassociation. Buffer sequence mapping and userspace pairing still\nrequire validation.')
(here/'camss-sm8150-sof-candidate.patch').write_text(patch)
r=dict(stage=222,candidate_only=True,original_sources_sha256={n:hashlib.sha256(a.encode()).hexdigest() for n,(a,b) in changes.items()},candidate_sources_sha256={n:hashlib.sha256(b.encode()).hexdigest() for n,(a,b) in changes.items()},patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),irq_masks_frequencies_and_power_policy_unchanged=True,sofs_not_yet_observed=True,buffer_sequence_mapping_and_manual_controls_still_open=True)
(here/'sof-candidate-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
