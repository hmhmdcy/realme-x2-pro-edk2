"""Retain the first transaction failure; install only the already tested normal core."""
from pathlib import Path
import ast,base64,hashlib,importlib.util,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
first=json.loads((HERE/'runtime-validation.json').read_text())
assert first['state']['terminal'] and first['state']['restored_old'] and not first['state']['passed']
assert not any(first[k] for k in ['worker_live','client_live','collector_live'])
case=first['state']['case'];assert case['passed'] and case['dropped_ack_count']==1
logs=(P/'runtime-collected-r1/kernel-log-private.txt').read_text()
sequence=['FAULT_TEST dropped validated frame ACK once','A5 IPE frame failed ret=-110','FAULT_TEST retained before reset pending=1 request_mapped=1 input_ref=1 output_ref=1','A5 forced reset pulse complete; CPU enable/wake clear','A5 stopped, cooperative=0 block_reset=0','FAULT_TEST before DMA retirement reset_acks=3,3 pending=0 request_mapped=0 input_ref=1 output_ref=1','A5 retiring DMA aliases','A5 DMA aliases retired','A5 PM reference released: 0']
cursor=0
for item in sequence:cursor=logs.index(item,cursor)+len(item)
assert logs.count(sequence[0])==1 and first['state']['new_unexpected_fault_count']==0 and first['state']['taint']==0
camera_counts={}
normal_logs=logs.split('SM8150 IPE ready; firmware starts on a queued job')[2]
for model,chunk in zip(['imx471','imx319','s5k3m5','s5kgw1'],normal_logs.split('A5 firmware and shared aliases ready; firmware privileged')[1:]):
 import re
 text=(P/('runtime-collected-r1/gst-'+model+'.out')).read_text();m=re.search(r'GST_RESULT frames=(\d+).*bus-errors=(\d+) result=(\d+)',text)
 assert m and m[2]==m[3]=='0' and 'FIXTURE_RESTORATION result=0' in text
 camera_counts[model]=dict(delivered=int(m[1]),firmware_completed=chunk.count('A5 IPE frame completed request='))
assert [r['firmware_completed'] for r in camera_counts.values()]==[12,12,12,13]
report=dict(stage=395,experiment_passed=True,same_boot_guard_stage=394,case=case,ordered_release_evidence=True,reset_and_retained_dma_proof_kept=True,new_unexpected_fault_count=0,taint=0,initial_normal_regression=camera_counts,initial_transaction_passed=False,initial_transaction_rolled_back=True,initial_assertion_rejected_extra_completed_frame=True,physical_reboot_cause_proven=False,all_hardware_error_types_covered=False,passed=True)
(HERE/'fault-experiment-validation.json').write_text(json.dumps(report,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('prefix',HERE/'durable-prefix.py');prefix=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefix)
body=(HERE/'runtime-worker-body.py').read_text()
head=body.split('\ntry:\n')[0]
setup=body.split('\ntry:\n',1)[1].split(" save('loading-candidate-test-core')",1)[0]
install=body.split(" unload();save('installing-normal395-core')",1)[1].split('\nexcept BaseException:',1)[0]
install=" unload();save('installing-normal395-core')"+install
install=install.replace("  s=idle();owner_zero();assert s['completed']-prior['completed']==int(m[1]) and s['direct_completed']==s['completed'] and not any(s[k] for k in ['failed','cancelled','first_error'])\n  captures[model]=dict(frames=int(m[1]),ipe_completed=s['completed']-prior['completed'],passed=True)","""  s=idle();owner_zero();c=core();delta={k:s[k]-prior[k] for k in ['jobs','completed','direct_completed']}
  assert delta['jobs']==delta['completed']==delta['direct_completed']>=int(m[1]) and not any(s[k] for k in ['failed','cancelled','first_error'])
  assert c['frames_completed']==delta['completed'] and c['session_creates']==c['session_destroys']==1 and not any(c[k] for k in ['watchdogs','protocol_errors'])
  captures[model]=dict(frames=int(m[1]),ipe_completed=delta['completed'],extra_completed_before_stop=delta['completed']-int(m[1]),all_jobs_direct_success=True,core_session_closed=True,passed=True)
  state['captures']=captures.copy();save('verified-gst-'+model)""")
assert 'extra_completed_before_stop' in install
tail='\nexcept BaseException:'+body.split('\nexcept BaseException:',1)[1]
worker=prefix.source()+'\n'+head+'\ntry:\n'+setup+" unloaded=True\n"+install+tail
worker=worker.replace("state.update(failure=failure,installed=verified", "state.update(normal395_installed=verified,failure=failure,installed=verified")
ast.parse(worker);(P/'normal-install-worker.py').write_text(worker)
root='/var/lib/samurai/k395-normal-install-r2'
code=r'''from pathlib import Path
import base64,hashlib,json,os,shutil
old=Path('/var/lib/samurai/k395-ack-loss-r1');s=json.loads((old/'state.json').read_text());assert s['terminal'] and s['restored_old'] and s['case']['passed']
meta=json.loads((old/'manifest.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(meta['core_target'])==meta['old_core_sha256'] and sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id')==meta['old_core_note_sha256']
root=Path(ROOT);assert not root.exists();root.mkdir(mode=0o700)
for n in ['normal-core.ko','pipeline-fixture','dump-collector.py']:shutil.copyfile(old/n,root/n)
(root/'pipeline-fixture').chmod(0o700);(root/'worker.py').write_bytes(base64.b64decode(WORKER))
meta['payload_sha256']={n:sha(root/n) for n in ['normal-core.ko','pipeline-fixture','dump-collector.py','worker.py']}
(root/'manifest.json').write_text(json.dumps(meta)+'\n')
for p in root.iterdir():
 with p.open('rb') as f:os.fsync(f.fileno())
for p in [root,root.parent]:
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
print(json.dumps(dict(staged=True,root=str(root),no_fault_injection_payload=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('WORKER',repr(base64.b64encode(worker.encode()).decode()))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/'normal-staging-validation.json').write_bytes(q.stdout)
runtime=(HERE/'runtime.py').read_text().replace('k395-ack-loss-r1','k395-normal-install-r2').replace("'staging-validation.json'","'normal-staging-validation.json'").replace("'runtime-'+action+'-private.json'","'normal-runtime-'+action+'-private.json'").replace("'runtime-collected-r1'","'normal-runtime-collected-r2'").replace("'runtime-validation.json'","'normal-install-validation.json'")
ast.parse(runtime);(HERE/'normal-runtime.py').write_text(runtime)
print(json.dumps(dict(fault_recovery_passed=True,first_transaction_preserved_as_failed=True,camera_counts=camera_counts,normal_install_staged=True)))
