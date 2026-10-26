"""Keep r1 failed observations and analyze the independent corrected r2 run."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
text=(HERE/'probe-pixels.py').read_text().replace('runtime-collected-r1','runtime-collected-r2').replace('patches-private.json','patches-r2-private.json').replace('pixel-probe-private.json','pixel-probe-r2-private.json')
text=text.replace('kernel400/runtime-collected-r2','kernel400/runtime-collected-r1')
text=text.replace("assert state['passed']","assert state['passed'] and state['pid']!=15169")
(HERE/'probe-pixels-r2.py').write_text(text)
text=(HERE/'close-current.py').read_text().replace('k402-gamma-r1','k402-gamma-r2').replace("['observation_completed']","['passed']")
text=text.replace('gamma_pixel_checks_passed=False,hardware_scope="Gamma pixels failed; successful transport and normal recovery only"','gamma_pixel_checks_passed=True,hardware_scope="Corrected opcode1 fixed Gamma diagnostics passed; full automatic calibration still pending"')
(HERE/'close-current-r2.py').write_text(text)
print('Prepared r2 host pixel and restored-state checks; failed r1 data retained.')
