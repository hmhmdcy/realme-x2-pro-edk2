"""Supplementary archive for the WLAN comparison and idle LDO attribution."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'export-evidence.py').read_text().replace("['k243-gnss-diag','k243-window-clock']","['k243-wlan-off-clock']")
lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('names='):
  lines[i]="assert json.loads((r/'k243-wlan-control/state-private.json').read_text())['terminal']\nassert json.loads((r/'k243-wlan-control/summary.json').read_text())['original_rfkill_restored']\nnames=['k243-regulator-origin','k243-wlan-control','k243-wlan-off-clock','k243-wlan-tools']"
s='\n'.join(lines)+'\n'
s=s.replace('k243-evidence-private.tar.gz','k243-wlan-evidence-private.tar.gz').replace("P/'evidence'","P/'wlan-evidence'").replace("P/'evidence-private.tar.gz'","P/'wlan-evidence-private.tar.gz'").replace('evidence-archive-private.json','wlan-evidence-archive-private.json').replace('evidence-export-validation.json','wlan-evidence-export-validation.json')
exec(compile(s,str(R/'export-wlan-evidence.py'),'exec'))
