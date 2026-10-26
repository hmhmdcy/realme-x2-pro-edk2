from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel323');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host322',Path(__file__).resolve().parents[1]/'kernel322/host.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
raw_ssh=old.raw_ssh
