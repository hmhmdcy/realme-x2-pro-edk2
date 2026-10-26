from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel379/finish-public.py').read_text()
s=s.replace("'final-state-validation.json'","'current-state-validation.json'")
s=s.replace("folders=[HERE.parent/('kernel'+str(n)) for n in [377,378,379]]","folders=[HERE]")
s=s.replace("['reference/kernel377','reference/kernel378','reference/kernel379',","['reference/kernel380',").replace('relatives[3:]','relatives[1:]')
s=s.replace("{'.py','.ps1','.md','.json','.c','.patch'}","{'.py','.ps1','.md','.json','.c','.h','.patch'}")
s=s.replace('camera: verify dual IPE IO configuration from target OEM ABI','camera: encode target IPE frames and execute OEM striping offline')
s=s.replace('stage=379,commit=','stage=380,commit=')
s=s.replace('actual_full_hfi_lifecycle_verified=True,ipe_io_config_hardware_verified=True,ipe_image_processing_verified=False,','last_hardware_experiment_stage=379,ipe_frame_builder_built=True,original_striping_and_frame_abi_offline_verified=True,ipe_image_processing_verified=False,')
s=s.replace('camera_capture_repeated=True','camera_capture_repeated=False')
(HERE/'finish-public.py').write_text(s)
print('Prepared public checkpoint with only own source, synthetic models and sanitized evidence.')
