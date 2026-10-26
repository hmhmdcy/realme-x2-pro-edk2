"""Check the previously investigated repository refs without altering checkouts."""
from pathlib import Path
import json, subprocess
HERE = Path(__file__).resolve().parent
repos = [('jwrdegoede/libcamera','refs/heads/camss_pipeline_v2.1'),
         ('0xB0D/ife-tests','refs/heads/master'), ('loicpoulain/linux','refs/heads/camss-isp-dev')]
rows = []
for repo, ref in repos:
    q = subprocess.run(['git','ls-remote','https://github.com/'+repo+'.git',ref], capture_output=True, text=True, timeout=30)
    rows.append(dict(repository='https://github.com/'+repo, ref=ref, exit=q.returncode,
                     tip=q.stdout.strip().split()[0] if q.stdout.strip() else None))
report = dict(stage=303, source_discovery_reused_from279=True, refs_checked=rows, no_hardware_claim=True)
(HERE/'existing-solutions-refresh.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
