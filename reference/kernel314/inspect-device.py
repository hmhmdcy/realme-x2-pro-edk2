from pathlib import Path
import host
q=host.raw_ssh('media-ctl -d /dev/media0 -p; uname -r')
host.PRIVATE.joinpath('media-before.txt').write_bytes(q.stdout)
lines=q.stdout.decode().splitlines()
for i,line in enumerate(lines):
 if '- entity ' in line and any(t in line for t in ['csid','vfe','s5kgw1','imx471']):
  end=next((j for j in range(i+1,len(lines)) if '- entity ' in lines[j]),min(i+25,len(lines)))
  print('\n'.join(lines[i:end]))
