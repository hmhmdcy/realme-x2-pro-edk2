"""Compile only the changed owner; reuse current input and real suppliers."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];OLD=HERE.parent/'apsd-final-transfer-candidate';ROUTE=HERE.parent/'eud-route-provider-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tested=json.loads((HERE/'test-r2-result.json').read_bytes());assert tested['passed'] and tested['group_count']==9
assert all(sha(HERE/name)==digest for name,digest in tested['files'].items())
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_mount_guard_EUD_route_client',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);BUILD=m.mounted_build()
free=shutil.disk_usage('/home/cy122').free;assert free>2*1024**3
old=json.loads((OLD/'build-result.json').read_bytes());current=json.loads((HERE.parent/'apsd-current-usb-integration-candidate/build-result.json').read_bytes())
route=json.loads((ROUTE/'build-r2-result.json').read_bytes());handoff=json.loads((HERE.parent/'eud-route-handoff-candidate/build-r2-result.json').read_bytes())
assert all(row['passed'] for row in [old,current,route,handoff])
assert 'CONFIG_TYPEC_QCOM_PMIC=m' in (BUILD/'.config').read_text().splitlines()
tracked=set(old['shared_after'])|set(current['shared_after'])|set(route['shared_inputs'])
before={name:sha(Path(name)) for name in sorted(tracked)}
OUT=Path('/home/cy122/charging-management-20261023/apsd-eud-route-client-objects-01');assert not OUT.exists();OUT.mkdir();(OUT/'tmp').mkdir()
include=OUT/'include';include.mkdir()
oldout=Path(old['private_output'])
for name,digest in old['headers'].items():
 original=oldout/'include'/name;assert sha(original)==digest
 target=include/name;target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(original.read_bytes())
(include/'samurai-apsd-owner.h').write_bytes((HERE/'samurai-apsd-owner.h').read_bytes())
(include/'linux/usb/samurai-eud-route.h').write_bytes((ROUTE/'samurai-eud-route.h').read_bytes())
future=OUT/'future-builtin-route-profile.h'
future.write_text((oldout/'future-builtin-only.h').read_text()+'\n#define CONFIG_QCOM_SAMURAI_EUD_ROUTE 1\n#define CONFIG_QCOM_SAMURAI_EUD_HANDOFF 1\n#define CONFIG_USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT 1\n')
commands=[];phases=[]
for index,name in enumerate(['owner-current-disabled','owner-builtin-route']):
 argv=list(old['commands'][index]);assert argv[0]=='aarch64-linux-gnu-gcc' and '-Werror' in argv and '-DKBUILD_EXTRA_WARN1' in argv
 argv[-1]=str(HERE/'samurai-apsd-owner.c');argv[argv.index('-o')+1]=str(OUT/(name+'.o'))
 argv=[('-Wp,-MMD,'+str(OUT/(name+'.d'))) if word.startswith('-Wp,-MMD,') else word for word in argv]
 argv=[('-I'+str(include)) if word=='-I'+str(oldout/'include') else '-I'+str(HERE) if word=='-I'+str(OLD) else str(future) if word==str(oldout/'future-builtin-only.h') else word for word in argv]
 commands.append(argv);child=subprocess.Popen(argv,cwd=BUILD,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 stdout,stderr=child.communicate();child.wait();(OUT/(name+'.stdout')).write_bytes(stdout);(OUT/(name+'.stderr')).write_bytes(stderr)
 phases.append(dict(name=name,pid=child.pid,original_child_terminal=True,returncode=child.returncode,diagnostic_bytes=len(stderr)))
 (OUT/'compile-terminal-private.json').write_text(json.dumps(dict(phases=phases,commands=commands),indent=2)+'\n')
 assert child.returncode==0 and not stderr,(name,child.returncode,stderr.decode())
disabled=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(OUT/'owner-current-disabled.o')],text=True)
assert 'samurai_eud_' not in disabled and 'eud_com_' not in disabled
owner_imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(OUT/'owner-builtin-route.o')],text=True)
assert 'eud_com_' not in owner_imports and 'samurai_eud_route_validate' in owner_imports
prior_interface=json.loads((OLD/'interface-result.json').read_bytes())
suppliers={Path(name):digest for name,digest in prior_interface['input_objects'].items() if name.endswith('phy-qcom-snps-femto-v2.o') or name.endswith('pd5v-metadata.o')}
input_path=Path(current['private_output'])/'input.o';suppliers[input_path]=current['input_object_sha256']
provider=Path(route['objects']['provider']['path']);suppliers[provider]=route['objects']['provider']['sha256']
receiver=Path(handoff['private_output'])/'samurai-eud-handoff.o';suppliers[receiver]=handoff['receiver_sha256']
assert len(suppliers)==5 and all(sha(path)==digest for path,digest in suppliers.items())
target=OUT/'private-interface-only.o';command=['aarch64-linux-gnu-ld','-r','--fatal-warnings','-o',str(target),str(OUT/'owner-builtin-route.o'),*[str(path) for path in suppliers]]
link=subprocess.run(command,capture_output=True,text=True)
(OUT/'interface-terminal-private.json').write_text(json.dumps(dict(command=command,returncode=link.returncode,stdout=link.stdout,stderr=link.stderr),indent=2)+'\n')
assert link.returncode==0 and not link.stderr,(link.returncode,link.stderr)
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines()
expected=prior_interface['expected_internal_definitions']+['samurai_eud_route_client_register','samurai_eud_route_client_unregister','samurai_eud_route_begin','samurai_eud_route_validate','samurai_eud_route_end','samurai_eud_route_status','samurai_eud_handoff_copy']
definitions={row.split()[-1] for row in subprocess.check_output(['aarch64-linux-gnu-nm','--defined-only',str(target)],text=True).splitlines()}
assert all(name in definitions for name in expected)
internal=[row for row in undefined if row.split()[-1] in expected or 'eud_com_' in row];assert not internal,internal
after={name:sha(Path(name)) for name in sorted(tracked)};assert before==after
result=dict(passed=True,private_output=str(OUT),phases=phases,commands=commands,
    objects={name:sha(OUT/(name+'.o')) for name in ['owner-current-disabled','owner-builtin-route']},
    current_disabled_no_route_or_COM_imports=True,builtin_legacy_COM_imports_absent=True,
    reused_five_supplier_input_objects={str(path):digest for path,digest in suppliers.items()},
    link_command=command,partial_interface_sha256=sha(target),expected_internal_definitions=expected,unresolved_internal=internal,
    shared_before=before,shared_after=after,shared_unchanged=True,WSL_free_before_bytes=free,
    actual_shared_TYPEC='m',future_builtin_command_view_only=True,Image_or_module_linked=False,phone_accessed=False,
    files={name:sha(HERE/name) for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h','route-client-functions.inc','Kconfig.fragment']})
with (HERE/'build-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,phases=phases,reused_objects=5,internal_APIs=len(expected),shared_unchanged=True)))
