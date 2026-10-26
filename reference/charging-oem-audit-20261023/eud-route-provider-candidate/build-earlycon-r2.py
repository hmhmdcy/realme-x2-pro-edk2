"""Reuse five successful objects; only earlycon changes after a baseline warning."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];HANDOFF=HERE.parent/'eud-route-handoff-candidate';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((HERE/'build-result.json').read_bytes());assert not old['passed'] and old['shared_unchanged']
reuse=['provider','COM-on','COM-off','qcom-EUD-on','qcom-EUD-off'];assert all(next(r for r in old['phases'] if r['name']==name)['returncode']==0 for name in reuse)
assert all(sha(HERE/name)==old['files'][name] for name in ['samurai-eud-route.c','samurai-eud-route.h','eud.c','qcom_eud.c'])
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_guard_earlycon_route_r2',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);BUILD=m.mounted_build()
OUT=Path('/home/cy122/charging-management-20261023/eud-route-provider-earlycon-r2-01');assert not OUT.exists();OUT.mkdir();(OUT/'tmp').mkdir()
oldout=Path(old['private_output']);original=Path(json.loads((HERE/'source-result.json').read_bytes())['files']['eud_earlycon.c']['original'])
assert sha(original)==sha((BUILD/'source').resolve()/'drivers/tty/serial/eud_earlycon.c')
objects={name:oldout/(name+'.o') for name in reuse};assert all(sha(path)==old['objects'][path.name] for path in objects.values())
paths=[Path(p) for p in old['after']]+list(objects.values());before={str(p):sha(p) for p in paths}
phases=[];commands=[]
for name,template,source in [('baseline-warning','earlycon-on',original),('earlycon-on','earlycon-on',HERE/'eud_earlycon.c'),('earlycon-off','earlycon-off',HERE/'eud_earlycon.c')]:
    argv=list(next(row['argv'] for row in old['commands'] if row['name']==template));argv[-1]=str(source);argv[argv.index('-o')+1]=str(OUT/(name+'.o'))
    argv=[('-Wp,-MMD,'+str(OUT/(name+'.d'))) if word.startswith('-Wp,-MMD,') else word for word in argv]
    commands.append(dict(name=name,argv=argv));child=subprocess.Popen(argv,cwd=BUILD,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();child.wait();(OUT/(name+'.stdout')).write_bytes(stdout);(OUT/(name+'.stderr')).write_bytes(stderr)
    phases.append(dict(name=name,pid=child.pid,terminal=True,returncode=child.returncode,diagnostic_bytes=len(stderr)))
    if name=='baseline-warning':assert child.returncode==1 and b'eud_wait_tx' in stderr and b'unused-function' in stderr
    else:assert child.returncode==0 and not stderr,(child.returncode,stderr.decode());objects[name]=OUT/(name+'.o')
(OUT/'compile-terminal-private.json').write_text(json.dumps(dict(phases=phases,commands=commands),indent=2)+'\n')
off_imports={name:subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(objects[name])],text=True).splitlines() for name in ['COM-off','earlycon-off','qcom-EUD-off']}
assert not any('samurai_eud_' in line for lines in off_imports.values() for line in lines)
h=json.loads((HANDOFF/'build-r2-result.json').read_bytes());receiver=Path(h['private_output'])/'samurai-eud-handoff.o';assert h['passed'] and sha(receiver)==h['receiver_sha256']
linked_objects=[objects[name] for name in ['provider','COM-on','earlycon-on','qcom-EUD-on']]+[receiver]
target=OUT/'private-interface-only.o';link=['aarch64-linux-gnu-ld','-r','--fatal-warnings','-o',str(target),*[str(p) for p in linked_objects]]
linked=subprocess.run(link,capture_output=True,text=True);assert linked.returncode==0 and not linked.stderr,(linked.returncode,linked.stderr)
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines();internal=[line for line in undefined if 'samurai_eud_' in line];assert not internal,internal
definitions=subprocess.check_output(['aarch64-linux-gnu-nm','--defined-only',str(objects['provider'])],text=True)
assert '__export_symbol_samurai_eud_producer_claim' in definitions and '__export_symbol_samurai_eud_producer_release' in definitions
after={str(p):sha(p) for p in paths};assert before==after
result=dict(passed=True,private_output=str(OUT),phases=phases,commands=commands,original_baseline_same_unused_warning_verified=True,
    reused_five_objects=True,objects={name:dict(path=str(path),sha256=sha(path)) for name,path in objects.items()},
    default_off_new_imports_absent=True,producer_exports_present=True,link_command=link,partial_interface_sha256=sha(target),unresolved_internal=internal,
    handoff_receiver_reused=dict(path=str(receiver),sha256=sha(receiver)),before=before,after=after,shared_unchanged=True,
    files={name:sha(HERE/name) for name in ['samurai-eud-route.c','samurai-eud-route.h','eud.c','eud_earlycon.c','qcom_eud.c']},
    Image_or_module_linked=False,phone_accessed=False,APSD_gate_enabled=False)
with (HERE/'build-r2-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,reused_five_objects=True,phases=phases,unresolved_internal=0,shared_unchanged=True)))
