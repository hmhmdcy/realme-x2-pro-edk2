"""Inspect existing local DT tools and copy exact-kernel PM code for offline review."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('schema_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
shared = storage.mount.mounted_build()
source = shared.parent / 'kernel453-lens-private/source-view'
output = shared.parent / 'kernel453-lens-private/O/schema'
private = Path('/mnt/e/edk2-samurai-out/kernel453/schema')
private.mkdir(exist_ok=True); output.mkdir(exist_ok=True)
toolbin = Path('/home/cy122/x2pro-linux/.venv-dtschema/bin')
tools = {}
for name in ['dt-doc-validate', 'dt-mk-schema', 'dt-validate']:
    path = toolbin / name
    assert path.is_file(), path
    tools[name] = str(path)
version = subprocess.check_output([str(toolbin / 'python'), '-c', 'import importlib.metadata as m; print(m.version("dtschema"));print(m.version("jsonschema"))'], text=True).splitlines()
dtc = subprocess.check_output(['dtc', '--version'], text=True).strip()
binding = HERE / 'rohm,bu64253.yaml'
doc = subprocess.run([tools['dt-doc-validate'], str(binding)], capture_output=True)
(private / 'original-doc-validation-private.log').write_bytes(doc.stdout + doc.stderr)
paths = [
    'drivers/base/power/runtime.c', 'include/linux/pm_runtime.h',
    'drivers/media/v4l2-core/v4l2-subdev.c', 'drivers/media/v4l2-core/v4l2-ctrls-api.c',
    'drivers/media/v4l2-core/v4l2-async.c', 'drivers/media/v4l2-core/v4l2-device.c',
    'drivers/media/v4l2-core/v4l2-dev.c', 'drivers/regulator/core.c',
    'drivers/base/dd.c', 'drivers/i2c/i2c-core-base.c',
    'include/media/v4l2-subdev.h', 'include/media/v4l2-device.h', 'include/linux/device/driver.h',
]
rows = []
for relative in paths:
    p = source / relative; raw = p.read_bytes()
    dest = private / 'kernel' / relative; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(raw)
    rows.append(dict(path=relative, sha256=hashlib.sha256(raw).hexdigest()))
report = dict(stage=453, dtschema_version=version[0], jsonschema_version=version[1], dtc_version=dtc,
              existing_tools=tools, source_view=str(source), private_output=str(output),
              original_binding_sha256=hashlib.sha256(binding.read_bytes()).hexdigest(),
              original_doc_exit=doc.returncode, original_doc_diagnostic_bytes=len(doc.stdout + doc.stderr),
              pm_review_sources=rows, tool_installations_or_shared_tree_changes=False, sdk_or_phone_accessed=False)
(HERE / 'schema-inspection.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k != 'pm_review_sources'}, indent=2))
