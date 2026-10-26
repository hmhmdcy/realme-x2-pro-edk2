"""Board probe configuration only; fixture owns graph/control restoration."""
from pathlib import Path
import re,subprocess,sys
model,first=sys.argv[1:3]
settings={'s5kgw1':('s5kgw1 6-0010',0,'SGBRG10_1X10',4608,3456,'GBRG'),
 'imx319':('imx319 7-0010',1,'SRGGB10_1X10',1632,1224,'RGGB'),
 'imx471':('imx471 9-0010',2,'SRGGB10_1X10',2304,1728,'RGGB'),
 's5k3m5':('s5k3m5 8-002d',3,'SGRBG10_1X10',2104,1560,'GRBG')}
sensor,phy,code,w,h,order=settings[model]
def media(*args):return subprocess.check_output(['media-ctl','-d','/dev/media0',*args],text=True).strip()
media('-r')
for link in [f'"msm_csiphy{phy}":1 -> "msm_csid0":0[1]',
 '"msm_csid0":1 -> "msm_vfe0_rdi0":0[1]','"msm_csid0":4 -> "msm_vfe0_pix":0[1]']:media('-l',link)
for entity,pad in [(sensor,0),(f'msm_csiphy{phy}',0),('msm_csid0',0),('msm_vfe0_rdi0',0),('msm_vfe0_pix',0)]:
 media('-V',f'"{entity}":{pad}[fmt:{code}/{w}x{h} field:none]')
media('-V','"msm_vfe0_pix":0[compose:(0,0)/640x480]')
root=Path(__file__).resolve().parent
raise SystemExit(subprocess.call([str(root/'dual-probe'),media('-e','msm_vfe0_video0'),media('-e','msm_vfe0_video3'),str(w),str(h),order,first]))
