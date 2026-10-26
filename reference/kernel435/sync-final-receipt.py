"""Finish the numerical receipt before the pipeline releases its next image."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;T=storage.candidate()/'src/libcamera-v0.7.2';p=T/'include/libcamera/ipa/camss.mojom';t=p.read_text();a='[async] frameProcessed(';assert t.count(a)==1;p.write_text(t.replace(a,'frameProcessed('))
p=T/'src/ipa/camss-vfe/ipe_tone_profile.cpp';t=p.read_text();a='if(*gtmEnabled && (!p.tmcEnabled_ || !p.tmcUseGtm_))return -ENOTSUP;';assert t.count(a)==1;p.write_text(t.replace(a,'if(*gtmEnabled != bool(p.tmcEnabled_ && p.tmcUseGtm_))return -ENOTSUP;'))
s=json.loads((HERE/'source-state.json').read_text());s['source_hashes'].append(dict(path='include/libcamera/ipa/camss.mojom'))
for row in s['source_hashes']:row['sha256']=hashlib.sha256((T/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
