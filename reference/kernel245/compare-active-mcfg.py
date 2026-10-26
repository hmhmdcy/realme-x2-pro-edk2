"""Compare active PDC metadata/IDs with original Android modem MCFG files."""
from pathlib import Path
import hashlib,json,struct,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel245');B=P.parent/'kernel242'
meta=json.loads((R/'read-active-pdc-info-validation.json').read_text())['selected_config_metadata'];events=json.loads((P/'read-selected-pdc-private.json').read_text())['private']['events'];ids={}
for x in events:
 b=bytes.fromhex(x['hex'])
 if len(b)<7:continue
 kind,txn,msg,n=struct.unpack_from('<BHHH',b)
 if kind!=4 or msg!=0x22:continue
 assert n==len(b)-7;off=7;v={}
 while off<len(b):
  t,size=struct.unpack_from('<BH',b,off);off+=3;v[t]=b[off:off+size];off+=size
 assert off==len(b) and v[1]==b'\0\0';a=v[0x11];assert len(a)==1+a[0];ids[x['config_type']]=a[1:]
assert set(ids)=={0,1}
manifest=json.loads(json.loads((B/'inspect-rf-firmware-private.json').read_text())['private']['snapshots']['/run/samurai-wifi/mcfg-state/source-manifest-private.json']);backup=Path(json.loads((B/'android-backup-source-private.json').read_text())['modem_image'])
matches={};records={}
for kind,label in [(0,'platform'),(1,'software')]:
 m=meta[label];assert m['ack_result']==0 and m['indication_result']==0;group=[]
 for name,v in manifest.items():
  if v['bytes']!=m['total_bytes']:continue
  x=subprocess.run(['mtype','-i',str(backup),'::/image/'+name],capture_output=True);assert x.returncode==0;b=x.stdout;assert hashlib.sha256(b).hexdigest()==v['sha256'];found=m['description'].encode() in b;sha1match=hashlib.sha1(b).digest()==ids[kind]
  row=dict(path=name,bytes=len(b),description_present_in_file=found,sha1_matches_active_id=sha1match);group.append(row);records[name]=row
 matches[label]=dict(selected_description=m['description'],selected_version=m['version'],selected_bytes=m['total_bytes'],same_size_source_candidates=len(group),description_matches=[x['path'] for x in group if x['description_present_in_file']],sha1_matches=[x['path'] for x in group if x['sha1_matches_active_id']])
report=dict(stage=245,active_runtime_pdc_metadata_compared=True,matches=matches,metadata_match_not_full_modem_configuration_readback=True,original_backup_read_only=True)
(P/'active-mcfg-comparison-private.json').write_text(json.dumps(dict(report=report,records=records),indent=2)+'\n');(R/'active-mcfg-comparison-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
