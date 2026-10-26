from pathlib import Path
import json
import storage
HERE=Path(__file__).resolve().parent;T=storage.candidate()/'src/libcamera-v0.7.2';s=json.loads((HERE/'source-state.json').read_text());paths=set()
for row in s['source_hashes']:
 for d in (T/row['path']).parents:paths.add(d/'AGENTS.md')
found=[str(p) for p in paths if p.is_file()];print(json.dumps(dict(applicable_source_instructions=found)));assert not found
