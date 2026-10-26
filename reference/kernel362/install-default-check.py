# Inserted into the native transaction after the matched module and profiles.
default_cases=json.loads((root/'default-cases.json').read_text())
default_results={}
for label,item in default_cases.items():
 model=item['model']
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')]
 if len(nodes)!=1:raise RuntimeError('Default sensor not unique: '+model)
 env=dict(os.environ,LIBCAMERA_IPA_FORCE_ISOLATION='1',LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
 for key in ['LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LD_LIBRARY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST']:env.pop(key,None)
 q=run([str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/adaptation-smoke'),model,'/dev/'+nodes[0].name,item['sensor_size'],str(item['test_pattern'])],
       'default-'+label,timeout=40,env=env)
 text=(q.stdout+q.stderr).decode(errors='replace')
 pids=re.findall(r'ADAPT_PID value=(\d+)',text);ipa_pids=set(re.findall(r'IPA stats pid=(\d+)',text))
 good=(len(pids)==1 and bool(ipa_pids) and all(pid!=pids[0] for pid in ipa_pids) and
       ' failed=0 result=0' in text and text.count('ADAPT_PHASE ')==5 and text.count('GAMMA_APPLIED ')==1 and
       '/etc/libcamera/ipa/camss-vfe/'+model+'.yaml' in text and
       'ADAPT_LIBRARY path=/usr/lib/libcamera.so.0.7.2' in text and
       'ADAPT_LIBRARY path=/usr/lib/libcamera-base.so.0.7.2' in text and 'FIXTURE_RESTORATION result=0' in text)
 default_results[label]=dict(frames=text.count('ADAPT_FRAME '),phases=text.count('ADAPT_PHASE '),gamma_ack=text.count('GAMMA_APPLIED '),isolated=True,standard_private_path=True,passed=good)
 if not good:raise RuntimeError('Installed default request check failed: '+label)
wait_idle()
