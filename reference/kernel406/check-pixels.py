"""Verify corrected LTM pixels and preserve the failed first attempt."""
from pathlib import Path
import binascii,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;C=P/'runtime-collected-r2';R1=P/'runtime-collected-r1'
r=json.loads((HERE/'runtime-validation-r2.json').read_text());s=r['state'];assert s['passed'] and s['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
assert s['pid']==21352 and s['after_native']['jobs']==s['after_native']['completed']==s['after_native']['direct_completed']==52 and s['after_native']['starts']==s['after_native']['stops']==52
assert s['after_normal']['jobs']==s['after_normal']['completed']==s['after_normal']['direct_completed']==48
meta=json.loads((P/'manifest-private.json').read_text());oldmeta=json.loads((P/'manifest-r1-private.json').read_text());assert all(meta['payload_sha256'][n]==oldmeta['payload_sha256'][n] for n in ['test-adapter.ko','colour-client'])
images={};controls=[];la=[];gamma=[];first_failure=json.loads((HERE/'pixels-validation-r1.json').read_text());assert not first_failure['passed']
def canonical(blob,w,fmt):
 if not fmt:return blob
 n=w*480;b=bytearray(blob);b[n::2]=blob[n+1::2];b[n+1::2]=blob[n::2];return bytes(b)
for w in [640,650]:
 n=w*480;size=n*3//2
 for fmt in [0,1]:
  source=(C/f'width-{w}-format-{fmt}-mode-0-input-private.nv12').read_bytes()
  expected_y=bytes((16+32*(x//80) if y<80 else 128 if y<320 else 64 if y<400 else 192)&255 for y in range(480) for x in range(w))
  uv=bytearray()
  for y in range(240):
   for x in range(w):
    row,col=2*y//80,x//80
    u,v=(128,128) if not row else (96+32*(col%3),96+32*(row-1)) if row<4 else (64+48*(col%4),208-48*(col//2))
    uv.append(((v if (x&1)^fmt else u))&255)
  assert source==expected_y+uv
  for mode in range(13):
   path=f'width-{w}-format-{fmt}-mode-{mode}-output-private.nv12';blob=(C/path).read_bytes();assert len(blob)==size
   row=next(v for v in s['native_cases'][:-1] if v['width']==w and v['format']==fmt and v['mode']==mode);assert (binascii.crc32(blob,0xffffffff)^0xffffffff)==row['output_crc']
   images[w,fmt,mode]=canonical(blob,w,fmt)
   if mode in [0,1,2,3,7,8,10,12]:assert blob==(R1/path).read_bytes(),(w,fmt,mode)
  assert images[w,fmt,0][:n]==expected_y
  pair=images[w,fmt,1]
  for mode in [2,3,4,8,10]:assert images[w,fmt,mode]==pair,(w,fmt,mode)
  for mode in [5,7,12]:assert images[w,fmt,mode]==bytes(n)+bytes([128])*(size-n),(w,fmt,mode)
  for mode,expected in [(6,128),(9,64)]:
   gray=[]
   for col in range(8):
    patch=[images[w,fmt,mode][y*w+x] for y in range(16,64) for x in range(col*80+16,col*80+64)]
    assert set(patch)=={expected},(w,fmt,mode,col,min(patch),max(patch));gray.append(expected)
   assert images[w,fmt,mode]!=pair
   la.append(dict(width=w,format=fmt,mode=mode,input_lut_base=2048 if mode==6 else 1024,gray_patches=8,expected_y=expected,max_abs_patch_error=0,whole_colour_image_not_claimed_constant=True))
  differences=[abs(a-b) for a,b in zip(images[w,fmt,11],pair)];assert max(differences)<=1
  gamma.append(dict(width=w,format=fmt,linear_vs_ltm_different_bytes=sum(bool(v) for v in differences),max_abs_byte_error=max(differences),zero_gamma_y0_uv128=True))
  controls.append(dict(width=w,format=fmt,ip_mask_identity_all_bytes_equal=True,reverse_gamma_linear_all_bytes_equal=True,la_zero_y0_uv128=True,reverse_gamma_zero_y0_uv128=True,combined_gamma_zero_y0_uv128=True))
 for mode in range(13):assert images[w,0,mode]==images[w,1,mode]
assert images[640,0,1]==(P.parent/'kernel402/runtime-collected-r2/format-0-mode-1-output-private.nv12').read_bytes()
logs=(C/'kernel-log-private.txt').read_text()
for width in [640,650]:
 for mode in range(1,13):assert logs.count(f'LTM_TEST mode={mode} request=1 width={width}')==2
assert not s['new_unexpected_fault_count'] and not s['taint'] and not s['collector_result']['captured'] and not s['collector_result']['timeout']
report=dict(stage=406,attempt=2,hardware_execution=True,frames=52,ltm_enabled_frames=44,combined_gamma_frames=8,widths=[640,650],height=480,formats=['NV12','NV21'],fixed_modes=13,host_recomputed_crc=True,synthetic_input_generator_and_input_unchanged_checked=True,output_tail_sequence_timestamp_checked=True,normalized_nv12_nv21_different_bytes_all_modes=0,ip_mask_two_pixel_shift_resolved=True,controls=controls,local_adaptation=la,gamma=gamma,conversion_pair640_matches402_all460800_bytes=True,r1_unchanged_controls_byte_identical=True,test_adapter_and_client_unchanged_between_attempts=True,only_core_full_pass_ip_field_corrected=True,original_hal_policy_intentionally_not_preserved_for_explicit_ip=True,
 data_collection_statistics_readback_not_verified=True,full_local_contrast_and_nonzero_scale_math_not_verified=True,forced_fault_reset_with_ltm_not_tested=True,full_factory_dynamic_interpolation_not_installed=True,scope='Fixed CST/identityCC/CV pair,zero-scale LTM,IP/mask identity,LAzero andconstant gray responses,reverseGammalinear/zero,combinedGammalinear/zero at640/650x480. Not full factory tuning,all geometries,DC statistics or fault recovery.',normal395_restored=True,normal_four_camera_frames=48,r1_failed_pixels_retained=True,candidate_permanently_installed=False,observation_completed=True,passed=True)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/'runtime-validation.json').write_bytes((HERE/'runtime-validation-r2.json').read_bytes())
text=(HERE/'close-current-r1.py').read_text().replace('k406-ltm-r1','k406-ltm-r2').replace("HERE/'pixels-validation-r1.json'","HERE/'pixels-validation.json'").replace("HERE/'current-state-validation-r1.json'","HERE/'current-state-validation.json'")
text=text.replace('ltm_pixel_checks_passed=False,combined_gamma_zero_verified=True,hardware_scope="R1 transport and normal restoration verified; mask-only shift and inactive LA remain unresolved"','ltm_fixed_diagnostics_verified=True,combined_gamma_zero_verified=True,hardware_scope="Corrected explicit full-pass IP: fixed52 LTM/colour/Gamma diagnostics and normal restoration; full factory calibration remains pending"')
(HERE/'close-current.py').write_text(text)
print(json.dumps({k:v for k,v in report.items() if k not in ['controls','local_adaptation','gamma']},indent=2))
