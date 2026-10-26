"""Repeat the CPU GUI check only after the user confirms an unlocked desktop."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent
for old,new in [('native-snapshot-cairo.py','native-snapshot-cairo-r2.py'),('start-snapshot-cairo.py','start-snapshot-cairo-r2.py'),('poll-snapshot-cairo.py','poll-snapshot-cairo-r2.py'),('analyze-snapshot-cairo.py','analyze-snapshot-cairo-r2.py')]:
 s=(R/old).read_text().replace('k240-snapshot-cairo','k240-snapshot-cairo-r2').replace('k240_snapshot_cairo','k240_snapshot_cairo_r2')
 s=s.replace('native-snapshot-cairo.py','native-snapshot-cairo-r2.py').replace('snapshot-cairo-launch','snapshot-cairo-r2-launch').replace('snapshot-cairo-poll','snapshot-cairo-r2-poll').replace('snapshot-cairo-gui-logs','snapshot-cairo-r2-gui-logs').replace('snapshot-cairo-startup-validation','snapshot-cairo-r2-startup-validation').replace('snapshot-cairo-analysis-host','snapshot-cairo-r2-analysis-host').replace('snapshot-cairo-frame-flow-validation','snapshot-cairo-r2-frame-flow-validation')
 s=s.replace('gtk4paintablesink:5','gtk4paintablesink:6')
 ast.parse(s);(R/new).write_text(s)
print('Foreground CPU test prepared; user confirmed unlocked desktop')
