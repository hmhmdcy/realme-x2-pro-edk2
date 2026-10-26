"""Publish paired statistics before a synchronous IPA call can dispatch events."""
from pathlib import Path
import difflib,hashlib,json
import host,storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2';base=tree.parents[2]/'libcamera420-request-r31/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text())
assert not state.get('statistics_published_before_ipa_parameter_call'),'Fix already applied; do not repeat'
for item in state['source_hashes']:assert hashlib.sha256((tree/item['path']).read_bytes()).hexdigest()==item['sha256']
name='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';p=tree/name;s=p.read_text()
a=s.index('void CamssVfeData::statsProcessed(');b=s.index('\nvoid CamssVfeData::finish',a);body=s[a:b]
line='if (!statistics.status && statistics.parametersKnown) queueIspUpdate(statistics.ispUpdate);';assert body.count(line)==1
body=body.replace(line,'/* Publish the same-SOF histogram before any synchronous IPA dispatch. */')
needle='int ret = stats_->queueBuffer(buffer);';assert body.count(needle)==1
body=body.replace(needle,'if (!running_ || epoch != epoch_) return;\n '+line+'\n if (!running_ || epoch != epoch_) return;\n '+needle)
s=s[:a]+body+s[b:]
needle='int ret = ipa_->prepareParameters(epoch_, buffer->cookie(), update.revision, &used);';assert s.count(needle)==1
s=s.replace(needle,'const uint64_t epoch=epoch_;\n\tint ret = ipa_->prepareParameters(epoch, buffer->cookie(), update.revision, &used);\n\tif (!running_ || epoch != epoch_) return;')
p.write_text(s)
patch=''
for item in state['source_hashes']:
 name=item['path'];a=(base/name).read_text() if (base/name).exists() else '';b=(tree/name).read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name))
 item['sha256']=hashlib.sha256((tree/name).read_bytes()).hexdigest()
(HERE/'0042-camss-ipe-frame-history.patch').write_text(patch)
state.update(statistics_published_before_ipa_parameter_call=True,stop_epoch_checked_after_parameter_call=True,hardware_evidence_before_fix='runtime-r1-validation.json',post_fix_hardware_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(stage=421,source_fixed=True,hardware_retest_needed=True)))
