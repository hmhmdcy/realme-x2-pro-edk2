"""Preserve size/timestamp evidence for any future ownership failure."""
from pathlib import Path
R=Path(__file__).parent;p=R/'advanced-probe.py';s=p.read_text();assert 'held_pts_changed' not in s
s=s.replace('held_content_changed=0,held_bytes_sampled=65536','held_content_changed=0,held_bytes_sampled=65536,held_pts_changed=0,held_change_details=[]')
s=s.replace("hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest()))", "hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest(),buffer.get_size(),buffer.pts,buffer.n_memory()))")
s=s.replace('timestamp,buffer,digest=held.pop(0)', 'timestamp,buffer,digest,original_size,original_pts,original_memories=held.pop(0)')
needle="   data['held_content_changed']+=hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest()!=digest"
assert s.count(needle)==1
s=s.replace(needle,"""   changed=hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest()!=digest
   pts_changed=buffer.pts!=original_pts
   data['held_content_changed']+=changed;data['held_pts_changed']+=pts_changed
   if changed or pts_changed:
    data['held_change_details'].append(dict(elapsed_ms=(time.monotonic()-start)*1000,before_size=original_size,after_size=buffer.get_size(),before_pts=original_pts,after_pts=buffer.pts,before_memories=original_memories,after_memories=buffer.n_memory()))""")
p.write_text(s)
p=R/'advanced-runner.py';s=p.read_text();s=s.replace("else:assert result['remote_node_reliable']=='true'", "else:assert result['remote_node_reliable']=='true' and result['held_pts_changed']==0")
p.write_text(s)
