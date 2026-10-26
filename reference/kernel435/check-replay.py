"""Replay the complete userspace patch against the authoritative 431 inputs."""
from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2';old=T.parents[2]/'libcamera431-pd10-auto/src/libcamera-v0.7.2';state=json.loads((HERE/'source-state.json').read_text());work=P/'patch-replay';assert not work.exists();work.mkdir()
for row in state['source_hashes']:
 p=old/row['path']
 if p.exists():q=work/row['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'0047-camss-gtm-applied-tone-history.patch')],cwd=work,capture_output=True);(P/'patch-replay-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'fuzz' not in q.stdout and b'offset' not in q.stdout,q.stdout.decode()+q.stderr.decode()
for row in state['source_hashes']:assert hashlib.sha256((work/row['path']).read_bytes()).hexdigest()==row['sha256']
r=dict(stage=435,authoritative_baseline431=True,files=len(state['source_hashes']),zero_fuzz_offset=True,all_replayed_bytes_match_final_sources=True,passed=True)
(HERE/'replay-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
