"""Prepare one typed-request ACK-loss run and restore the formal stack."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
body=(HERE.parent/'kernel418/runtime-worker-body.py').read_text()
# Future runs anchor to an actual kernel log line. printk and /proc/uptime
# were observed to differ; the executed r2 worker/result remain preserved.
body=body.replace("start_uptime=float(Path('/proc/uptime').read_text().split()[0])", "start_uptime=float(Path('/proc/uptime').read_text().split()[0]);kernel_anchor=subprocess.check_output(['dmesg']).decode(errors='replace').splitlines()[-1]")
old="assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists();state['probe_'+kind]=s"
new="param=Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack')\n if kind=='candidate':assert param.exists() and param.read_text().strip()=='0'\n else:assert not param.exists()\n state['probe_'+kind]=s"
assert body.count(old)==1;body=body.replace(old,new)
a=body.index(" launch([str(root/'ipe-smoke')");b=body.index(" unload();load('normal');restored=True;",a)
middle=r''' state['fault_start_uptime']=float(Path('/proc/uptime').read_text().split()[0]);save('typed-request-fault-client')
 launch([str(root/'ack-loss-client'),'/dev/'+nodes[0].name,media[0],str(root)],'typed-ack-loss',env=env,timeout=90)
 case=json.loads((root/'typed-ack-loss.out').read_text());assert case['passed'] and case['dropped_ack_count']==1 and case['actual_libcamera418']
 assert case['warm_core']['session_peak']==2 and case['combined_ltm_gamma_timeout'] and case['idle_consumer_preserves_fatal_gate'] and case['blocked_callback_seconds']<1
 state['case']=case;state['fault_end_uptime']=float(Path('/proc/uptime').read_text().split()[0]);state['after_fault_test']=idle();owner_zero()
 s=state['after_fault_test'];assert s['completed']==s['direct_completed']==3 and s['first_error']==-110 and s['failed']>=2
 assert s['jobs']==s['completed']+s['failed']+s['cancelled'] and not any(s[k] for k in ['users','running','fatal','pinned','orphans'])
 state['test_core_after']=core();assert not state['test_core_after']['watchdogs'] and not state['test_core_after']['protocol_errors']
 save('typed-ack-loss-reset-recovery-complete')
'''
body=body[:a]+middle+body[b:]
old="faults=[l for l in new if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed',l)]"
new=r'''expected=[];faults=[];begin=end=-1
 if state.get('case',{}).get('passed'):
  dropped=[i for i,l in enumerate(new) if 'FAULT_TEST dropped validated frame ACK once' in l];assert len(dropped)==1;begin=dropped[0]
  end=next(i for i in range(begin+1,len(new)) if 'A5 SYS_INIT acknowledged' in new[i])
 for i,line in enumerate(new):
  in_case=begin<=i<end
  if in_case and re.search(r'(?:A5 IPE frame failed|IPE m2m job failed) ret=-(?:110|5)(?:\s|$)',line):expected.append(line);continue
  if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed',line):faults.append(line)
 state['expected_frame_error_log_count']=len(expected)'''
assert body.count(old)==1;body=body.replace(old,new)
old="new=[l for l in logs.splitlines() if (m:=re.search(r'\\[\\s*(\\d+\\.\\d+)\\]',l)) and float(m[1])>=start_uptime]"
new="lines=logs.splitlines();assert lines.count(kernel_anchor)==1;new=lines[lines.index(kernel_anchor)+1:]"
assert body.count(old)==1;body=body.replace(old,new)
ast.parse(body);(HERE/'runtime-worker-body.py').write_text(body)
stage=(HERE.parent/'kernel418/stage-runtime.py').read_text()
old="build=json.loads((HERE.parent/'kernel417/intree-build-validation.json').read_text());assert build['passed'] and not build['diagnostics']\ncore,adapter=build['modules'][:2]\nassert json.loads((HERE/'ipe-validation.json').read_text())['passed']\nassert json.loads((HERE/'runtime-build-validation.json').read_text())['passed']"
new="build=json.loads((HERE/'test-intree-build-validation.json').read_text());assert build['passed'] and not build['diagnostics']\ncore=build['modules'][0];normal=json.loads((HERE/'intree-build-validation.json').read_text());assert normal['passed'] and not normal['diagnostics'];adapter=normal['modules'][1]\nassert json.loads((HERE/'hook-validation.json').read_text())['passed']\nassert json.loads((HERE/'adapter-validation.json').read_text())['passed']\nassert json.loads((HERE/'client-build-validation.json').read_text())['passed']\nassert 'test_drop_frame_ack' in subprocess.check_output(['modinfo','-F','parm',core['private_path']],text=True)"
assert stage.count(old)==1;stage=stage.replace(old,new)
stage=stage.replace('stage=418','stage=419').replace("'stage':418","'stage':419").replace('k418-libcamera-r2','k419-typed-ack-r2')
stage=stage.replace("'ipe-smoke':P/'ipe-smoke','libcamera.so.0.7.2':P/'libcamera.so.0.7.2','pipeline-smoke':P.parent/'kernel387/pipeline-smoke'","'ack-loss-client':P/'ack-loss-client','libcamera.so.0.7.2':P/'libcamera.so.0.7.2'")
stage=stage.replace("['pipeline-fixture','ipe-smoke','pipeline-smoke']","['pipeline-fixture','ack-loss-client']")
stage=stage.replace("prior=Path('/var/lib/samurai/k418-libcamera-r1')","prior=Path('/var/lib/samurai/k419-typed-ack-r1')")
ast.parse(stage);(HERE/'stage-runtime.py').write_text(stage)
runtime=(HERE.parent/'kernel418/runtime.py').read_text().replace('stage=418','stage=419').replace('k418-libcamera-r2','k419-typed-ack-r2').replace("['ipe-smoke','pipeline-fixture','pipeline-smoke']","['ack-loss-client','pipeline-fixture']")
ast.parse(runtime);(HERE/'runtime.py').write_text(runtime)
print('Prepared one-shot typed ACK-loss worker, scoped expected errors and original formal restoration.')
