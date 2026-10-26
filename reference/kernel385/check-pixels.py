"""Validate changing inputs and each real completion; inspect last full image."""
from pathlib import Path
import hashlib,json,sys,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1] if len(sys.argv)>1 else 'r1'
runtime=json.loads((HERE/('boot-runtime-'+run+'-validation.json')).read_text())
assert runtime['passed'] and runtime['terminal'] and runtime['same_boot'] and not runtime['worker_live'] and not runtime['collector_live']
d=runtime['device_result'];w=d['test_width'];h=d['test_height'];swap=d['test_uv_swap'];frames=d['test_frames'];pixels=w*h
crc=lambda data:(zlib.crc32(data,0xffffffff)^0xffffffff)&0xffffffff
def image(sequence):
 rows=[bytes(16+((x//8+phase)%28)*8 for x in range(w)) for phase in range(28)]
 y=b''.join(rows[(row//8*3+sequence*5)%28] for row in range(h))
 chroma=[]
 for phase in range(2):
  row=bytearray(w)
  for x in range(0,w,2):
   u=96+((x//80+sequence)%2)*64;v=64+phase*96
   row[x:x+2]=bytes((v,u) if swap else (u,v))
  chroma.append(bytes(row))
 return y+b''.join(chroma[(row//60+sequence)%2] for row in range(h//2))
records=d['frame_results'];assert len(records)==frames and len({r['output_crc'] for r in records})==frames
for i,r in enumerate(records):
 source=image(i)
 assert r['sequence']==i and r['non_rt']==bool(i&1) and r['input_crc']==crc(source) and r['y_different']==0
 assert 0<=r['uv_abs_error']<pixels//2
output=(P/('collected-'+run)/'ipe-output-private.nv12').read_bytes()
assert len(output)==pixels*3//2 and crc(output)==records[-1]['output_crc']==d['output_crc'] and crc(source)==d['input_crc']
assert output[:pixels]==source[:pixels]
uv_error=sum(abs(x-y) for x,y in zip(output[pixels:],source[pixels:]));assert uv_error==records[-1]['uv_abs_error']
report=dict(stage=385,run=run,width=w,height=h,output_port=d['test_port'],max_cores=d['test_cores'],uv_swap=swap,
 actual_frames=frames,actual_RT_frames=(frames+1)//2,actual_non_RT_frames=frames//2,
 all_frame_input_crc_values_match_independent_host_pattern=True,all_frame_output_crc_values_differ=True,
 all_frame_Y_bytes_equal_current_input_in_kernel=True,last_image_Y_equality_and_crc_and_UV_error_recomputed_on_host=True,
 last_image_bytes=len(output),last_image_sha256=hashlib.sha256(output).hexdigest(),
 per_frame_uv_mae=[r['uv_abs_error']/(pixels//2) for r in records],chroma_not_claimed_exact_identity=True,
 actual_sensor_capture=False,full_iq_or_optical_calibration_proven=False,passed=True)
(HERE/('pixels-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
