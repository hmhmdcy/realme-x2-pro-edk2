"""Stage a reversible, bounded IPE replay with exact built-module identities."""
from pathlib import Path
import ast,hashlib,io,json,shlex,struct,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt.startswith('r') and attempt[1:].isdigit() and 1<=int(attempt[1:])<=20
if (HERE/'incident-validation.json').exists():
 assert (HERE/'camera-recovery-validation.json').exists() and json.loads((HERE/'camera-recovery-validation.json').read_text())['passed'],'Recover and verify the device before another experiment'
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and not build['diagnostics']
assert json.loads((HERE/'runtime-validation.json').read_text())['passed']
probe=json.loads((HERE/'client-build-validation.json').read_text());assert probe['passed']
assert probe['source_sha256']==hashlib.sha256((HERE/'pd10-ipe.c').read_bytes()).hexdigest()
assert probe['probe_sha256']==hashlib.sha256((P/'pd10-ipe').read_bytes()).hexdigest()
assert build['attempt']==1,'Only the build with the unsafe MMIO diagnostic removed is eligible'
recovered=json.loads((P.parent/'kernel429/postboot-adoption-private.json').read_text());guard=recovered['guard_path']
baseline_code='''from pathlib import Path
import hashlib,json
d=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),status=json.loads((d/'m2m_status').read_text()),notes={n:hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest() for n in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']})))
'''
q=host.ssh('python3 -c '+shlex.quote(baseline_code),timeout=20);q.check_returncode();baseline=json.loads(q.stdout)
normal=json.loads((P.parent/'kernel429/runtime-collected-r3/state.json').read_text())['before_notes']
assert baseline['taint']==0 and baseline['notes']==normal
assert not any(baseline['status'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert baseline['status']['jobs']==baseline['status']['completed']==baseline['status']['direct_completed']
(P/('preflight-'+attempt+'-private.json')).write_text(json.dumps(baseline,indent=2)+'\n')
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':430")
body=(HERE.parent/'kernel428/multicamera-worker-body.py').read_text()
body=body.replace('/var/lib/samurai/k394-recovered/boot-id-private.txt',guard).replace("assert state['taint_before']==512","assert state['taint_before']==0")
a=body.index(" expected_jobs=793");z=body.index(" items=services();",a)
body=body[:a]+''' baseline=BASELINE
 assert notes()==baseline['notes']
 assert all(status()[k]==baseline['status'][k] for k in ['jobs','completed','direct_completed','failed','cancelled','first_error'])
 assert not any(status()[k] for k in ['users','running','fatal','pinned','orphans'])
'''.replace('BASELINE',repr(baseline))+body[z:]
a=body.index(" state['captures']={}");z=body.index(" state['candidate_final_status']",a)
body=body[:a]+''' import fcntl
 video=[str(Path('/dev')/p.parent.name) for p in Path('/sys/class/video4linux').glob('video*/name') if p.read_text().strip()=='qcom-ipe-a5']
 assert len(video)==1,video
 media=[]
 for path in Path('/dev').glob('media[0-9]*'):
  try:
   with path.open('rb',buffering=0) as f:
    data=bytearray(256);fcntl.ioctl(f.fileno(),0xc1007c00,data,True)
   model=bytes(data[16:48]).split(b'\\0')[0].decode()
   if model=='SM8150 IPE':media.append(str(path))
  except OSError:continue
 assert len(media)==1,media
 scene=root/'scene';scene.mkdir();shutil.copyfile(root/'params-s5kgw1-private.bin',scene/'params-private.bin')
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
 case=root/'replay';case.mkdir()
 shutil.copyfile(scene/('full-%d.bin'%selected),case/'full-private.bin');shutil.copyfile(scene/('ds4-%d.bin'%selected),case/'pd10-private.bin');shutil.copyfile(root/'parameters-private.bin',case/'parameters-private.bin')
 with (case/'client.log').open('xb') as log:
  child=subprocess.Popen([str(root/'pd10-ipe'),video[0],media[0],str(case)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save('replaying-real-pd10',client_pid=child.pid);code=child.wait(timeout=55)
 text=(case/'client.log').read_text(errors='replace');state['replay_exit_code']=code
 assert code==0 and 'PD10_IPE_RESULT result=0 frames=4' in text,text[-3000:]
 idle();s=status();assert s['jobs']==s['completed']==s['direct_completed']==4 and not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
 state['frames']=4;state['live_sensor_capture']=True
'''+body[z:]
body=body.replace("  if changed:\n   idle()", "  if changed:\n   if not released(core()) or status()['fatal']:\n    (dev/'cleanup').write_text('1\\n')\n   idle()")
source=prefix+'\n'+body;ast.parse(source);(P/'runtime-worker.py').write_text(source)
files={'worker.py':P/'runtime-worker.py','pd10-ipe':P/'pd10-ipe'}
files.update({'scene-pair':P/'scene-pair','pipeline-fixture':P.parent/'kernel363/pipeline-fixture','params-s5kgw1-private.bin':P.parent/'kernel428/params-s5kgw1-private.bin'})
for name in ['full-private.bin','pd10-private.bin','parameters-private.bin']:files[name]=P/name
proof={'modules':{}}
for row in build['modules']:
 if not row['runtime_candidate']:continue
 path=Path(row['private_path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
 shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)];names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 note=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id');name=row['name'].replace('-','_');filename=row['name']+'.ko'
 files[filename]=path;proof['modules'][name]=dict(file=filename,sha256=row['sha256'],note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest())
(P/'runtime-proof-private.json').write_text(json.dumps(proof,indent=2)+'\n');files['proof.json']=P/'runtime-proof-private.json'
manifest={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()};payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n)
 data=json.dumps(manifest).encode();member=tarfile.TarInfo('manifest.json');member.size=len(data);tar.addfile(member,io.BytesIO(data))
code='''from pathlib import Path
import hashlib,io,json,os,sys,tarfile
root=Path(ROOT);assert not root.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
tar=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz');members=tar.getmembers();assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
root.mkdir(mode=0o700)
for m in members:
 with (root/m.name).open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,digest in json.loads((root/'manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==digest
for n in ['pd10-ipe','scene-pair','pipeline-fixture']:(root/n).chmod(0o700)
print(json.dumps(dict(staged=True,root=str(root),passed=True)))
'''.replace('/var/lib/samurai/k394-recovered/boot-id-private.txt',guard).replace('ROOT',repr('/var/lib/samurai/k430-dc-topology-'+attempt)).replace('NAMES',repr(set(files)|{'manifest.json'}))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=30);print(q.stdout.decode());q.check_returncode()
(HERE/('runtime-staging-'+attempt+'-validation.json')).write_bytes(q.stdout)
