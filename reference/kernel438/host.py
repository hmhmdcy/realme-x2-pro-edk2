from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel438');PRIVATE.mkdir(mode=0o700,exist_ok=True)
s=importlib.util.spec_from_file_location('host437',Path(__file__).resolve().parents[1]/'kernel437/host.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
ssh=old.ssh;raw_ssh=old.raw_ssh
