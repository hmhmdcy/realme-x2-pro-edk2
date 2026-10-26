from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();o=r/'k245-resume-rf-r3';s=json.loads((o/'state-private.json').read_text());assert not s['terminal'] and s['state']=='waiting' and s['phases_completed']==['baseline-off'];p=Path('/proc',str(s['pid']));assert p.joinpath('stat').read_text().split()[21]==s['start_ticks'];f=o/'stop-request';assert not f.exists();f.write_bytes(b'stop\n');print(json.dumps(dict(stage=245,stop_requested=True,worker_identity_matched=True)))
