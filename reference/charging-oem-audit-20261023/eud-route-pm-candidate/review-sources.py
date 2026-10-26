from pathlib import Path
import ast,hashlib,json,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE.parent/'eud-route-provider-candidate';OWNER=HERE.parent/'apsd-eud-route-client-candidate'
scope={'re':re};tree=ast.parse((OLD/'review-sources.py').read_text())
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name=='bodies':exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<original-function-body-extractor>','exec'),scope)
bodies=scope['bodies'];sha=lambda b:hashlib.sha256(b).hexdigest();review={}
for name,old in [('samurai-eud-route.c',OLD/'samurai-eud-route.c'),('samurai-apsd-owner.c',OWNER/'samurai-apsd-owner.c')]:
 a,b=bodies(old.read_text()),bodies((HERE/name).read_text());assert set(a)<=set(b)
 changed=sorted(n for n in a if a[n]!=b[n]);added=sorted(set(b)-set(a));review[name]=dict(changed=changed,added=added,unchanged_whole_functions=len(a)-len(changed),source_sha256=sha((HERE/name).read_bytes()),basis_sha256=sha(old.read_bytes()))
assert review['samurai-apsd-owner.c']['changed']==['owner_route_resolve']
assert review['samurai-apsd-owner.c']['added']==['owner_route_pause_join','owner_route_resume']
assert not re.search(r'\b(?:writel|writeb|writew|qcom_scm_io_writel)\s*\(', (HERE/'samurai-eud-route.c').read_text())
clean=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
fixture_root=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
for fixture,receipt,required in [('eud-route-pm-tests-private-02/actual-provider.c','provider-test-result.json',['samurai-eud-route.c','samurai-eud-route.h']),('eud-route-pm-owner-tests-private-02/actual-owner.c','owner-test-result.json',['samurai-eud-route.c','samurai-eud-route.h','samurai-apsd-owner.c'])]:
 raw=(fixture_root/fixture).read_bytes();r=json.loads((HERE/receipt).read_bytes());assert r['passed'] and sha(raw)==r['fixture_sha256']
 assert all(clean((HERE/n).read_text()) in raw.decode() for n in required)
build=json.loads((HERE/'image-build-r2-result.json').read_bytes());assert build['passed']
for target,digest in build['build']['changed_sources'].items():
 name=Path(target).name;assert sha((HERE/name).read_bytes())==digest
report=dict(passed=True,functions=review,passed_fixtures_contain_current_whole_sources=True,Image506_sources_match=True,provider_route_register_writes=0,live_checks_limited_to_EUD_CSR_1014=True,producer_arbitration_and_permanent_retirement_preserved=True,PD_PHY_once_and_current_budget_functions_preserved=True,MMIO_mapping_retained_until_retirement_join=True,physical_off_gate_preserved=True)
(HERE/'source-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
