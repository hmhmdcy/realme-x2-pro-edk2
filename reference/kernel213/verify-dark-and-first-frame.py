from pathlib import Path
import json
here=Path(__file__).resolve().parent
def read(name):return json.loads((here/name).read_text())
dark=read('helper-raw-p0-sync-probe-validation.json')
white=read('helper-raw-csid-p4-sync-probe-validation.json')
before=read('helper-rgb-csid-p4-sync-probe-validation.json')
after=read('lut-rgb-csid-p4-sync-probe-validation.json')
for report in [dark,white,before,after]:
    assert report['program_exit']==0 and not report['timed_out'] and not report['forced_kill']
    assert report['taint']==0 and not any(report['fault_delta'].values()) and not report['error_lines']
    assert report['test_pattern_and_sensor_controls_restored'] and report['camera_devices_suspended'] and report['dma_buf_sync_start_end_read']
    assert len(report['frames'])==6
assert dark['requested_sensor_pattern']==0 and dark['raw_row_padding_excluded']
assert all(0<f['stddev']<2 and 60<f['mean']<68 and not f['all_zero'] and f['occupied_bins']>=5 for f in dark['frames'])
assert all(.1<f['changed_fraction']<.9 for f in dark['frames'][1:])
assert all(f['byte_min']==f['byte_max']==1023 and f['stddev']==0 for f in white['frames'])
assert before['frames'][0]['all_zero'] and all(f['byte_min']==f['byte_max']==254 for f in before['frames'][1:])
assert all(f['byte_min']==f['byte_max']==254 and not f['all_zero'] for f in after['frames'])
a=read('helper-candidate-staging-validation.json')['products'];b=read('lut-candidate-staging-validation.json')['products']
assert set(a)==set(b) and [name for name in a if a[name]!=b[name]]==['usr/lib/libcamera.so.0.7.2']
report=dict(stage=213,human_confirmed_lights_off=True,raw10_dark_noise_and_frame_changes_verified=True,raw_row_padding_excluded=True,dma_read_start_end_sync_verified=True,dark_raw_mean_range=[min(f['mean'] for f in dark['frames']),max(f['mean'] for f in dark['frames'])],dark_raw_stddev_range=[min(f['stddev'] for f in dark['frames']),max(f['stddev'] for f in dark['frames'])],dark_frame_changed_fraction_range=[min(f['changed_fraction'] for f in dark['frames'][1:]),max(f['changed_fraction'] for f in dark['frames'][1:])],all_zero_or_frozen_raw_rejected=True,processed_rgb_zero_alone_not_a_bug_diagnosis=True,ambient_independent_csid_raw_input_verified_all_pixels_1023=True,old_candidate_first_rgb_all_zero=True,one_line_fix_candidate_all_six_rgb_pixels_254=True,only_candidate_libcamera_core_binary_changed=True,first_frame_not_discarded=True,sensor_internal_pattern_not_accepted_as_positive_control=True,control_and_link_restoration_verified=True,no_new_kernel_faults=True,installed_camera_libraries_not_replaced=True,full_image_quality_not_accepted=True,rear_four_cameras_not_accepted=True)
(here/'dark-and-first-frame-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for name in ['helper-pattern-probe-validation.json']:
    path=here/name;old=json.loads(path.read_text());old.update(sensor_pattern_effectiveness_verified=False,not_accepted_as_positive_control=True,superseded_by='dark-and-first-frame-validation.json');path.write_text(json.dumps(old,indent=2)+'\n')
for variant in ['helper','lut']:
    path=here/(variant+'-capture-validation.json');old=json.loads(path.read_text());old['all_six_rgb_frames_nonconstant']=old.pop('six_rgb_frames_captured');old['captured_frame_count']=len(old['frames']);old['dark_room_nonconstant_is_not_a_capture_success_requirement']=True;path.write_text(json.dumps(old,indent=2)+'\n')
print(json.dumps(report))
