"""User-requested thirty-second retry of the verified CPU mmap preview."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent
for stem in ['native','start','poll','analyze']:
 old=R/(stem+'-snapshot-mmap.py');new=R/(stem+'-snapshot-mmap-r2.py')
 s=old.read_text().replace('k240-snapshot-mmap','k240-snapshot-mmap-r2').replace('k240_snapshot_mmap','k240_snapshot_mmap_r2')
 s=s.replace('native-snapshot-mmap.py','native-snapshot-mmap-r2.py').replace('snapshot-mmap-launch','snapshot-mmap-r2-launch').replace('snapshot-mmap-poll','snapshot-mmap-r2-poll').replace('snapshot-mmap-gui-logs','snapshot-mmap-r2-gui-logs').replace('snapshot-mmap-startup-validation','snapshot-mmap-r2-startup-validation').replace('snapshot-mmap-analysis-host','snapshot-mmap-r2-analysis-host').replace('snapshot-mmap-frame-flow-validation','snapshot-mmap-r2-frame-flow-validation')
 s=s.replace('time.monotonic()+16','time.monotonic()+30').replace('app_still_running_at16s','app_still_running_at30s')
 ast.parse(s);new.write_text(s)
print('User-requested30s preview retry prepared')
