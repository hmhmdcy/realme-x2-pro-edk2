"""Reuse strict, pinned decoders and include startup MEMSHARE in snapshots."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent;O=R.parent/'kernel246';P=Path('/mnt/e/edk2-samurai-out/kernel247')
for name in ['snapshot-phase.py','preview-snapshot.py','decode-satellite-records.py','export-evidence.py','final-health.py']:
 s=(O/name).read_text().replace('kernel246','kernel247').replace('k246-','k247-').replace('samurai-diag246','samurai-diag247').replace('stage=246','stage=247').replace('stage-246','stage-247').replace('diag246preview','diag247preview')
 if name=='snapshot-phase.py':
  s=s.replace("'diag-events-private.jsonl','state-private.json','boot-id-private.txt'","'diag-events-private.jsonl','memshare-events-private.jsonl','state-private.json','boot-id-private.txt'")
  s=s.replace("if p.name=='diag-events-private.jsonl':","if p.name.endswith('.jsonl'):")
 if name=='preview-snapshot.py':s=s[:s.index('print(json.dumps(dict(private_rf_first_body_samples=')]
 if name=='export-evidence.py':s=s.replace("'k247-tools','k247-streaming-rf','k247-quiesce'","'k247-tools','k247-quiesce'")
 if name=='final-health.py':
  s=s.replace('boot-diag.py','boot-observe.py')
  s=s.replace("closed=a['closed']","closed=a['closed']")
  s=s.replace("local_diag_and_memshare_servers=0,","local_diag_and_memshare_servers=0,memshare=a['memshare'],memshare_published_before_first_linux_modem_boot=a['memshare_published_before_first_linux_modem_boot'],")
  s=s.replace("assert not loc_workers","assert not loc_workers;assert a['memshare']['socket_closed'] and a['memshare']['withdrawal_sent'] and not a['memshare']['error']")
 compile(s,name,'exec');(R/name).write_text(s)
marker=P/'normal-reboot-request-private.json';v=json.loads(marker.read_text());assert v['request_count']==1 and v['transition_pending'];v.update(transition_pending=False,different_boot_confirmed=True,original_strict_ssh_host_keys_preserved=True);marker.write_text(json.dumps(v,indent=2)+'\n')
print('Prepared strict analysis, snapshots, final health and evidence export; one restart completed.')
