"""Inspect the entire owned accessibility tree, including deeply nested controls."""
from pathlib import Path

R=Path(__file__).resolve().parent
for old,new in [('gui-auto-r3.py','gui-auto-r4.py'),('native-snapshot-gui-r3.py','native-snapshot-gui-r4.py'),('run-gui-r3.py','run-gui-r4.py')]:
    s=(R/old).read_text().replace('gui-r3','gui-r4').replace('gui_r3','gui_r4').replace('gui-auto-r3','gui-auto-r4')
    if old.startswith('gui-auto'):
        s=s.replace('if depth<20:', 'if depth<64:')
        s=s.replace('description=props.get(\'Description\'),actions=actions)', 'description=props.get(\'Description\'),depth=depth,actions=actions)')
    compile(s,new,'exec');(R/new).write_text(s)
print('Prepared depth64 owned-window test.')
