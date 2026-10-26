"""Prepare a new tele payload locally; this tool does not access the phone."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,struct,tarfile,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;reference=HERE.parent;workspace=reference.parent
private=Path('/mnt/e/edk2-samurai-out/kernel467')
p=argparse.ArgumentParser();p.add_argument('--handoff',type=Path,required=True);args=p.parse_args()
spec=importlib.util.spec_from_file_location('storage467',reference/'kernel461/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mount.mounted_build()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
handoff_path=args.handoff;handoff=json.loads(handoff_path.read_bytes())
assert handoff['window_id']=='k467-tele-r1' and handoff['fresh_preflight_verified']
work=private/'prepared-r1';work.mkdir(mode=0o700,exist_ok=False)
inputs=json.loads((private.parent/'kernel450/runtime-input-files-private.json').read_bytes())
files={name:(private.parent/'kernel461/libcamera.so.0.7.2' if name=='lib/libcamera.so.0.7.2' else Path(row['path'])) for name,row in inputs.items()}
for name,path in files.items():assert sha(path)==('9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af' if name=='lib/libcamera.so.0.7.2' else inputs[name]['sha256'])
files['factory-s5k3m5-private.yaml']=private.parent/'kernel440/factory-s5k3m5-private.yaml'
files['gst-sustained']=private.parent/'kernel449/gst-sustained'
assert sha(files['factory-s5k3m5-private.yaml'])=='41cba861b491d583c685e07fdc0e97d635f8922f7132abefa15d0632d4fab0a4'
assert sha(files['gst-sustained'])=='7f4d6a1f8527280d8bbe11e6af638348200bd9bc8465be8357cdc0ca732b852a'
common_payload={name:sha(path) for name,path in files.items()}
files['pipeline-fixture']=private.parent/'kernel449/pipeline-fixture-long'
assert sha(files['pipeline-fixture'])=='bad0dc79d95d070f089c158b159a21f72a44a459f4c1606f9c27493457863a43'
files['user-launcher.py']=reference/'kernel449/user-launcher.py'
modules=json.loads((reference/'kernel441/intree-build-validation.json').read_bytes());assert modules['passed'] and not modules['diagnostics']
module_proof={}
for row in modules['modules']:
    if not row['runtime_candidate']:continue
    path=Path(row['private_path']);raw=path.read_bytes();assert sha(path)==row['sha256']
    shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    note=next(section for section in sections if names[section[0]:].split(bytes([0]))[0]==b'.note.gnu.build-id')
    filename=row['name']+'.ko';files[filename]=path
    module_proof[row['name'].replace('-','_')]=dict(file=filename,sha256=row['sha256'],note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest())
proof=dict(modules=module_proof,boot_guard=handoff['boot_guard_path'])
(work/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');files['proof.json']=work/'proof.json'
plan=dict(stage=467,window_id=handoff['window_id'],kernel_release=modules['modules'][0]['vermagic'].split()[0],
    common_payload=common_payload,cases=['1280x720-isolated','1920x1080-isolated'],target_frames=32,
    model='s5k3m5',sensor_mode=3,actual_sensor=[2104,1560],original440_profile_preserved=True,
    old444_proxy_preserved=True,normal_16_9_mode_claimed=False,trace_role_required=True)
(work/'tele-plan-private.json').write_text(json.dumps(plan,indent=2)+'\n');files['tele-plan-private.json']=work/'tele-plan-private.json'
helper_path=reference/'kernel451/capture-body-comparison.py'
assert sha(helper_path)=='a65f6326fc2366e8bd0b225c1399c386d0aa86f83260d28e57e02ed04e279fff'
text=helper_path.read_text();helper=text[:text.index('def live_witness(')]+text[text.index('def finalize('):]
helper=helper.replace('k451-proxy-comparison-','k467-tele-').replace('comparison','tele').replace('k450-user-','k449-user-')
ast.parse(helper);(work/'capture-common-private.py').write_text(helper);files['capture-common-private.py']=work/'capture-common-private.py'
files['capture-body-tele.py']=HERE/'capture-body-tele.py'
trace_base=(reference/'kernel461/capture-body-lifecycle.py').read_text()
start=trace_base.index('def start_trace(');end=trace_base.index('\ndef witness(',start)
trace_base='from pathlib import Path\nimport hashlib,importlib.util,json,re,secrets,subprocess\n\n'+trace_base[start:end]
trace_base=trace_base.replace('k459-full-461-','k459-full-467-');ast.parse(trace_base)
(work/'capture-trace-base.py').write_text(trace_base);files['capture-trace-base.py']=work/'capture-trace-base.py'
files['handoff-private.json']=handoff_path;files['baseline-private.json']=handoff_path.parent/'baseline-private.json'
for name in ['kernel459/trace-instance.py','kernel463/full-role.py','kernel463/guarded-trace.py']:files[name]=reference/name
prefix=(reference/'kernel342/native-install.py').read_text().split('def versions():',1)[0].replace("'stage':342","'stage':467")+'\nimport runpy\n'
body=(reference/'kernel434/capture-worker-body.py').read_text()
old_clock="start_uptime=float(Path('/proc/uptime').read_text().split()[0])"
assert body.count(old_clock)==1;body=body.replace(old_clock,'start_uptime=time.monotonic()')
start=body.index(" state['captures']={}");end=body.index('\nexcept BaseException:',start)
body=body[:start]+" tele['run_tele'](root,state,save,status,idle,core)\n verified=True\n"+body[end:]
needle="try:\n assert Path('/proc/sys/kernel/random/boot_id')";assert body.count(needle)==1
body=body.replace(needle,"tele=runpy.run_path(str(root/'capture-body-tele.py'))\ntry:\n tele['validate_handoff'](root,state)\n assert Path('/proc/sys/kernel/random/boot_id')")
start=body.index('  if child is not None and child.poll() is None:');end=body.index('  if changed:',start)
body=body[:start]+"  assert child is None, 'Tele body owns its bounded fixture; never blindly signal it'\n"+body[end:]
needle="  state['after_status']=status();state['after_core']=core();assert released(core())";assert body.count(needle)==1
body=body.replace(needle,needle+"\n  state['tele_final_checks']=tele['finalize'](root,state)")
worker=prefix+body;ast.parse(worker);assert 'os.killpg' not in worker
(work/'worker.py').write_text(worker);files['worker.py']=work/'worker.py'
for name,path in files.items():
    if name.endswith('.py'):ast.parse(path.read_text())
manifest={name:sha(path) for name,path in files.items()}
(work/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');files['manifest.json']=work/'manifest.json'
(work/'payload-files-private.json').write_text(json.dumps({name:str(path) for name,path in files.items()},indent=2)+'\n')
with tarfile.open(work/'tele-payload.tar.gz','w:gz',compresslevel=1) as archive:
    for name,path in files.items():archive.add(path,arcname=name,recursive=False)
report=dict(prepared=True,files=len(files),existing_core_modules_clients_and_factory_profile_reused=True,
    trace_constructor_reused=True,monotonic_cutoff=True,no_blind_process_signals=True,
    phone_accessed=False,staged=False,launched=False,passed=True)
(private/'prepared-validation-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
