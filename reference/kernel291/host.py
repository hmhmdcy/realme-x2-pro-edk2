"""Use the strict, adopted kernel290 transport; keep new evidence separate."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('camera290_transport',Path(__file__).resolve().parents[1]/'kernel290/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
ssh=previous.ssh
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel291')
PRIVATE.mkdir(mode=0o700,exist_ok=True)
