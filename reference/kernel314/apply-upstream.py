"""One-time import into the isolated RAW/streams worktree; inspect rejects."""
from pathlib import Path
import subprocess
import host
HERE=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera314-streams-kernel')
for n in [1,2,4,6]:
 q=subprocess.run(['git','-C',str(TREE),'apply','--reject',str(HERE/'upstream'/f'{n}-streams.patch')],capture_output=True)
 (host.PRIVATE/f'upstream-{n}-apply.log').write_bytes(q.stdout+q.stderr)
 print(str(n)+': '+(q.stdout+q.stderr).decode()[-3500:])
