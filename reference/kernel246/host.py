"""Fresh scoped USB endpoint, preserving the original strict SSH host keys."""
from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel246')
spec=importlib.util.spec_from_file_location('transport246',Path(__file__).resolve().parent.parent/'kernel240/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
transport.PRIVATE=PRIVATE;transport.transport.PRIVATE=PRIVATE
ssh,upload,download=transport.ssh,transport.upload,transport.download
