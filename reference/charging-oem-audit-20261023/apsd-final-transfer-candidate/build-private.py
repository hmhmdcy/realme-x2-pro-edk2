"""Three changed private W1/Werror objects; reuse original compiler recipes."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OWNER=HERE.parent/'apsd-phy-client-candidate';OLD=HERE.parent/'apsd-pd5v-client-bridge-candidate';BUS=HERE.parent/'apsd-input-backend-candidate'
OUT=Path('/home/cy122/charging-management-20261023/apsd-final-transfer-objects-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['owner-test-result.json','transfer-test-result.json']:
    result=json.loads((HERE/name).read_bytes());assert result['passed']
    assert all(sha(HERE/n)==h for n,h in result['files'].items())
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_mount_guard_final_transfer',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
BUILD=m.mounted_build();SOURCE=(BUILD/'source').resolve();assert SOURCE==Path('/mnt/samurai-full282/source354')
assert shutil.disk_usage('/home/cy122').free>2*1024**3
prior_owner=json.loads((OWNER/'build-result.json').read_bytes());prior_bus=json.loads((BUS/'object-build-result.json').read_bytes())
assert prior_owner['passed'] and prior_bus['passed'] and not OUT.exists()
tracked=set(prior_owner['shared_after'])|set(prior_bus['after'])
before={p:sha(Path(p)) for p in sorted(tracked)}
assert 'CONFIG_TYPEC_QCOM_PMIC=m' in (BUILD/'.config').read_text().splitlines()
OUT.mkdir();(OUT/'tmp').mkdir();include=OUT/'include';include.mkdir()
headers={'core.h':OLD/'core.h','samurai-apsd-owner.h':HERE/'samurai-apsd-owner.h',
    'linux/usb/samurai-apsd-backend.h':HERE/'samurai-apsd-backend.h',
    'linux/usb/samurai-pd5v.h':OLD/'qcom_pmic_typec_5v.h',
    'eud-com-window.h':REF/'charging-session-20261023/eud-runtime-window-candidate/eud-com-window.h',
    'phy-qcom-snps-femto-v2-window.h':OWNER/'phy-qcom-snps-femto-v2-window.h'}
for name,path in headers.items():
    target=include/name;target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(path.read_bytes())
future=OUT/'future-builtin-only.h';future.write_bytes((Path(prior_owner['private_output'])/'future-builtin-only.h').read_bytes())
commands=[];phases=[]
recipes=[('owner-current-m',prior_owner['commands'][0],BUILD,HERE/'samurai-apsd-owner.c'),
    ('owner-future-builtin',prior_owner['commands'][1],BUILD,HERE/'samurai-apsd-owner.c'),
    ('input',prior_bus['command'],Path('/home/cy122/charging-management-20261023/source-float-candidate/kbuild'),HERE/'samurai-usb-input.c')]
for name,recipe,cwd,source in recipes:
    argv=list(recipe);assert argv[0]=='aarch64-linux-gnu-gcc' and '-Werror' in argv and '-DKBUILD_EXTRA_WARN1' in argv
    argv[-1]=str(source);argv[argv.index('-o')+1]=str(OUT/(name+'.o'))
    argv=[('-Wp,-MMD,'+str(OUT/(name+'.d'))) if word.startswith('-Wp,-MMD,') else word for word in argv]
    argv=[('-I'+str(include)) if word=='-I'+prior_owner['private_output']+'/include' else word for word in argv]
    argv=[('-I'+str(HERE)) if word=='-I'+str(OWNER) else word for word in argv]
    argv=[str(future) if word==prior_owner['private_output']+'/future-builtin-only.h' else word for word in argv]
    if name=='input':argv[1:1]=['-I'+str(include)]
    commands.append(argv)
    child=subprocess.Popen(argv,cwd=cwd,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();child.wait()
    (OUT/(name+'.stdout')).write_bytes(stdout);(OUT/(name+'.stderr')).write_bytes(stderr)
    phases.append(dict(name=name,pid=child.pid,original_child_terminal=True,returncode=child.returncode,diagnostic_bytes=len(stderr)))
    if child.returncode or stderr:break
after={p:sha(Path(p)) for p in sorted(tracked)}
result=dict(passed=len(phases)==3 and all(p['returncode']==p['diagnostic_bytes']==0 for p in phases) and before==after,
    phases=phases,commands=commands,private_output=str(OUT),objects={p.name:sha(p) for p in OUT.glob('*.o')},
    shared_before=before,shared_after=after,shared_unchanged=before==after,
    actual_shared_TYPEC='m',future_builtin='command-only private header, no config activation',
    files={name:sha(HERE/name) for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h','samurai-apsd-backend.h','samurai-usb-input.c','samurai-apsd-input.inc','samurai-usb-input-decode.h']},
    headers={name:sha(path) for name,path in headers.items()},Image_or_module_linked=False,phone_accessed=False,SDK_invoked=False)
with (HERE/'build-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=result['passed'],phases=phases,objects=result['objects'],shared_unchanged=before==after)))
if not result['passed']:
    for path in OUT.glob('*.stderr'):print(path.name,path.read_text()[-2500:])
    raise SystemExit(1)
