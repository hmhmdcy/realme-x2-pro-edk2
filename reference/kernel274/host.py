"""Current deployment remains boot273; never reuse an older boot guard."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('camera273_transport',Path(__file__).resolve().parents[1]/'kernel273/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
ssh=previous.ssh
raw_ssh=previous.raw_ssh
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel274');PRIVATE.mkdir(mode=0o700,exist_ok=True)
