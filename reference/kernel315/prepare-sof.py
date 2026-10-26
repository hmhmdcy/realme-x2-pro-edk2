"""Discarded prototype: CSI frame reception must not be labelled exposure."""
raise SystemExit('Retired before build/deployment; 315 uses existing FRAME_SYNC events. Do not replay.')
from pathlib import Path
ROOT=Path('/home/cy122/x2pro-linux/camera314-streams-kernel/drivers/media/platform/qcom/camss')
def edit(name,old,new,count=1):
 p=ROOT/name;s=p.read_text();assert s.count(old)==count,(name,old[:60],s.count(old));p.write_text(s.replace(old,new))
edit('camss-video.h','\tbool sof_valid;','\tbool sof_valid;\n\tu64 sof_timestamp;')
edit('camss-video.h','\tunsigned int bpl_alignment;','\tunsigned int bpl_alignment;\n\tu32 timestamp_flags;')
edit('camss-vfe.h','struct vfe_device {','struct vfe_device {\n\tu64 irq_timestamp;')
edit('camss-vfe-17x.c','''\tu32 status0, status1, vfe_bus_status[3];
\tint i, wm;

\tstatus0 =''','''\tu32 status0, status1, vfe_bus_status[3];
\tint i, wm;

\tvfe->irq_timestamp = ktime_get_ns();
\tstatus0 =''')
edit('camss-vfe-17x.c','''\t\t\t\tbuf->sof_valid = true;''','''\t\t\t\tbuf->sof_valid = true;
\t\t\t\tbuf->sof_timestamp = vfe->irq_timestamp;''')
edit('camss-vfe-17x.c','''\tready_buf->vb.vb2_buf.timestamp = ts;
\tif (vfe->camss->res->version == CAMSS_8150) {''','''\tready_buf->vb.vb2_buf.timestamp =
\t\tvfe->camss->res->version == CAMSS_8150 ? ready_buf->sof_timestamp : ts;
\tif (vfe->camss->res->version == CAMSS_8150) {''')
edit('camss-vfe.c','''\tready_buf->vb.vb2_buf.timestamp = ts;
\tif (line->is_pix && vfe->camss->res->version == CAMSS_8150) {''','''\tready_buf->vb.vb2_buf.timestamp =
\t\tline->is_pix && vfe->camss->res->version == CAMSS_8150
\t\t? ready_buf->sof_timestamp : ts;
\tif (line->is_pix && vfe->camss->res->version == CAMSS_8150) {''')
edit('camss-vfe.c','''\tbuf->sof_valid = false;

\tif (output->state ==''','''\tbuf->sof_valid = false;
\tbuf->sof_timestamp = 0;

\tif (output->state ==''')
edit('camss-vfe.c','''\t\tvideo_out->ops = &vfe->video_ops;
\t\tif (vfe->line[i].is_pix) {''','''\t\tvideo_out->ops = &vfe->video_ops;
\t\tif (vfe->camss->res->version == CAMSS_8150)
\t\t\tvideo_out->timestamp_flags = V4L2_BUF_FLAG_TSTAMP_SRC_SOE;
\t\tif (vfe->line[i].is_pix) {''')
edit('camss-video.c','\tq->timestamp_flags = V4L2_BUF_FLAG_TIMESTAMP_MONOTONIC;',
 '\tq->timestamp_flags = V4L2_BUF_FLAG_TIMESTAMP_MONOTONIC | video->timestamp_flags;')
print('SM8150 image timestamps now retain the IRQ SOF sample and declare SOE.')
