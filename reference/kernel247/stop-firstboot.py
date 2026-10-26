from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k247-runtime/boot-id-private.txt').read_bytes();base=r/'k247-nextboot';s=json.loads((base/'capture/state-private.json').read_text());p=Path('/proc',str(s['pid']));assert not s['terminal'] and s['state']=='ready' and p.joinpath('stat').read_text().split()[21]==s['start_ticks'];q=base/'stop-request';assert not q.exists();q.write_bytes(b'stop\n');print(json.dumps(dict(stage=247,stop_requested=True,live_diag_worker_identity_verified=True)))
