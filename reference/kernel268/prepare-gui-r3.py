"""Use a fresh context after the verified unlocked Phosh startup."""
from pathlib import Path

R=Path(__file__).resolve().parent
for old,new in [('gui-auto-r2.py','gui-auto-r3.py'),('native-snapshot-gui-r2.py','native-snapshot-gui-r3.py'),('run-gui-r2.py','run-gui-r3.py')]:
    s=(R/old).read_text().replace('gui-r2','gui-r3').replace('gui_r2','gui_r3').replace('gui-auto-r2','gui-auto-r3')
    compile(s,new,'exec');(R/new).write_text(s)
print('Prepared a fresh owned-window test after verified unlocked shell startup.')
