"""Restore only the known missing original link after the failed default-mode test."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k298-work/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai/k300-ipa-r3')
report=json.loads((root/'summary-private.json').read_text());assert not report['passed'] and report['tool_exit']==1
assert all(s=='suspended' for s in report['after']['sensors'].values())
for name in ['acb3000.camss','ac4a000.cci','ac4b000.cci']:
 assert Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip()=='suspended'
actual=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'])
before=(root/'graph-before-private.txt').read_bytes();after=(root/'graph-after-private.txt').read_bytes()
assert actual==after
expected=before.replace(b'-> "msm_csid0":0 [ENABLED]\n',b'-> "msm_csid0":0 []\n',1).replace(b'<- "msm_csiphy0":1 [ENABLED]\n',b'<- "msm_csiphy0":1 []\n',1)
assert expected==after and before!=after
subprocess.run(['media-ctl','-d','/dev/media0','--links','"msm_csiphy0":1 -> "msm_csid0":0 [1]'],check=True,capture_output=True)
assert subprocess.check_output(['media-ctl','-d','/dev/media0','-p'])==before
out=dict(stage=300,kernel_build=298,original_graph_fully_restored=True,changed_only_original_missing_link=True,
 source='msm_csiphy0:1',sink='msm_csid0:0',prior_failed_attempt_preserved=True,standard_media_api_only=True,
 no_reboot_or_force_suspend=True)
(root/'recovery-private.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(HERE/'graph-recovery-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
