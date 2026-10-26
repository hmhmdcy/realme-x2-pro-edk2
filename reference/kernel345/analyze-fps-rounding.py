from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
proof=json.loads((HERE/'fps-knee-validation.json').read_text());assert proof['passed']
raw=(P/'fps-input-private.bin').read_bytes();expected=(P/'fps-expected-private.bin').read_bytes();count=struct.unpack_from('<I',raw)[0];pos=4;overshoots=[];below_minimum=0;valid=0
for i in range(count):
 maximum,size=struct.unpack_from('<QI',raw,pos);pos+=12
 first=struct.unpack_from('<fQIf',raw,pos);pos+=size*20
 ok,gain,time,priority,index=struct.unpack_from('<IfQIf',expected,i*24)
 if not ok:continue
 valid+=1
 if maximum<first[1]:below_minimum+=1;continue
 if time>maximum:overshoots.append(time-maximum)
assert pos==len(raw)
report=dict(stage=345,source='Already verified OEM UpdateFPSKnee results; no repeated emulation or device capture',valid_cases=valid,
 duration_below_table_first_knee_cases=below_minimum,at_or_above_first_knee_overshoot_cases=len(overshoots),maximum_overshoot_ns=max(overshoots,default=0),
 native_float_rounding_preserved=True,not_a_hard_sensor_time_limiter=True,actual_line_frame_limit_application_pending=True)
(HERE/'fps-rounding-observation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
