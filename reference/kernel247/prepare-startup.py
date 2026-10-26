"""Build a before-modem MEMSHARE observer plus persistent known DIAG capture."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;O=R.parent/'kernel246';P=Path('/mnt/e/edk2-samurai-out/kernel247')
def write(name,s):
 if name.endswith('.py'):compile(s,name,'exec')
 (R/name).write_text(s)
s=(O/'boot-diag.py').read_text().replace('stage=246','stage=247').replace('k246-nextboot','k247-nextboot').replace('k246-runtime','k247-runtime').replace('samurai-diag246','samurai-diag247')
s=s.replace('diag=None;child=None;failure=None','diag=None;mem=None;child=None;failure=None')
s=s.replace('def properties():',"def poll_all(timeout):\n mem.check();diag.poll(timeout);mem.check()\ndef properties():")
s=s.replace("not watch['active'] and watch['time_prepared']","not watch['active'] and watch['running'] and watch['time_prepared'] and watch['time_preparation_completions']>0")
s=s.replace('diag.poll(0.25)','poll_all(0.25)').replace('from loc_decode import summarize','from loc_decode import summarize;from memshare_observer import Memshare')
s=s.replace("with (o/'diag-events-private.jsonl').open('x') as log:","with (o/'diag-events-private.jsonl').open('x') as log,(o/'memshare-events-private.jsonl').open('x') as mlog:")
s=s.replace('  diag=Diag(log)\n  try:\n',"  diag=Diag(log);mem=Memshare(mlog)\n  try:\n   mem.prepare();publication_dm=subprocess.check_output(['dmesg']);(o/'dmesg-after-publication-private.txt').write_bytes(publication_dm)\n   assert not any(b'Booting fw image' in line and b'/modem.mdt' in line for line in publication_dm.splitlines()),'MEMSHARE publication was too late'\n   state.update(memshare_published_before_first_linux_modem_boot=True,memshare=mem.snapshot());save()\n")
s=s.replace("diag_log_counts=c,invalid_log_lengths=bad,diag_decode_errors=diag.decode_errors,elapsed_seconds=", "diag_log_counts=c,invalid_log_lengths=bad,diag_decode_errors=diag.decode_errors,memshare=mem.snapshot(),elapsed_seconds=")
s=s.replace("finally:diag.close()\n if props", "finally:\n    try:diag.close()\n    finally:mem.close()\n if props")
s=s.replace("stage=247,first_startup_fresh_feature=queried", "stage=247,memshare_published_before_first_linux_modem_boot=True,memshare=mem.snapshot(),first_startup_fresh_feature=queried")
s=s.replace("  if diag and not diag.closed:diag.close()\n", "  if diag and not diag.closed:diag.close()\n  if mem and not mem.closed:mem.close()\n")
s=s.replace('time.monotonic()-began<1200','time.monotonic()-began<1800')
assert 'mem.prepare()' in s and 'def poll_all' in s and 'finally:mem.close()' in s;write('boot-observe.py',s)
write('diag_streaming.py',(O/'diag_streaming.py').read_text());write('loc_decode.py',(O/'loc_decode.py').read_text())
service=(O/'samurai-diag246.initd').read_text().replace('246','247').replace('boot-diag.py','boot-observe.py').replace('"$n" -lt 20','"$n" -lt 100');write('samurai-diag247.initd',service)
s=(O/'install-nextboot.py').read_text().replace('kernel246','kernel247').replace('kernel244/host.py','kernel246/host.py').replace('stage=246','stage=247').replace('k244-runtime','k246-runtime').replace('k246-nextboot','k247-nextboot').replace('samurai-diag246','samurai-diag247').replace('boot-diag.py','boot-observe.py')
s=s.replace("['boot-observe.py','diag_streaming.py','loc_decode.py','samurai-diag247.initd']","['boot-observe.py','diag_streaming.py','loc_decode.py','memshare_observer.py','samurai-diag247.initd']")
s=s.replace("base.mkdir(mode=0o700);service=", "base.mkdir(mode=0o700);tools=r/'k247-tools';assert not tools.exists();tools.mkdir(mode=0o700);service=");write('install-nextboot.py',s)
for name in ['native-quiesce.py','launch-quiesce.py','poll-quiesce.py','normal-reboot.py','submit-normal-reboot.py']:
 s=(O/name).read_text().replace('kernel246','kernel247').replace('kernel244/host.py','kernel246/host.py').replace('k244-runtime','k246-runtime').replace('k246-quiesce','k247-quiesce').replace('k246-tools','k247-tools').replace('k246-reboot-phase','k247-reboot-phase').replace('samurai-diag246','samurai-diag247').replace('stage=246','stage=247').replace("P.parent/'kernel244/transport-last-failure-private.log'","P.parent/'kernel246/transport-last-failure-private.log'")
 write(name,s)
# Final246 capture is authoritative for the current boot, unlike its old
# pre-reboot streaming-test PID, which belongs to a different boot.
s=(R/'inspect-current.py').read_text();anchor="print(json.dumps({'report':report"
extra="requested=next(p for p in Path('/sys/class/remoteproc').glob('*') if (p/'name').read_text().strip()=='modem');param=Path('/sys/module/firmware_class/parameters/path').read_text().strip();fwbase=(Path(param)/(requested/'firmware').read_text().strip()).parent;expected={line.split()[1]:line.split()[0] for line in Path('/etc/samurai-wifi/modem-sha256.txt').read_text().splitlines()};checks={name:hashlib.sha256((fwbase/name).read_bytes()).hexdigest()==digest for name,digest in expected.items()};assert len(checks)==34 and all(checks.values());mount=next(x.split() for x in Path('/proc/mounts').read_text().splitlines() if x.split()[1]=='/');assert mount[0]=='/dev/sda16' and mount[2]=='f2fs' and os.uname().version.startswith('#183 ');report.update(current_boot_guard_pass=True,all_modem_firmware_hashes_match=True,modem_firmware_files=34,root_device=mount[0],root_fs=mount[2],no_reboot_sent_yet=True)\n"
assert anchor in s;s=s.replace(anchor,extra+anchor);write('pre-reboot-health.py',s)
write('host.py',(O/'host.py').read_text().replace('kernel246','kernel247').replace('transport246','transport247'));write('refresh-usb-endpoint.ps1',(O/'refresh-usb-endpoint.ps1').read_text().replace('kernel246','kernel247'))
for name in ['run-postboot.py','observe-nextboot.py','inspect-readiness.py','poll-firstboot.py','request-baseline.py','request-online.py','stop-firstboot.py','remove-boot-hook.py']:
 s=(O/name).read_text().replace('kernel246','kernel247').replace('k246-nextboot','k247-nextboot').replace('k246-runtime','k247-runtime').replace('samurai-diag246','samurai-diag247').replace('stage=246','stage=247').replace('boot-diag.py','boot-observe.py');write(name,s)
report=dict(stage=247,prepared_not_installed=True,current_guard='k246-runtime',future_guard='k247-runtime',memshare_namespace_readback_before_radio=True,assert_no_linux_modem_boot_before_publication=True,independent_memshare_poll_thread=True,no_physical_allocation_or_scm=True,retained_diag_sockets=True,deadline_seconds=1800,all_generated_python_compiles=True,boot_source_sha256=hashlib.sha256((R/'boot-observe.py').read_bytes()).hexdigest())
(R/'startup-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n');(P/'user-hardware-context-private.json').write_text(json.dumps(dict(user_reports_never_disassembled=True,user_reports_complete_assembly=True,last_confirmed_android_gnss_fix_time='unknown',location_environment='indoor open window',no_assumption_of_hardware_fault=True),indent=2)+'\n');print(json.dumps(report))
