"""Reuse the maintained host configuration for offline TMC11 generation recovery."""
from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel413');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host412',Path(__file__).resolve().parents[1]/'kernel412/host.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
raw_ssh=old.raw_ssh
