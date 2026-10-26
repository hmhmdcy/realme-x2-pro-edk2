from pathlib import Path
import importlib.util,json,re,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
runtime=json.loads((HERE/'runtime-r4-validation.json').read_text());s=runtime['state']
assert s['passed'] and s['installed'] and not s['rollback'] and not any(runtime[k] for k in ['worker_live','client_live','collector_live'])
assert s['after']==dict(s['after'],jobs=55,completed=53,direct_completed=53,cancelled=1,failed=1,first_error=-22)
assert s['cases'][0]['during']['failed']==1 and s['cases'][0]['during']['completed']==1 and not s['cases'][0]['during']['fatal']
assert s['cases'][0]['repaired']['completed']==3 and s['cases'][0]['repaired']['starts']==1 and s['cases'][0]['repaired']['stops']==0
events={}
for a in ['r1','r2','r3','r4']:
 text=(P/('runtime-collected-'+a)/'kernel-log-private.txt').read_text()
 events[a]=dict(hardware_frame_completions=len(re.findall('A5 IPE frame completed request=',text)),job_errors=[int(v) for v in re.findall(r'IPE m2m job failed ret=(-?\d+)',text)])
assert events['r4']==dict(hardware_frame_completions=54,job_errors=[-22]) and events['r3']==dict(hardware_frame_completions=2,job_errors=[-22])
hardware=dict(stage=393,verified_window='r4',cases=s['cases'],captures=s['captures'],m2m=s['after'],core=s['core_after'],verified_window_hardware_frame_completions=54,all_attempt_log_frame_completions=56,failed_attempts_not_counted_as_passed=True,peer_not_failed_on_local_rejection=True,same_context_repaired_without_backend_restart=True,unknown_hardware_error_concurrency_still_unverified=True,log_events=events,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(hardware,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
meta=json.loads((P/'manifest-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,json
meta=META;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for r in meta['modules']:
 assert sha(r['target'])==r['new_sha256']
 assert sha('/sys/module/'+r['module']+'/notes/.note.gnu.build-id')==r['new_note_sha256']
 assert sha('/var/lib/samurai/k393-deployment-r4/backup/'+Path(r['target']).name)==r['old_sha256']
assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==meta['camss_note_sha256']
assert all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
dev=Path('/sys/bus/platform/devices/ac10000.icp');workers=[]
for a in ['r1','r2','r3','r4']:
 root=Path('/var/lib/samurai/k393-deployment-'+a);s=json.loads((root/'state.json').read_text());live=[]
 for k,names in [('pid',['worker.py']),('client_pid',['local-error-client','pipeline-fixture']),('collector_pid',['dump-collector.py'])]:
  p=Path('/proc',str(s.get(k,-1)))
  try:active=(p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and any(str(root/n).encode() in (p/'cmdline').read_bytes() for n in names)
  except OSError:active=False
  if active:live.append(k)
 workers.append(dict(attempt=a,terminal=s['terminal'],live=live))
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
print(json.dumps(dict(module_pair_files_and_loaded_notes_match=True,original_pair_backup_matches=True,camss_composite_note_unchanged=True,private_profiles_unchanged=True,packages=versions,workers=workers,services=services,clocks=clocks,m2m=json.loads((dev/'m2m_status').read_text()),core=json.loads((dev/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))})))
'''.replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(P/'current-state-private.json').write_bytes(q.stdout)
assert d['m2m']['jobs']==55 and d['m2m']['completed']==d['m2m']['direct_completed']==53 and d['m2m']['cancelled']==1 and d['m2m']['failed']==1 and d['m2m']['first_error']==-22
assert not d['taint'] and not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans'])
assert not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
assert len(d['clocks'])==17 and not any(d['clocks'].values()) and len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert all(v=='suspended' for v in d['camera_pm'].values()) and all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values())
assert all(w['terminal'] and not w['live'] for w in d['workers'])
assert d['packages']==json.loads((HERE.parent/'kernel391/current-state-validation.json').read_text())['packages']
report=dict(stage=393,driver_source_commit=state['commit'],driver_source_branch=state['branch'],source_clean=True,boot_image_board_and_userspace_unchanged=True,core_adapter_pair_permanently_updated=True,old392_counters_archived_before_normal_unload=True,current_counter_epoch='393-r4-loaded-pair',**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
attempts=dict(stage=393,core_source_unchanged_between_attempts=True,build_r1_failed_missing_modpost_dependency_targets=True,build_r2_passed=True,adapter_provider_first_compile_name_collision_fixed=True,
 r1=dict(passed=False,reason='Wrongly required static platform device to disappear after driver unload',files_not_replaced=True,explicit_recovery='r1-recovery-validation.json'),
 r2=dict(passed=False,reason='Probe transient owner reference did not immediately reach zero',automatic_pair_rollback=True),
 r3=dict(passed=False,reason='Client reused offset16 without exporter extra rows; QBUF rejected exact-size backing',two_peer_frames_and_local_rejection_observed=True,automatic_pair_rollback=True),
 r4=dict(passed=True,probe_owner_bounded_wait=True,exact_size_dmabuf_uses_offset_zero=True,new_pair_kept=True),all_workers_collectors_clients_terminal=True,passed=True)
(HERE/'attempts-validation.json').write_text(json.dumps(attempts,indent=2)+'\n')
print(json.dumps(dict(passed=True,installed_pair=state['commit'],m2m=d['m2m'],services=d['services'])))
