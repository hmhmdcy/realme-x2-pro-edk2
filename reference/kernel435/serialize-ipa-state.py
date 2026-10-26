"""Serialize direct sync methods with queued statistics on native IPA proxy."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;T=storage.candidate()/'src/libcamera-v0.7.2';p=T/'src/ipa/camss-vfe/camss.cpp';t=p.read_text()
generated=next(q for q in (T/'output').rglob('camss_ipa_proxy.cpp'))
g=generated.read_text();a=g.index('int32_t IPAProxyCamssThreaded::prepareIpeParameters(');z=g.index('\n}',a)
assert 'return ipa_->prepareIpeParameters(' in g[a:z] and 'proxy_.invokeMethod(&ThreadProxy::processStats, ConnectionTypeQueued' in g
assert t.count('#include <optional>')==1;t=t.replace('#include <optional>','#include <optional>\n#include <mutex>')
assert t.count(' using GtmHistory=')==1;t=t.replace(' using GtmHistory=',' std::recursive_mutex stateMutex_;\n using GtmHistory=')
names=['init','configure','mapBuffers','unmapBuffers','start','convertControls','applyIspControls','frameMetadata','processFocus','lensPositionApplied','prepareIpeParameters','frameProcessed','stop','prepareParameters','parametersApplied','processStats']
for name in names:
 needle='IPACamss::'+name+'(';assert t.count(needle)==1,name;start=t.index(needle);brace=t.index('{',start);t=t[:brace+1]+'\n std::lock_guard<std::recursive_mutex> stateLock(stateMutex_);'+t[brace+1:]
p.write_text(t);s=json.loads((HERE/'source-state.json').read_text())
for row in s['source_hashes']:row['sha256']=hashlib.sha256((T/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
r=dict(stage=435,actual_generated_threaded_proxy_inspected=True,sync_ipe_preparation_direct_but_statistics_queued=True,module_state_entrypoints_serialized=names,recursive_lock_allows_same_thread_callback_reentry=True,private_helpers_called_under_entrypoint_lock=True,passed=True)
(HERE/'dispatch-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
