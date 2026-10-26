"""Independently check saved synthetic outputs, without claiming full RGB calibration."""
from pathlib import Path
import binascii,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;directory=P/'runtime-collected-r1'
runtime=json.loads((HERE/'runtime-validation.json').read_text());s=runtime['state'];assert s['passed'] and not any(runtime[k] for k in ['worker_live','client_live','collector_live'])
rows=s['native_cases'][:4];assert [r['mode'] for r in rows]==[0,1,2,3]
outputs=[(directory/('mode-'+str(i)+'-output-private.nv12')).read_bytes() for i in range(4)];source=(directory/'mode-0-input-private.nv12').read_bytes();assert len(source)==460800 and all(len(x)==len(source) for x in outputs)
crc=lambda data:binascii.crc32(data,0xffffffff)^0xffffffff
assert [crc(x) for x in outputs]==[r['output_crc'] for r in rows]
y=bytes(16+((x//8+(row//8)*3+60*7)%28)*8 for row in range(480) for x in range(640));assert source[:307200]==y==outputs[0][:307200]==outputs[1][:307200]
assert outputs[0]==outputs[1] and not any(outputs[2]) and outputs[3][:307200]==bytes(v//2 for v in y)
uv_delta=[a-b//2 for a,b in zip(outputs[3][307200:],outputs[0][307200:])];assert set(uv_delta)<={0,1}
assert s['after_native']['jobs']==s['after_native']['completed']==s['after_native']['direct_completed']==4
assert s['after_normal']['jobs']==s['after_normal']['completed']==s['after_normal']['direct_completed']==48
logs=(directory/'kernel-log-private.txt').read_text();assert all(logs.count('COLOUR_TEST mode='+str(i)+' request=1')==1 for i in [1,2,3])
report=dict(stage=397,hardware_execution=True,source='native V4L2 MMAP buffers imported by the normal SoC core; private temporary fixed-matrix adapter',width=640,height=480,format='NV12',same_synthetic_input_all_modes=True,frames=4,direct_jobs=4,core_image_cpu_copy=False,host_recomputed_client_crc_match=True,identity_equals_bypass_bytes=460800,zero_output_bytes=460800,half_luma_exact_bytes=307200,half_chroma_vs_floor_bypass_differing_bytes=sum(v!=0 for v in uv_delta),half_chroma_vs_floor_bypass_delta_range=[min(uv_delta),max(uv_delta)],chroma_rounding_or_filter_cause_not_isolated=True,hardware_fixed_diagonal_cc_effect_verified=True,off_diagonal_matrix_hardware_effect_verified=False,signed_offsets_hardware_effect_verified=False,general_saturation_and_rounding_verified=False,hardware_rgb_processing_domain_established=False,factory_rgb_matrices_ready_for_default=False,input_and_output_colour_conversion_still_disabled=True,normal395_restored=True,normal_four_camera_frames=48,native_and_restored_normal_counter_epochs_separate=True,full_iq_or_optical_calibration_proven=False,passed=True)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
