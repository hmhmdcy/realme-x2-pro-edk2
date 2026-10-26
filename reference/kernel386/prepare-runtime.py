"""Derive the guarded platform transaction; keep m2m clients separately owned."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel385'
worker=(OLD/'boot-worker.py').read_text()
worker=worker.replace("extra_firmware=[]","extra_firmware=[]\nowned_helper=False;owned_adapter=False;client=None")
worker=worker.replace("def read_result():","def read_m2m():return json.loads(Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/m2m_status').read_text())\n\ndef read_result():")
worker=worker.replace(" ready_result=read_result()",r'''
 ready_result=read_result();observation['probe_snapshot_before_refresh']=ready_result
 deadline=time.monotonic()+3
 while True:
  refreshed=read_m2m();ready_result=read_result()
  observation['ready_result']=ready_result;observation['ready_m2m_status']=refreshed
  observation['ready_pm_status']=Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/power/runtime_status').read_text().strip()
  save('post-bind-result',device_result=ready_result)
  assert not ready_result.get('cpu_release_attempted') and not refreshed['jobs'],'Unexpected pre-client firmware activity'
  if releasable(ready_result) and observation['ready_pm_status']=='suspended':break
  if time.monotonic()>deadline:raise RuntimeError('Post-bind runtime PM did not reach idle')
  time.sleep(.02)
''')
worker=worker.replace(" image_case=meta['image_test'];expected_frames=image_case['frames'];expected_image_bytes=image_case['width']*image_case['height']*3//2\n",'')
worker=worker.replace(" save('load-core');run(['insmod',str(ROOT/'core.ko')]);owned_core=True"," save('load-core');run(['insmod',str(ROOT/'core.ko')]);owned_core=True\n save('load-helper');run(['insmod',str(ROOT/'helper.ko')]);owned_helper=True\n save('load-adapter');run(['insmod',str(ROOT/'adapter.ko')]);owned_adapter=True")
a="'enable_frame=1',*['test_'+k+'='+str(int(image_case[k]) if k=='uv_swap' else image_case[k]) for k in ['width','height','port','cores','frames','uv_swap']]]";assert a in worker
worker=worker.replace(a,"'enable_m2m=1']")
a=worker.index(" save('binding-ready'");b=worker.index("\nexcept BaseException as error:",a)
worker=worker[:a]+r'''
 save('binding-ready',device_result=ready_result,binding_returned_before_cpu_release=True)
 before=read_m2m();assert before['registered'] and not before['users'] and not before['running'] and not before['pinned'] and not before['jobs']
 nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5']
 assert len(nodes)==1 and (nodes[0]/'device').resolve().name=='ac10000.samurai-icp356-boot'
 media=[p for p in Path('/sys/bus/media/devices').glob('media*') if any(parent.name=='ac10000.samurai-icp356-boot' for parent in p.resolve().parents)]
 observation['media_discovery']=[dict(name=p.name,path=str(p.resolve())) for p in Path('/sys/bus/media/devices').glob('media*')]
 assert len(media)==1,'M2M media device must be discoverable'
 (ROOT/'m2m-client').chmod(0o700)
 with (ROOT/'client-private.json').open('xb') as output,(ROOT/'client-private.log').open('xb') as errors:
  client=subprocess.Popen([str(ROOT/'m2m-client'),'/dev/'+nodes[0].name,str(ROOT)],stdin=subprocess.DEVNULL,stdout=output,stderr=errors)
  save('client-running',client_pid=client.pid,video_node=nodes[0].name,media_node=media[0].name)
  exit_code=client.wait(timeout=45)
 observation['client_exit']=exit_code
 assert exit_code==0,'V4L2 client failed; preserve private output/log and inspect cleanup'
 client_report=json.loads((ROOT/'client-private.json').read_text());assert client_report['passed'] and len(client_report['cases'])==4
 after=read_m2m()
 assert after['registered'] and not any(after[k] for k in ['users','running','fatal','pinned','orphans','failed'])
 assert after['jobs']==after['completed']==18 and after['starts']==3
 observation.update(m2m_before=before,m2m_after_client=after,client_report=client_report)
 save('m2m-client-complete')
 save('cleanup-dma-pm',cleanup_attempted=True);cleanup_attempted=True
 Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
 final=read_m2m();result=read_result()
 assert not any(final[k] for k in ['users','running','fatal','pinned','orphans'])
 assert releasable(result) and result['error']==result['cleanup_error']==result['pc_error']==0
 assert result['init_response']==1 and result['init_done'] and result['pc_done']
 assert result['session_creates']==result['session_destroys']==result['session_peak']==2
 assert result['frames_completed']==result['image_frames']==8
 (ROOT/'collector-stop').touch()
 deadline=time.monotonic()+13
 while not (ROOT/'collector-result.json').exists() and collector.poll() is None and time.monotonic()<deadline:time.sleep(.005)
 assert (ROOT/'collector-result.json').exists()
 collected=json.loads((ROOT/'collector-result.json').read_text());observation['collector_result']=collected
 assert not collected.get('captured') or collected.get('owned_snapshot_acknowledged')
 observation.update(m2m_final=final,device_result=result,firmware_handshake_passed=True,
  m2m_control_and_pixel_client_passed=True,passed=True)
''' +worker[b:]
a=worker.index("finally:\n try:");b=worker.index(" deadline=time.monotonic()+5",a)
worker=worker[:a]+r'''finally:
 try:
  child_live=client is not None and client.poll() is None
  observation['client_live']=child_live
  if collector is not None:
   if collector.poll() is None:
    (ROOT/'collector-stop').touch();collector.wait(timeout=3)
   observation['collector_exit']=collector.returncode
   if (ROOT/'collector-result.json').exists():observation['collector_result']=json.loads((ROOT/'collector-result.json').read_text())
   if collector_log is not None:collector_log.close()
  if attempted_test and Path('/sys/module',test).exists():
   if child_live:
    observation['requires_cleanup_attention']=True
   else:
    status=read_m2m();observation['m2m_before_removal']=status
    if not status['users'] and not cleanup_attempted:
     save('cleanup-after-client-error',cleanup_attempted=True);cleanup_attempted=True
     Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/cleanup').write_text('1')
     status=read_m2m();observation['m2m_cleanup_retry_result']=status
    result=read_result();observation['device_result']=result
    (ROOT/'sfr-private.txt').write_text(Path('/sys/module',test,'parameters/sfr').read_text())
    collected=observation.get('collector_result',{})
    snapshots_safe=not collected.get('captured') or collected.get('owned_snapshot_acknowledged',False)
    live_owned=[p for p in Path('/sys/class/devcoredump').glob('devcd*') if (p/'failing_device').exists() and (p/'failing_device').resolve().name=='ac10000.samurai-icp356-boot']
    if not any(status[k] for k in ['users','running','pinned','orphans']) and releasable(result) and snapshots_safe and not live_owned:
     save('unload-platform-owner');run(['rmmod',test])
    else:observation['requires_cleanup_attention']=True
  if owned_adapter and not Path('/sys/module',test).exists():
   save('unload-adapter');run(['rmmod','camss_icp_a5_m2m']);owned_adapter=False
  if owned_helper and not Path('/sys/module/camss_icp_a5_m2m').exists() and not Path('/sys/module',test).exists():
   save('unload-helper');run(['rmmod','v4l2_mem2mem']);owned_helper=False
  if owned_core and not Path('/sys/module',test).exists() and not Path('/sys/module/camss_icp_a5_m2m').exists():
   save('unload-core');run(['rmmod',core]);owned_core=False
  if owned_firmware and not Path('/sys/module',test).exists():
   firmware.unlink();owned_firmware=False
 except BaseException as error:
  observation['cleanup_error']=str(error);observation['passed']=False
''' +worker[b:]
worker=worker.replace(" observation['core_absent']="," observation['adapter_absent']=not Path('/sys/module/camss_icp_a5_m2m').exists();observation['helper_absent']=not Path('/sys/module/v4l2_mem2mem').exists()\n observation['m2m_video_absent']=not any((p/'name').read_text().strip()=='qcom-ipe-a5' for p in Path('/sys/class/video4linux').glob('video*'))\n observation['passed']=bool(observation['passed'] and observation['adapter_absent'] and observation['helper_absent'] and observation['m2m_video_absent'] and not observation['client_live'])\n observation['core_absent']=")
(HERE/'m2m-worker.py').write_text(worker)
(HERE/'snapshot-collector.py').write_text((OLD/'snapshot-collector.py').read_text())
(HERE/'firmware-context-validation.json').write_text((OLD/'firmware-context-validation.json').read_text())
launch=(OLD/'launch-boot.py').read_text().replace('k385-boot-','k386-m2m-').replace('Prepared385','Prepared386')
a=launch.index("case=sys.argv[2]");b=launch.index("for name in ",a)
launch=launch[:a]+"preflight=json.loads((HERE/'runtime-preflight-validation.json').read_text());assert preflight['passed'] and preflight['run']==run\n"+launch[b:]
launch=launch.replace("['diagnostic','worker','intree-build']","['m2m','worker','client-build','intree-build']")
a=launch.index("files={'core.ko'");b=launch.index("for row in build['modules']",a)
launch=launch[:a]+"""modules={r['name']:r for r in build['modules']};client=json.loads((HERE/'client-build-validation.json').read_text())
files={name:Path(modules[key]['private_path']) for name,key in [('core.ko','qcom-camss-icp-a5-core'),('helper.ko','v4l2-mem2mem'),('adapter.ko','camss-icp-a5-m2m'),('test.ko','camss-icp-a5-boot-test')]}
files.update({'worker.py':HERE/'m2m-worker.py','snapshot-collector.py':HERE/'snapshot-collector.py','dump_decoder.py':HERE.parent/'kernel368/decode-start-dump.py','firmware.elf':P.parent/'kernel352/CAMERA_ICP.elf-private','m2m-client':Path(client['private_path'])})
assert hashlib.sha256(files['m2m-client'].read_bytes()).hexdigest()==client['sha256']
""" +launch[b:]
launch=launch.replace("manifest=dict(image_test=image,kernel_release=","manifest=dict(kernel_release=")
(HERE/'launch-m2m.py').write_text(launch)
print('Prepared a unique m2m platform/client transaction with retained-failure ownership.')
