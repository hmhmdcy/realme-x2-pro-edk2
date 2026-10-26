from pathlib import Path
ref=Path(__file__).resolve().parent
s=(ref.parent/'kernel197/final-health.py').read_text().replace('k197','k198').replace('stage=197','stage=198').replace('k198-front-capture-r5','k198-front-capture-r1').replace('physical_image_capture_proven=False','physical_image_capture_proven=True').replace('csid_reset_timeout_unresolved=True','production_max_clock_operation_unresolved=True')
s=s.replace("assert not Path('/lib/firmware/samurai/k196-front.dtbo').exists()", "assert not Path('/lib/firmware/samurai/k196-front.dtbo').exists()\nassert not Path('/sys/kernel/tracing/instances/samurai-camera198').exists()")
s=s.replace("front['pins_restored_exact']", "front['physical_image_capture'] and front['pins_restored_exact']")
s=s.replace("r=dict(stage=198,", "r=dict(stage=198,physical_frame_count=3,temporary_max_400mhz_experiment=True,frame_test_patterns_disabled=True,full_camera_function_not_yet_complete=True,")
(ref/'final-health.py').write_text(s)
s=(ref.parent/'kernel197/export-native.py').read_text().replace('k197','k198').replace('stage=197','stage=198');(ref/'export-native.py').write_text(s)
print('Final health and private image-containing export prepared')
