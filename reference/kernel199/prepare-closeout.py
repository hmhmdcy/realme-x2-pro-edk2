from pathlib import Path
ref=Path(__file__).resolve().parent
s=(ref.parent/'kernel198/final-health.py').read_text().replace('k198','k199').replace('stage=198','stage=199').replace('physical_frame_count=3','physical_frame_count=6').replace('temporary_max_400mhz_experiment=True','integrated_runtime_mmcx_request=True,unmodified_frequency_tables=True,no_external_performance_helper=True').replace('production_max_clock_operation_unresolved=True','normal_runtime_vote_and_capture_proven=True,static_dt_deployment_pending=True').replace("assert counts==dict(warning=1,","assert counts==dict(warning=3,")
s=s.replace("names=['samurai_front_overlay'","names=['samurai_camera_perf','samurai_front_overlay'")
s=s.replace("r=dict(stage=199,", "assert log.count(b'OF: overlay: WARNING: memory leak will occur')==2 and log.count(b'WARNING: CPU:')==1\nr=dict(stage=199,of_overlay_property_memory_warnings=2,new_kernel_cpu_warnings=0,")
(ref/'final-health.py').write_text(s)
s=(ref.parent/'kernel198/export-native.py').read_text().replace('k198','k199').replace('stage=198','stage=199');(ref/'export-native.py').write_text(s)
print('Final health preserves two OF property warnings and original kernel taint')
