"""Use the verified276 device transport; stage279 initially changes source candidates only."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('camera278_transport',Path(__file__).resolve().parents[1]/'kernel278/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel279');PRIVATE.mkdir(mode=0o700,exist_ok=True)
ssh=previous.ssh
raw_ssh=previous.raw_ssh
