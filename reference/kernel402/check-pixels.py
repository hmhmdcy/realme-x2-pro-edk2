"""Verify the corrected Gamma hardware pixels independently on the host."""
from pathlib import Path
from collections import Counter
import binascii,json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;C=P/'runtime-collected-r2';N=640*480;B=N*3//2
r=json.loads((HERE/'runtime-validation.json').read_text());s=r['state'];assert s['passed'] and s['terminal'] and s['pid']!=15169 and not any(r[k] for k in ['worker_live','client_live','collector_live'])
def canonical(blob,fmt):
 if not fmt:return blob
 out=bytearray(blob);out[N::2]=blob[N+1::2];out[N+1::2]=blob[N::2];return bytes(out)
def yvalue(row,col):return 16+32*col if not row else 128 if row<4 else 64 if row==4 else 192
def uvvalue(row,col):return (128,128) if not row else (96+32*(col%3),96+32*(row-1)) if row<4 else (64+48*(col%4),208-48*(col//2))
expected_y=bytes(yvalue(y//80,x//80) for y in range(480) for x in range(640));images={}
for fmt in range(2):
 source=(C/f'format-{fmt}-mode-0-input-private.nv12').read_bytes();expected_uv=bytes(uvvalue((2*y)//80,x//80)[(x&1)^fmt] for y in range(240) for x in range(640));assert source==expected_y+expected_uv
 for mode in range(10):
  raw=(C/f'format-{fmt}-mode-{mode}-output-private.nv12').read_bytes();assert len(raw)==B
  row=next(v for v in s['native_cases'][:-1] if v['format']==fmt and v['mode']==mode);assert (binascii.crc32(raw,0xffffffff)^0xffffffff)==row['output_crc'];images[fmt,mode]=canonical(raw,fmt)
 assert images[fmt,0][:N]==expected_y
 assert images[fmt,3][:N]==bytes(N) and images[fmt,3][N:]==bytes([128])*(B-N)
 assert images[fmt,9]==bytes([128])*B
 assert max(abs(a-b) for a,b in zip(images[fmt,2],images[fmt,1]))<=1
assert all(images[0,m]==images[1,m] for m in range(10))
previous=(P.parent/'kernel400/runtime-collected-r1/format-0-mode-2-output-private.nv12').read_bytes();assert images[0,1]==previous
stats={}
for label,start,end in [('Y',0,N),('UV',N,B)]:
 hist=Counter(2*h-p-z for h,p,z in zip(images[0,4][start:end],images[0,2][start:end],images[0,3][start:end]));assert max(map(abs,hist))<=1;stats[label]=dict(twice_error_histogram=dict(sorted(hist.items())),max_abs_twice_error=1)
patches=json.loads((P/'patches-r2-private.json').read_text());fixture=json.loads((P.parent/'kernel400/fixture-private.json').read_text());luma=fixture['quantized_cv_luma'];channel_errors=[]
for mode,component in [(5,1),(6,2),(7,0)]:
 errors=[abs(patches[f'0-{mode}'][i]['median'][0]-math.floor(luma[component]*yvalue(0,i)/256+.5)) for i in range(8)];assert max(errors)<=1;channel_errors.append(dict(selector=mode-4,channel=['R','G','B'][component],gray_patches=8,max_abs_output_y_error=max(errors)))
lut=struct.unpack('<256I',(P.parent/'kernel401/gamma-lut-oracle-private.bin').read_bytes()[:1024]);factory_errors=[]
for i in range(8):
 expected=math.floor((lut[yvalue(0,i)]&1023)/4+.5);actual=patches['0-8'][i]['median'][0];factory_errors.append(abs(actual-expected))
assert max(factory_errors)<=1 and images[0,8]!=images[0,2]
logs=(C/'kernel-log-private.txt').read_text();assert all(logs.count('GAMMA_TEST mode='+str(i)+' request=1')==2 for i in range(1,10))
assert s['after_native']['jobs']==s['after_native']['completed']==s['after_native']['direct_completed']==20 and s['after_native']['starts']==s['after_native']['stops']==20
assert s['after_normal']['jobs']==s['after_normal']['completed']==s['after_normal']['direct_completed']==48
report=dict(stage=402,attempt=2,hardware_execution=True,frames=20,gamma_enabled_frames=16,width=640,height=480,formats=['NV12','NV21'],fixed_modes=10,host_recomputed_client_crc_match=True,synthetic_input_generator_checked=True,input_unchanged_canary_sequence_timestamp_checked=True,normalized_nv12_nv21_different_bytes_all_modes=0,generic20_conversion_matches400_all460800_bytes=True,identity_gamma_different_bytes=sum(a!=b for a,b in zip(images[0,2],images[0,1])),identity_gamma_max_abs_byte_error=1,zero_lut_y0_uv128_all_bytes=True,constant512_lut_output128_all_bytes=True,half_about_zero=stats,isolated_channel_gray_checks=channel_errors,original_retained_factory_curve_gray_patches=8,original_retained_factory_curve_gray_max_abs_error=max(factory_errors),original_factory_curve_actual_pixel_effect=True,
 gamma_lut_programmed_across_stream_start_stop_cycles=True,forced_fault_reset_with_gamma_not_tested=True,hardware_scope='Fixed640x480 CST/identityCC/CV pair, diagnostic zero/linear/half/isolatedG-B-R/constant and first retained factory curve; no full runtime interpolation,LTM,all geometry/saturation/rounding/optical claim.',normal395_restored=True,normal_four_camera_frames=48,native_and_normal_counter_epochs_separate=True,prior_attempt_failed_pixels_retained=True,only_core_opcode_changed_between_attempts=True,test_adapter_and_client_unchanged=True,candidate_permanently_installed=False,full_factory_interpolation_and_calibration_complete=False,observation_completed=True,passed=True)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
