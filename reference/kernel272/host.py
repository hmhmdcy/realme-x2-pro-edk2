"""Use the current boot270 strict-key guard; no boot transition is implied."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('camera271_transport',Path(__file__).resolve().parents[1]/'kernel271/host.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
ssh=transport.ssh
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel272');PRIVATE.mkdir(mode=0o700,exist_ok=True)
