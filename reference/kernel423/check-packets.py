"""Validate real IPA-produced packets with the maintained native kernel codec."""
from pathlib import Path
import ctypes,hashlib,importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'ipa-validation.json').read_text())['passed']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
kernel=storage.mounted_build().parent/'source354'
codec=P.parent/'kernel422/codec422/colour.c'
assert codec.read_bytes()==(kernel/'drivers/media/platform/qcom/camss/camss-icp-a5-colour.c').read_bytes()
library=ctypes.CDLL(str(P.parent/'kernel422/current-colour-codec.so'))
validate=library.camss_a5_ipe_frame_params_check;validate.argtypes=[ctypes.c_void_p];validate.restype=ctypes.c_int
rows=[]
for mode in ['colour-roundtrip','gamma-roundtrip','factory']:
 raw=(P/(mode+'-contract-private.bin')).read_bytes();assert len(raw)==6008
 result=validate(ctypes.create_string_buffer(raw));rows.append(dict(mode=mode,bytes=len(raw),kernel_check=result,sha256=hashlib.sha256(raw).hexdigest(),passed=result==0))
r=dict(stage=423,actual_ipa_generated_packets=True,current_native_kernel_validator=True,kernel_codec_source_unchanged_since422=True,rows=rows,passed=all(r['passed'] for r in rows))
(HERE/'packet-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
