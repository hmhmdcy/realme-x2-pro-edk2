"""One-time resolution of upstream imports against the existing175 PIX tree."""
from pathlib import Path
ROOT=Path('/home/cy122/x2pro-linux/camera314-streams-kernel/drivers/media/platform/qcom/camss')
def edit(name,old,new,count=1):
 p=ROOT/name;s=p.read_text();assert s.count(old)==count,(name,old[:70],s.count(old));p.write_text(s.replace(old,new))

# Use the SoC-level flag requested in the upstream follow-up, not per-block flags.
for name in ['camss-csiphy.h','camss-vfe.h']:
 edit(name,'\tbool streams_enable;\n','')
edit('camss.h','struct camss_resources {','struct camss_resources {\n\tbool streams_enable;')
edit('camss.c','static const struct camss_resources sm8150_resources = {','static const struct camss_resources sm8150_resources = {\n\t.streams_enable = true,')
for name,old,new in [
 ('camss-csiphy.c','csiphy->res->streams_enable','csiphy->camss->res->streams_enable'),
 ('camss-csid.c','csid->res->streams_enable','csid->camss->res->streams_enable'),
 ('camss-vfe.c','vfe->res->streams_enable','vfe->camss->res->streams_enable')]:
 p=ROOT/name;p.write_text(p.read_text().replace(old,new))
edit('camss-csid.h','\tint (*configure_stream)(struct csid_device *csid, u8 enable);',
 '''\tint (*configure_stream)(struct csid_device *csid, u8 enable);
\tvoid (*configure_rx)(struct csid_device *csid);
\tint (*enable_stream)(struct csid_device *csid, u32 port, u8 vc, u8 dt);
\tint (*disable_stream)(struct csid_device *csid, u32 port);''')
# This7.3-rc6 tree retains the original three-argument set_fmt operation;
# the later linux-next client-info signature follow-up does not apply here.
edit('camss-csid.c','unsigned int num_pads = csid_is_lite(csid) ? MSM_CSID_PADS_NUM : MSM_CSID_PADS_NUM - 1;',
 'unsigned int num_pads = !streams_api || csid_is_lite(csid) || csid->res->has_ipp\n\t\t\t      ? MSM_CSID_PADS_NUM : MSM_CSID_PADS_NUM - 1;')
edit('camss-csid.c',"/* The full IFE has only 3 rdi's and pix output is not functional */\n\tif (csid_is_lite(csid))",
 '/*175 exposes three RDIs plus the independent IPP/PIX port. */\n\tif (csid_is_lite(csid) || csid->res->has_ipp)')
# Hardware IPP validation/stop can fail; do not acknowledge a failed transition.
edit('camss-csid.c','''\tcsid->enabled_streams[MSM_CSID_PAD_SINK] |= sink_streams;
\tcsid->enabled_streams[pad] |= streams_mask;

\tformat =''','''\tformat =''')
edit('camss-csid.c','\thw_ops->enable_stream(csid, hw_port, desc_csi2.vc, desc_csi2.dt);',
 '''\tret = hw_ops->enable_stream(csid, hw_port, desc_csi2.vc, desc_csi2.dt);
\tif (ret)
\t\treturn ret;
\tcsid->enabled_streams[MSM_CSID_PAD_SINK] |= sink_streams;
\tcsid->enabled_streams[pad] |= streams_mask;''')
edit('camss-csid.c','\n\thw_ops->disable_stream(csid, hw_port);',
 '''
\t{
\t\tint stop_ret = hw_ops->disable_stream(csid, hw_port);

\t\tif (!ret)
\t\t\tret = stop_ret;
\t}''')
# gen2 streams ops reuse the verified RDI and175 IPP helpers, including C-PHY RX.
backend='''static void csid_configure_rx(struct csid_device *csid)
{
\t__csid_configure_rx(csid, &csid->phy, 0);
}

static int csid_enable_stream(struct csid_device *csid, u32 port, u8 vc, u8 dt)
{
\tconst struct csid_format_info *format;
\tint ret;

\tif (port >= MSM_CSID_MAX_SRC_STREAMS)
\t\treturn -EINVAL;
\tformat = csid_get_fmt_entry(csid->res->formats->formats,
\t\t\t\t    csid->res->formats->nformats,
\t\t\t\t    csid->fmt[MSM_CSID_PAD_FIRST_SRC + port].code);
\tif (dt != format->data_type)
\t\treturn -EINVAL;
\tif (csid_gen2_port_is_ipp(csid, port)) {
\t\tret = csid_gen2_configure_ipp(csid, port, vc);
\t\tif (ret)
\t\t\treturn ret;
\t\twritel(1, csid->base + CSID_IPP_CTRL);
\t} else {
\t\t__csid_configure_rdi_stream(csid, 1, port, vc);
\t\t__csid_ctrl_rdi(csid, 1, port);
\t}
\t/* A shared generator is started only after the first output is armed. */
\tif (csid->testgen.enabled && !csid->enabled_streams[MSM_CSID_PAD_SINK])
\t\t__csid_configure_testgen(csid, 1, port, vc);
\treturn 0;
}

static int csid_disable_stream(struct csid_device *csid, u32 port)
{
\tunsigned int i;
\tbool other = false;
\tint ret = 0;

\tif (port >= MSM_CSID_MAX_SRC_STREAMS)
\t\treturn -EINVAL;
\tif (csid_gen2_port_is_ipp(csid, port))
\t\tret = csid_gen2_stop_ipp(csid);
\telse {
\t\t__csid_ctrl_rdi(csid, 0, port);
\t\t__csid_configure_rdi_stream(csid, 0, port, 0);
\t}
\tfor (i = MSM_CSID_PAD_FIRST_SRC; i < csid->subdev.entity.num_pads; i++)
\t\tif (i != MSM_CSID_PAD_FIRST_SRC + port && csid->enabled_streams[i])
\t\t\tother = true;
\tif (csid->testgen.enabled && !other)
\t\t__csid_configure_testgen(csid, 0, port, 0);
\treturn ret;
}

'''
edit('camss-csid-gen2.c','static int csid_configure_testgen_pattern(',backend+'static int csid_configure_testgen_pattern(')
edit('camss-csid-gen2.c','\t.configure_stream = csid_configure_stream,',
 '\t.configure_stream = csid_configure_stream,\n\t.configure_rx = csid_configure_rx,\n\t.enable_stream = csid_enable_stream,\n\t.disable_stream = csid_disable_stream,')
# Keep the existing175 multi-output representation and metadata cleanup.
edit('camss-vfe.c','\tline->output.state = VFE_OUTPUT_RESERVED;','\tif (pad != MSM_VFE_PAD_SRC || streams_mask != BIT_ULL(0))\n\t\treturn -EINVAL;\n\tline->output[0].state = VFE_OUTPUT_RESERVED;')
edit('camss-vfe.c','\t\tv4l2_subdev_init(sd, &vfe_v4l2_ops);',
 '\t\tv4l2_subdev_init(sd, vfe->camss->res->streams_enable\n\t\t\t\t ? &vfe_streams_v4l2_ops : &vfe_v4l2_ops);')
edit('camss-vfe.c','''\t\tv4l2_device_unregister_subdev(sd);
\t\tmedia_entity_cleanup(&sd->entity);''',
 '''\t\tv4l2_device_unregister_subdev(sd);
\t\tif (vfe->camss->res->streams_enable)
\t\t\tv4l2_subdev_cleanup(sd);
\t\tmedia_entity_cleanup(&sd->entity);''',count=2)
# Import the streams dispatch without discarding existing legacy partial-start unwind.
edit('camss-video.c','''\tentity = &vdev->entity;
\twhile (1) {''',
 '''\tpad = media_pad_remote_pad_first(&vdev->entity.pads[0]);
\tif (pad && is_media_entity_v4l2_subdev(pad->entity)) {
\t\tsubdev = media_entity_to_v4l2_subdev(pad->entity);
\t\tif (v4l2_subdev_has_op(subdev, pad, enable_streams)) {
\t\t\tret = v4l2_subdev_enable_streams(subdev, pad->index, BIT_ULL(0));
\t\t\tif (ret)
\t\t\t\tgoto error;
\t\t\treturn 0;
\t\t}
\t}
\tentity = &vdev->entity;
\twhile (1) {''')
edit('camss-video.c','''\tvideo_stop_subdevices(video, NULL);
\tvideo_device_pipeline_stop(vdev);''',
 '''\tstruct media_pad *pad = media_pad_remote_pad_first(&vdev->entity.pads[0]);
\tstruct v4l2_subdev *subdev = pad && is_media_entity_v4l2_subdev(pad->entity)
\t\t\t\t   ? media_entity_to_v4l2_subdev(pad->entity) : NULL;

\tif (subdev && v4l2_subdev_has_op(subdev, pad, disable_streams)) {
\t\tint ret = v4l2_subdev_disable_streams(subdev, pad->index, BIT_ULL(0));

\t\tif (ret)
\t\t\tdev_err(video->camss->dev, "Stream stop failed: %d\\n", ret);
\t} else {
\t\tvideo_stop_subdevices(video, NULL);
\t}
\tvideo_device_pipeline_stop(vdev);''')
print('Adapted streams import to175 PIX, metadata outputs and the SoC resource flag.')
