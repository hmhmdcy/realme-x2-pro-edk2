from pathlib import Path
import ast,hashlib,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-final-transfer-candidate'
# Reuse just the checked function extractor; do not execute an earlier audit.
tree=ast.parse((HERE.parent/'eud-route-provider-candidate/review-sources.py').read_text())
scope={};exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.Import(names=[ast.alias(name='re')])]+[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='bodies'],type_ignores=[])),'<existing-function-extractor>','exec'),scope)
bodies=scope['bodies'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old,new=bodies((OLD/'samurai-apsd-owner.c').read_text()),bodies((HERE/'samurai-apsd-owner.c').read_text())
added=set(new)-set(old);changed={name for name in set(old)&set(new) if old[name]!=new[name]};removed=set(old)-set(new)
assert added=={'owner_route_fence','owner_route_release','owner_route_cancel_join','owner_route_resolve'} and not removed,(added,removed)
expected={'owner_free','owner_phy_cancel_join','owner_pd_cancel_join','owner_entry_gate','owner_restore','owner_enter_windows','owner_attempt_validate','owner_work','owner_join','dwc3_apsd_owner_unbind'}
assert changed==expected,changed
with tempfile.TemporaryDirectory(prefix='samurai-owner-route-review-') as directory:
 root=Path(directory)
 for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h']:
  target=root/'drivers/usb/dwc3'/name;target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes((OLD/name).read_bytes())
 child=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'route-client.patch')],cwd=root,capture_output=True,text=True)
 assert child.returncode==0 and 'offset' not in child.stdout.lower() and 'fuzz' not in child.stdout.lower(),(child.returncode,child.stdout,child.stderr)
 assert all((root/'drivers/usb/dwc3'/name).read_bytes()==(HERE/name).read_bytes() for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h'])
source=(HERE/'samurai-apsd-owner.c').read_text()
assert 'eud_com_' not in source and 'o->eud' not in source
assert new['owner_enter_windows'].index('samurai_eud_route_begin')<new['owner_enter_windows'].index('dwc3_gadget_window_begin')<new['owner_enter_windows'].index('qcom_snps_hsphy_window_begin')
assert new['owner_restore'].index('if (o->phy_error)')<new['owner_restore'].index('qcom_snps_hsphy_window_end')
assert new['owner_restore'].index('qcom_snps_hsphy_window_end')<new['owner_restore'].index('dwc3_gadget_window_end')<new['owner_restore'].index('samurai_eud_route_end')<new['owner_restore'].index('pm_runtime_put')
result=dict(passed=True,added_functions=sorted(added),changed_functions=sorted(changed),unchanged_functions=len(set(old)&set(new))-len(changed),patch_fuzz=0,patch_outputs_exact=True,
 legacy_COM_calls_absent=True,entry_and_reverse_restoration_order_verified=True,failed_PHY_restore_automatic_retry_fenced=True,
 transfer_once_PD_and_original_budget_math_unchanged=True,phone_accessed=False,installed=False,
 files={name:sha(HERE/name) for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h','route-client.patch','route-client-functions.inc','Kconfig.fragment']})
with (HERE/'source-review.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,changed=sorted(changed),unchanged=result['unchanged_functions'],patch_fuzz=0)))
