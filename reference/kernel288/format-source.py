"""Wrap the one new overlong declaration before saving the candidate."""
from pathlib import Path

p=Path('/home/cy122/x2pro-linux/camera279-isp-kernel/drivers/media/platform/qcom/camss/camss-vfe.c')
s=p.read_text()
old='\t\t\tconst struct v4l2_frmsize_stepwise *s = to_vfe(line)->res->pix_sink_frame_sizes;'
assert s.count(old)==1
p.write_text(s.replace(old,'\t\t\tconst struct v4l2_frmsize_stepwise *s =\n\t\t\t\tto_vfe(line)->res->pix_sink_frame_sizes;'))
