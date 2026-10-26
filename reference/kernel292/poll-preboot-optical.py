"""Poll the single fresh optical check, preserving the dark earlier capture."""
from pathlib import Path
source=(Path(__file__).resolve().parents[1]/'kernel291/poll-physical.py').read_text()
source=source.replace('physical-launch','preboot-optical-launch').replace('k291-physical-r1','k292-preboot-optical-r1').replace('physical-poll','preboot-optical-poll').replace('physical-capture-validation','preboot-optical-capture-validation')
exec(compile(source,__file__,'exec'))
