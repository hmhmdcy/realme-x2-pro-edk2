"""Use the adopted #298 transport; keep this phase's artifacts separate."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('transport298',Path(__file__).resolve().parents[1]/'kernel298/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel299');PRIVATE.mkdir(mode=0o700,exist_ok=True)
raw_ssh=previous.raw_ssh
ssh=previous.ssh
