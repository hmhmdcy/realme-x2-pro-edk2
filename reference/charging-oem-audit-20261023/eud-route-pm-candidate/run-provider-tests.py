from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'eud-route-provider-candidate';HANDOFF=HERE.parent/'eud-route-handoff-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest();clean=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
builder=(HANDOFF/'run-tests.py').read_text().split("flags=['-std=gnu11'",1)[0]
scope={'__file__':str(HANDOFF/'run-tests.py'),'__name__':'fixture_only'};exec(compile(builder,'<original-frozen-handoff-fixture>','exec'),scope)
fixture=scope['fixture'].replace('int main(void)','int prior_handoff_tests(void)',1)
boundary=(OLD/'test-kernel-boundary.inc').read_text().replace('/* ACTUAL_NEXT_ARG */',(OLD/'next-arg.actual.c.inc').read_text())
boundary=boundary.replace('struct dev_pm_ops {int(*prepare)(struct device*);};','struct dev_pm_ops {int(*prepare)(struct device*);void(*complete)(struct device*);};')
boundary=boundary.replace('/* ACTUAL_ROUTE_API */',(HERE/'route-mmio-test.inc').read_text()+'\n'+clean((HERE/'samurai-eud-route.h').read_text()))
boundary=boundary.replace('/* ACTUAL_ROUTE_PROVIDER */',clean((HERE/'samurai-eud-route.c').read_text()))
old_tests=(OLD/'test-route.c').read_text().replace('int main(void)','int legacy_route_tests(void)',1)
old_tests=old_tests.replace('owner_ops={owner_get,owner_put,cancel_owner}','owner_ops={.get_unless_zero=owner_get,.put=owner_put,.cancel_join=cancel_owner}')
old_tests=old_tests.replace(' reset();boot_record();producer_ever_granted',' assert(!route_region_held&&!route_mapping_live);route_region_fail=route_mapping_fail=route_change_on_second=false;route_csr_reads=route_live_csr=route_csr_second=0;\n reset();boot_record();producer_ever_granted')
fixture+='\n'+boundary+'\n'+old_tests+'\n'+(HERE/'test-provider-pm.c').read_text()+'\nint main(void){assert(!legacy_route_tests());assert(!run_provider_pm_cases());return 0;}\n'
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-route-pm-tests-private-02');assert not private.exists();private.mkdir()
(private/'actual-provider.c').write_text(fixture)
flags=['-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread','-no-pie']
run=subprocess.run(['gcc',*flags,str(private/'actual-provider.c'),'-o',str(private/'test')],capture_output=True,text=True)
(private/'build.stdout').write_text(run.stdout);(private/'build.stderr').write_text(run.stderr)
assert run.returncode==0,run.stderr
run=subprocess.run([str(private/'test')],capture_output=True,text=True,timeout=35)
(private/'run.stdout').write_text(run.stdout);(private/'run.stderr').write_text(run.stderr);assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
groups=[line for line in run.stdout.splitlines() if line.startswith('route: ')];assert len(groups)==23 and not run.stderr
report=dict(passed=True,groups=groups,actual_whole_provider_C=True,real_pthread_join_and_ref_lifetimes=True,MMIO_resource_and_driver_core_boundaries_modeled=True,phone_accessed=False,fixture_sha256=sha(fixture.encode()))
(HERE/'provider-test-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,groups=len(groups))))
