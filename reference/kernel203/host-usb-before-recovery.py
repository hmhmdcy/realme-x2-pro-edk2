from pathlib import Path
import importlib.util

spec=importlib.util.spec_from_file_location('current202r2',Path(__file__).resolve().parent.parent/'kernel202/reboot-r2/host.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
ssh,upload,download=transport.ssh,transport.upload,transport.download
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel203');PRIVATE.mkdir(mode=0o700,exist_ok=True)
