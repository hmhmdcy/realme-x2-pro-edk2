from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel335');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host334',Path(__file__).resolve().parents[1]/'kernel334/host.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
raw_ssh=old.raw_ssh
