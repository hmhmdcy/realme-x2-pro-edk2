"""Reuse scoped checkpoint publication; raw OEM data and pixels stay private."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel384/finish-public.py').read_text()
s=s.replace('kernel384','kernel385').replace('through383','through384').replace('stage=384','stage=385')
s=s.replace('camera: generate native bypass striping and verify real IPE pixel output','camera: validate native IPE sizes formats and alternating frame sessions')
s=s.replace('last_hardware_experiment_stage=384','last_hardware_experiment_stage=385')
s=s.replace('all_synthetic_output_bytes_match_stage382_original_striping=True','sixteen_changing_frames_and_both_session_types_verified=True')
exec(compile(s,str(HERE/'finish-public-generated.py'),'exec'),globals())
