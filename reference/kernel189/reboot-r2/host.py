from pathlib import Path
import importlib.util,shutil

spec=importlib.util.spec_from_file_location('parent189',Path(__file__).resolve().parent.parent/'host.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
PRIVATE=parent.PRIVATE/'reboot-r2';PRIVATE.mkdir(exist_ok=True)
candidate=PRIVATE/'usb-ipv6-candidates-private.json'
if not candidate.exists():shutil.copyfile(parent.PRIVATE/'usb-ipv6-candidates-private.json',candidate)
parent.transport.PRIVATE=PRIVATE
ssh,upload,download=parent.ssh,parent.upload,parent.download
