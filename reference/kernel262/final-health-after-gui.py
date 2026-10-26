"""Repeat health verification after the additional GUI and ownership probes."""
from pathlib import Path
R=Path(__file__).parent
source=(R/'final-health.py').read_text()
assert source.count("out=root/'k262-final-health'")==1
source=source.replace("out=root/'k262-final-health'", "out=root/'k262-final-health-after-gui'")
source=source.replace("gui_acceptance_pending=True", "gui_preview_verified=True,gui_shutter_acceptance_pending=True")
source=source.replace("final-health-private.json", "final-health-after-gui-private.json")
source=source.replace("final-health-validation.json", "final-health-after-gui-validation.json")
exec(compile(source,str(R/'final-health.py'),'exec'),{'__file__':str(R/'final-health.py'),'__name__':'__main__'})
