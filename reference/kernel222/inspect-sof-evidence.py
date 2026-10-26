from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,statistics
root=Path('/var/lib/samurai');out=root/'k222-sof-trial-r2';rows=json.loads((out/'events-private.json').read_text());state=json.loads((out/'state-private.json').read_text());assert state['phase']=='verified-restored'
deltas=[(b['timestamp_ns']-a['timestamp_ns'])/1000000 for a,b in zip(rows,rows[1:])]
run=json.loads((out/'gap-runner-stdout-private.json').read_text());frames=run['frames'];assert len(frames)==16
r=dict(stage=222,frame_sync_events=len(rows),consecutive_frame_sequence=all(b['frame_sequence']==a['frame_sequence']+1 for a,b in zip(rows,rows[1:])),consecutive_queue_sequence=all(b['queue_sequence']==a['queue_sequence']+1 for a,b in zip(rows,rows[1:])),median_interval_ms=statistics.median(deltas),minimum_interval_ms=min(deltas),maximum_interval_ms=max(deltas),intervals_over_25_ms=sum(x>25 for x in deltas),request_sequences=[x['request_sequence'] for x in frames],buffer_sequences=[x['buffer_sequence'] for x in frames],frame_start_emitter_observed=run['frame_start_emitter_observed'],metadata_mapping_not_yet_fixed=True,original_module_and_policy_restored=True)
(out/'event-analysis-summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);(host.PRIVATE/'sof-event-analysis-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'sof-event-analysis-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
