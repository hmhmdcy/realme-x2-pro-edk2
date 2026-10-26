from pathlib import Path
import json,sys
import host
R=Path(__file__).parent;run=int(sys.argv[1]);assert run in range(12,19)
code=r'''
from pathlib import Path
import json,re,sys
run=int(sys.argv[1]);p=Path('/var/lib/samurai')/('k265-camera-'+str(run));d=json.loads((p/'summary.json').read_text());assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
t=(p/'stderr-private.txt').read_text(errors='replace')
adds=re.findall(r'ownership-add buffer:(\S+) busy:(\S+) count:(\d+) meta-inode:(\d+) image-inode:(\d+) type:(\d+)',t)
held=re.findall(r'ownership-held buffer:(\S+) seq:(\d+) pts:(\d+) busy:(\S+) count:(\d+) held:(\d+)',t)
removed=re.findall(r'ownership-remove buffer:(\S+) busy:(\S+) count:(\d+) held:(\d+)',t)
private=dict(adds=adds,held=held,removed=removed,change_details=(d.get('probe_result') or {}).get('held_change_details'))
(p/'ownership-decoded-private.json').write_text(json.dumps(private,indent=2)+'\n')
q=d.get('probe_result') or {}
print(json.dumps(dict(stage=265,run=run,completed=d['diagnostic_completed'],source_plugin=q.get('source_plugin'),private_spa=d.get('private_spa_candidate_active'),held_checks=q.get('held_checked'),held_changes=q.get('held_content_changed'),photos=len(q.get('shots') or []),ownership_adds=len(adds),ownership_held=len(held),missing_busy=sum(a[1] in ['0','0x0','(nil)'] for a in adds),held_without_extra_loan=sum(int(x[5])!=1 or int(x[4])<1 for x in held),removed_with_live_gst_loan=sum(int(x[3])==1 for x in removed),image_inodes=len(set(x[4] for x in adds)),metadata_inodes=len(set(x[3] for x in adds)),not_recycled_errors=t.count('was not recycled'),runtime_logging_restored=d['runtime_logging_restored']),indent=2))
'''
q=host.ssh('python3 - '+str(run),input=code.encode(),timeout=20);d=json.loads(q.stdout);(R/('ownership-'+str(run)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');print(q.stdout.decode())

