from pathlib import Path
import json,sys
import host
run=int(sys.argv[1]);assert run in [1,6]
code=r'''
from pathlib import Path
import json,re,sys
run=int(sys.argv[1]);p=Path('/var/lib/samurai')/('k265-camera-'+str(run));d=json.loads((p/'summary.json').read_text());lines=(p/'stderr-private.txt').read_text(errors='replace').splitlines();r=[]
for change in d['probe_result']['held_change_details']:
 target=str(change['before_pts']);matches=[i for i,l in enumerate(lines) if 'gstpipewiresrc.c' in l and re.search(r'pts '+target+r',',l)]
 entries=[]
 for i in matches:
  nearby=lines[max(0,i-8):i+3];pool=[]
  for l in nearby:
   m=re.search(r'got new buffer (0x[0-9a-f]+)',l)
   if m:pool.append(m[1])
  for pointer in pool:
   relevant=[l for l in lines if pointer in l and any(x in l for x in ['remove buffer','queued buffer','recycle buffer','was not recycled','add buffer'])]
   entries.append(dict(pool_buffer=pointer,frame_lines=nearby,lifetime_lines=relevant[-16:]))
 r.append(dict(change=change,matches=entries))
print(json.dumps(dict(run=run,retirement=r,all_remove_timestamps=[l for l in lines if 'remove buffer' in l and 'queued: 0' in l]),indent=2))
'''
q=host.ssh('python3 - '+str(run),input=code.encode(),timeout=25);(host.PRIVATE/('retirement-'+str(run)+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
