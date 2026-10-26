"""Fix compile-time API use and reject incomplete source buffers before adoption."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
def edit(rel,a,b):
 p=tree/rel;t=p.read_text();assert t.count(a)==1,(rel,a,t.count(a));p.write_text(t.replace(a,b))
edit('src/ipa/camss-vfe/camss.cpp','coarse.asList().size()!=3','coarse.size()!=3')
edit('src/ipa/camss-vfe/camss.cpp','{ true, *exposureDelay, *gainDelay }','{ true, *exposureDelay, *gainDelay, false }')
edit('src/libcamera/pipeline/camss-vfe/camss_ipe.cpp','coarse->metadata().status!=FrameMetadata::FrameSuccess ||','coarse->metadata().status!=FrameMetadata::FrameSuccess ||\n        coarse->metadata().planes()[0].bytesused!=46080 || input->metadata().planes()[0].bytesused!=460800 ||')
p=HERE/'source-state.json';s=json.loads(p.read_text())
for r in s['source_hashes']:r['sha256']=hashlib.sha256((tree/r['path']).read_bytes()).hexdigest()
p.write_text(json.dumps(s,indent=2)+'\n')
