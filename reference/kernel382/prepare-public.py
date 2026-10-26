from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel381/finish-public.py').read_text().replace('stage=381','stage=382').replace("'reference/kernel381'","'reference/kernel382'").replace('NEXT-SESSION-through380-','NEXT-SESSION-through381-')
s=s.replace('camera: complete first target IPE pixel transfer with owned DMA','camera: initialize target ICA defaults and verify corrected NV12 levels')
s=s.replace('last_hardware_experiment_stage=381','last_hardware_experiment_stage=382')
s=s.replace('ipe_nv12_output_levels_correct=False','ipe_nv12_output_levels_correct=True,ipe_kernel_generated_bypass_iq=True')
s=s.replace('camera_capture_repeated=True','camera_capture_repeated=False')
s=s.replace('normal_camera_capture_reference_stage=382','normal_camera_capture_reference_stage=381')
(HERE/'finish-public.py').write_text(s)
print('Prepared scoped public checkpoint; vendor inputs, images and full logs stay private.')
