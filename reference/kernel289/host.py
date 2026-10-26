"""Use the independently verified kernel288 boot and strict host identity."""
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('camera288_transport', Path(__file__).resolve().parents[1] / 'kernel288/host.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
ssh = previous.ssh
raw_ssh = previous.raw_ssh
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel289')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
