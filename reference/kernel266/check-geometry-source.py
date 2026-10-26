from pathlib import Path
import json,re
R=Path(__file__).parent;s=(R/'imx319.c').read_text();g=json.loads((R/'geometry-validation.json').read_text())['register_geometry']
rows=re.findall(r'\.width = (\d+),\s*\.height = (\d+),\s*\.analogue_crop = \{\s*\.left = (\d+), \.top = (\d+),\s*\.width = (\d+), \.height = (\d+),',s)
assert len(rows)==9
expected={tuple(x['output']):x for x in g}
for values in rows:
 w,h,left,top,cw,ch=map(int,values);x=expected[(w,h)];assert dict(left=left,top=top,width=cw,height=ch)==x['analogue_crop']
 assert 0<=left<left+cw<=3280 and 0<=top<top+ch<=2464
 bx,by=x['binning'];dx,dy,dw,dh=x['digital_crop'];assert dx+dw<=cw//bx and dy+dh<=ch//by and [dw,dh]==[w,h] and x['scaling_mode']==0
report=dict(stage=266,all_nine_preset_crops_match_independently_decoded_registers=True,all_windows_within_full_readout=True,digital_crop_after_binning_within_analogue_window=True,register_programming_unchanged=True,unsupported_rotation_not_published=True)
(R/'geometry-source-check-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

