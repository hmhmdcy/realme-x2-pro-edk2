from pathlib import Path
import ctypes,importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'ipa-validation.json').read_text())['passed']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
kernel=storage.mounted_build().parent/'source354'
assert (P.parent/'kernel422/codec422/colour.c').read_bytes()==(kernel/'drivers/media/platform/qcom/camss/camss-icp-a5-colour.c').read_bytes()
lib=ctypes.CDLL(str(P.parent/'kernel422/current-colour-codec.so'));validate=lib.camss_a5_ipe_frame_params_check;validate.argtypes=[ctypes.c_void_p];validate.restype=ctypes.c_int
rows=[]
for mode in ['colour-roundtrip','gamma-roundtrip','factory']:
 raw=(P/(mode+'-contract-private.bin')).read_bytes();assert len(raw)==6008;ret=validate(ctypes.create_string_buffer(raw));assert not ret;rows.append(dict(mode=mode,bytes=len(raw),kernel_check=ret))
r=dict(stage=424,actual_candidate_ipa_generated_packets=True,current_kernel_validator=True,rows=rows,passed=True)
(HERE/'packet-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
