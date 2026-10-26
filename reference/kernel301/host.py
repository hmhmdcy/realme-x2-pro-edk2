"""Use the verified298 transport; separate the control-delay/calibration artifacts."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('transport300',Path(__file__).resolve().parents[1]/'kernel300/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel301');PRIVATE.mkdir(mode=0o700,exist_ok=True)
ssh=previous.ssh
raw_ssh=previous.raw_ssh
