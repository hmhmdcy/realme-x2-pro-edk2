"""Prepare a single durable package/driver transaction with offline rollback."""
from pathlib import Path
import ast,hashlib,importlib.util,io,json,shlex,subprocess,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'package-artifact-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('prefix395',HERE.parent/'kernel395/durable-prefix.py');prefix=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefix)
header=prefix.source().replace("'stage':395","'stage':420")
body=(HERE.parent/'kernel391/install-worker-body.py').read_text()
body=body.replace('packages_sent=False;verified=False','packages_sent=False;driver_changed=False;verified=False')
body=body.replace("start_uptime=float(Path('/proc/uptime').read_text().split()[0])","kernel_anchor=before.decode(errors='replace').splitlines()[-1]")
at=body.index('\ntry:\n');body=body[:at]+'\n'+(HERE/'driver-install-functions.py').read_text()+body[at:]
body=body.replace("strip()=='0' and versions()", "strip()=='512' and versions()")
old=" assert defaults_unchanged() and released(core())";assert body.count(old)==1
body=body.replace(old,old+"\n driver_notes('old')\n assert all(sha(i['target'])==i['old_sha256'] for i in proof['driver_pair'])")
old=" (root/'services-private.json').write_text";assert body.count(old)==1
body=body.replace(old," for i,item in enumerate(proof['driver_pair']):shutil.copyfile(item['target'],backup/('module-'+str(i)+'.ko'))\n"+old)
body=body.replace('samurai-camera-stack=0.1.0-r25','samurai-camera-stack=0.1.0-r26')
old=" save('installing-r30-r25');packages_sent=True";assert body.count(old)==1
body=body.replace(old," save('installing-production419-pair');driver_changed=True;unload_pair();replace_pair('new');load_pair('new');state['ipe_before']=m2m()\n save('installing-r31-r26');packages_sent=True")
old="  idle()\n  if not verified and stopped:";assert body.count(old)==1
body=body.replace(old,"  if (dev/'m2m_status').exists():idle()\n  if not verified and stopped:")
old="   idle();owner_zero()\n   if packages_sent:";assert body.count(old)==1
body=body.replace(old,"   if (dev/'m2m_status').exists():idle();owner_zero()\n   if driver_changed:unload_pair();replace_pair('old');load_pair('old')\n   if packages_sent:")
old=" logs=subprocess.check_output(['dmesg']).decode(errors='replace');new=[]\n for line in logs.splitlines():\n  m=re.search(r'\\[\\s*(\\d+\\.\\d+)\\]',line)\n  if m and float(m[1])>=start_uptime:new.append(line)"
assert body.count(old)==1
body=body.replace(old," logs=subprocess.check_output(['dmesg']).decode(errors='replace');lines=logs.splitlines()\n assert lines.count(kernel_anchor)==1,'Kernel log anchor unavailable: retain evidence and inspect'\n new=lines[lines.index(kernel_anchor)+1:]")
body=body.replace("Stream stop failed:'", "Stream stop failed:|A5 IPE frame failed|IPE m2m job failed'")
body=body.replace('and not taint and all','and taint==512 and all').replace('state.update(installed=verified','state.update(driver_pair_installed=verified,installed=verified')
body=body.replace(" state['ipe_after']=after;state['core_after']=core();verified=True", " driver_notes('new')\n state['ipe_after']=after;state['core_after']=core();verified=True")
ast.parse(header+'\n'+body);(HERE/'install-worker-body.py').write_text(body);worker=P/'install-worker.py';worker.write_text(header+'\n'+body)
client=(HERE.parent/'kernel391/camera-client.py').read_text().replace("'stage':391","'stage':420").replace('stage=391','stage=420').replace('k390-active','k394-recovered').replace("strip()=='0'","strip()=='512'").replace("report['taint']==0","report['taint']==512")
ast.parse(client);(HERE/'camera-client.py').write_text(client)
collector=(HERE.parent/'kernel391/dump-collector.py').read_text().replace('k390-active','k394-recovered');(HERE/'dump-collector.py').write_text(collector)
initial=json.loads((P/'initial-device-private.json').read_text());records=json.loads((P/'runtime-records.json').read_text());oldmeta=json.loads((P.parent/'kernel419/manifest-private.json').read_text())
build=json.loads((HERE.parent/'kernel419/intree-build-validation.json').read_text());pair=[];files={}
for i,(module,row) in enumerate(zip(['qcom_camss_icp_a5_core','camss_icp_a5_m2m'],build['modules'][:2])):
 local=Path(row['private_path']);assert hashlib.sha256(local.read_bytes()).hexdigest()==row['sha256']
 parms=subprocess.check_output(['modinfo','-F','parm',str(local)],text=True);assert 'test_' not in parms
 payload='production-core.ko' if i==0 else 'production-adapter.ko';files[payload]=local
 note=P/(module+'.note');subprocess.run(['aarch64-linux-gnu-objcopy','--dump-section','.note.gnu.build-id='+str(note),str(local)],check=True)
 target=next(n for n in oldmeta['normal_files'] if n.endswith('/'+row['name']+'.ko'))
 pair.append(dict(module=module,target=target,payload=payload,new_sha256=row['sha256'],old_sha256=oldmeta['normal_files'][target],new_note_sha256=hashlib.sha256(note.read_bytes()).hexdigest(),old_note_sha256=oldmeta[('normal_core' if i==0 else 'normal_adapter')+'_note_sha256']))
proof=dict(stage=420,boot_guard='/var/lib/samurai/k394-recovered/boot-id-private.txt',old_packages=initial['packages'],packages={r['name']:r['version'] for r in records},private_defaults=initial['private_defaults'],installed_files=json.loads((P/'installed-file-sha256.json').read_text()),camss_note_sha256=oldmeta['camss_note_sha256'],driver_pair=pair)
proofpath=P/'install-proof-private.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n')
files.update({'worker.py':worker,'camera-client.py':HERE/'camera-client.py','dump-collector.py':HERE/'dump-collector.py','proof.json':proofpath})
for p in (P/'runtime-repository/forward').iterdir():files['repository/forward/'+p.name]=p
files['repository/rollback/packages.adb']=P/'runtime-repository/rollback/packages.adb'
cached={}
for p in (P/'runtime-repository/rollback').glob('*.apk'):cached['repository/rollback/'+p.name]=dict(path='/var/lib/samurai/k391-install-r2/repository/forward/'+p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
for n,remote,local in [('pipeline-fixture','/var/lib/samurai/k387-pipeline-r5/pipeline-fixture',P.parent/'kernel363/pipeline-fixture'),('pipeline-smoke','/var/lib/samurai/k387-pipeline-r5/pipeline-smoke',P.parent/'kernel388/pipeline-smoke')]:cached[n]=dict(path=remote,sha256=hashlib.sha256(local.read_bytes()).hexdigest())
cached['pw-hardware-probe']=dict(path='/var/lib/samurai/k362-install-r1/bin/pw-hardware-probe',sha256=hashlib.sha256((storage.SDK/'private/camss316-runtime/pw-hardware-probe').read_bytes()).hexdigest())
payload=P/'install-payload-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n,recursive=False)
metadata=dict(files_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},payload_sha256=hashlib.sha256(payload.read_bytes()).hexdigest(),cached=cached)
(P/'stage-manifest-private.json').write_text(json.dumps(metadata,indent=2)+'\n')
stage=(HERE.parent/'kernel391/stage-install.py').read_text().replace('k391-install-r1','k420-install-r1').replace('k390-active','k394-recovered').replace('stage=391','stage=420').replace('created391','created420')
ast.parse(stage);(HERE/'stage-install.py').write_text(stage)
step=(HERE.parent/'kernel391/install-step.py').read_text().replace('k391-install-','k420-install-').replace('stage=391','stage=420')
step=step.replace("'ipe_before','ipe_after_suite'","'driver_pair_installed','ipe_before','ipe_after_suite'")
ast.parse(step);(HERE/'install-step.py').write_text(step)
print(json.dumps(dict(prepared=True,payload_bytes=payload.stat().st_size,forward_packages=7,rollback_packages_cached=7,production_driver_files=2,no_test_modules=True,installed=False)))
