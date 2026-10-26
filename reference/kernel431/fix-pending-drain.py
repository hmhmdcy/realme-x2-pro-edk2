"""Bound expiration work when one pending image starts an asynchronous IPE job."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2';p=tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';t=p.read_text()
a=' while (!images_.empty()) finish(images_.begin()->first,histograms_.count(images_.begin()->first),true);'
assert t.count(a)==1;t=t.replace(a,' while (!images_.empty() && !ipeActive_) finish(images_.begin()->first,histograms_.count(images_.begin()->first),true);')
p.write_text(t);s=json.loads((HERE/'source-state.json').read_text())
for r in s['source_hashes']:r['sha256']=hashlib.sha256((tree/r['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
