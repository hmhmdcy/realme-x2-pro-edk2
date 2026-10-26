"""Preserve the already frozen R1 bytes, with an explicit README raw mapping."""
from pathlib import Path
import hashlib, json
HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
raw = (HERE / 'delivery.json').read_bytes()
assert sha(raw) == '93b0bc012d8f65321779863258b900b2820fa10818054cc3b53954f009ab6f86'
delivery = json.loads(raw)
for name, item in delivery['files'].items(): assert sha((HERE / name).read_bytes()) == item['sha256']
history = HERE / 'history/revision-1'; assert not history.exists()
history.mkdir(parents=True)
mapping = {}
for name, item in delivery['files'].items():
    stored = 'README-original.md.inc' if name == 'README.md' else name
    data = (HERE / name).read_bytes()
    with (history / stored).open('xb') as stream: stream.write(data)
    mapping[name] = dict(stored_path='history/revision-1/' + stored, sha256=sha(data), bytes=len(data))
with (history / 'delivery.json').open('xb') as stream: stream.write(raw)
layout = dict(original_delivery_sha256=sha(raw), raw_originals=mapping,
              reason='R1 README bytes retained as raw .md.inc; no obsolete relative-link rendering implied')
with (HERE / 'archive-layout.json').open('x') as stream: stream.write(json.dumps(layout, indent=2) + '\n')
print(json.dumps(dict(archived=True, original_files=len(mapping), original_delivery_sha256=sha(raw))))
