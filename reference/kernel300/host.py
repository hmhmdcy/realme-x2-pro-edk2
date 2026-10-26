"""Retain the verified298 boot guard and original key; separate stage300 artifacts."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('transport299',Path(__file__).resolve().parents[1]/'kernel299/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel300');PRIVATE.mkdir(mode=0o700,exist_ok=True)
ssh=previous.ssh
raw_ssh=previous.raw_ssh
