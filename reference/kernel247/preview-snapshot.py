"""Validate envelopes and display layouts without assigning undocumented fields."""
from pathlib import Path
import collections,importlib.util,json,struct,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel247');label=sys.argv[1];assert label in ['baseline-off','comparison-online'];o=P/(label+'-snapshot');spec=importlib.util.spec_from_file_location('diag247preview',R/'diag_streaming.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);packets=[];by=collections.defaultdict(list)
raw=(o/'diag-events-private.jsonl').read_bytes();excluded_prefix=0
if label=='comparison-online':
 prefix=(P/'baseline-off-snapshot/diag-events-private.jsonl').read_bytes();assert raw.startswith(prefix);excluded_prefix=len(prefix);raw=raw[len(prefix):]
for line in raw.splitlines():
 x=json.loads(line)
 if x['kind']=='rx' and x.get('channel') in [1,3] and x['port']!=0xfffffffe:
  for p in m.frames(bytes.fromhex(x['hex'])):
   if p and p[0]==0x10:
    assert len(p)>=16;a,b,code=struct.unpack_from('<HHH',p,2);assert a==b==len(p)-4;by[code].append(p[16:]);packets.append(dict(code=code,elapsed_ms=x['elapsed_ms'],payload_hex=p.hex()))
shapes={hex(code):dict(reports=len(bodies),body_size_counts=dict(collections.Counter(map(len,bodies))),leading_byte_counts=dict(collections.Counter(b[0] if b else None for b in bodies)),distinct_body_count=len(set(bodies))) for code,bodies in by.items()}
phase=json.loads((o/(label+'-summary.json')).read_text());report=dict(stage=247,phase=label,packets=len(packets),earlier_snapshot_prefix_bytes_excluded=excluded_prefix,log_shapes=shapes,exact_envelope_lengths_validated=True,leading_byte_not_assumed_version=True,receiver_sv=phase['receiver']['sv'],position_status_counts=phase['receiver']['position_status_counts'],utc_prepared_before=phase['time_prepared_before'],mm_power=phase['mm_power'],cleanup=phase['cleanup'])
(P/(label+'-decoded-log-envelopes-private.json')).write_text(json.dumps(packets,indent=2)+'\n');(R/(label+'-preview-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
