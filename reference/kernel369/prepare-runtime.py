"""Prepare a fresh, pre-armed fault capture; do not replay any earlier run."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['collector-validation.json','ownership-validation.json','intree-build-validation.json']:assert json.loads((HERE/name).read_text())['passed']
old=HERE.parent/'kernel366'
s=(old/'boot-worker.py').read_text().replace('import json,os,re,subprocess,time,traceback','import errno,json,os,re,subprocess,sys,time,traceback')
s=s.replace("observation=dict(pid=os.getpid(),terminal=False,passed=False,events=[])","collector=None;collector_log=None\nobservation=dict(pid=os.getpid(),terminal=False,passed=False,firmware_handshake_passed=False,diagnostic_completed=False,events=[])")
s=s.replace("and not result.get('mapped_bytes')","and not result.get('mapped_bytes') and not result.get('remaining_groups') and not result.get('remaining_domains')")
anchor=" assert observation['camss_before']=='suspended','CAMSS has an active consumer'"
s=s.replace(anchor,anchor+"\n assert Path('/sys/class/devcoredump').is_dir()\n disabled=Path('/sys/class/devcoredump/disabled')\n assert not disabled.exists() or disabled.read_text().strip()=='0','Standard devcoredump is disabled'\n assert not any((p/'failing_device').exists() and (p/'failing_device').resolve().name=='ac10000.samurai-icp356-boot' for p in Path('/sys/class/devcoredump').glob('devcd*'))")
anchor=" save('load-boot-test');attempted_test=True;run(['insmod',str(ROOT/'test.ko')])"
arm=''' save('arm-collector')
 collector_log=(ROOT/'collector.log').open('xb')
 collector=subprocess.Popen([sys.executable,str(ROOT/'dump-collector.py'),str(ROOT)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 deadline=time.monotonic()+3
 while not (ROOT/'collector-ready.json').exists() and collector.poll() is None and time.monotonic()<deadline:time.sleep(.01)
 assert collector.poll() is None and (ROOT/'collector-ready.json').exists(),'Collector not live and armed; no A5 start allowed'
 ready=json.loads((ROOT/'collector-ready.json').read_text());assert ready['pid']==collector.pid and ready['ready']
 observation.update(collector_pid=collector.pid,collector_armed_before_boot_module=True)
'''
assert s.count(anchor)==1;s=s.replace(anchor,arm+anchor)
a=s.index(' if not releasable(result):');b=s.index(" observation['passed']=True",a)+len(" observation['passed']=True")
s=s[:a]+''' assert releasable(result),'A5 or power/mapping resources remain owned; preserve modules for inspection'
 if result.get('error')==0 or not result.get('cpu_release_attempted'):(ROOT/'collector-stop').touch()
 deadline=time.monotonic()+16
 while not (ROOT/'collector-result.json').exists() and time.monotonic()<deadline:time.sleep(.01)
 assert (ROOT/'collector-result.json').exists(),'Collector has not completed; preserve device ownership'
 collected=json.loads((ROOT/'collector-result.json').read_text());observation['collector_result']=collected
 assert not collected.get('captured') or collected.get('owned_snapshot_acknowledged'),'Snapshot still owns device reference'
 handshake=bool(result['error']==0 and result['cleanup_error']==0 and result['pc_error']==0 and result['init_response']==1 and result['init_done'] and result['ping_done'] and result['pc_done'] and result['fw_version'] and result['interrupts']>=3 and result['messages']>=3 and result['reset_asserted'] and not result['watchdogs'] and not result['protocol_errors'])
 observation['firmware_handshake_passed']=handshake
 if result.get('init_response')==3:
  assert result['error']==-errno.EREMOTEIO and result['cleanup_error']==0 and result['pc_error']==0,result
  observation['firmware_failure_observed']=True
  observation['sfr_recovered']=bool(collected.get('decoded') and collected.get('init_response')==3 and collected.get('sfr_characters',0)>0)
  observation['diagnostic_completed']=observation['sfr_recovered']
 else:
  assert handshake,result
  observation['diagnostic_completed']=True
 observation['passed']=handshake
'''+s[b:]
# Before unloading an overlay, finish or stop its collector, and never remove
# the device while a captured snapshot still holds its reference.
anchor=" try:\n  if attempted_test and Path('/sys/module',test).exists():"
replacement=""" try:
  if collector is not None:
   if collector.poll() is None:
    (ROOT/'collector-stop').touch();collector.wait(timeout=3)
   observation['collector_exit']=collector.returncode
   if (ROOT/'collector-result.json').exists():observation['collector_result']=json.loads((ROOT/'collector-result.json').read_text())
   if collector_log is not None:collector_log.close()
  if attempted_test and Path('/sys/module',test).exists():"""
assert s.count(anchor)==1;s=s.replace(anchor,replacement)
s=s.replace("   if releasable(result):", "   collected=observation.get('collector_result',{})\n   snapshot_safe=not collected.get('captured') or collected.get('owned_snapshot_acknowledged',False)\n   live_owned=[p for p in Path('/sys/class/devcoredump').glob('devcd*') if (p/'failing_device').exists() and (p/'failing_device').resolve().name=='ac10000.samurai-icp356-boot']\n   if releasable(result) and snapshot_safe and not live_owned:")
s=s.replace("|OF: ERROR'","|OF: ERROR|watchdog received|crash detected in modem'")
anchor=" save('finished',terminal=True)"
s=s.replace(anchor," observation['diagnostic_completed']=bool(observation.get('diagnostic_completed') and observation['core_absent'] and observation['test_absent'] and observation['temporary_dt_nodes_absent'] and observation['temporary_firmware_removed'] and observation['camss_after']=='suspended' and observation['clocks_after']==observation['clocks_before'] and observation['taint_after']==taint_before and not observation['new_relevant_faults'])\n"+anchor)
compile(s,'boot-worker.py','exec');(HERE/'boot-worker.py').write_text(s)
s=(old/'launch-boot.py').read_text().replace('/var/lib/samurai/k366-boot-','/var/lib/samurai/k369-boot-')
s=s.replace("P/'postboot-adoption-private.json'","P.parent/'kernel367/postboot-adoption-private.json'")
s=s.replace(" tar.add(HERE/'boot-worker.py',arcname='worker.py')", " tar.add(HERE/'boot-worker.py',arcname='worker.py')\n tar.add(HERE/'dump-collector.py',arcname='dump-collector.py')\n tar.add(HERE.parent/'kernel368/decode-start-dump.py',arcname='dump_decoder.py')")
s=s.replace("{'core.ko','test.ko','worker.py','manifest.json','firmware.elf'}", "{'core.ko','test.ko','worker.py','manifest.json','firmware.elf','dump-collector.py','dump_decoder.py'}")
compile(s,'launch-boot.py','exec');(HERE/'launch-boot.py').write_text(s)
print('Prepared fresh369 transaction with collector before CPU release and no automatic cleanup retry.')
