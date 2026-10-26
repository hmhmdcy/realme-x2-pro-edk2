"""Prepare one held-failure transaction, using the current369 guard, not old launchers."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['collector-validation.json','intree-build-validation.json']:assert json.loads((HERE/name).read_text())['passed']
s=(HERE.parent/'kernel369/boot-worker.py').read_text().replace('import errno,json,os,re,subprocess,sys,time,traceback','import errno,hashlib,json,os,re,subprocess,sys,time,traceback')
s=s.replace('collector=None;collector_log=None','collector=None;collector_log=None;cleanup_attempted=False')
s=s.replace("observation=dict(pid=os.getpid(),terminal=False,passed=False,firmware_handshake_passed=False,diagnostic_completed=False,events=[])","observation=dict(pid=os.getpid(),terminal=False,passed=False,firmware_handshake_passed=False,diagnostic_completed=False,snapshot_saved=False,events=[])")
s=s.replace(" assert Path('/proc/sys/kernel/osrelease').read_text().strip()==meta['kernel_release']", " assert Path('/proc/sys/kernel/osrelease').read_text().strip()==meta['kernel_release']\n for name,digest in meta['payload_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest\n assert hashlib.sha256((ROOT/'firmware.elf').read_bytes()).hexdigest()==meta['firmware_sha256']")
s=s.replace("str(ROOT/'dump-collector.py')","str(ROOT/'snapshot-collector.py')")
s=s.replace("run(['insmod',str(ROOT/'test.ko')])", "run(['insmod',str(ROOT/'test.ko'),'hold_start_failure=1'])")
a=s.index(" assert releasable(result),'A5 or power/mapping resources remain owned");b=s.index('\nexcept BaseException as error:',a)
s=s[:a]+''' held=bool(result.get('phase')=='failed-held' and result.get('terminal') and result.get('error') and result.get('cpu_release_attempted') and not result.get('cleanup_error') and not result.get('cpu_enabled') and not result.get('irq_enabled') and result.get('reset_asserted') and result.get('power_held') and result.get('backing_owned'))
 observation['held_window_returned']=held
 assert held or releasable(result),'Start has no confirmed held or fully released terminal state; inspect ownership'
 if not result.get('cpu_release_attempted') or not result.get('error'):(ROOT/'collector-stop').touch()
 save('wait-snapshot',device_result=result)
 deadline=time.monotonic()+13
 while not (ROOT/'collector-result.json').exists() and collector.poll() is None and time.monotonic()<deadline:time.sleep(.005)
 assert (ROOT/'collector-result.json').exists(),'Collector incomplete; preserve standard dump and inspect owner'
 collected=json.loads((ROOT/'collector-result.json').read_text());observation['collector_result']=collected
 observation['snapshot_saved']=bool(collected.get('snapshot_saved'))
 observation['code_page_match']=bool(collected.get('snapshot',{}).get('code_page_match'))
 save('snapshot-collected')
 if held:
  save('cleanup-dma-pm',cleanup_attempted=True);cleanup_attempted=True
  Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
  result=read_result();save('cleanup-returned',device_result=result)
 assert releasable(result),'DMA/PM cleanup did not release all resources'
 assert not collected.get('captured') or collected.get('owned_snapshot_acknowledged'),'Standard snapshot still owns device reference'
 handshake=bool(result['error']==0 and result['cleanup_error']==0 and result['pc_error']==0 and result['init_response']==1 and result['init_done'] and result['ping_done'] and result['pc_done'] and result['fw_version'] and result['interrupts']>=3 and result['messages']>=3 and not result['watchdogs'] and not result['protocol_errors'])
 observation['firmware_handshake_passed']=handshake
 observation['firmware_failure_observed']=bool(result.get('init_response')==3)
 observation['diagnostic_completed']=bool(held and observation['snapshot_saved'] and not collected.get('error') and collected.get('owned_snapshot_acknowledged'))
 observation['passed']=handshake
''' +s[b:]
anchor="   result=read_result();observation['device_result']=result"
new="""   result=read_result();observation['device_result']=result
   if result.get('phase')=='failed-held' and not cleanup_attempted:
    save('cleanup-after-collector-error',cleanup_attempted=True);cleanup_attempted=True
    Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
    result=read_result();observation['device_result']=result"""
assert s.count(anchor)==1;s=s.replace(anchor,new)
compile(s,'boot-worker.py','exec');(HERE/'boot-worker.py').write_text(s)
# Re-run just the relevant actual bodies after adding lifecycle observations.
s=(HERE.parent/'kernel370/check-lifecycle.py').read_text().replace("run_body('start-before',s,start_body(before),[2,10],False)",'').replace('stage=370','stage=371')
s=s.replace('before_source_rejected_by_new_failure_ownership_checks=True','before_source_regression_evidence_stage=370')
(HERE/'check-lifecycle.py').write_text(s)
print('Prepared explicit held-failure worker with current369 boot guard supplied by launcher; no hardware launched.')
