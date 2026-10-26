"""Correct the request helper against this kernel's existing vb2 API."""
from pathlib import Path
import importlib.util
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('storage284', HERE.parent/'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
source = storage.mounted_build().parent/'source354'
path = source/'drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c'
text = path.read_text()
old = 'return ret ?: v4l2_m2m_request_validate(request);'
assert text.count(old) == 1
path.write_text(text.replace(old, 'return ret ?: vb2_request_validate(request);'))
print('Corrected to vb2_request_validate; original failed build retained.')
