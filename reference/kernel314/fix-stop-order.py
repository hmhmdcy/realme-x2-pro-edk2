"""Keep the incoming CSI clock available until175 IPP has halted."""
from pathlib import Path
ROOT=Path('/home/cy122/x2pro-linux/camera314-streams-kernel/drivers/media/platform/qcom/camss')
p=ROOT/'camss-csid.c';s=p.read_text()
old='''
\t{
\t\tint stop_ret = hw_ops->disable_stream(csid, hw_port);

\t\tif (!ret)
\t\t\tret = stop_ret;
\t}
'''
assert s.count(old)==1;s=s.replace(old,'')
marker='''\tif (disable_sink_streams && remote_pad) {
\t\tret = v4l2_subdev_disable_streams'''
assert s.count(marker)==1
s=s.replace(marker,'''\t/* IPP halts at a frame boundary: keep the transmitter running until then. */
\tret = hw_ops->disable_stream(csid, hw_port);

\tif (disable_sink_streams && remote_pad) {
\t\tint remote_ret = v4l2_subdev_disable_streams''')
old='''\t\tif (ret)
\t\t\tdev_err(csid->camss->dev,
\t\t\t\t"Failed to disable stream on remote pad: %d\\n", ret);'''
new='''\t\tif (remote_ret)
\t\t\tdev_err(csid->camss->dev,
\t\t\t\t"Failed to disable stream on remote pad: %d\\n", remote_ret);
\t\tif (!ret)
\t\t\tret = remote_ret;'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
# Frame descriptors are optional on these single-VC sensors. Avoid the generic
# passthrough helper's error log for a supported fallback to VC0 + mbus type.
p=ROOT/'camss-csiphy.c';s=p.read_text()
body='''static int csiphy_get_frame_desc(struct v4l2_subdev *sd, unsigned int pad,
\t\t\t\t struct v4l2_mbus_frame_desc *fd)
{
\tstruct csiphy_device *csiphy = v4l2_get_subdevdata(sd);
\tstruct media_pad *remote = media_pad_remote_pad_first(&csiphy->pads[MSM_CSIPHY_PAD_SINK]);

\tif (!remote)
\t\treturn -ENOLINK;
\treturn v4l2_subdev_call(media_entity_to_v4l2_subdev(remote->entity),
\t\t\t\tpad, get_frame_desc, remote->index, fd);
}

'''
marker='static const struct v4l2_subdev_pad_ops csiphy_streams_pad_ops = {'
assert s.count(marker)==1;s=s.replace(marker,body+marker)
s=s.replace('.get_frame_desc = v4l2_subdev_get_frame_desc_passthrough,','.get_frame_desc = csiphy_get_frame_desc,')
p.write_text(s)
print('Local175 IPP stop now precedes releasing its shared CSI input.')
