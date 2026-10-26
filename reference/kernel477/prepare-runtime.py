"""Local-only477 preparation; renders target queries but never transports them."""
from pathlib import Path
import argparse, ast, hashlib, importlib.util, io, json, os, shutil, sys, tarfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel477')
WINDOW = 'k477-target-deps-r1'
TARGET = '/var/lib/samurai/' + WINDOW
SHA = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path, value): path.write_text(json.dumps(value, indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff', type=Path); parser.add_argument('--owner-return', type=Path)
    parser.add_argument('--scoped-owner-return', type=Path)
    args=parser.parse_args(); assert all([args.handoff,args.owner_return,args.scoped_owner_return]) or not any([args.handoff,args.owner_return,args.scoped_owner_return])
    spec=importlib.util.spec_from_file_location('guard477',HERE.parent/'kernel284/storage.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);build=guard.mounted_build()
    assert shutil.disk_usage(build).free > 2*1024**3
    src=HERE.parent/'kernel475'; private475=PRIVATE.parent/'kernel475'
    candidate=json.loads((src/'candidate-state.json').read_text())
    receipts={}
    for name in ['package-r1-validation.json','private-archive-r2-validation.json']:
        assert SHA(src/name)==candidate['public_files_sha256'][name]
        receipts[name]=json.loads((src/name).read_text())
    manifest=private475/'cohort-r2-manifest-private.json'
    assert SHA(manifest)==receipts['private-archive-r2-validation.json']['revised_manifest_sha256']
    cohort=json.loads(manifest.read_text()); packages=receipts['package-r1-validation.json']['packages'];assert len(packages)==7
    hashes={'repository/'+p['file']:p['sha256'] for p in packages}
    hashes['repository/packages.adb']=cohort['files_sha256']['forward/repository/packages.adb']
    repo=private475/'repository-r1/forward'
    for name,digest in hashes.items():assert SHA(repo/Path(name).name)==digest
    work=PRIVATE/(WINDOW+('-bound' if args.handoff else '-offline-template')); assert not work.exists(), 'Never overwrite a prepared attempt'
    work.mkdir(mode=0o700,parents=True)
    plan=dict(stage=477,window_id=WINDOW,deployable=bool(args.handoff),target_root=TARGET,
              candidate_state_sha256=SHA(src/'candidate-state.json'),
              bound_receipts_sha256={n:SHA(src/n) for n in receipts},cohort_manifest_sha256=SHA(manifest),
              packages=[{k:p[k] for k in ['name','version','file','bytes','sha256']} for p in packages],
              pins=sorted(p['name']+'='+p['version'] for p in packages),payload_sha256=hashes)
    plan['payload_sha256']['worker.py']=SHA(HERE/'target-worker.py')
    if args.handoff:
        plan.update(handoff=json.loads(args.handoff.read_text()),owner=json.loads(args.owner_return.read_text()),scoped_owner=json.loads(args.scoped_owner_return.read_text()),
                    authorization_files_sha256={str(p):SHA(p) for p in [args.handoff,args.owner_return,args.scoped_owner_return]})
        handoff=plan['handoff']; baseline=args.handoff.parent/'baseline-private.json'
        assert SHA(baseline)==handoff['formal_baseline_sha256']
        for key in ['charging_manifest_private','provenance_private']:
            assert SHA(plan['owner'][key])==plan['owner'][key.replace('_private','_sha256')]
        # Same target gate runs locally with only host-specific boot checks suppressed.
        source=(HERE/'target-worker.py').read_text(); start=source.index("    boot = Path('/proc/sys/kernel/random/boot_id')"); end=source.index('\n\n\ndef inventory',start)
        namespace={'__name__':'gate_check'};exec(compile(source[:start]+source[end:],str(HERE/'target-worker.py'),'exec'),namespace);namespace['gate'](plan)
    files={'worker.py':HERE/'target-worker.py',**{name:repo/Path(name).name for name in hashes if name.startswith('repository/')}}
    write(work/'plan-private.json',plan);files['plan-private.json']=work/'plan-private.json'
    bundle=work/'payload-private.tar.gz'
    with tarfile.open(bundle,'w:gz',format=tarfile.PAX_FORMAT) as tar:
        d=tarfile.TarInfo('repository');d.type=tarfile.DIRTYPE;d.uid=d.gid=0;d.mode=0o700;tar.addfile(d)
        for name,path in sorted(files.items()):
            data=path.read_bytes();info=tarfile.TarInfo(name);info.uid=info.gid=0;info.mode=0o600;info.size=len(data);tar.addfile(info,io.BytesIO(data))
    mapping={name:SHA(path) for name,path in files.items()}
    prefix="from pathlib import Path\nimport hashlib,json,os,sys,tarfile,io,subprocess,time\nroot=Path("+repr(TARGET)+")\nexpected="+repr(mapping)+"\nplan="+repr(plan)+"\n"
    worker=(HERE/'target-worker.py').read_text();gate_code=worker[worker.index('def gate('):worker.index('\n\ndef inventory')]
    common=prefix+'from datetime import datetime,timezone\nWINDOW='+repr(WINDOW)+'\n'+gate_code+'\ngate(plan)\n'
    stage=common+'''assert not root.exists(), 'No restaging or replacing an existing attempt'
os.umask(0o077);root.mkdir(mode=0o700)
data=sys.stdin.buffer.read(32*1024*1024);assert hashlib.sha256(data).hexdigest()==BUNDLE_HASH
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
    members=archive.getmembers();assert {m.name for m in members}==set(expected)|{'repository'}
    assert len(members)==len(expected)+1
    (root/'repository').mkdir(mode=0o700)
    for member in members:
        assert member.uid==member.gid==0 and member.mode==(0o700 if member.isdir() else 0o600)
        if member.isdir():assert member.name=='repository';continue
        assert member.isfile() and member.name in expected
        content=archive.extractfile(member).read();assert hashlib.sha256(content).hexdigest()==expected[member.name]
        destination=root/member.name;destination.write_bytes(content);destination.chmod(0o600)
(root/'staged-private.json').write_text(json.dumps({'passed':True,'files_sha256':expected})+chr(10))
print(json.dumps({'staged':True,'root':str(root)}))
'''.replace('BUNDLE_HASH',repr(SHA(bundle)))
    launch=common+'''assert root.is_dir() and not (root/'launch-private.json').exists() and not (root/'worker-once-private').exists()
assert json.loads((root/'staged-private.json').read_text())['files_sha256']==expected
for name,digest in expected.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
os.umask(0o077)
fd=os.open(root/'launch-private.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
out=(root/'worker-stdout-private.txt').open('xb');err=(root/'worker-stderr-private.txt').open('xb')
p=subprocess.Popen(['/usr/bin/python3','-B',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,cwd=root)
ticks=Path('/proc',str(p.pid),'stat').read_text().split(') ',1)[1].split()[19]
record={'pid':p.pid,'start_ticks':ticks,'launched':True};os.write(fd,(json.dumps(record)+chr(10)).encode());os.close(fd)
print(json.dumps(record))
'''
    observe=prefix+'''record=json.loads((root/'launch-private.json').read_text());p=Path('/proc',str(record['pid']),'stat');live=False;proc_state=None
if p.exists():
    values=p.read_text().split(') ',1)[1].split();proc_state=values[0];live=values[19]==record['start_ticks'] and proc_state!='Z'
state=json.loads((root/'state-private.json').read_text()) if (root/'state-private.json').exists() else None
print(json.dumps({'worker_live':live,'process_state':proc_state,'launch':record,'state':state}))
'''
    collect=observe.replace("print(json.dumps({'worker_live':live,'process_state':proc_state,'launch':record,'state':state}))",'''assert not live, 'Wait for the launched worker; never collect a live operation'
assert state and state['terminal'], 'Missing terminal state; preserve stderr and report failure'
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
    for path in sorted(root.iterdir()):
        if path.is_file() and path.name!='worker.py':
            content=path.read_bytes();member=tarfile.TarInfo(path.name);member.uid=member.gid=0;member.mode=0o600;member.size=len(content);archive.addfile(member,io.BytesIO(content))''')
    for name,source in [('stage',stage),('launch',launch),('observe',observe),('collect',collect)]:
        ast.parse(source);(work/(name+'-query.py')).write_text(source)
    report=dict(stage=477,prepared=True,deployable=plan['deployable'],no_ssh=True,no_sdk=True,no_target_execution=True,
                bundle_sha256=SHA(bundle),bundle_bytes=bundle.stat().st_size,repository_files=8,
                candidate_state_sha256=plan['candidate_state_sha256'],source_sha256={p.name:SHA(p) for p in [HERE/'target-worker.py',HERE/'prepare-runtime.py']},
                query_sha256={n:SHA(work/(n+'-query.py')) for n in ['stage','launch','observe','collect']})
    write(work/'preparation-private.json',report);print(json.dumps(dict(report,work=str(work))))


if __name__=='__main__':main()
