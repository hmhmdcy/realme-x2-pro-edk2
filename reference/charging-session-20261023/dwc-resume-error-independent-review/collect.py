"""Copy only relevant exact Image-source callers for an offline PM review."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('original_storage', HERE.parents[1] / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
build = storage.mounted_build()
source = (build / 'source').resolve()
commit = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
paths = [p.relative_to(source).as_posix() for p in (source / 'drivers/usb/dwc3').glob('*qcom*') if p.is_file()]
paths += ['drivers/base/power/runtime.c', 'drivers/base/power/main.c', 'drivers/base/power/common.c']
result = []
for name in paths:
    raw = (source / name).read_bytes()
    original = subprocess.check_output(['git', '-C', str(source), 'show', commit + ':' + name])
    assert raw == original, name
    snapshot = 'source--' + name.replace('/', '--')
    (HERE / snapshot).write_bytes(raw)
    result.append({'source': name, 'snapshot': snapshot, 'sha256': hashlib.sha256(raw).hexdigest(),
                   'byte_equal_to_image_source_commit': True})
config = (build / '.config').read_text()
selected = [line for line in config.splitlines() if any(x in line for x in ['CONFIG_USB_DWC3', 'CONFIG_PM_SLEEP=', 'CONFIG_PM='])]
(HERE / 'source-manifest.json').write_bytes((json.dumps({'commit': commit, 'files': result, 'config_scope': selected,
    'sdk_invoked': False, 'shared_sources_modified': False, 'phone_ssh_usb_accessed': False}, indent=2) + '\n').encode())
print(json.dumps({'files': result, 'config_scope': selected}, indent=2))
