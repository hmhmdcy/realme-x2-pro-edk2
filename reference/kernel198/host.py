from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('transport197',Path(__file__).resolve().parent.parent/'kernel197/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport);ssh,upload,download=transport.ssh,transport.upload,transport.download
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel198');PRIVATE.mkdir(exist_ok=True)
