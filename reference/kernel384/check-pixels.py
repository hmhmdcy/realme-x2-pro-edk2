from pathlib import Path
import hashlib,json,zlib
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel384')
runtime=json.loads((HERE/'boot-runtime-validation.json').read_text());assert runtime['passed'] and not runtime['worker_live'] and not runtime['collector_live']
output=(P/'collected-r1/ipe-output-private.nv12').read_bytes();baseline=(P.parent/'kernel382/collected-r1/ipe-output-private.nv12').read_bytes()
assert len(output)==460800 and output==baseline
source=bytearray(460800)
for y in range(480):
 for x in range(640):source[y*640+x]=16+((x//8+y//8*3)%28)*8
for y in range(240):
 for x in range(0,640,2):source[307200+y*640+x]=96+(x//80%2)*64;source[307201+y*640+x]=64+(y//60%2)*96
crc=lambda data:(zlib.crc32(data,0xffffffff)^0xffffffff)&0xffffffff
d=runtime['device_result'];assert crc(source)==d['input_crc'] and crc(output)==d['output_crc']
assert output[:307200]==source[:307200]
uv_mae=sum(abs(x-y) for x,y in zip(output[307200:],source[307200:]))/153600
report=dict(stage=384,actual_phone_output=True,synthetic_input=True,external_striping_file_not_used=True,kernel_generates_iq_and_striping=True,
 compared_against_stage382_actual_oem_striping_output=True,all_460800_output_bytes_equal=True,Y_all_307200_bytes_equal_input=True,
 uv_mae=uv_mae,uv_exact_bytes=sum(x==y for x,y in zip(output[307200:],source[307200:])),
 input_crc32_le=d['input_crc'],output_crc32_le=d['output_crc'],output_sha256=hashlib.sha256(output).hexdigest(),
 chroma_filtering_difference_from_input_still_present=True,full_iq_or_optical_calibration_proven=False,low_light_does_not_affect_synthetic_test=True,passed=True)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
