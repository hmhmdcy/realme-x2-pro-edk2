from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel364');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host363',Path(__file__).resolve().parents[1]/'kernel363/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
raw_ssh=previous.raw_ssh
ssh=previous.ssh
