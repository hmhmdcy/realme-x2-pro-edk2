"""Keep statistics owners through the bounded processed-image backlog."""
from pathlib import Path
import difflib,hashlib,json
import host,storage
HERE=Path(__file__).resolve().parent;storage.mount.mounted_build()
tree=storage.candidate()/'src/libcamera-v0.7.2';rel='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';p=tree/rel
before=p.read_text();a='ret = d->stats_->allocateBuffers(4, &d->statsBuffers_);\n if (ret < 3) { ret = ret < 0 ? ret : -ENOMEM; goto error; }'
b='''{
 /* Isolated IPA calls and the first IPE firmware boot may hold the
  * camera event loop while FULL requests remain queued. Keep the same
  * bounded backlog as PD10 instead of exhausting a four-frame stats pool. */
 const unsigned int statsCount = d->processedEnabled_ && d->ipe_ ?
     d->stream_.configuration().bufferCount + 4 : 4;
 ret = d->stats_->allocateBuffers(statsCount, &d->statsBuffers_);
 if (ret < int(statsCount)) { ret = ret < 0 ? ret : -ENOMEM; goto error; }
 }'''
if not before.count(a):
 # Repair the first local build's declaration scope before regenerating 0054.
 start=before.index('/* Isolated IPA calls and the first IPE firmware boot')
 end=before.index('if (ret < int(statsCount)) { ret = ret < 0 ? ret : -ENOMEM; goto error; }',start)+len('if (ret < int(statsCount)) { ret = ret < 0 ? ret : -ENOMEM; goto error; }')
 before=before[:start]+a+before[end:]
assert before.count(a)==1;p.write_text(before.replace(a,b))
(HERE/'0054-camss-ipe-statistics-backlog.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),p.read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
state=json.loads((HERE/'source-state.json').read_text())
for row in state['source_hashes']:
 if row['path']==rel:row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
state.update(statistics_pool_tracks_processed_request_backlog=True,raw_only_statistics_pool_unchanged=True,build_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=441,bounded_statistics_pool_uses_processed_request_count_plus_four=True,raw_only_pool_preserved=True,ipa_math_and_stock_profiles_unchanged=True,phone_changed=False,passed=True)))
