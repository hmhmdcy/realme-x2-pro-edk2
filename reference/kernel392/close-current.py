from pathlib import Path
import importlib.util,json,re,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
runs={a:json.loads((HERE/('runtime-'+a+'-validation.json')).read_text()) for a in ['r1','r2','r3']}
assert not runs['r1']['state']['passed'] and all(runs[a]['state']['passed'] for a in ['r2','r3'])
assert all(r['state']['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live']) for r in runs.values())
cases=runs['r1']['state']['cases']+runs['r2']['state']['cases'];assert [c['case'] for c in cases]==list(range(5)) and all(c['passed'] for c in cases)
before=runs['r1']['state']['before'];after=runs['r3']['state']['after'];delta={k:after[k]-before[k] for k in ['jobs','completed','direct_completed','cancelled','failed','starts','stops']}
assert delta==dict(jobs=26,completed=20,direct_completed=20,cancelled=4,failed=2,starts=12,stops=12)
events={}
for a in runs:
 text=(P/('runtime-collected-'+a)/'kernel-log-private.txt').read_text()
 events[a]=dict(frame_completions=len(re.findall('A5 IPE frame completed request=',text)),expected_rejections=[int(x) for x in re.findall(r'IPE m2m job failed ret=(-?\d+)',text)])
assert sum(e['frame_completions'] for e in events.values())==24
assert events['r1']['expected_rejections']==events['r3']['expected_rejections']==[] and events['r2']['expected_rejections']==[-22,-5]
hardware=dict(stage=392,cases=cases,first_attempt_timing_failure_preserved=True,passed_cases_not_repeated=True,delta=delta,hardware_frame_completions_including_four_cancelled=24,normal_default_gstreamer_recovery_frames=12,log_events=events,cancelled_after_configured_marker=True,exact_dma_pending_instant_not_observed=True,input_alias_rejection_and_peer_error_hardware_verified=True,hardware_fault_concurrency_verified=False,unknown_dma_failure_branch_not_newly_exercised=True,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(hardware,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07'
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
code=r'''from pathlib import Path
import json
dev=Path('/sys/bus/platform/devices/ac10000.icp');workers=[]
for a in ['r1','r2','r3']:
 root=Path('/var/lib/samurai/k392-runtime-'+a);s=json.loads((root/'state.json').read_text());active=[]
 for key,needle in [('pid','worker.py'),('client_pid','cancel-client' if a!='r3' else 'pipeline-fixture'),('collector_pid','dump-collector.py')]:
  p=Path('/proc',str(s.get(key,-1)))
  try:live=(p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and str(root/needle).encode() in (p/'cmdline').read_bytes()
  except OSError:live=False
  if live:active.append(key)
 workers.append(dict(attempt=a,terminal=s['terminal'],live=active))
services={n:[] for n in ['pipewire','wireplumber']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in services and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':services[n].append(dict(pid=int(p.name),uid=p.stat().st_uid))
 except OSError:pass
clocks={}
for l in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
 f=l.split()
 if f and any(f[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):clocks[f[0]]=int(f[1])
versions={}
for b in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(l.split(':',1) for l in b.splitlines() if ':' in l)
 if f.get('P') in ['libcamera','libcamera-gstreamer','libcamera-ipa','libcamera-tools','libcamera-v4l2','samurai-camera-config','samurai-camera-stack']:versions[f['P']]=f['V']
print(json.dumps(dict(workers=workers,services=services,clocks=clocks,packages=versions,m2m=json.loads((dev/'m2m_status').read_text()),core=json.loads((dev/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(P/'current-state-private.json').write_bytes(q.stdout)
assert d['m2m']['jobs']==132 and d['m2m']['completed']==d['m2m']['direct_completed']==126 and d['m2m']['cancelled']==4 and d['m2m']['failed']==2 and d['m2m']['first_error']==-22
assert not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans']) and not d['taint']
assert not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
assert len(d['clocks'])==17 and not any(d['clocks'].values()) and len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert all(v=='suspended' for v in d['camera_pm'].values()) and all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values())
assert all(w['terminal'] and not w['live'] for w in d['workers'])
assert d['packages']==json.loads((HERE.parent/'kernel391/current-state-validation.json').read_text())['packages']
report=dict(stage=392,kernel_board_packages_and_profiles_not_modified=True,driver_source_clean=True,prior_deployment_file_evidence_reused_stage=391,expected_historical_failed_jobs=2,first_error_is_cumulative_diagnostic=True,hardware_fault_concurrency_still_pending=True,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,delta=delta,services=d['services'],expected_failed=2,cancelled=4,active_fault=False)))
