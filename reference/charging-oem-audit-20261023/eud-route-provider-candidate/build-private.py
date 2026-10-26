"""Actual provider and three paired producers, with on/off object checks."""
from pathlib import Path
import hashlib,importlib.util,json,os,shlex,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];HANDOFF=HERE.parent/'eud-route-handoff-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tested=json.loads((HERE/'test-result.json').read_bytes());assert tested['passed'] and all(sha(HERE/n)==h for n,h in tested['files'].items())
sources=json.loads((HERE/'source-result.json').read_bytes())
assert all(sha(HERE/name)==row['sha256'] and sha(Path(row['original']))==row['original_sha256'] for name,row in sources['files'].items())
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_guard_route_producers',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);BUILD=m.mounted_build();SOURCE=(BUILD/'source').resolve()
OUT=Path('/home/cy122/charging-management-20261023/eud-route-provider-objects-01');assert not OUT.exists()
specs=[('provider','drivers/firmware/efi','efi',HERE/'samurai-eud-route.c',True)]
for name,rel,base in [('COM','drivers/tty/serial','eud'),('earlycon','drivers/tty/serial','eud_earlycon'),('qcom-EUD','drivers/usb/misc','qcom_eud')]:
    for enabled in [True,False]:specs.append((name+('-on' if enabled else '-off'),rel,base,HERE/(base+'.c'),enabled))
tracked=[BUILD/'.config',BUILD/'include/generated/autoconf.h',BUILD/'Module.symvers']
for _,rel,base,_,_ in specs:
    tracked += [BUILD/rel/('.'+base+'.o.cmd'),SOURCE/rel/(base+'.c')]
tracked=sorted(set(tracked));before={str(p):sha(p) for p in tracked}
OUT.mkdir();(OUT/'tmp').mkdir();include=OUT/'include';(include/'linux/usb').mkdir(parents=True);(include/'linux/firmware').mkdir(parents=True)
(include/'linux/usb/samurai-eud-route.h').write_bytes((HERE/'samurai-eud-route.h').read_bytes())
(include/'eud-com-window.h').write_bytes((REF/'charging-session-20261023/eud-runtime-window-candidate-r2/eud-com-window.h').read_bytes())
for name in ['samurai-eud-handoff.h','samurai-eud-handoff-wire.h']:(include/'linux/firmware'/name).write_bytes((HANDOFF/name).read_bytes())
commands=[];children=[];phases=[]
for name,rel,base,source,enabled in specs:
    saved=BUILD/rel/('.'+base+'.o.cmd');line=saved.read_text().splitlines()[0];assert line.startswith('savedcmd_'+rel+'/'+base+'.o := ')
    argv=shlex.split(line.split(' := ',1)[1]);assert argv[0]=='aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in argv and argv[-1]==str(SOURCE/rel/(base+'.c'))
    argv[-1]=str(source);argv[argv.index('-o')+1]=str(OUT/(name+'.o'))
    argv=[('-Wp,-MMD,'+str(OUT/(name+'.d'))) if word.startswith('-Wp,-MMD,') else word for word in argv]
    argv[1:1]=['-Werror','-I'+str(include),'-I'+str(source.parent),'-I'+str(SOURCE/rel)]
    if enabled:argv[1:1]=['-DCONFIG_QCOM_SAMURAI_EUD_ROUTE=1','-DCONFIG_QCOM_SAMURAI_EUD_HANDOFF=1']
    if name=='provider':
        argv=[('-DKBUILD_BASENAME="samurai_eud_route"') if word.startswith('-DKBUILD_BASENAME=') else word for word in argv]
        argv=[('-DKBUILD_MODNAME="samurai_eud_route"') if word.startswith('-DKBUILD_MODNAME=') else word for word in argv]
    commands.append(dict(name=name,enabled=enabled,argv=argv))
    child=subprocess.Popen(argv,cwd=BUILD,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE);children.append((name,child))
for name,child in children:
    try:stdout,stderr=child.communicate()
    finally:child.wait()
    (OUT/(name+'.stdout')).write_bytes(stdout);(OUT/(name+'.stderr')).write_bytes(stderr)
    phases.append(dict(name=name,pid=child.pid,original_child_terminal=True,returncode=child.returncode,diagnostic_bytes=len(stderr)))
after={str(p):sha(p) for p in tracked}
result=dict(passed=before==after and all(p['returncode']==p['diagnostic_bytes']==0 for p in phases),private_output=str(OUT),phases=phases,commands=commands,
    before=before,after=after,shared_unchanged=before==after,objects={p.name:sha(p) for p in OUT.glob('*.o')},
    files={name:sha(HERE/name) for name in ['samurai-eud-route.c','samurai-eud-route.h','eud.c','eud_earlycon.c','qcom_eud.c']},
    kernel_options_command_only=True,shared_config_changed=False,Image_or_module_linked=False,phone_accessed=False,SDK_invoked=False)
if result['passed']:
    off_imports={name:subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(OUT/(name+'.o'))],text=True).splitlines() for name in ['COM-off','earlycon-off','qcom-EUD-off']}
    assert not any('samurai_eud_' in line for lines in off_imports.values() for line in lines)
    h=json.loads((HANDOFF/'build-r2-result.json').read_bytes());assert h['passed']
    receiver=Path(h['private_output'])/'samurai-eud-handoff.o';assert sha(receiver)==h['receiver_sha256']
    objects=[OUT/(name+'.o') for name in ['provider','COM-on','earlycon-on','qcom-EUD-on']]+[receiver]
    target=OUT/'private-interface-only.o';link=['aarch64-linux-gnu-ld','-r','--fatal-warnings','-o',str(target),*[str(p) for p in objects]]
    linked=subprocess.run(link,capture_output=True,text=True);assert linked.returncode==0 and not linked.stderr,(linked.returncode,linked.stderr)
    undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines()
    internal=[line for line in undefined if 'samurai_eud_' in line];assert not internal,internal
    definitions=subprocess.check_output(['aarch64-linux-gnu-nm','--defined-only',str(OUT/'provider.o')],text=True)
    assert '__export_symbol_samurai_eud_producer_claim' in definitions and '__export_symbol_samurai_eud_producer_release' in definitions
    result.update(default_off_new_imports_absent=True,producer_exports_present=True,partial_interface_link_command=link,
        partial_interface_linked=True,full_Image_or_module_linked=False,partial_sha256=sha(target),unresolved_internal=internal,
        reused_handoff_receiver=dict(path=str(receiver),sha256=sha(receiver)))
with (HERE/'build-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=result['passed'],phases=phases,shared_unchanged=before==after,default_off_new_imports_absent=result.get('default_off_new_imports_absent'))))
if not result['passed']:
    for path in OUT.glob('*.stderr'):
        if path.stat().st_size:print(path.name,path.read_text()[-4000:])
    raise SystemExit(1)
