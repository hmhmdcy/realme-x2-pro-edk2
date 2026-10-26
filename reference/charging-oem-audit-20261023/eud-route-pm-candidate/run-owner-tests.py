from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-eud-route-client-candidate';ROUTE=HERE.parent/'eud-route-provider-candidate'
clean=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
builder=(OLD/'run-tests.py').read_text().split("\nflags=['-std=gnu11'",1)[0]
scope={'__file__':str(OLD/'run-tests.py'),'__name__':'fixture_only'};exec(compile(builder,'<existing-whole-owner-PD-PHY-route-fixture>','exec'),scope)
fixture=scope['fixture'];oldmain=(OLD/'test-client.c').read_text();assert fixture.endswith(oldmain);fixture=fixture[:-len(oldmain)]
def replace(before,after):
 global fixture
 assert fixture.count(before)==1,(before[:80],fixture.count(before));fixture=fixture.replace(before,after)
replace(clean((ROUTE/'samurai-eud-route.h').read_text()),(HERE/'route-mmio-test.inc').read_text()+'\n'+clean((HERE/'samurai-eud-route.h').read_text()))
replace(clean((ROUTE/'samurai-eud-route.c').read_text()),clean((HERE/'samurai-eud-route.c').read_text()))
replace(clean((OLD/'samurai-apsd-owner.c').read_text()),clean((HERE/'samurai-apsd-owner.c').read_text()))
replace('struct dev_pm_ops {int(*prepare)(struct device*);};','struct dev_pm_ops {int(*prepare)(struct device*);void(*complete)(struct device*);};')
replace(' route_evidence_error=mock_apsd_writes=0;', ' assert(!route_region_held&&!route_mapping_live);route_region_fail=route_mapping_fail=route_change_on_second=false;route_csr_reads=route_live_csr=route_csr_second=0;\n route_evidence_error=mock_apsd_writes=0;')
oldmain=oldmain[:oldmain.index(' setup(true);prepared();wire(true);tick();o=bound_owner;assert(o->route_lease.client&&mock_apsd_writes==1);')]
oldmain=oldmain.replace('int main(void)','static void original_eight_cases(void)',1)+' assert(!APSD_writes);\n}\n'
fixture+='\n'+oldmain+'\n'+(HERE/'test-owner-pm.c').read_text()+'\nint main(void){original_eight_cases();pm_owner_cases();return 0;}\n'
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-route-pm-owner-tests-private-02');assert not private.exists();private.mkdir()
(private/'actual-owner.c').write_text(fixture)
flags=['-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
built=subprocess.run(['gcc',*flags,str(private/'actual-owner.c'),'-o',str(private/'test')],capture_output=True,text=True)
(private/'build.stdout').write_text(built.stdout);(private/'build.stderr').write_text(built.stderr);assert built.returncode==0,built.stderr
run=subprocess.run([str(private/'test')],capture_output=True,text=True,timeout=35)
(private/'run.stdout').write_text(run.stdout);(private/'run.stderr').write_text(run.stderr);assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
groups=run.stdout.splitlines();assert len(groups)==13 and not run.stderr
report=dict(passed=True,groups=groups,actual_whole_owner_PD_PHY_route_C=True,driver_core_scheduling_and_MMIO_edges_modeled=True,phone_accessed=False,fixture_sha256=hashlib.sha256(fixture.encode()).hexdigest())
(HERE/'owner-test-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,groups=len(groups))))
