from pathlib import Path
import json
import re

out = Path('/mnt/e/edk2-samurai-out/kernel136')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')
t = (out / 'decoded-legacy-core-private.txt').read_text()
lines = t.splitlines()
index = next(i for i,line in enumerate(lines) if 'ESTIMATED CRASH LOCATION' in line)
window = '\n'.join(lines[max(0,index-18):index+24])
(out / 'estimated-crash-window-private.txt').write_text(window)
# Keep values private; only command/register labels are printed for diagnosis.
print(re.sub(r'(?<![A-Za-z_])(?:0x)?[0-9a-fA-F]{4,}(?![A-Za-z_])', '<value>',window))
labels = sorted(set(re.findall(r'\b(?:RB|GRAS|CP|SP|HLSQ|PC)_[A-Z0-9_]+',window)))
record = dict(stage=136,estimated_stop_labels=labels,
    estimated_command_location_only=True,root_cause_proven=False,gpu_fix_accepted=False,goal_complete=False)
(ref / 'decoded-stop-validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
