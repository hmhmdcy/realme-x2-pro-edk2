"""Independently verify saved conversion/CC pixels and delimit the RGB claim."""
from pathlib import Path
from collections import Counter
import binascii,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;C=P/'runtime-collected-r1';N=640*480;B=N*3//2
runtime=json.loads((HERE/'runtime-validation.json').read_text());s=runtime['state'];assert s['passed'] and not any(runtime[k] for k in ['worker_live','client_live','collector_live'])
def canonical(blob,fmt):
 if not fmt:return blob
 out=bytearray(blob);out[N::2]=blob[N+1::2];out[N+1::2]=blob[N::2];return bytes(out)
def yvalue(row,col):return 16+32*col if not row else 128 if row<4 else 64 if row==4 else 192
def uvvalue(row,col):return (128,128) if not row else (96+32*(col%3),96+32*(row-1)) if row<4 else (64+48*(col%4),208-48*(col//2))
expected_y=bytes(yvalue(y//80,x//80) for y in range(480) for x in range(640))
images={};format_rows=[]
for fmt in range(2):
 source=(C/f'format-{fmt}-mode-0-input-private.nv12').read_bytes();expected_uv=bytes(uvvalue((y*2)//80,x//80)[(x&1)^fmt] for y in range(240) for x in range(640));assert source==expected_y+expected_uv
 for mode in range(8):
  raw=(C/f'format-{fmt}-mode-{mode}-output-private.nv12').read_bytes();assert len(raw)==B
  row=next(r for r in s['native_cases'][:-1] if r['format']==fmt and r['mode']==mode);assert (binascii.crc32(raw,0xffffffff)^0xffffffff)==row['output_crc']
  images[fmt,mode]=canonical(raw,fmt)
 assert images[fmt,0][:N]==expected_y and images[fmt,1]==images[fmt,2]
 assert images[fmt,3][:N]==bytes(N) and images[fmt,3][N:]==bytes([128])*(N//2)
 assert images[fmt,5]!=images[fmt,2] and images[fmt,6]!=images[fmt,2] and images[fmt,7]!=images[fmt,2] and images[fmt,6]!=images[fmt,7]
 half=[]
 for label,start,end in [('Y',0,N),('UV',N,B)]:
  histogram=Counter(2*a-b-c for a,b,c in zip(images[fmt,4][start:end],images[fmt,2][start:end],images[fmt,3][start:end]));assert max(map(abs,histogram))<=1
  half.append(dict(plane=label,twice_error_histogram=dict(sorted(histogram.items())),max_abs_twice_error=1))
 format_rows.append(dict(format=['NV12','NV21'][fmt],identity_cc_equals_pair_bytes=B,zero_y_bytes=N,zero_uv128_bytes=N//2,half_about_encoded_black=half,swap_different_bytes=sum(a!=b for a,b in zip(images[fmt,5],images[fmt,2])),signed_offset_positive_different_bytes=sum(a!=b for a,b in zip(images[fmt,6],images[fmt,2])),signed_offset_negative_different_bytes=sum(a!=b for a,b in zip(images[fmt,7],images[fmt,2])),passed=True))
assert all(images[0,mode]==images[1,mode] for mode in range(8))
patches=json.loads((P/'patches-private.json').read_text());gray=[];offsets=[]
for i in range(48):
 if i//8==0:gray.append(abs(patches['0-1'][i]['median'][0]-yvalue(0,i%8)))
 if i//8 in [1,2,3]:
  a=patches['0-6'][i]['median'][0];b=patches['0-7'][i]['median'][0];z=patches['0-2'][i]['median'][0];offsets.append(dict(delta=a-z,opposite_sum=a+b-2*z))
assert max(gray)<=1 and {r['delta'] for r in offsets}=={1} and max(abs(r['opposite_sum']) for r in offsets)<=1
logs=(C/'kernel-log-private.txt').read_text();assert all(logs.count('CHAIN_TEST mode='+str(i)+' request=1')==2 for i in range(1,8))
assert s['after_native']['jobs']==s['after_native']['completed']==s['after_native']['direct_completed']==16 and s['after_native']['starts']==s['after_native']['stops']==16
assert s['after_normal']['jobs']==s['after_normal']['completed']==s['after_normal']['direct_completed']==48
report=dict(stage=400,hardware_execution=True,frames=16,width=640,height=480,formats=format_rows,normalized_nv12_nv21_different_bytes_all_modes=0,host_recomputed_client_crc_match=True,fixed_synthetic_input_generator_checked=True,no_image_cpu_processing_in_driver=True,conversion_pair_hardware_active=True,hardware_colour_domain_scope='Fixed retained CST/CV pair,640x480 linear NV12/NV21,48 flat synthetic patches. Identity CC equals pair; zero CC encodes Y0/UV128; half scales about encoded black; R/B swap and signed offsets change pixels.',hardware_rgb_processing_domain_established_for_tested_pair=True,logical_rgb_semantics_supported_by_target_contract_and_pixels=True,full_channel_transfer_equation_independently_proven=False,off_diagonal_hardware_pixel_effect_verified=True,signed_offsets_hardware_pixel_effect_verified=True,gray_patch_luma_max_abs_error=max(gray),middle_patch_signed_offset_luma_delta=1,middle_patch_opposite_offset_sum_max_error=max(abs(r['opposite_sum']) for r in offsets),fitted_luma_model_is_inference_only=True,general_saturation_and_rounding_not_proven=True,factory_rgb_matrices_ready_for_default=False,full_gamma_ltm_and_optical_calibration_proven=False,normal395_restored=True,normal_four_camera_frames=48,native_and_normal_counter_epochs_separate=True,candidate_permanently_installed=False,passed=True)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
