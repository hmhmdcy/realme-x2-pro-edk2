from pathlib import Path
import collections,importlib.util,json,struct,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel244');v=json.loads((P/'collect-live-packets-private.json').read_text())['private'];sys.path.insert(0,str(R.parent/'kernel226'));from loc_decode import summarize
rows=[json.loads(x) for x in v.get('loc-events-private.jsonl','').splitlines()];loc=summarize(rows)
spec=importlib.util.spec_from_file_location('diag_boot244',R/'diag_transport_boot.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
packets=[];bad=0
for line in v['diag-events-private.jsonl'].splitlines():
 x=json.loads(line)
 if x['kind']=='rx' and x.get('channel') in [1,3] and x['port']!=0xfffffffe:
  try:packets+=m.frames(bytes.fromhex(x['hex']))
  except ValueError:bad+=1
counts=collections.Counter(p[0] for p in packets if p);logs=collections.Counter(struct.unpack_from('<H',p,6)[0] for p in packets if len(p)>=16 and p[0]==0x10)
report=dict(stage=244,loc=loc,diag_payload_commands=dict(counts),diag_log_ids=dict(logs),diag_payload_lengths=sorted(set(len(p) for p in packets)),diag_decode_errors=bad)
(R/'packet-preview-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=244,sv=loc['sv'],diag_payload_commands=dict(counts),diag_log_ids=dict(logs),diag_payload_lengths=report['diag_payload_lengths'],diag_decode_errors=bad)))
