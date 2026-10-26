from pathlib import Path
R=Path(__file__).resolve().parent
text=(R.parent/'kernel271/verify-current-lock.py').read_text().replace('k270-work','k273-work').replace('stage=271','stage=273').replace('physical_sensor_pattern_off=True','telephoto_sensor_pattern_off=True')
exec(compile(text,'verify-current273-generated.py','exec'),dict(__file__=str(R/'verify-current273-generated.py')))
