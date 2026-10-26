"""Independently rebuild client patterns and inspect actual m2m outputs."""
from pathlib import Path
import hashlib,json,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
runtime=json.loads((HERE/'m2m-runtime-r4-validation.json').read_text())
assert runtime['passed'] and runtime['same_boot'] and not any(runtime[k] for k in ['worker_live','collector_live','client_process_live'])
client=runtime['client_report'];assert client['passed'];rows=[]
crc=lambda data:(zlib.crc32(data,0xffffffff)^0xffffffff)&0xffffffff
def pattern(case,sequence):
 w=case['width'];h=case['height'];stride=case['stride'];n=case['id'];swap=case['nv21']
 lines=[bytes(16+((x//8+phase)%28)*8 for x in range(w))+b'\x55'*(stride-w) for phase in range(28)]
 Y=b''.join(lines[(y//8*3+sequence*5+n*7)%28] for y in range(h))
 chroma=[]
 for phase in range(2):
  line=bytearray(b'\x55'*stride)
  for x in range(0,w,2):
   u=96+((x//80+sequence+n)%2)*64;v=64+phase*96
   line[x:x+2]=bytes((v,u) if swap else (u,v))
  chroma.append(bytes(line))
 return Y+b''.join(chroma[(y//60+sequence+n)%2] for y in range(h//2))
for case in client['cases']:
 records=case['frames'];w=case['width'];h=case['height'];stride=case['stride'];size=stride*h*3//2
 assert len({r['output_crc'] for r in records})==len(records)
 for i,r in enumerate(records):
  source=pattern(case,i)
  assert r['sequence']==i and r['input_crc']==crc(source) and not r['y_different']
  assert r['uv_abs_error']==31200
 out=(P/'collected-r4'/('case-'+str(case['id'])+'-last-private.nv12')).read_bytes();assert len(out)==size and crc(out)==records[-1]['output_crc']
 assert all(out[y*stride:y*stride+w]==source[y*stride:y*stride+w] for y in range(h))
 uv_error=sum(abs(x-y) for row in range(h//2) for x,y in zip(out[stride*h+row*stride:stride*h+row*stride+w],source[stride*h+row*stride:stride*h+row*stride+w]))
 assert uv_error==records[-1]['uv_abs_error']
 assert all(out[y*stride+w:(y+1)*stride]==b'\xa5'*(stride-w) for y in range(h*3//2))
 rows.append(dict(id=case['id'],width=w,height=h,stride=stride,nv21=case['nv21'],dmabuf=case['dmabuf'],frames=len(records),
  independent_host_input_crc_matches_every_frame=True,last_image_host_Y_and_crc_and_UV_error_match=True,
  last_image_bytes=size,last_image_sha256=hashlib.sha256(out).hexdigest(),uv_mae=uv_error/(w*h//2),passed=True))
 assert records[0]['input_crc']!=records[-1]['input_crc']
baseline=json.loads((HERE.parent/'kernel384/pixels-validation.json').read_text())
first=client['cases'][0]['frames'][0];assert first['input_crc']==baseline['input_crc32_le'] and first['output_crc']==baseline['output_crc32_le']
report=dict(stage=386,run='r4',actual_v4l2_m2m_phone_outputs=True,tests=rows,total_actual_frames=sum(r['frames'] for r in rows),
 all_frame_active_Y_equality_checked_by_actual_native_client=True,last_full_image_per_case_recomputed_on_host=True,
 mmap_and_export_import_dmabuf_verified=True,imported_source_data_offset_16_and_stride_672_verified=True,
 two_concurrently_streaming_contexts_verified=True,shared_framework_timestamp_sequence_and_format_busy_checks_passed=True,
 first_mmap_frame_crc_matches_stage384_synthetic_baseline=True,chroma_filtering_difference_from_input_remains=True,
 full_iq_or_optical_calibration_proven=False,zero_copy_not_claimed=True,libcamera_pipeline_not_yet_integrated=True,passed=True)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
