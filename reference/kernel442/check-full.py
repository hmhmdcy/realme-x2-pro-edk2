"""Keep the original per-frame and causal audits, adding RAW stop compatibility."""
from pathlib import Path
import re
import host
HERE=Path(__file__).resolve().parent

def join_split_frame_record(text):
 """Rejoin an application line interrupted by complete stderr log records.

 The original bytes remain private and unchanged. Only the observed split
 of ADAPT_FRAME is accepted; all frame fields and the intervening logger
 records still pass the existing strict audit.
 """
 out=[];splits=0;pending=None
 logger=re.compile(r'\[\d+:\d+:\d+\.\d+\] \[\d+\] +(INFO|DEBUG|WARN|ERROR) \w+ \S+:\d+ ')
 for line in text.splitlines():
  match=logger.search(line)
  if pending is None:
   if line.startswith('ADAPT_FRAME ') and match:
    pending=line[:match.start()];out.append(line[match.start():]);splits+=1
   else:out.append(line)
  elif match:
   pending+=line[:match.start()];out.append(line[match.start():])
  else:
   pending+=line
   assert re.match(r'^ADAPT_FRAME phase=\d+ request=\d+ sequence=\d+ timestamp=\d+ matched=[01] ev=',pending)
   assert all(k+'=' in pending for k in ['mean-y','red','blue','matrix'])
   out.append(pending);pending=None
 assert pending is None
 result='\n'.join(out)+'\n'
 for marker in ['ADAPT_FRAME ','AWB_STATE ','IPE_TONE_QUEUE ','IPE_RECEIPT ']:
  assert result.count(marker)==text.count(marker)
 return result,splits

source=(HERE.parent/'kernel441/check-hardware.py').read_text()
source=source.replace("HERE/'frame-audit.py'", "HERE.parent/'kernel441/frame-audit.py'")
source=source.replace('stage=441','stage=442').replace('formal440_modules_services_resources_restored=True','formal440_modules_services_resources_restored=True,stop_cancellation_semantics_corrected=True,app_thread_dispatch_used=True')
source=source.replace("text=(folder/'client.log').read_text();w=", "text,log_splits=join_split_frame_record((folder/'client.log').read_text());w=")
source=source.replace('replays=[]', "assert set(state['replays'])=={'1280x720','1920x1080'}\nreplays=[]")
marker=" trace=summary['trace'];"
extra=''' dispatch=re.findall(r'CAPTURE_DISPATCH queued=(\\d+) callback-tid=(\\d+) process-tid=(\\d+) event-peak=(\\d+)',text)
 assert len(dispatch)==1
 queued,callback,process,peak=map(int,dispatch[0]);app_pid=int(next(iter(app)))
 assert queued==1 and callback!=process==app_pid and 1<=peak<=4
 assert 'CAPTURE_MODE queued=1 injected-delay-ms=0' in text
 cancellations=text.count('REQUEST_STOP_CANCEL ');assert cancellations>0
 row.update(stop_cancellations=cancellations,application_dispatch_queued=True,split_application_log_records_rejoined=log_splits)
'''
assert source.count(marker)==1;source=source.replace(marker,extra+marker)
marker="s=state['candidate_final_status'];"
extra='''compatibility=[]
assert set(state['compatibility'])=={'raw','dual'}
for kind,summary in state['compatibility'].items():
 text=(root/('compatibility-'+kind)/'client.log').read_text()
 assert summary['passed'] and summary['frames']==6 and 'failed=0 result=0' in text
 assert 'IPE_TONE_REJECT' not in text and 'IFE_GTM_REJECT' not in text and 'IMAGE_PAIR_TIMEOUT' not in text
 pairs=re.findall(r'RawPair request=(\\d+) pix-sof=(\\d+) raw-sof=(\\d+) pix-start=(\\d+) raw-start=(\\d+) delta-ns=(\\d+) tolerance-ns=(\\d+) matched=(\\d+)',text)
 assert len(pairs)==6 and all(p[1]==p[2] and int(p[5])<=int(p[6]) and p[7]=='1' for p in pairs)
 images=re.findall(r'RAW_IMAGE request=(\\d+) format=(\\S+) sequence=(\\d+) timestamp=(\\d+) bytes=(\\d+) status=(\\d+) sample-hash=(\\d+)',text)
 assert len(images)==(6 if kind=='raw' else 12)
 assert all(int(i[3])>0 and int(i[4])>0 and i[5]=='0' and int(i[6])>0 for i in images)
 assert sum(i[1]=='NV12' for i in images)==(0 if kind=='raw' else 6)
 stop=re.findall(r'IPE_HISTORY_STOP epoch=1 prepared=(\\d+) committed=(\\d+) discarded=(\\d+) superseded=(\\d+) aborted=(\\d+) pending=(\\d+)',text)
 assert len(stop)==1;prepared,committed,discarded,superseded,aborted,pending=map(int,stop[0])
 assert not pending and not superseded and prepared==committed+discarded+aborted
 if kind=='raw':
  assert not summary['ipe_completed'] and not committed
  assert all(t not in text for t in ['PD10_READY ','IPE_TONE_PREPARE ','IPE_TONE_QUEUE '])
  assert re.search(r'IPE_TONE_STOP epoch=1 revision=0 pending=0',text)
 else:assert committed==6
 assert re.search(r'REQUEST_STOP_CANCEL .* raw=1',text)
 completed+=summary['ipe_completed'];compatibility.append(dict(kind=kind,**summary))
'''
assert source.count(marker)==1;source=source.replace(marker,extra+marker)
source=source.replace("rows=rows,replays=replays,", "rows=rows,replays=replays,compatibility=compatibility,")
exec(compile(source,str(HERE/'check-full.py'),'exec'))
