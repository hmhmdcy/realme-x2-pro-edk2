from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel375/finish-public.py').read_text().replace('stage=375','stage=376')
s=s.replace("['reference/kernel374','reference/kernel375',", "['reference/kernel376',")
s=s.replace("for folder in [HERE.parent/'kernel374',HERE]", "for folder in [HERE]").replace('relatives[2:]','relatives[1:]')
s=s.replace('camera: verify OEM A5 HFI lifecycle with cooperative shutdown','camera: verify concurrent A5 IPE session creation and destruction')
s=s.replace('normal_camera_baseline_passed=True','normal_camera_capture_reference_stage=375,camera_capture_repeated=False,ipe_session_lifecycle_verified=True')
(HERE/'finish-public.py').write_text(s)
print('Prepared public source/evidence checkpoint for376; raw firmware/packets/logs stay private.')
