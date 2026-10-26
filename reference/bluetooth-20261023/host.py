"""Use the adopted current boot and original authenticated USB transport."""
from pathlib import Path
import importlib.util

PRIVATE = Path('/mnt/e/edk2-samurai-out/bluetooth-20261023')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
spec = importlib.util.spec_from_file_location('bt_host449', Path(__file__).resolve().parents[1] / 'kernel449/host.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
ssh = previous.ssh

