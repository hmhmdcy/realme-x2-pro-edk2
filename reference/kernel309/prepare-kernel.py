"""Separate receiver throughput from sensor-array timing in common CAMSS."""
from pathlib import Path
TREE=Path('/home/cy122/x2pro-linux/camera309-link-kernel')
root=TREE/'drivers/media/platform/qcom/camss'
p=root/'camss.h';s=p.read_text()
needle='int camss_get_pixel_clock(struct media_entity *entity, u64 *pixel_clock);'
assert s.count(needle)==1
s=s.replace(needle,needle+'\nint camss_get_link_pixel_rate(struct media_entity *entity, unsigned int bpp,\n\t\t\t      u64 *pixel_rate);')
p.write_text(s)
p=root/'camss.c';s=p.read_text()
needle='int camss_pm_domain_on(struct camss *camss, int id)'
assert s.count(needle)==1
body='''/*
 * camss_get_link_pixel_rate - Pixel throughput received over CSI-2
 *
 * V4L2_CID_PIXEL_RATE describes the sensor array, including its timing
 * blanking. The receiver consumes the CSI-2 link, which may have a different
 * pixel rate. Keep the array rate available to exposure/frame calculations.
 */
int camss_get_link_pixel_rate(struct media_entity *entity, unsigned int bpp,
\t\t\t      u64 *pixel_rate)
{
\tstruct media_pad *pad = camss_find_sensor_pad(entity);
\tstruct csiphy_lanes_cfg *lanes;
\tstruct csiphy_device *csiphy;
\tstruct v4l2_subdev *sensor;
\ts64 frequency;
\tu32 mul, div;

\tif (!pad || !pixel_rate)
\t\treturn -ENODEV;
\tsensor = media_entity_to_v4l2_subdev(pad->entity);
\tcsiphy = sensor->host_priv;
\tif (!csiphy || !csiphy->cfg.csi2)
\t\treturn -ENODEV;
\tlanes = &csiphy->cfg.csi2->lane_cfg;
\tfrequency = camss_get_link_freq(entity, bpp, lanes->num_data, lanes->is_cphy);
\tif (frequency <= 0)
\t\treturn frequency ? frequency : -EINVAL;
\t/* CSI-2: two edges; C-PHY carries sixteen bits per seven symbols. */
\tmul = 2 * lanes->num_data * (lanes->is_cphy ? 16 : 1);
\tdiv = bpp * (lanes->is_cphy ? 7 : 1);
\t*pixel_rate = mul_u64_u32_div(frequency, mul, div);
\treturn 0;
}

'''
s=s.replace(needle,body+needle)
if '#include <linux/math64.h>' not in s:
    s=s.replace('#include <linux/clk.h>','#include <linux/clk.h>\n#include <linux/math64.h>')
p.write_text(s)
p=root/'camss-vfe.c';s=p.read_text()
needle='''\t\tret = camss_get_pixel_clock(&vfe->line[i].subdev.entity,
\t\t\t\t\t    &pixel_clock[i]);'''
assert s.count(needle)==2
s=s.replace(needle,'''\t\tstruct vfe_line *line = &vfe->line[i];
\t\tu8 bpp = camss_format_get_bpp(line->formats, line->nformats,
\t\t\t\t\t     line->fmt[MSM_VFE_PAD_SINK].code);

\t\tret = camss_get_link_pixel_rate(&line->subdev.entity, bpp,
\t\t\t\t\t       &pixel_clock[i]);''')
p.write_text(s)
print('Prepared common CSI-2 receiver-rate clock selection; array rate untouched.')
