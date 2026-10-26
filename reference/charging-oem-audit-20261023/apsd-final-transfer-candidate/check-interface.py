"""Four real private objects; interface linkage, not a bootable kernel."""
from pathlib import Path
import difflib,hashlib,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent;OWNER=HERE.parent/'apsd-phy-client-candidate';PHY=HERE.parent/'apsd-phy-withdrawal-candidate';BUS=HERE.parent/'apsd-input-backend-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=json.loads((HERE/'build-result.json').read_bytes());pb=json.loads((PHY/'build-result.json').read_bytes());old=json.loads((OWNER/'build-result.json').read_bytes())
assert b['passed'] and pb['passed'] and old['passed'] and b['shared_unchanged']
assert all(sha(HERE/name)==digest for name,digest in b['files'].items())
assert all(sha(PHY/name)==digest for name,digest in pb['files'].items())
out=Path(b['private_output']);owner=out/'owner-future-builtin.o';input_obj=out/'input.o'
phy=Path(pb['private_build'])/'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.o';pd=Path(old['unchanged_PD_object_reused']['path'])
assert sha(owner)==b['objects'][owner.name] and sha(input_obj)==b['objects'][input_obj.name]
assert sha(phy)==pb['object_sha256'] and sha(pd)==old['unchanged_PD_object_reused']['sha256']
target=out/'private-interface-only.o';assert not target.exists()
command=['aarch64-linux-gnu-ld','-r','--fatal-warnings','-o',str(target),str(owner),str(input_obj),str(phy),str(pd)]
child=subprocess.run(command,capture_output=True,text=True);assert child.returncode==0 and not child.stderr,(child.returncode,child.stderr)
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines()
prefixes=['qcom_snps_hsphy_window_','qcom_pmic_typec_5v_','samurai_pd5v_','samurai_apsd_bus_']
internal=[line for line in undefined if any(prefix in line for prefix in prefixes)];assert not internal,internal
expected=['qcom_snps_hsphy_window_client_register','qcom_snps_hsphy_window_client_unregister','qcom_snps_hsphy_window_begin',
    'qcom_snps_hsphy_window_end','qcom_snps_hsphy_window_status','qcom_pmic_typec_5v_status','qcom_pmic_typec_5v_acquire',
    'samurai_pd5v_validate','samurai_pd5v_release','samurai_apsd_bus_register','samurai_apsd_bus_unregister']
defined=subprocess.check_output(['aarch64-linux-gnu-nm','--defined-only',str(target)],text=True).splitlines()
assert all(any(line.endswith(' T '+name) for line in defined) for name in expected)
patch=''
for origin,name,target_name in [(OWNER,'samurai-apsd-owner.c','drivers/usb/dwc3/samurai-apsd-owner.c'),
    (BUS,'samurai-apsd-input.inc','drivers/power/supply/samurai-apsd-input.inc'),
    (BUS,'samurai-apsd-backend.h','include/linux/usb/samurai-apsd-backend.h')]:
    patch+=''.join(difflib.unified_diff((origin/name).read_text().splitlines(True),(HERE/name).read_text().splitlines(True),
        fromfile='a/'+target_name,tofile='b/'+target_name))
with (HERE/'final-transfer.patch').open('x') as stream:stream.write(patch)
with tempfile.TemporaryDirectory(prefix='samurai-final-transfer-patch-') as directory:
    root=Path(directory)
    for origin,name,target_name in [(OWNER,'samurai-apsd-owner.c','drivers/usb/dwc3/samurai-apsd-owner.c'),
        (BUS,'samurai-apsd-input.inc','drivers/power/supply/samurai-apsd-input.inc'),
        (BUS,'samurai-apsd-backend.h','include/linux/usb/samurai-apsd-backend.h')]:
        path=root/target_name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((origin/name).read_bytes())
    applied=subprocess.run(['patch','--fuzz=0','-p1','-i',str(HERE/'final-transfer.patch')],cwd=root,capture_output=True,text=True)
    assert applied.returncode==0,applied.stderr
    for name,target_name in [('samurai-apsd-owner.c','drivers/usb/dwc3/samurai-apsd-owner.c'),
        ('samurai-apsd-input.inc','drivers/power/supply/samurai-apsd-input.inc'),('samurai-apsd-backend.h','include/linux/usb/samurai-apsd-backend.h')]:
        assert (root/target_name).read_bytes()==(HERE/name).read_bytes()
result=dict(passed=True,relocatable_interface_only=True,command=command,returncode=child.returncode,
    input_objects={str(p):sha(p) for p in [owner,input_obj,phy,pd]},result_sha256=sha(target),expected_internal_definitions=expected,
    unresolved_internal_symbols=internal,remaining_kernel_imports=len(undefined),patch_fuzz0_exact=True,
    actual_shared_TYPEC='m',future_builtin_command_view_only=True,Image_or_module_linked=False,phone_accessed=False,attempt_gate_enabled=False)
with (HERE/'interface-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,internal_definitions=len(expected),unresolved_internal=0,Image_or_module_linked=False)))
