"""Execute original FULL Crop to produce, rather than inject, DS4 precrop geometry."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('geometry428',HERE/'native-geometry.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n);m=n.Machine();rows=[]
for iw,ih,w,h in [(4608,3456,640,480),(2304,1728,640,480),(1632,1224,640,480),(640,480,640,480),(650,480,650,480)]:
 m.u.mem_write(n.h.DATA,bytes(0x90000));data,writes=m.full_crop(w,h,iw,ih);values=list(struct.unpack('<8I',data))
 assert values==[0,0,w-1,h-1,0,0,w-1,h//2-1],values
 assert [a for a,b in writes]==[0xe10,0xe30]
 rows.append(dict(input_width=iw,input_height=ih,full_width=w,full_height=h,produced_precrop_y=values[:4],produced_precrop_c=values[4:],chroma_x_counts_components=True))
 (P/('native-produced-precrop-'+str(iw)+'x'+str(ih)+'-private.bin')).write_bytes(data)
r=dict(stage=428,original_target_full_crop_create_and_execute=True,explicit_valid_writable_constructor_state=True,original_image_memory_not_modified=True,
 native_geometry_not_manual_precrop_injection=True,source_scaler_dimensions_supplied_not_complete_mnds_execution=True,
 original_video_full_module_path=0,original_video_full_output_index=1,original_nv12_format=3,rows=rows,
 earlier_half_width_chroma_fixture_retracted=True,phone_accessed=False,passed=True)
(HERE/'native-crop-production-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
