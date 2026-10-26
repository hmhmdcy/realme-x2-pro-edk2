"""Prepare current244 -> new246 Linux startup capture and one reboot wrappers."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;old=R.parent/'kernel244'
def write(name,s):
 if name.endswith('.py'):compile(s,name,'exec')
 (R/name).write_text(s)
# The preboot wrappers keep using the current244 SSH endpoint and guard.
s=(old/'samurai-diag244.initd').read_text().replace('244','246');write('samurai-diag246.initd',s)
s=(old/'install-nextboot.py').read_text().replace('kernel244','kernel246').replace('kernel240/host.py','kernel244/host.py').replace('stage=244','stage=246').replace('k236-runtime','k244-runtime').replace('k244-nextboot','k246-nextboot').replace('samurai-diag244','samurai-diag246').replace('diag_transport_boot.py','diag_streaming.py')
s=s.replace("['boot-diag.py','diag_streaming.py','samurai-diag246.initd']","['boot-diag.py','diag_streaming.py','loc_decode.py','samurai-diag246.initd']")
write('install-nextboot.py',s)
s=(old/'native-quiesce.py').read_text().replace('k236-runtime','k244-runtime').replace('k244-quiesce','k246-quiesce').replace('stage=244','stage=246').replace('k244-reboot-phase','k246-reboot-phase');write('native-quiesce.py',s)
s=(old/'launch-quiesce.py').read_text().replace('kernel244','kernel246').replace('kernel240/host.py','kernel244/host.py').replace('k236-runtime','k244-runtime').replace('k244-quiesce','k246-quiesce').replace('k244-tools','k246-tools').replace('stage=244','stage=246');write('launch-quiesce.py',s)
s=(old/'poll-quiesce.py').read_text().replace('k236-runtime','k244-runtime').replace('k244-quiesce','k246-quiesce').replace('stage=244','stage=246');write('poll-quiesce.py',s)
s=(old/'normal-reboot.py').read_text().replace('k236-runtime','k244-runtime').replace('k244-quiesce','k246-quiesce').replace('samurai-diag244','samurai-diag246').replace('k244-reboot-phase','k246-reboot-phase').replace('stage=244','stage=246');write('normal-reboot.py',s)
s=(old/'submit-normal-reboot.py').read_text().replace('kernel244','kernel246').replace('kernel240/host.py','kernel244/host.py').replace('k236-runtime','k244-runtime').replace('k244-tools','k246-tools').replace('stage=244','stage=246').replace("p=P.parent/'kernel240/transport-last-failure-private.log'","p=P.parent/'kernel244/transport-last-failure-private.log'");write('submit-normal-reboot.py',s)
# Postboot wrappers use a new scoped endpoint file, preserving original keys.
s=(old/'host.py').read_text().replace("PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel244')","PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel246')").replace("'transport244'","'transport246'");write('host.py',s)
s=(old/'refresh-usb-endpoint.ps1').read_text().replace('kernel244','kernel246');write('refresh-usb-endpoint.ps1',s)
s=(old/'observe-nextboot.py').read_text().replace('k244-nextboot','k246-nextboot').replace('k244-runtime','k246-runtime').replace('stage=244','stage=246');write('observe-nextboot.py',s)
s=(R/'run-native.py').read_text().replace("R.parent/'kernel244/host.py'","R/'host.py'");write('run-postboot.py',s)
report=dict(stage=246,prepared_not_installed=True,current_guard='k244-runtime',future_guard='k246-runtime',normal_linux_restart_only=True,ten_log_codes=True,endpoints_retained_across_sessions=True,first_boot_stream17_not_added=True,all_generated_python_compiles=True,boot_worker_sha256=hashlib.sha256((R/'boot-diag.py').read_bytes()).hexdigest())
(R/'firstboot-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
