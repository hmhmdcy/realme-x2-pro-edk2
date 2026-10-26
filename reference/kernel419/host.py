from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel419');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host418',Path(__file__).resolve().parent.parent/'kernel418/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
ssh=previous.ssh
raw_ssh=previous.raw_ssh
