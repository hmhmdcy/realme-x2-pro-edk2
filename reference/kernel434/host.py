from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel434');PRIVATE.mkdir(mode=0o700,exist_ok=True)
s=importlib.util.spec_from_file_location('host433',Path(__file__).resolve().parents[1]/'kernel433/host.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
ssh=old.ssh;raw_ssh=old.raw_ssh
