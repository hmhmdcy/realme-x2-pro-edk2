from pathlib import Path
import collections,json,struct,sys
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();sys.path.insert(0,str(r/'k245-tools'));from diag_resume_rf import frames
def read(path):
 rows=[json.loads(x) for x in path.read_text().splitlines()];packets=[]
 for x in rows:
  if x['kind']=='rx' and x.get('channel') in [1,3] and x['port']!=0xfffffffe:packets.extend(frames(bytes.fromhex(x['hex'])))
 return rows,[p for p in packets if p and p[0]==0]
old,versions=read(r/'k244-nextboot/capture/diag-events-private.jsonl');probe,pversions=read(r/'k245-fixed-reconnect/events-private.jsonl');current,cversions=read(r/'k245-resume-rf-r2/diag-events-private.jsonl')
seed_control=next((x['node'],x['port']) for x in old if x['kind']=='rx' and x.get('channel')==0 and x['port']!=0xfffffffe and struct.unpack_from('<I',bytes.fromhex(x['hex']))[0]==8)
def deletes(rows):
 return [struct.unpack_from('<II',bytes.fromhex(x['hex']),4) for x in rows if x['kind']=='rx' and x['port']==0xfffffffe and len(bytes.fromhex(x['hex']))==20 and struct.unpack_from('<I',bytes.fromhex(x['hex']))[0]==6]
report=dict(stage=245,seed_version_lengths=[len(p) for p in versions],probe_version_lengths=[len(p) for p in pversions],resume_version_lengths=[len(p) for p in cversions],probe_matches_seed=[p in versions for p in pversions],resume_matches_seed=[p in versions for p in cversions],resume_kinds=dict(collections.Counter(x['kind'] for x in current)),byte_differences_from_seed=[[i for i,(a,b) in enumerate(zip(p,versions[0])) if a!=b] for p in cversions],control_messages_sent=next(x['control_messages_sent'] for x in current if x['kind']=='transport_cleanup'))
report.update(seed_control_deleted_in_first_probe=seed_control in deletes(probe),seed_control_deleted_in_resume=seed_control in deletes(current),new_modem_features_in_resume=sum(x['kind']=='feature_negotiation' for x in current))
tagged=[bytes.fromhex(x['hex']) for x in old if x['kind']=='response' and x['request_code']==0]
report.update(seed_all_versions_distinct=len(set(versions)),seed_tagged_version_count=len(tagged),resume_matches_tagged_only=[p in tagged for p in cversions],resume_matches_original_rx=[p in versions for p in cversions])
print(json.dumps({'report':report,'private':dict(events=current)}))
