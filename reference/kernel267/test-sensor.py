"""Reuse fault injection against the newly generated actual sensor functions."""
from pathlib import Path
import subprocess
import sys

R=Path(__file__).resolve().parent
for name in ['imx319-fault-prefix.c','imx319-fault-main.c']:
    text=(R.parent/'kernel235'/name).read_text().replace('of_power_resources','managed_power')
    (R/name).write_text(text)
text=(R.parent/'kernel235/test-imx319-faults.py').read_text()
text=text.replace("kernel235')", "kernel267')").replace("'imx319-fault-tests-r2'", "'sensor-fault-tests-r1'")
text=text.replace('imx319-oem-tables.h','imx319-222mhz-tables.h').replace('imx319_oem','imx319_222mhz')
text=text.replace('stage=235','stage=267')
exec(compile(text,str(R/'test-sensor-generated.py'),'exec'),dict(__file__=str(R/'test-sensor-generated.py')))
