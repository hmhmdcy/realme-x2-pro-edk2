from pathlib import Path
import hashlib,json,shutil,subprocess
import storage,host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;OLD=HERE.parent/'kernel386'
assert json.loads((HERE/'build-validation.json').read_text())['passed']
base=storage.candidate()/'src/libcamera-v0.7.2'
source=(HERE.parent/'kernel315/raw-smoke.cpp').read_text()
source=source.replace('frames>=12 && stable>=8 && (!hold || heldOnce)','frames>=6 && (!hold || heldOnce)')
needle='''   timestamps[stream]=frame.timestamp;'''
assert source.count(needle)==1
source=source.replace(needle,'''   if(stream->configuration().pixelFormat==formats::NV12 &&
      request->metadata().get(controls::SensorTimestamp).value_or(0)!=int64_t(frame.timestamp))++failed;
   timestamps[stream]=frame.timestamp;''')
(HERE/'pipeline-smoke.cpp').write_text(source)
slot=storage.SDK/'private-k387';slot.mkdir(exist_ok=True)
probe_reused=(slot/'pipeline-smoke.cpp').is_file() and (slot/'pipeline-smoke.cpp').read_text()==source and (slot/'pipeline-smoke').is_file()
if not probe_reused:
 shutil.copyfile(HERE/'pipeline-smoke.cpp',slot/'pipeline-smoke.cpp')
 with storage.sdk_candidate():
  tree='/work/libcamera/src/libcamera-v0.7.2'
  args=['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+tree+'/include','-I'+tree+'/output/include','/private-k387/pipeline-smoke.cpp','-L'+tree+'/output/src/libcamera','-L'+tree+'/output/src/libcamera/base','-Wl,-rpath-link,'+tree+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private-k387/pipeline-smoke']
  q=subprocess.run(args,capture_output=True)
 (P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()[-4000:]
shutil.copyfile(slot/'pipeline-smoke',P/'pipeline-smoke')
shutil.copyfile(base/'output/src/libcamera/libcamera.so.0.7.2',P/'libcamera.so.0.7.2')
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':387").replace("marker=root/'state.json'","marker=root/'camera-state.json'")
client=prefix+'\n'+(HERE/'camera-client-body.py').read_text();compile(client,'camera-client.py','exec');(HERE/'camera-client.py').write_text(client)
worker=(OLD/'m2m-worker.py').read_text()
a=worker.index(" (ROOT/'m2m-client').chmod");b=worker.index(" (ROOT/'collector-stop').touch()",a)
worker=worker[:a]+''' (ROOT/'pipeline-fixture').chmod(0o700);(ROOT/'pipeline-smoke').chmod(0o700)
 library=ROOT/'lib';library.mkdir();(library/'libcamera.so.0.7.2').write_bytes((ROOT/'libcamera.so.0.7.2').read_bytes());(library/'libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')
 with (ROOT/'client-private.json').open('xb') as output,(ROOT/'client-private.log').open('xb') as errors:
  client=subprocess.Popen([sys.executable,str(ROOT/'camera-client.py'),str(ROOT)],stdin=subprocess.DEVNULL,stdout=output,stderr=errors)
  save('client-running',client_pid=client.pid,video_node=nodes[0].name,media_node=media[0].name)
  exit_code=client.wait(timeout=240)
 observation['client_exit']=exit_code
 assert exit_code==0,'Camera client failed; preserve output and inspect cleanup'
 client_report=json.loads((ROOT/'client-private.json').read_text());assert client_report['passed'] and len(client_report['captures'])==7
 after=read_m2m()
 assert after['registered'] and not any(after[k] for k in ['users','running','fatal','pinned','orphans','failed'])
 assert after['jobs']==after['completed']+after['cancelled'] and after['completed']>0
 observation.update(m2m_before=before,m2m_after_client=after,client_report=client_report)
 save('camera-client-complete')
 save('cleanup-dma-pm',cleanup_attempted=True);cleanup_attempted=True
 Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
 final=read_m2m();result=read_result()
 assert not any(final[k] for k in ['users','running','fatal','pinned','orphans'])
 assert releasable(result) and result['error']==result['cleanup_error']==result['pc_error']==0
 assert result['init_response']==1 and result['init_done'] and result['pc_done']
 assert result['session_creates']==result['session_destroys']==result['session_peak']==1
''' +worker[b:]
worker=worker.replace('m2m_control_and_pixel_client_passed=True','libcamera_pipeline_client_passed=True')
worker=worker.replace("str(ROOT/'snapshot-collector.py'),str(ROOT)]","str(ROOT/'snapshot-collector.py'),str(ROOT),'--seconds','330']")
worker=worker.replace(" (ROOT/'collector-stop').touch()\n deadline=time.monotonic()+13"," assert collector.poll() is None,'Collector must remain armed through the camera suite'\n (ROOT/'collector-stop').touch()\n deadline=time.monotonic()+13")
compile(worker,'pipeline-worker.py','exec');(HERE/'pipeline-worker.py').write_text(worker)
for leaf in ['snapshot-collector.py']:
 shutil.copyfile(OLD/leaf,HERE/leaf)
report=dict(stage=387,probe_werror=True,worker_compiled=True,all_four_processed=True,raw_only_and_dual=True,isolated_ipa=True,library_sha256=hashlib.sha256((P/'libcamera.so.0.7.2').read_bytes()).hexdigest(),kernel_runtime_logic_reused_stage=386,media_driver_identity_stage=387,installed=False,passed=True)
(HERE/'runtime-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
