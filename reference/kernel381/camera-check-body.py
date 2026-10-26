before=subprocess.check_output(['dmesg']);items={};started={};stopped=False;failure=None;captures={}
save('preflight')
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k378-recovered/boot-id-private.txt').read_bytes()
 assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 tools=Path('/var/lib/samurai/k362-install-r1');assert (tools/'bin/adaptation-smoke').is_file()
 fixture=root/'pipeline-fixture';assert fixture.is_file()
 items=services();wait_idle();stopped=True;stop_services(items);wait_idle()
 env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
 for key in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
 for model in ['imx471','imx319','s5k3m5','s5kgw1']:
  save('capture-'+model)
  devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists()];assert len(devices)==1
  camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
  q=run([str(fixture),'/dev/media0',str(tools/'bin/gst-hardware-probe'),camera_id,'640','480'],'gst-'+model,timeout=35,env=env)
  text=(q.stdout+q.stderr).decode(errors='replace');match=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
  assert match and int(match[1])>0 and not int(match[4]) and not int(match[5]) and 'FIXTURE_RESTORATION result=0' in text
  captures[model]=dict(gstreamer_frames=int(match[1]),width=int(match[2]),height=int(match[3]),passed=True)
 save('isolated-main-controls')
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')];assert len(nodes)==1
 env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
 q=run([str(fixture),'/dev/media0',str(tools/'bin/adaptation-smoke'),'s5kgw1','/dev/'+nodes[0].name,'4608x3456','2'],'isolated-main',timeout=40,env=env)
 text=(q.stdout+q.stderr).decode(errors='replace');app=re.findall(r'ADAPT_PID value=(\d+)',text);ipa=set(re.findall(r'IPA stats pid=(\d+)',text))
 assert len(app)==1 and bool(ipa) and all(x!=app[0] for x in ipa) and ' failed=0 result=0' in text and text.count('ADAPT_PHASE ')==5 and text.count('GAMMA_APPLIED ')==1 and 'FIXTURE_RESTORATION result=0' in text
 captures['isolated-main']=dict(frames=text.count('ADAPT_FRAME '),phases=5,gamma_ack=1,actual_isolation_verified=True,passed=True)
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 restored=False
 try:
  wait_idle()
  if stopped:restart(items,'restore',started)
  wait_idle();restored=all(len(processes(name))==1 for name in ['pipewire','wireplumber'])
 except BaseException:(root/'restore-failure.txt').write_text(traceback.format_exc())
 after=subprocess.check_output(['dmesg']);(root/'dmesg-after.txt').write_bytes(after)
 faults={w.decode():after.count(w)-before.count(w) for w in [b'WARNING:',b'Oops:',b'CCI error',b'Stream stop failed:',b'Missing SOF tag',b'Unhandled context fault',b'OF: ERROR']}
 health=dict(platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
  rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))})
 report=dict(stage=381,captures=captures,services_restored=restored,failure=failure is not None,fault_delta=faults,health=health,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
  camss_note_sha256=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest(),kernel_image_stage=363,dt_stage=365,static_board_dt_exercised=True,installed362_userspace_unchanged=True)
 report['passed']=bool(not failure and restored and len(captures)==5 and not any(faults.values()) and report['taint']==0 and all(x=='suspended' for x in health['platforms'].values()) and all(x==dict(state='disabled',users=0) for x in health['rails'].values()))
 save('complete' if report['passed'] else 'failed',terminal=True,summary=report);print(json.dumps(report))
