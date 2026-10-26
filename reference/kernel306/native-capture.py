"""Run the opt-in candidate through real libcamera requests with state restoration."""
from pathlib import Path
import json,os,re,signal,subprocess,sys,time,traceback
root=Path(sys.argv[1]);assert re.fullmatch(r'/var/lib/samurai/k306-(?:joint|ae)-r[1-9][0-9]*',str(root)) and root.is_dir() and not (root/'state-private.json').exists()
force=os.environ.get('CAMSS_TEST_FORCE_ISOLATION','1');assert force in ['0','1']
kind = 'ae' if '/k306-ae-' in str(root) else 'joint'
state=dict(stage=306,terminal=False,phase='preflight',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
def save():
 p=root/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'state-private.json')
def health():
 runtime={}
 for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
  for p in Path('/sys/bus/i2c/drivers',driver).glob('*'):
   if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name):runtime[driver]=(p/'power/runtime_status').read_text().strip()
 rails={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  name=(p/'name').read_text().strip()
  if name.startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-')):rails[name]={k:(p/k).read_text().strip() for k in ['state','num_users']}
 platforms={name:Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip() for name in ['acb3000.camss','ac4a000.cci','ac4b000.cci']}
 return dict(sensors=runtime,rails=rails,platforms=platforms,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()
 assert os.uname().version.startswith('#298 ')
 before=health();assert len(before['sensors'])==5 and len(before['rails'])==9 and not before['taint']
 assert all(v=='suspended' for v in before['sensors'].values()) and all(v=='suspended' for v in before['platforms'].values())
 assert all(v['state']=='disabled' and v['num_users']=='0' for v in before['rails'].values())
 dmesg_before=subprocess.check_output(['dmesg']);(root/'dmesg-before-private.txt').write_bytes(dmesg_before)
 graph_before=subprocess.check_output(['media-ctl','-d','/dev/media0','-p']);(root/'graph-before-private.txt').write_bytes(graph_before)
 stage=root/'bundle';env=dict(os.environ,LD_LIBRARY_PATH=str(stage/'lib'),LIBCAMERA_CAMSS_VFE_ENABLE='1',LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
  LIBCAMERA_CAMSS_VFE_PROFILE=str(stage/'profile/manual.yaml'),LIBCAMERA_IPA_MODULE_PATH=str(stage/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(stage/'proxy'),LIBCAMERA_IPA_FORCE_ISOLATION=force,LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,DelayedControls:DEBUG,IPACamss:DEBUG,IPAManager:DEBUG,IPAProxy:DEBUG')
 if force=='0':env.pop('LIBCAMERA_IPA_FORCE_ISOLATION',None)
 with (root/'capture-private.log').open('xb') as output:
  child=subprocess.Popen([str(stage/'bin/pipeline-fixture'),'/dev/media0',str(stage/'bin/pipeline-smoke'),'s5k3m5'],stdout=output,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  state.update(phase='capturing',child_pid=child.pid,child_start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
  try:ret=child.wait(timeout=62)
  except subprocess.TimeoutExpired:
   child.send_signal(signal.SIGINT);state.update(phase='interrupt_sent');save();ret=child.wait(timeout=10)
 idle_start=time.monotonic();idle_observations=[]
 while True:
  after=health();idle_observations.append(dict(elapsed_ms=round((time.monotonic()-idle_start)*1000),platforms=after['platforms']))
  if after==before or time.monotonic()-idle_start>=5:break
  time.sleep(.2)
 dmesg_after=subprocess.check_output(['dmesg']);(root/'dmesg-after-private.txt').write_bytes(dmesg_after)
 graph_after=subprocess.check_output(['media-ctl','-d','/dev/media0','-p']);(root/'graph-after-private.txt').write_bytes(graph_after)
 text=(root/'capture-private.log').read_text(errors='replace')
 pairs=[dict(epoch=int(e),sof=int(s),request=int(r),population=int(p),mean=float(m),params_ack=int(a)) for e,s,r,p,m,a in re.findall(r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)',text)]
 epochs=[dict(epoch=int(e),frames=int(n),failed=int(f),stop=int(s)) for e,n,f,s in re.findall(r'APPLICATION_EPOCH epoch=(\d+) frames=(\d+) failed=(\d+) stop=(-?\d+)',text)]
 applied=[dict(epoch=int(e),first_sof=int(s)) for e,s in re.findall(r'Parameters epoch=(\d+) first-sof=(\d+)',text)]
 pixels=[(int(n),int(lo),int(hi)) for n,lo,hi in re.findall(r'bytes=(\d+) hash=\d+ first_plane_min=(\d+) first_plane_max=(\d+)',text)]
 faults={k:dmesg_after.count(v)-dmesg_before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
 report=dict(stage=306,kernel_build=298,tool_exit=ret,before=before,after=after,idle_observations=idle_observations,idle_deadline_ms=5000,fault_delta=faults,graph_restored=graph_before==graph_after,
  application_frames=len(re.findall(r'APPLICATION_FRAME ',text)),epochs=epochs,parameter_completions=applied,exact_sof_pairs=pairs,
  cpu_dma_sync_and_pixel_probes=len(pixels),image_bytes=sorted(set(r[0] for r in pixels)),frames_with_nonconstant_luma=sum(hi>lo for _,lo,hi in pixels),
  actual_libcamera_requests=bool(pairs or epochs),no_system_library_replacement=True,no_cpu_isp=True,no_dark_calibration=True,unity_wb_no_awb=True,
  full_iq_not_implemented=True,hardware_ae_requested=(kind=='ae'))
 app_pids=set(map(int,re.findall(r'APPLICATION_PROCESS pid=(\d+)',text)))
 all_ipa_pids=set(map(int,re.findall(r'IPA init pid=(\d+)',text)))
 ipa_pids=set(map(int,re.findall(r'IPA init pid=(\d+) model=s5k3m5',text)))
 stats_pids=set(map(int,re.findall(r'IPA stats pid=(\d+)',text)))
 ipa_live=[]
 for pid in all_ipa_pids:
  p=Path('/proc',str(pid),'stat')
  if p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z':
   cmd=Path('/proc',str(pid),'cmdline').read_bytes()
   if str(stage).encode() in cmd:ipa_live.append(pid)
 report.update(ipa_isolation_forced=('forced through configuration' in text),ipa_isolation_requested=(force=='1'),application_pids=sorted(app_pids),ipa_pids=sorted(ipa_pids),all_initialized_ipa_pids=sorted(all_ipa_pids),ipa_statistics_process_pids=sorted(stats_pids),ipa_workers_still_live=ipa_live,
  ipa_metadata_frames=len(re.findall(r'APPLICATION_IPA_METADATA ',text)),ipa_metadata_reports_logical_startup_colour_gains=True,
  candidate_hardware_ipa_integrated=True,test_kind=kind,full_iq_not_implemented=True,hardware_ae_requested=(kind=='ae'))
 report['passed']=ret==0 and len(epochs)==2 and all(r['frames']>=240 and not r['failed'] and not r['stop'] for r in epochs) and len(applied)==2 and set(p['epoch'] for p in pairs)=={1,2} and len(pairs)>=480 and report['graph_restored'] and before==after and not any(faults.values()) and 'FIXTURE_RESULT result=0' in text and 'FIXTURE_RESTORATION result=0' in text
 process_mode_ok=len(app_pids)==1 and len(ipa_pids)==1 and stats_pids==ipa_pids and ((force=='1' and not app_pids.intersection(ipa_pids)) or (force=='0' and app_pids==ipa_pids and 'signature is valid' in text))
 report['passed']=report['passed'] and process_mode_ok and not ipa_live and report['ipa_metadata_frames']==report['application_frames']
 sensor_metadata=re.findall(r'APPLICATION_SENSOR_METADATA epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)',text)
 sensor_commands=re.findall(r'APPLICATION_SENSOR_COMMAND epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)',text)
 contexts=re.findall(r'SensorContext epoch=(\d+) sof=(\d+) valid=(\d+) exposure-lines=(\d+) gain-code=(\d+) source=(\d+)',text)
 report.update(sensor_metadata_frames=len(sensor_metadata),standard_sensor_control_commands=len(sensor_commands),sensor_sof_contexts=len(contexts),
  known_sensor_sof_contexts=sum(int(c[2]) for c in contexts),sensor_helper_and_delayed_controls_integrated=True,
  sensor_values_are_quantized_effective_sof_context_not_requested_values=True)
 report['passed']=(report['passed'] and len(sensor_metadata)==report['application_frames'] and len(sensor_commands)==(18 if kind=='joint' else 0)
  and len(contexts)>=480 and all(c[2]=='1' for c in contexts))
 (root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');state.update(terminal=True,phase='finished',exit_code=ret);save()
except BaseException:
 (root/'failure-private.txt').write_text(traceback.format_exc());state.update(terminal=True,phase='failed',exit_code=1);save()
