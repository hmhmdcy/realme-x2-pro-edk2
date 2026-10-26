"""Only the reviewed EFI usability check changes: reuse BDS and EFI objects."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tested=json.loads((HERE/'test-result.json').read_bytes());assert tested['passed'] and all(sha(HERE/n)==h for n,h in tested['files'].items())
old=json.loads((HERE/'build-result.json').read_bytes());assert old['passed']
unchanged=['PlatformBm.c.candidate','efi.c','samurai-eud-handoff.h','samurai-eud-handoff-wire.h','firmware-record-functions.inc']
assert all(sha(HERE/name)==old['files'][name] for name in unchanged)
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_guard_handoff_receiver_r2',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);BUILD=m.mounted_build()
OUT=Path('/home/cy122/charging-management-20261023/eud-route-handoff-kernel-r2-01');assert not OUT.exists()
oldout=Path(old['private_output']);reused={name:oldout/name for name in ['PlatformBm.o','efi.o']}
assert all(sha(path)==old['objects'][name] for name,path in reused.items())
paths=[Path(name) for name in old['original_shared_after']]+list(reused.values())
before={str(p):sha(p) for p in paths};OUT.mkdir();(OUT/'tmp').mkdir();include=OUT/'include/linux/firmware';include.mkdir(parents=True)
for name in ['samurai-eud-handoff.h','samurai-eud-handoff-wire.h']:(include/name).write_bytes((HERE/name).read_bytes())
argv=list(old['commands'][2]);assert argv[-1]==str(HERE/'samurai-eud-handoff.c')
argv[argv.index('-o')+1]=str(OUT/'samurai-eud-handoff.o')
argv=[('-Wp,-MMD,'+str(OUT/'samurai-eud-handoff.d')) if word.startswith('-Wp,-MMD,') else word for word in argv]
argv=[('-I'+str(OUT/'include')) if word=='-I'+str(oldout/'include') else word for word in argv]
phases=[]
def run(name,command,cwd):
    child=subprocess.Popen(command,cwd=cwd,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();child.wait();(OUT/(name+'.stdout')).write_bytes(stdout);(OUT/(name+'.stderr')).write_bytes(stderr)
    row=dict(name=name,pid=child.pid,terminal=True,returncode=child.returncode,diagnostic_bytes=len(stderr));phases.append(row)
    assert child.returncode==0 and not stderr,(row,stderr.decode())
run('receiver-W1',argv,BUILD)
target=OUT/'kernel-interface-only.o';link=['aarch64-linux-gnu-ld','-r','--fatal-warnings','-o',str(target),str(reused['efi.o']),str(OUT/'samurai-eud-handoff.o')]
run('kernel-interface',link,OUT)
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines();assert not any('samurai_eud_handoff_' in line for line in undefined)
after={str(p):sha(p) for p in paths};assert before==after
result=dict(passed=True,private_output=str(OUT),phases=phases,command=argv,link_command=link,
    receiver_sha256=sha(OUT/'samurai-eud-handoff.o'),partial_kernel_interface_sha256=sha(target),
    reused_objects={name:dict(path=str(path),sha256=sha(path)) for name,path in reused.items()},
    current_source_files={name:sha(HERE/name) for name in [*unchanged,'samurai-eud-handoff.c']},
    before=before,after=after,shared_unchanged=True,original_BDS_import_check_reused=True,
    Image_or_firmware_linked=False,phone_accessed=False,actual_EFI_table_usability_policy_used=True,route_authorization=False)
with (HERE/'build-r2-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,only_receiver_recompiled=True,phases=phases,shared_unchanged=True)))
