from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent;HANDOFF=HERE.parent/'eud-route-handoff-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
# Reuse the real wire/BDS/EFI receiver fixture, not a fake route permission.
builder=(HANDOFF/'run-tests.py').read_text().split("flags=['-std=gnu11'",1)[0]
scope={'__file__':str(HANDOFF/'run-tests.py'),'__name__':'fixture_only'};exec(compile(builder,'<existing-handoff-fixture>','exec'),scope)
fixture=scope['fixture'].replace('int main(void)','int prior_handoff_tests(void)',1)
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-route-provider-source-private-01')
next_arg=(private/'next-arg.actual.c.inc').read_text()
boundary=(HERE/'test-kernel-boundary.inc').read_text().replace('/* ACTUAL_NEXT_ARG */',next_arg)
clean=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
boundary=boundary.replace('/* ACTUAL_ROUTE_API */',clean((HERE/'samurai-eud-route.h').read_text()))
boundary=boundary.replace('/* ACTUAL_ROUTE_PROVIDER */',clean((HERE/'samurai-eud-route.c').read_text()))
fixture+='\n'+boundary+'\n'+(HERE/'test-route.c').read_text()
flags=['-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread','-no-pie']
with tempfile.TemporaryDirectory(prefix='samurai-real-EUD-route-') as directory:
    root=Path(directory);code=root/'actual.c';code.write_text(fixture);binary=root/'test'
    built=subprocess.run(['gcc',*flags,str(code),'-o',str(binary)],capture_output=True,text=True);assert built.returncode==0,built.stderr
    run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
    groups=[line for line in run.stdout.splitlines() if line.startswith('route: ')];assert len(groups)==12 and not run.stderr
result=dict(passed=True,groups=groups,group_count=len(groups),flags=flags,actual_whole_route_provider_and_handoff_receiver=True,
    prior10_handoff_cases_rerun_as_combined_fixture=True,real_pthread_join_mutex_completion_and_references=True,
    firmware_driver_core_OF_and_mapping_edges_modeled=True,actual_kernel_next_arg_reused=True,
    fixture_sha256=sha(fixture.encode()),files={name:sha((HERE/name).read_bytes()) for name in ['samurai-eud-route.c','samurai-eud-route.h','test-route.c','test-kernel-boundary.inc','run-tests.py']},
    phone_accessed=False,APSD_gate_enabled=False,PM_route_retention_proved=False)
with (HERE/'test-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,route_groups=12,prior_handoff_groups=10,phone_accessed=False)))
