"""Drain each CSI path before releasing its DMA buffers on independent stop."""
from pathlib import Path
ROOT=Path('/home/cy122/x2pro-linux/camera314-streams-kernel/drivers/media/platform/qcom/camss')
p=ROOT/'camss-csid-gen2.c';s=p.read_text()
marker='static void csid_configure_rx(struct csid_device *csid)'
body='''/*175 OEM status bit0 acknowledges a path halted at a frame boundary. */
static int csid_stop_rdi(struct csid_device *csid, u32 port)
{
\tu32 value;
\tu32 status = (csid_is_lite(csid) ? 0x250 : 0x350) + 0x100 * port;
\tint ret;

\tif (!(readl(csid->base + CSID_RDI_CFG0(port)) & BIT(RDI_CFG0_ENABLE)))
\t\treturn 0;
\t__csid_ctrl_rdi(csid, 0, port);
\tret = readl_poll_timeout(csid->base + status, value, value & BIT(0),
\t\t\t\t10, CSID_RESET_TIMEOUT_MS * 1000);
\tif (!ret)
\t\t__csid_configure_rdi_stream(csid, 0, port, 0);
\treturn ret;
}

'''
assert s.count(marker)==1;s=s.replace(marker,body+marker)
old='''\telse {
\t\t__csid_ctrl_rdi(csid, 0, port);
\t\t__csid_configure_rdi_stream(csid, 0, port, 0);
\t}'''
assert s.count(old)==1;s=s.replace(old,'''\telse
\t\tret = csid_stop_rdi(csid, port);''');p.write_text(s)
p=ROOT/'camss-vfe.c';s=p.read_text()
begin=s.index('static int vfe_pad_disable_streams(');end=s.index('static const struct v4l2_subdev_pad_ops vfe_streams_pad_ops',begin)
part=s[begin:end]
old='\tret = vfe->res->hw_ops->vfe_disable(line);'
assert part.count(old)==1;part=part.replace(old,'\tret = 0;')
part=part.replace('''\treturn ret;
}''','''\t/* Let CSID finish the current frame before stopping/recycling its DMA. */
\t{
\t\tint local_ret = vfe->res->hw_ops->vfe_disable(line);

\t\tif (local_ret)
\t\t\tret = local_ret;
\t}
\treturn ret;
}''')
s=s[:begin]+part+s[end:];p.write_text(s)
print('CSI RDI halt is acknowledged before the corresponding VFE DMA is released.')
