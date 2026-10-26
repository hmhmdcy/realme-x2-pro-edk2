"""Stage189 transport; reuse the current authenticated USB endpoint only after boot check."""
from pathlib import Path
import importlib.util
import shutil

spec=importlib.util.spec_from_file_location('transport188',Path(__file__).resolve().parent.parent/'kernel188/host.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
ssh,upload,download=transport.ssh,transport.upload,transport.download
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel189');PRIVATE.mkdir(exist_ok=True)
candidate=PRIVATE/'usb-ipv6-candidates-private.json'
if not candidate.exists():
 shutil.copyfile(transport.PRIVATE/'usb-ipv6-candidates-private.json',candidate)
transport.PRIVATE=PRIVATE
