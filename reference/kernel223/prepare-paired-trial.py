from pathlib import Path
import json
here=Path(__file__).resolve().parent
proof=json.loads((here/'sof-candidate-build-validation.json').read_text());assert proof['checkpatch_exit']==0
text=(here.parent/'kernel222/native-sof-trial-r2.py').read_text().replace('k222-','k223-').replace('stage=222','stage=223')
text=text.replace("out=root/'k223-sof-trial-r2'","out=root/'k223-paired-sof-trial'")
text=text.replace('9c3b9db6b2933ebf5f1c01deea9fca7bb823fb2a745cd7f3a1d88e3ccc54e83e',proof['compiled_module_sha256'])
a=text.index(" eventfd=os.open('/dev/'+nodes()['msm_vfe0_rdi0']");b=text.index('\nfinally:',a)
text=text[:a]+''' tests=[]
 for kind,width,height in [('raw',1928,1088),('rgb',1920,1088),('raw',2304,1728),('rgb',2296,1728)]:
  label=f'{kind}-{width}x{height}'
  events=[];event_errors=[];thread_stop.clear()
  eventfd=os.open('/dev/'+nodes()['msm_vfe0_rdi0'],os.O_RDWR|os.O_NONBLOCK|os.O_CLOEXEC)
  subscription=bytearray(32);struct.pack_into('I',subscription,0,4);fcntl.ioctl(eventfd,0x4020565a,subscription,True)
  def observe():
   poll=select.poll();poll.register(eventfd,select.POLLPRI)
   while not thread_stop.is_set():
    if not poll.poll(50):continue
    while True:
     data=bytearray(136)
     try:fcntl.ioctl(eventfd,0x80885659,data,True)
     except OSError as error:
      if error.errno in [2,11]:break
      event_errors.append(error.errno);return
     assert struct.unpack_from('I',data,0)[0]==4
     events.append(dict(frame_sequence=struct.unpack_from('I',data,8)[0],queue_sequence=struct.unpack_from('I',data,76)[0],timestamp_ns=struct.unpack_from('q',data,80)[0]*1000000000+struct.unpack_from('q',data,88)[0]))
  event_thread=threading.Thread(target=observe);event_thread.start()
  state.update(phase='paired-capture-live',case=label);save()
  test=subprocess.Popen(['python3',str(stage/'paired-runner.py'),kind,'0',str(width),str(height),'1','system'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  stdout,stderr=test.communicate(timeout=50)
  (out/(label+'-runner-stdout-private.json')).write_bytes(stdout);(out/(label+'-runner-stderr-private.txt')).write_bytes(stderr)
  thread_stop.set();event_thread.join(timeout=3);assert not event_thread.is_alive();event_thread=None
  os.close(eventfd);eventfd=None
  (out/(label+'-events-private.json')).write_text(json.dumps(events,indent=2)+'\\n')
  assert test.returncode==0;test_data=json.loads(stdout);assert test_data['program_exit']==0 and len(test_data['frames'])==16
  assert not event_errors and events
  tests.append(dict(case=label,frames=test_data['frames'],events=events,client_exit=test_data['program_exit']))
  (out/'all-cases-private.json').write_text(json.dumps(tests,indent=2)+'\\n')
''' +text[b:]
a=text.index('consecutive=all(');b=text.index("state.update(phase='verified-restored'",a)
text=text[:a]+'''cases=[]
for case in tests:
 events=case['events'];by_id={x['frame_sequence']:x for x in events};frames=case['frames']
 pairs=[f['timestamp_ns']-by_id[f['buffer_sequence']]['timestamp_ns'] for f in frames if f['buffer_sequence'] in by_id]
 cases.append(dict(case=case['case'],capture_frames=len(frames),frame_sync_events=len(events),consecutive_event_sequence=all(b['frame_sequence']==a['frame_sequence']+1 for a,b in zip(events,events[1:])),all_buffers_have_observed_sof=len(pairs)==len(frames),buffer_sequences=[f['buffer_sequence'] for f in frames],maximum_capture_gap=max(b['buffer_sequence']-a['buffer_sequence'] for a,b in zip(frames,frames[1:])),minimum_sof_to_completion_ms=min(pairs)/1000000 if pairs else None,maximum_sof_to_completion_ms=max(pairs)/1000000 if pairs else None))
assert len(cases)==4
r=dict(stage=223,temporary_candidate_trial=True,candidate_module_loaded_and_verified=True,cases=cases,original_camss_loaded_note_verified=True,original_module_file_unchanged=True,graph_and_formats_restored_before_policy=True,wireplumber_restored=True,desktop_and_pipewire_identities_preserved=True,taint=0,fault_delta=faults,missing_sof_tag_messages=after.count(b'Missing SOF tag')-before.count(b'Missing SOF tag'),manual_api_and_control_snapshots_not_yet_accepted=True,no_flash_or_reboot=True)
''' +text[b:]
compile(text,'native-paired-trial223','exec');(here/'native-paired-trial.py').write_text(text)
wrapper=(here.parent/'kernel222/run-sof-trial-r2.py').read_text().replace("here/'native-sof-trial-r2.py'","here/'native-paired-trial.py'").replace('sof-trial-r2-host-private.log','paired-trial-host-private.log').replace('sof-candidate-native-validation.json','paired-sof-native-validation.json')
compile(wrapper,'run-paired-trial223','exec');(here/'run-paired-trial.py').write_text(wrapper)
print('K223_FOUR_CASE_RAW_RGB_PAIRED_TRIAL_PREPARED')
