"""Original-key USB transport; guard state-changing experiments once per run."""
from pathlib import Path
import importlib.util

PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel307')
spec = importlib.util.spec_from_file_location('host305', Path(__file__).resolve().parents[1] / 'kernel305/host.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
raw_ssh = old.raw_ssh
ssh = old.ssh
