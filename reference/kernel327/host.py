from pathlib import Path
import importlib.util

PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel327')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
spec = importlib.util.spec_from_file_location('host326', Path(__file__).resolve().parents[1] / 'kernel326/host.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
raw_ssh = old.raw_ssh
