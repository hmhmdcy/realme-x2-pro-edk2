"""Prepare one481 installation transaction locally; no transport or SDK."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,io,json,shutil,struct,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel481')
WINDOW='k481-package-adoption-r1';TARGET='/var/lib/samurai/'+WINDOW
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def modinfo(path):
 data=path.read_bytes();offset=struct.unpack_from('<Q',data,40)[0];stride,count,strings=struct.unpack_from('<HHH',data,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*stride) for i in range(count)]
 names=data[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 section=next(row for row in sections if names[row[0]:].split(bytes([0]))[0]==b'.modinfo')
 result={}
 for value in data[section[4]:section[4]+section[5]].split(bytes([0])):
  if b'=' in value:
   key,text=value.decode().split('=',1);result.setdefault(key,[]).append(text)
 return {key:sorted(result.get(key,[])) for key in ['depends','softdep','alias','vermagic']}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--template-revision',type=int,choices=range(1,10),default=1)
 for name in ['handoff','owner-return','scoped-owner-return']:parser.add_argument('--'+name,type=Path)
 args=parser.parse_args();assert all([args.handoff,args.owner_return,args.scoped_owner_return]) or not any([args.handoff,args.owner_return,args.scoped_owner_return])
 guard=load_module(HERE.parent/'kernel284/storage.py','guard481');volume=guard.mounted_build().parent
 assert shutil.disk_usage(volume).free>2*1024**3
 old=PRIVATE.parent/'kernel475';source475=HERE.parent/'kernel475';candidate=json.loads((source475/'candidate-state.json').read_text())
 for name in ['package-r1-validation.json','private-archive-r2-validation.json','payload-loader-validation.json']:
  assert sha(source475/name)==candidate['public_files_sha256'][name]
 assert json.loads((HERE.parent/'kernel480/runtime-validation.json').read_text())['passed']
 manifest_path=old/'cohort-r2-manifest-private.json';manifest=json.loads(manifest_path.read_text())
 assert sha(manifest_path)==json.loads((source475/'private-archive-r2-validation.json').read_text())['revised_manifest_sha256']
 assert not args.handoff or args.template_revision==1
 suffix='-bound' if args.handoff else '-offline-template'+('' if args.template_revision==1 else '-r'+str(args.template_revision))
 work=PRIVATE/(WINDOW+suffix);assert not work.exists(),'Preserve an existing prepared attempt'
 work.mkdir(mode=0o700,parents=True)
 files={}
 for name,digest in manifest['files_sha256'].items():
  path=old/'cohort-r1'/name;assert sha(path)==digest;files[name]=path
 dependencies={}
 for row in manifest['modules']:
  before=modinfo(files['rollback/modules/'+row['name']+'.ko']);after=modinfo(files['forward/modules/'+row['name']+'.ko'])
  assert before==after,'Module dependency/alias metadata changed';dependencies[row['name']]=after
 cached=json.loads((old/'package-state-r1-private.json').read_text());package_files={}
 for kind,key in [('rollback','before_files'),('forward','after_files')]:
  combined={}
  for item in cached['inventories']:
   for name,row in item[key].items():
    path='/'+name;assert path not in combined or combined[path]==row;combined[path]=row
  package_files[kind]=combined
 scripts={}
 for path in sorted((old/'cohort-r1/rollback/repository').glob('*.apk')):
  with tarfile.open(path,'r:gz',ignore_zeros=True) as archive:
   script_names=[m.name for m in archive.getmembers() if m.name.lstrip('./') in ['pre-install','post-install','pre-upgrade','post-upgrade','pre-deinstall','post-deinstall','trigger']]
   info=archive.extractfile('.PKGINFO').read().decode();scripts[path.name]=dict(scripts=script_names,triggers=[line for line in info.splitlines() if line.startswith('triggers =')])
 #475 mkpkg forwards only payload plus the explicit info fields, no script/trigger arguments.
 packaging=(source475/'package-cohort.py').read_text();assert '--script' not in packaging and "'triggers'" not in packaging
 scripts['forward']='475 mkpkg has no script or trigger input; native global APK hooks/triggers remain enabled'
 body=(HERE/'worker-body.py').read_text();prefix_path=PRIVATE.parent/'kernel440/install-worker-r3.py'
 prefix=prefix_path.read_text().split('"""Coherent r32/r27, three production modules and four private factory profiles."""')[0]
 prefix=prefix.replace("'stage':440","'stage':481").replace("marker=root/'state.json'","marker=root/'state-private.json'")
 prefix=prefix.replace("'cwd':os.readlink(p/'cwd')","'start_ticks':(p/'stat').read_text().rsplit(')',1)[1].split()[19],'cwd':os.readlink(p/'cwd')")
 prefix=prefix.replace("fd=os.pidfd_open(pid)","assert p.read_text().rsplit(')',1)[1].split()[19]==items[name]['start_ticks']\n  fd=os.pidfd_open(pid)")
 prefix=prefix.replace("result[name]={**item,'pid':child.pid}","result[name]={**item,'pid':child.pid,'start_ticks':Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]}")
 worker480=(HERE.parent/'kernel480/target-worker.py').read_text();assert sha(HERE.parent/'kernel480/target-worker.py')=='42a5d4110dc2c17af66c095a1d77ea02841a3dca3e09d51ced1d1cdf2d92981c'
 gate=next(ast.get_source_segment(worker480,n) for n in ast.parse(worker480).body if isinstance(n,ast.FunctionDef) and n.name=='gate')
 gate=gate.replace('k476-control-delay-r2','k476-control-delay-r3')
 #WINDOW is resolved by the copied function, so the minimal481 namespace is fixed here.
 prefix=prefix.replace("marker=root/'state-private.json'","plan=json.loads((root/'plan-private.json').read_text());gate(plan)\nmarker=root/'state-private.json'")
 comparison_path=HERE.parent/'kernel451/capture-body-comparison.py';comparison=comparison_path.read_text()
 assert sha(comparison_path)=='a65f6326fc2366e8bd0b225c1399c386d0aa86f83260d28e57e02ed04e279fff'
 charging=next(ast.get_source_segment(comparison,n) for n in ast.parse(comparison).body if isinstance(n,ast.FunctionDef) and n.name=='charging')
 worker='from datetime import datetime,timezone\nimport runpy\nWINDOW='+repr(WINDOW)+'\n'+gate+'\n'+prefix+'\n'+charging+'\n'+body
 ast.parse(worker);(work/'worker.py').write_text(worker);files['worker.py']=work/'worker.py'
 probe_receipt=HERE.parent/'kernel482/preparation-validation.json';probe_prepared=json.loads(probe_receipt.read_text());assert probe_prepared['passed']
 for name in ['default-probe.py','probe-log-audit.py']:
  path=HERE.parent/'kernel482'/name;assert path.is_file() and sha(path)==probe_prepared['source_files'][name];ast.parse(path.read_text());files[name]=path
 tools={
  'pipeline-fixture':(PRIVATE.parent/'kernel449/pipeline-fixture-long','bad0dc79d95d070f089c158b159a21f72a44a459f4c1606f9c27493457863a43'),
  'gst-sustained':(PRIVATE.parent/'kernel449/gst-sustained','7f4d6a1f8527280d8bbe11e6af638348200bd9bc8465be8357cdc0ca732b852a'),
  'pipeline-smoke':(PRIVATE.parent/'kernel440/pipeline-smoke','0d692025b2adaf6b5cbadd7fac24ae3034214f5f262ce811061d1a6ea745f4fc'),
  'user-launcher.py':(HERE.parent/'kernel449/user-launcher.py','1d1fb6567439ff600c0116d8561ba9c60914306ebb89ccb9b5e08242f9c52ee6')}
 probe_tools={}
 for name,(path,digest) in tools.items():assert sha(path)==digest;files[name]=path;probe_tools[name]=dict(path=name,sha256=digest)
 cohort={key:manifest[key] for key in ['release','modules','profiles','forward_packages','rollback_packages']}
 expected=dict(packages=cohort['forward_packages'],runtime_files={path:row['sha256'] for path,row in package_files['forward'].items() if 'sha256' in row},
  modules=[dict(name=row['name'],path=row['path'],sha256=row['forward_sha256'],note_sha256=row['forward_note_sha256']) for row in cohort['modules']],
  profiles=[dict(model=row['model'],path=row['path'],sha256=row['forward_sha256']) for row in cohort['profiles']],probe_tools=probe_tools)
 plan=dict(stage=481,window_id=WINDOW,deployable=bool(args.handoff),target_root=TARGET,cohort=cohort,package_files=package_files,
  expected_forward=expected,payload_sha256={name:sha(path) for name,path in files.items()},scripts_metadata=scripts,
  native_scripts_hooks_policy='enabled; absent cohort scripts are not claimed exercised; fresh global hook inventory is recorded',
  minimum_target_free_bytes=512*1024**2,promotion_deadline_seconds=300,diagnostic_budget_seconds=480,
  persistent_repository_dir='/var/lib/samurai/camera-r33-r28-k481-r1',persistent_repository_file='/etc/apk/repositories.d/61-samurai-camera-r33-k481.list',
  candidate_state_sha256=sha(source475/'candidate-state.json'),cohort_manifest_sha256=sha(manifest_path),package_inventory_source_sha256=sha(old/'package-state-r1-private.json'),
  prior_target_solver_receipt_sha256=sha(HERE.parent/'kernel480/runtime-validation.json'),module_dependency_metadata=dependencies,
  probe_preparation_receipt_sha256=sha(probe_receipt),
  source_sha256={str(p.relative_to(HERE.parent)):sha(p) for p in [HERE/'worker-body.py',HERE/'prepare-runtime.py',HERE/'render-queries.py',comparison_path,HERE.parent/'kernel482/default-probe.py',HERE.parent/'kernel482/probe-log-audit.py']},
  reused440_actual_worker_sha256=sha(prefix_path))
 if args.handoff:
  plan.update(handoff=json.loads(args.handoff.read_text()),owner=json.loads(args.owner_return.read_text()),scoped_owner=json.loads(args.scoped_owner_return.read_text()))
  baseline=args.handoff.parent/'baseline-private.json';assert sha(baseline)==plan['handoff']['formal_baseline_sha256']
  files['baseline-private.json']=baseline;plan['payload_sha256']['baseline-private.json']=sha(baseline)
  for key in ['charging_manifest_private','provenance_private']:assert sha(plan['owner'][key])==plan['owner'][key.replace('_private','_sha256')]
  start=gate.index("    boot = Path('/proc/sys/kernel/random/boot_id')")
  context={'datetime':__import__('datetime').datetime,'timezone':__import__('datetime').timezone,'WINDOW':WINDOW}
  exec(gate[:start],context);context['gate'](plan)
  plan['authorization_files_sha256']={str(path):sha(path) for path in [args.handoff,args.owner_return,args.scoped_owner_return]}
 (work/'plan-private.json').write_text(json.dumps(plan,indent=2)+'\n');files['plan-private.json']=work/'plan-private.json'
 modes={name:(0o755 if name in tools else 0o600) for name in files}
 directories=sorted({parent.as_posix() for name in files for parent in Path(name).parents if str(parent)!='.'},key=lambda value:(value.count('/'),value))
 archive=work/'payload-private.tar.gz'
 with tarfile.open(archive,'w:gz',format=tarfile.PAX_FORMAT) as tar:
  for name in directories:
   item=tarfile.TarInfo(name);item.type=tarfile.DIRTYPE;item.mode=0o700;item.uid=item.gid=0;tar.addfile(item)
  for name,path in sorted(files.items()):
   data=path.read_bytes();item=tarfile.TarInfo(name);item.mode=modes[name];item.uid=item.gid=0;item.size=len(data);tar.addfile(item,io.BytesIO(data))
 mapping={name:sha(path) for name,path in files.items()}
 renderer=load_module(HERE/'render-queries.py','render481');renderer.render(work,plan,mapping,modes,directories,sha(archive),gate,charging)
 report=dict(stage=481,prepared=True,deployable=plan['deployable'],no_ssh=True,no_sdk=True,no_target_execution=True,
  files=len(files),archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),worker_sha256=sha(work/'worker.py'),
  plan_sha256=sha(work/'plan-private.json'),candidate_state_sha256=plan['candidate_state_sha256'],
  query_sha256={name:sha(work/(name+'-query.py')) for name in ['stage','launch','observe','collect']},source_sha256=plan['source_sha256'])
 (work/'preparation-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(work=str(work),**report)))

if __name__=='__main__':main()
