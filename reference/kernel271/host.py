"""Reuse the independently adopted boot270 strict-key guard."""
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('camera270_transport', Path(__file__).resolve().parents[1] / 'kernel270/host.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel271')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
ssh = transport.ssh
