"""Reuse the verified boot276 transport for stage281; no new boot is implied."""
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('camera280_transport', Path(__file__).resolve().parents[1] / 'kernel280/host.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel281')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
ssh = previous.ssh
raw_ssh = previous.raw_ssh
