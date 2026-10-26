from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel402');PRIVATE.mkdir(mode=0o700,exist_ok=True)
s=importlib.util.spec_from_file_location('host401',Path(__file__).resolve().parents[1]/'kernel401/host.py');previous=importlib.util.module_from_spec(s);s.loader.exec_module(previous)
ssh=previous.ssh
raw_ssh=previous.raw_ssh
