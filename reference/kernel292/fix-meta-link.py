"""Validate metadata-output links instead of relying on the V4L2 warning fallback."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='8a16fbe17010c1eede868f8b8eb7d1dbd77c81ad' and not git('status','--porcelain')
p=TREE/'drivers/media/platform/qcom/camss/camss-video.c';s=p.read_text()
insert='''/* Metadata output links are delegated here by the subdevice validator. */
static int video_meta_out_link_validate(struct media_link *link)
{
	struct v4l2_subdev_format format = {
		.which = V4L2_SUBDEV_FORMAT_ACTIVE,
		.pad = link->sink->index,
	};
	struct video_device *vdev;
	struct camss_video *video;
	struct v4l2_subdev *sink;
	int ret;

	if (!is_media_entity_v4l2_video_device(link->source->entity) ||
	    !is_media_entity_v4l2_subdev(link->sink->entity))
		return -EPIPE;

	vdev = media_entity_to_video_device(link->source->entity);
	video = container_of(vdev, struct camss_video, vdev);
	if (video->type != V4L2_BUF_TYPE_META_OUTPUT ||
	    link->source != &video->pad)
		return -EPIPE;

	sink = media_entity_to_v4l2_subdev(link->sink->entity);
	ret = v4l2_subdev_call(sink, pad, get_fmt, NULL, &format);
	if (ret)
		return ret;

	return format.format.code == MEDIA_BUS_FMT_METADATA_FIXED ? 0 : -EPIPE;
}

static const struct media_entity_operations msm_video_meta_out_entity_ops = {
	.link_validate = video_meta_out_link_validate,
};

'''
needle='static int video_meta_enum_fmt(';assert s.count(needle)==1;s=s.replace(needle,insert+needle)
needle='\tpad->flags = meta_out ? MEDIA_PAD_FL_SOURCE : MEDIA_PAD_FL_SINK;';assert s.count(needle)==1
s=s.replace(needle,'\tvdev->entity.ops = meta_out ? &msm_video_meta_out_entity_ops : NULL;\n'+needle)
p.write_text(s)
patch=ROOT/'metadata-link-candidate.patch';patch.write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','--','drivers/media/platform/qcom/camss/camss-video.c']))
q=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(patch)],capture_output=True);(host.PRIVATE/'metadata-link-checkpatch-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
(ROOT/'metadata-link-source-validation.json').write_text(json.dumps(dict(stage=292,parent=git('rev-parse','HEAD'),patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),checkpatch_errors=0,checkpatch_warnings=0,no_private_uapi=True,not_deployed=True),indent=2)+'\n')
print('Added metadata source link validation; kernel292 r1 remains unbooted.')
