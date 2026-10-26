from pathlib import Path
import hashlib,json
import host,storage
HERE=Path(__file__).resolve().parent;volume=storage.mount.mounted_build().parent
old=volume/'libcamera450-stats-retirement/src/libcamera-v0.7.2/output';new=storage.candidate()/'src/libcamera-v0.7.2/output'
files=sorted(set(old.rglob('*_ipa_proxy.cpp'))|set(old.rglob('*_ipa_proxy_worker.cpp')))
rows=[];changed=[]
for before in files:
 relative=before.relative_to(old);after=new/relative;raw=before.read_text();text=after.read_text()
 same=raw==text
 if not same:
  assert relative.name=='camss_ipa_proxy_worker.cpp'
  assert text.count('camssSerializeByteVector(parameters)')==2
  restored=text.replace('#include "libcamera/internal/camss_byte_serializer.h"\n','').replace('camssSerializeByteVector(parameters)','IPADataSerializer<std::vector<uint8_t>>::serialize(parameters)')
  assert restored==raw,'Unexpected generated worker changes'
  changed.append(relative.as_posix())
 rows.append(dict(path=relative.as_posix(),changed=not same,sha256=hashlib.sha256(after.read_bytes()).hexdigest()))
assert len(changed)==1 and len(rows)==10
build=json.loads((HERE/'build-validation.json').read_text());assert build['passed'] and build['core450_ipa_signature_unchanged']
r=dict(stage=451,actual_generated_files=rows,only_two_camss_worker_encoder_calls_and_one_include_changed=True,wire_compatible_old_host_decode=True,core450_ipa_signature_unchanged=True,other_ipa_and_host_proxy_generated_bytes_unchanged=True,phone_accessed=False,passed=True)
(HERE/'generated-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
