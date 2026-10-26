"""Build a short same-SOF capture and derive a reversible fresh-input replay."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
text=(HERE.parent/'kernel428/ds4-capture.c').read_text()
text=text.replace('unsigned held[4],nh=0,hold_full=0,resume_full=0,stop_full=0;bool holding=false,resumed=false,stopped=false;','bool stopped=false;')
a=text.index('   /* Keep disk writes');z=text.index('\n }\ndone:',a)
text=text[:a]+'''   if(dump(argv[1],k?"ds4":"full",b.sequence,data,q->size)||enqueue(q,b.index))goto done;
  }
  if(full.frames>=6&&ds.frames>=6){result=0;break;}
'''+text[z:]
assert 'STARVE' not in text
(HERE/'scene-pair.c').write_text(text)
s=importlib.util.spec_from_file_location('storage430scene',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
kernel=m.mounted_build().parent/'source354';inc=P.parent/'kernel428/capture-includes'
assert (inc/'linux/qcom-camss-config.h').read_bytes()==(kernel/'include/uapi/linux/qcom-camss-config.h').read_bytes()
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I'+str(inc),str(HERE/'scene-pair.c'),'-o',str(P/'scene-pair')],capture_output=True)
(P/'scene-pair-build.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
report=dict(stage=430,frames_per_stream=6,static_arm64=True,compiler_warnings=[],source_sha256=hashlib.sha256(text.encode()).hexdigest(),probe_sha256=hashlib.sha256((P/'scene-pair').read_bytes()).hexdigest(),passed=True)
(HERE/'scene-pair-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
prepare=(HERE/'prepare-runtime.py').read_text()
anchor=" case=root/'replay';case.mkdir()"
assert prepare.count(anchor)==1
fresh=''' scene=root/'scene';scene.mkdir();shutil.copyfile(root/'params-s5kgw1-private.bin',scene/'params-private.bin')
 with (scene/'capture.log').open('xb') as log:
  env=os.environ.copy();env['DS4_SENSOR_MODEL']='s5kgw1';env.pop('DS4_CAPTURE_FULL_ONLY',None)
  child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'scene-pair'),str(scene),'0'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save('fresh-main-paired-capture',client_pid=child.pid);code=child.wait(timeout=30)
 text=(scene/'capture.log').read_text(errors='replace')
 assert code==0 and 'DS4_RESULT result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3000:]
 sequences={int(p.stem.split('-')[-1]) for p in scene.glob('full-*.bin')}&{int(p.stem.split('-')[-1]) for p in scene.glob('ds4-*.bin')}
 assert len(sequences)>=5,sequences
 selected=max(sequences)
 state['fresh_capture']=dict(model='s5kgw1',pattern=0,full_frames=text.count('FRAME kind=full '),pd10_frames=text.count('FRAME kind=ds4 '),paired_frames=len(sequences),selected_sof=selected,fixture_restored=True)
 idle();assert status()['jobs']==0 and released(core())
 case=root/'replay';case.mkdir()'''
prepare=prepare.replace(anchor,fresh)
anchor=" for name in ['full-private.bin','pd10-private.bin','parameters-private.bin']:shutil.copyfile(root/name,case/name)"
assert prepare.count(anchor)==1
prepare=prepare.replace(anchor," shutil.copyfile(scene/('full-%d.bin'%selected),case/'full-private.bin');shutil.copyfile(scene/('ds4-%d.bin'%selected),case/'pd10-private.bin');shutil.copyfile(root/'parameters-private.bin',case/'parameters-private.bin')")
prepare=prepare.replace("state['live_sensor_capture']=False","state['live_sensor_capture']=True")
anchor="files={'worker.py':P/'runtime-worker.py','pd10-ipe':P/'pd10-ipe'}"
assert prepare.count(anchor)==1
prepare=prepare.replace(anchor,anchor+"\nfiles.update({'scene-pair':P/'scene-pair','pipeline-fixture':P.parent/'kernel363/pipeline-fixture','params-s5kgw1-private.bin':P.parent/'kernel428/params-s5kgw1-private.bin'})")
prepare=prepare.replace("(root/'pd10-ipe').chmod(0o700)","for n in ['pd10-ipe','scene-pair','pipeline-fixture']:(root/n).chmod(0o700)")
ast.parse(prepare);(HERE/'prepare-fresh-runtime.py').write_text(prepare)
print(json.dumps(report))
