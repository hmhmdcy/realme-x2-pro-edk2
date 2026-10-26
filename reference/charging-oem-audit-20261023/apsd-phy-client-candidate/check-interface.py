"""Relocatable interface check only; never a kernel Image or loadable module."""
from pathlib import Path
import difflib,hashlib,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent;PHY=HERE.parent/'apsd-phy-withdrawal-candidate';OLD=HERE.parent/'apsd-pd5v-client-bridge-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=json.loads((HERE/'build-result.json').read_bytes());pb=json.loads((PHY/'build-result.json').read_bytes())
assert build['passed'] and pb['passed'] and build['shared_unchanged']
for name,digest in build['sources'].items():assert sha(HERE/name)==digest
for name,digest in pb['files'].items():assert sha(PHY/name)==digest
out=Path(build['private_output']);owner=out/'owner-future-builtin.o';phy=Path(pb['private_build'])/'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.o'
pd=Path(build['unchanged_PD_object_reused']['path'])
assert sha(owner)==build['objects'][owner.name] and sha(phy)==pb['object_sha256'] and sha(pd)==build['unchanged_PD_object_reused']['sha256']
target=out/'private-interface-only.o';assert not target.exists()
command=['aarch64-linux-gnu-ld','-r','--fatal-warnings','-o',str(target),str(owner),str(phy),str(pd)]
child=subprocess.run(command,capture_output=True,text=True);assert child.returncode==0 and not child.stderr,(child.returncode,child.stderr)
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines()
internal=[line for line in undefined if any(prefix in line for prefix in ['qcom_snps_hsphy_window_','qcom_pmic_typec_5v_','samurai_pd5v_'])]
assert not internal,internal
defined=subprocess.check_output(['aarch64-linux-gnu-nm','--defined-only',str(target)],text=True)
expected=['qcom_snps_hsphy_window_client_register','qcom_snps_hsphy_window_client_unregister','qcom_snps_hsphy_window_begin','qcom_snps_hsphy_window_end','qcom_snps_hsphy_window_status',
          'qcom_pmic_typec_5v_status','qcom_pmic_typec_5v_acquire','samurai_pd5v_validate','samurai_pd5v_release']
assert all(any(line.endswith(' T '+name) for line in defined.splitlines()) for name in expected)
with tempfile.TemporaryDirectory(prefix='samurai-phy-client-patch-') as directory:
    root=Path(directory);path=root/'drivers/usb/dwc3';path.mkdir(parents=True)
    for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h','Kconfig.fragment']:(path/name).write_bytes((OLD/name).read_bytes())
    patch=subprocess.run(['patch','--fuzz=0','-p1','-i',str(HERE/'phy-client.patch')],cwd=root,capture_output=True,text=True)
    assert patch.returncode==0,patch.stderr
    assert all((path/name).read_bytes()==(HERE/name).read_bytes() for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h','Kconfig.fragment'])
result=dict(passed=True,relocatable_internal_interface_only=True,command=command,original_child_terminal=True,returncode=child.returncode,
    input_objects={str(p):sha(p) for p in [owner,phy,pd]},result_sha256=sha(target),result_bytes=target.stat().st_size,
    nine_expected_internal_definitions=expected,unresolved_internal_symbols=internal,remaining_kernel_imports=len(undefined),patch_fuzz0_exact=True,
    actual_shared_TYPEC='m',future_builtin_command_view_only=True,Image_or_module_linked=False,phone_accessed=False,attempt_gate_enabled=False)
with (HERE/'interface-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,internal_definitions=len(expected),unresolved_internal=0,Image_or_module_linked=False,phone_accessed=False)))
