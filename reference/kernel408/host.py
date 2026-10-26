"""Reuse host configuration; temporal math work is offline."""
from pathlib import Path
import importlib.util
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel408')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
spec = importlib.util.spec_from_file_location('host407', Path(__file__).resolve().parents[1] / 'kernel407/host.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
raw_ssh = old.raw_ssh
