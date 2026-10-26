from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel315');PRIVATE.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('host314',Path(__file__).resolve().parents[1]/'kernel314/host.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
raw_ssh=old.raw_ssh
ssh=raw_ssh
