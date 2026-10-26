from pathlib import Path
import json
p=Path('/run/k248-backup');s=json.loads((p/'state-private.json').read_text());manifest=json.loads((p/'source-manifest-private.json').read_text()) if (p/'source-manifest-private.json').exists() else None
print(json.dumps(dict(report=dict(state=s['state'],terminal=s['terminal'],source_count=len(s['verified_sources']),pid=s['pid'],completed_requests=s.get('completed_requests',0),source_total_bytes=sum(x['bytes'] for x in manifest.values()) if manifest else None),private=dict(state=s,manifest=manifest,failure=(p/'failure-private.txt').read_text() if (p/'failure-private.txt').exists() else None))))
