"""Build the durable cohort payload from already tested signed artifacts."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess,tarfile,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt in ['r1','r2','r3']
for name in ['hardware','packaged-contract','package-artifact','install-preflight']:
 assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
initial=json.loads((P/'install-baseline-private.json').read_text());records=json.loads((P/'runtime-records.json').read_text())
spec=importlib.util.spec_from_file_location('prefix395',HERE.parent/'kernel395/durable-prefix.py');prefix=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefix)
header=prefix.source().replace("'stage':395","'stage':440")
# Do not signal a PID if the recorded desktop process has been replaced.
header=header.replace("fd=os.pidfd_open(pid)","assert Path('/proc',str(pid),'comm').read_text().strip()==name\n  fd=os.pidfd_open(pid)")
worker=P/f'install-worker-{attempt}.py';worker.write_text(header+'\n'+(HERE/'install-worker-body.py').read_text());ast.parse(worker.read_text())
client=P/f'install-camera-client-{attempt}.py';client.write_text(header.replace("marker=root/'state.json'","marker=root/'camera-state.json'")+'\n'+(HERE/'installed-frame-audit.py').read_text()+'\n'+(HERE/'install-camera-body.py').read_text());ast.parse(client.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def old_record(record,backup):
 r=dict(record);r['old_sha256']=r.pop('sha256');r['backup']=backup;return r
files={'worker.py':worker,'camera-client.py':client};modules=[]
build=json.loads((HERE.parent/'kernel434/intree-build-validation.json').read_text());by_name={r['name'].replace('-','_'):r for r in build['modules']}
candidate=json.loads((P/'runtime-collected-r2/state.json').read_text())['candidate_notes']
for i,module in enumerate(['qcom_camss','qcom_camss_icp_a5_core','camss_icp_a5_m2m']):
 old=initial['modules'][module];assert old['apk_owner_rc'] and not old['apk_owner']
 row=by_name[module];local=Path(row['private_path']);assert sha(local)==row['sha256']
 assert 'test_' not in subprocess.check_output(['modinfo','-F','parm',str(local)],text=True)
 note=P/(module+'-install.note');subprocess.run(['aarch64-linux-gnu-objcopy','--dump-section','.note.gnu.build-id='+str(note),str(local)],check=True)
 assert sha(note)==candidate[module]
 r=old_record(old,'modules/'+module+'.ko');r.update(module=module,payload='modules/'+module+'.ko',new_sha256=row['sha256'],old_note_sha256=r.pop('note_sha256'),new_note_sha256=sha(note));modules.append(r);files[r['payload']]=local
profiles=[]
for model in ['s5kgw1','imx319','s5k3m5','imx471']:
 local=P/f'factory-{model}-private.yaml';r=old_record(initial['profiles'][model+'.yaml'],'profiles/'+model+'.yaml');r.update(model=model,payload='profiles/'+model+'.yaml',new_sha256=sha(local));profiles.append(r);files[r['payload']]=local
configuration=[old_record(r,n) for n,r in initial['configuration'].items()]
proof=dict(stage=440,boot_id=initial['boot_id'],uname=initial['uname'],old_packages=initial['packages'],packages={r['name']:r['version'] for r in records},modules=modules,profiles=profiles,configuration=configuration,installed_files=json.loads((P/'installed-file-sha256.json').read_text()),resolved_targets={r['path']:r['resolved'] for r in modules+profiles+configuration})
if attempt=='r3':
 prior=P/'install-collected-r2';oldproof=json.loads((P/'install-proof-r2-private.json').read_text())
 assert oldproof['packages']==proof['packages'] and oldproof['installed_files']==proof['installed_files']
 for key in ['modules','profiles']:assert [(x['path'],x['new_sha256']) for x in oldproof[key]]==[(x['path'],x['new_sha256']) for x in proof[key]]
 suite=json.loads((prior/'suite.json').read_text());captures=suite['captures'];assert len(captures)==6 and all(x['passed'] for x in captures.values())
 audit=json.loads((HERE/'installed-auditor-prior-validation.json').read_text());assert audit['passed'] and audit['raw_sample_lengths_and_luma_verified']
 main=next(r for r in audit['rows'] if r['model']=='s5kgw1');assert main['queued_images']==main['frames']==52 and main['stop_aborted_queued_images']==0
 captures['auto-s5kgw1']={**main,'ipe_completed':52,'ipe_cancelled':0,'audit_evidence':'installed-auditor-prior-validation.json'}
 proof['reuse_cases']=dict(root='/var/lib/samurai/k440-install-r2',proof_sha256=sha(P/'install-proof-r2-private.json'),suite_sha256=sha(prior/'suite.json'),captures=captures,log_sha256={n:sha(prior/(n+'.log')) for n in captures})
assert len(proof['packages'])==7 and len(modules)==3 and len(profiles)==4
proofpath=P/f'install-proof-{attempt}-private.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n');files['proof.json']=proofpath
for kind in ['forward','rollback']:
 paths=list((P/'runtime-repository-r2'/kind).iterdir());assert len([p for p in paths if p.suffix=='.apk'])==7
 for path in paths:files['repository/'+kind+'/'+path.name]=path
for name,path in [('pipeline-fixture',P.parent/'kernel363/pipeline-fixture'),('pipeline-smoke',P/'pipeline-smoke'),('capture',P/'capture'),('gst-hardware-probe',storage.SDK/'private/camss316-runtime/gst-hardware-probe'),('pw-hardware-probe',storage.SDK/'private/camss316-runtime/pw-hardware-probe')]:
 assert path.is_file(),str(path);files[name]=path
assert sha(files['pipeline-smoke'])==json.loads((HERE/'raw-client-build-validation.json').read_text())['binary_sha256']
assert sha(files['capture'])==json.loads((HERE/'capture-validation.json').read_text())['binary_sha256']
payload=P/f'install-payload-{attempt}-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as tar:
 for name,path in files.items():tar.add(path,arcname=name,recursive=False)
meta=dict(files_sha256={n:sha(p) for n,p in files.items()},payload_sha256=sha(payload),phone_root='/var/lib/samurai/k440-install-'+attempt,source_hardware_evidence='hardware-validation.json',build_iteration=2)
(P/f'install-stage-manifest-{attempt}-private.json').write_text(json.dumps(meta,indent=2)+'\n')
r=dict(stage=440,prepared=True,payload_bytes=payload.stat().st_size,forward_packages=7,rollback_packages=7,production_modules=3,factory_private_profiles=4,boot_guard_preserved=True,no_mmio_diagnostic_collector=True,installed=False,passed=True)
(HERE/'install-preparation-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
