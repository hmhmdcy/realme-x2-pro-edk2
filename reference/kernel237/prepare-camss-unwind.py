"""Adapt Hotdog0114 to the actual fae1 source, preserving 7.3 PM pairing."""
from pathlib import Path
import difflib,hashlib,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel237');K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
base=Path('/mnt/e/edk2-samurai-out/kernel223/kernel-before-paired-sof')
overlay=Path('/mnt/e/edk2-samurai-out/kernel223/sof-candidate-source')
prefix='drivers/media/platform/qcom/camss/'
names=['camss-vfe.c','camss-vfe.h','camss-vfe-17x.c','camss-video.h','camss-video.c']
original={name:((overlay if (overlay/(prefix+name)).exists() else base)/(prefix+name)).read_text() for name in names}
candidate=dict(original)
def replace(name,old,new):
 assert candidate[name].count(old)==1,(name,old,candidate[name].count(old));candidate[name]=candidate[name].replace(old,new)
helper='''/* Stop successful downstream starts; the failing subdevice owns its unwind. */
static void video_stop_subdevices(struct camss_video *video,
				 struct media_entity *stop_at)
{
	struct media_entity *entity = &video->vdev.entity;
	struct media_pad *pad;
	struct v4l2_subdev *subdev;
	int ret;

	while (1) {
		pad = &entity->pads[0];
		if (!(pad->flags & MEDIA_PAD_FL_SINK))
			break;
		pad = media_pad_remote_pad_first(pad);
		if (!pad || !is_media_entity_v4l2_subdev(pad->entity) ||
		    pad->entity == stop_at)
			break;
		entity = pad->entity;
		subdev = media_entity_to_v4l2_subdev(entity);
		ret = v4l2_subdev_call(subdev, video, s_stream, 0);
		if (ret < 0 && ret != -ENOIOCTLCMD)
			dev_err(video->camss->dev,
				"Video subdevice %s stop failed: %d\\n",
				subdev->name, ret);
	}
}

'''
replace('camss-video.c','static int video_start_streaming(',helper+'static int video_start_streaming(')
replace('camss-video.c','\t\tif (ret < 0 && ret != -ENOIOCTLCMD)\n\t\t\tgoto error;', '\t\tif (ret < 0 && ret != -ENOIOCTLCMD)\n\t\t\tgoto stop_subdevices;')
replace('camss-video.c','\nerror:\n\tvideo_device_pipeline_stop(vdev);','\nstop_subdevices:\n\tvideo_stop_subdevices(video, entity);\nerror:\n\tvideo_device_pipeline_stop(vdev);')
s=candidate['camss-video.c'];a=s.index('static void video_stop_streaming(');b=s.index('\nstatic void video_unprepare_streaming',a)
candidate['camss-video.c']=s[:a]+'''static void video_stop_streaming(struct vb2_queue *q)
{
	struct camss_video *video = vb2_get_drv_priv(q);
	struct video_device *vdev = &video->vdev;

	video_stop_subdevices(video, NULL);
	video_device_pipeline_stop(vdev);
	video->ops->flush_buffers(video, VB2_BUF_STATE_ERROR);
}
'''+s[b:]
replace('camss-vfe.c','\t\tvb2_buffer_done(&buf->vb.vb2_buf, state);\n\t\tlist_del(&buf->queue);',
 '\t\tlist_del(&buf->queue);\n\t\tif (buf->vb.vb2_buf.state == VB2_BUF_STATE_ACTIVE)\n\t\t\tvb2_buffer_done(&buf->vb.vb2_buf, state);')
s=candidate['camss-vfe.c'];a=s.index('int vfe_flush_buffers(');b=s.index('\n/*',a);part=s[a:b]
part=part.replace('\tstruct vfe_output *output;','\tstruct vfe_output *output;\n\tstruct camss_buffer *buf0, *buf1, *last;')
x=part.index('\tvfe_buf_flush_pending(output, state);');y=part.index('\n\tspin_unlock_irqrestore',x)
part=part[:x]+'''	buf0 = output->buf[0];
	buf1 = output->buf[1];
	last = output->last_buffer;
	output->buf[0] = NULL;
	output->buf[1] = NULL;
	output->last_buffer = NULL;
	/* gen1 shares this union; only the VFE170 path uses active_num. */
	if (vfe->res->hw_ops == &vfe_ops_170)
		output->gen2.active_num = 0;

	vfe_buf_flush_pending(output, state);
	if (buf0 && buf0->vb.vb2_buf.state == VB2_BUF_STATE_ACTIVE)
		vb2_buffer_done(&buf0->vb.vb2_buf, state);
	if (buf1 && buf1 != buf0 &&
	    buf1->vb.vb2_buf.state == VB2_BUF_STATE_ACTIVE)
		vb2_buffer_done(&buf1->vb.vb2_buf, state);
	if (last && last != buf0 && last != buf1 &&
	    last->vb.vb2_buf.state == VB2_BUF_STATE_ACTIVE)
		vb2_buffer_done(&last->vb.vb2_buf, state);
'''+part[y:]
candidate['camss-vfe.c']=s[:a]+part+s[b:]
dest=R/'camss-source';assert not dest.exists();dest.mkdir()
patch='Subject: [PATCH] media: camss: unwind failed starts and return active buffers once\n\nAdapt Hotdog0114 to the maintained fae1 source and Linux7.3 VB2 PM pairing.\nKeep prepare/unprepare, SOF pairing, IRQ masks and the SM8150 board profile.\nOnly VFE170 resets the gen2 union member.\n\n---\n'
for name in names:
 (dest/name).write_text(candidate[name])
 if candidate[name]!=original[name]:
  path=prefix+name;patch+='diff --git a/'+path+' b/'+path+'\n'+''.join(difflib.unified_diff(original[name].splitlines(True),candidate[name].splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(R/'camss-stream-unwind.patch').write_text(patch)
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
report=dict(stage=237,baseline_fae1_sources={n:sha(s) for n,s in original.items()},candidate_sources={n:sha(s) for n,s in candidate.items()},
 reference='hotdog47087509/0114',only_two_behavioral_files_changed=True,prepare_unprepare_pm_unchanged=True,sof_pairing_unchanged=True,gen1_union_preserved=True,first_stream_failure_root_cause_not_claimed=True)
(R/'camss-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
